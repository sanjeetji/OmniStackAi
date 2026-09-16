"""R-465: grounded hybrid UI synthesis — the LLM writes the UI over the REAL typed data layer.

Everything here runs against in-memory stub providers: 0 real model calls, 0 network. Covers:
  * grounding: the prompt embeds the real generated hook signatures (parsed from the same generator, so it
    cannot drift), the real component export names, and the real design-token names;
  * no hallucination: an IR without entity-schema APIs gets an explicit "NO data hooks" instruction;
  * the bounded repair loop: validator rejection feeds the reason back and retries; exhaustion and provider
    exceptions fall back to the deterministic template (exceptions never retry);
  * the explicit `synthesize_screens` switch (default off; deterministic output byte-identical);
  * import-whitelist hardening (multi-line imports, react-* packages, require/dynamic import);
  * the flag threads through assemble_project and build_app_from_ir.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    UiSynthesisOutcome,
    assemble_project,
    summarize_components,
    summarize_data_layer,
    summarize_design_tokens,
)
from omnistackai_agent_engine.codegen.auth_guard import needs_auth
from omnistackai_agent_engine.codegen.llm_ui import (
    MARKER_PREFIX,
    build_screen_synthesis_prompt,
    build_ui_synthesis_prompt,
    clean_and_validate_jsx,
    synthesize_overview_page_sync,
    synthesize_screen_page_sync,
)
from omnistackai_agent_engine.codegen.nextjs import _overview_page, _screen_page, render_hooks
from omnistackai_agent_engine.intake import build_app_from_ir
from omnistackai_agent_engine.model_gateway.contracts import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    TokenUsage,
)
from omnistackai_agent_engine.model_gateway.errors import ProviderTimeoutError

VALID_JSX = (
    '"use client";\n'
    'import { useListVehicles } from "@/lib/hooks";\n'
    "export default function Page() {\n"
    "  const { data } = useListVehicles();\n"
    '  return <main style={{ padding: "var(--space-6)" }}>{(data ?? []).length}</main>;\n'
    "}\n"
)
BAD_JSX = (
    '"use client";\n'
    'import axios from "axios";\n'
    "export default function Page() { return <div>x</div>; }\n"
)


class SequenceStubProvider:
    """In-memory ModelProvider returning canned texts in sequence; records every request it sees."""

    def __init__(self, responses: list[str], *, provider_id: str = "stub", fail: bool = False) -> None:
        self._responses = list(responses)
        self._provider_id = provider_id
        self._fail = fail
        self.requests: list[GenerateRequest] = []

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.requests.append(request)
        if self._fail:
            raise ProviderTimeoutError("Model timed out")
        index = min(len(self.requests) - 1, len(self._responses) - 1)
        return GenerateResponse(
            request.request_id, request.model, self._responses[index], FinishReason.STOP, TokenUsage(12, 34), 5
        )


def _make_ir(*, with_apis: bool = True, with_auth: bool = False) -> ApplicationIR:
    apis: tuple[ApiEndpoint, ...] = ()
    if with_apis:
        apis = (
            ApiEndpoint(HttpMethod.GET, "/vehicles", auth=with_auth, response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.POST, "/vehicles", auth=with_auth, request_schema="Vehicle", response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.GET, "/vehicles/{vehicleId}", auth=with_auth, response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.PUT, "/vehicles/{vehicleId}", auth=with_auth, request_schema="Vehicle", response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.DELETE, "/vehicles/{vehicleId}", auth=with_auth, response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.GET, "/vehicles/{vehicleId}/fuel_logs", auth=with_auth, response_schema="FuelLog"),
        )
    return ApplicationIR(
        name="FleetTrack",
        description="Fleet management with vehicles and fuel logs",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("user", ("read", "write")), Role("admin", ("read", "write"))),
        entities=(
            Entity(
                "Vehicle",
                (
                    Field("id", FieldType.UUID),
                    Field("vin", FieldType.STRING),
                    Field("is_active", FieldType.BOOL),
                ),
            ),
            Entity(
                "FuelLog",
                (Field("id", FieldType.UUID), Field("gallons", FieldType.FLOAT)),
                relations=(Relation("vehicle", "Vehicle", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=apis,
        screens=(
            Screen("vehicle_list", "user", components=("list",), actions=("open",)),
            Screen("vehicle_editor", "admin", components=("form",), actions=("save",)),
        ),
    )


class GroundingTests(unittest.TestCase):
    def test_prompt_embeds_real_hook_signatures_not_drifted_ones(self) -> None:
        prompt = build_ui_synthesis_prompt(_make_ir(), "Build a fleet app")
        for real in (
            "useListVehicles(",
            "useVehicle(",
            "useCreateVehicle(",
            "useUpdateVehicle(",
            "useDeleteVehicle(",
            "useListFuelLogsByVehicle(",
            "limit?: number",
            "offset?: number",
            "refetch",
        ):
            self.assertIn(real, prompt, real)
        # The R-462 drift — a hand-written hook shape returning `refresh` and taking page/pageSize *params* —
        # must be gone (the rules may still *forbid* refresh() by name).
        self.assertNotIn("error, refresh }", prompt)
        self.assertNotIn("pageSize?: number", prompt)
        # The screen prompt is grounded by the same blocks.
        screen_prompt = build_screen_synthesis_prompt(_make_ir().screens[0], _make_ir(), "Build a fleet app")
        self.assertIn("useListFuelLogsByVehicle(", screen_prompt)
        self.assertNotIn("error, refresh }", screen_prompt)

    def test_ir_without_entity_apis_gets_explicit_no_hooks_instruction(self) -> None:
        prompt = build_ui_synthesis_prompt(_make_ir(with_apis=False), "Build a fleet app")
        self.assertIn("NO data hooks", prompt)
        self.assertNotIn("useListVehicles", prompt)

    def test_data_layer_summary_cannot_drift_from_render_hooks(self) -> None:
        ir = _make_ir()
        summary = summarize_data_layer(ir)
        hooks_src = render_hooks(ir)
        names = set(re.findall(r"\buse[A-Z]\w*", summary))
        self.assertTrue(names, "expected hook names in the summary")
        for name in names:
            self.assertRegex(hooks_src, rf"(?m)^export function {name}\(", f"{name} is not a real exported hook")
        # Annotated signatures are reproduced verbatim (modulo whitespace collapsing).
        self.assertIn("useListVehicles(initialParams: UseCollectionListParams = {}, options?: ApiOptions): UseCollectionListState<Vehicle>", summary)
        # Mutation hooks are rendered from their real bodies.
        self.assertIn("useCreateVehicle(): { create, mutate: create, loading, error, reset }", summary)
        self.assertIn("(data: Partial<Vehicle>, options?: ApiOptions) => Promise<Vehicle>", summary)
        # Entity interfaces come from the same generator as lib/types.ts.
        self.assertIn("export interface FuelLog {", summary)
        self.assertIn("vehicle_id?: string;", summary)

    def test_prompt_uses_design_tokens_not_hardcoded_hex(self) -> None:
        prompt = build_ui_synthesis_prompt(_make_ir(), "Build a fleet app")
        self.assertIn("var(--color-", prompt)
        self.assertIn("--color-*:", prompt)
        self.assertIn("primary", prompt)
        self.assertIn("--space-*:", prompt)
        for hex_color in ("#0f172a", "#2563eb", "#f8fafc"):
            self.assertNotIn(hex_color, prompt)
        tokens = summarize_design_tokens()
        self.assertIn("surface", tokens)
        self.assertNotIn("#", tokens)

    def test_prompt_lists_real_components_and_auth_only_when_needed(self) -> None:
        plain = _make_ir()
        prompt = build_ui_synthesis_prompt(plain, "Build a fleet app")
        self.assertIn("AVAILABLE PRE-BUILT UI COMPONENTS", prompt)
        for real in ("@/components/stat-card", "DataGrid", "Rating", "useToast", "StatCardValue"):
            self.assertIn(real, prompt, real)
        self.assertFalse(needs_auth(plain))
        self.assertNotIn("@/components/auth-provider", summarize_components(plain))
        self.assertIn("NO auth provider", prompt)
        authed = _make_ir(with_auth=True)
        self.assertTrue(needs_auth(authed))
        self.assertRegex(summarize_components(authed), r"@/components/auth-provider:.*useAuth")
        self.assertIn("useAuth()", build_ui_synthesis_prompt(authed, "Build a fleet app"))
        # The full library (~110 files) must not be lost to the size cap.
        self.assertNotIn("(truncated)", summarize_components(authed))
        self.assertIn("@/components/whiteboard", summarize_components(plain))


class RepairLoopTests(unittest.TestCase):
    def test_repair_succeeds_on_second_attempt_and_feeds_reason_back(self) -> None:
        ir = _make_ir()
        stub = SequenceStubProvider([BAD_JSX, VALID_JSX])
        outcomes: list[UiSynthesisOutcome] = []
        result = synthesize_overview_page_sync(ir, "Build a fleet app", provider=stub, outcomes=outcomes)
        self.assertIn(MARKER_PREFIX, result)
        self.assertEqual(len(stub.requests), 2)
        roles = [m.role for m in stub.requests[1].messages]
        self.assertEqual(roles, [ChatRole.SYSTEM, ChatRole.USER, ChatRole.ASSISTANT, ChatRole.USER])
        self.assertIn("REJECTED", stub.requests[1].messages[-1].content)
        self.assertIn("axios", stub.requests[1].messages[-1].content)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts, outcomes[0].path), ("llm", 2, "app/page.tsx"))
        self.assertIn("attempt 2/3", result)

    def test_exhaustion_falls_back_to_deterministic_template(self) -> None:
        ir = _make_ir()
        stub = SequenceStubProvider([BAD_JSX, BAD_JSX, BAD_JSX])
        outcomes: list[UiSynthesisOutcome] = []
        result = synthesize_overview_page_sync(ir, "Build a fleet app", provider=stub, outcomes=outcomes)
        self.assertEqual(result, _overview_page(ir))
        self.assertNotIn(MARKER_PREFIX, result)
        self.assertEqual(len(stub.requests), 3)
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("deterministic", 3))
        self.assertTrue(outcomes[0].last_reason)
        # JSON-safe, secret-free record.
        self.assertEqual(set(outcomes[0].to_dict()), {"path", "mode", "attempts", "model_id", "last_reason"})

    def test_provider_exception_never_retries(self) -> None:
        ir = _make_ir()
        stub = SequenceStubProvider([VALID_JSX], fail=True)
        outcomes: list[UiSynthesisOutcome] = []
        result = synthesize_screen_page_sync(ir.screens[0], ir, provider=stub, outcomes=outcomes)
        self.assertEqual(result, _screen_page(ir.screens[0], ir))
        self.assertEqual(len(stub.requests), 1)
        self.assertEqual(outcomes[0].last_reason, "ProviderTimeoutError")
        self.assertEqual(outcomes[0].mode, "deterministic")


class SwitchTests(unittest.TestCase):
    def test_default_output_is_byte_identical(self) -> None:
        ir = _make_ir()
        adapter = NextjsWebAdapter()
        a = {f.path: f.content for f in adapter.generate(ir).files()}
        b = {f.path: f.content for f in adapter.generate(ir, synthesize_screens=False).files()}
        self.assertEqual(a, b)

    def test_screens_stay_deterministic_unless_opted_in(self) -> None:
        ir = _make_ir()
        stub = SequenceStubProvider([VALID_JSX])
        project = NextjsWebAdapter().generate(ir, provider=stub, prompt="Build a fleet app")
        self.assertEqual(len(stub.requests), 1)  # overview only
        for screen in ir.screens:
            self.assertEqual(project.get(f"app/{screen.id}/page.tsx").content, _screen_page(screen, ir))

    def test_opt_in_synthesizes_every_screen(self) -> None:
        ir = _make_ir()
        stub = SequenceStubProvider([VALID_JSX])
        outcomes: list[UiSynthesisOutcome] = []
        project = NextjsWebAdapter().generate(
            ir, provider=stub, prompt="Build a fleet app", synthesize_screens=True, ui_outcomes=outcomes
        )
        self.assertEqual(len(stub.requests), 1 + len(ir.screens))
        for screen in ir.screens:
            self.assertIn(MARKER_PREFIX, project.get(f"app/{screen.id}/page.tsx").content)
        self.assertEqual(sorted(o.path for o in outcomes), sorted(["app/page.tsx", *[f"app/{s.id}/page.tsx" for s in ir.screens]]))
        self.assertTrue(all(o.mode == "llm" for o in outcomes))

    def test_flag_threads_through_assemble_and_build(self) -> None:
        ir = _make_ir()
        stub = SequenceStubProvider([VALID_JSX])
        outcomes: list[UiSynthesisOutcome] = []
        project = assemble_project(ir, provider=stub, prompt="p", synthesize_screens=True, ui_outcomes=outcomes)
        self.assertIn(MARKER_PREFIX, project.get("apps/web/app/vehicle_list/page.tsx").content)
        self.assertTrue(outcomes)
        # Without a provider the flag is a silent no-op.
        plain = assemble_project(ir, synthesize_screens=True)
        self.assertNotIn(MARKER_PREFIX, plain.get("apps/web/app/vehicle_list/page.tsx").content)
        with tempfile.TemporaryDirectory() as tmp:
            built = build_app_from_ir(
                ir, tmp, author_name="sanjeetji", author_email="sk698166@gmail.com",
                provider=SequenceStubProvider([VALID_JSX]), synthesize_screens=True, ui_outcomes=[],
            )
            page = Path(built.target_dir) / "apps" / "web" / "app" / "vehicle_editor" / "page.tsx"
            self.assertIn(MARKER_PREFIX, page.read_text())


class ImportHardeningTests(unittest.TestCase):
    def _valid_with(self, imports: str) -> tuple[bool, str]:
        raw = f'"use client";\n{imports}\nexport default function Page() {{ return <div>ok</div>; }}\n'
        valid, _, reason = clean_and_validate_jsx(raw)
        return valid, reason

    def test_exact_react_packages_allowed_but_react_star_rejected(self) -> None:
        self.assertTrue(self._valid_with('import { useState } from "react";')[0])
        self.assertTrue(self._valid_with('import { createPortal } from "react-dom";')[0])
        valid, reason = self._valid_with('import { FaCar } from "react-icons/fa";')
        self.assertFalse(valid)
        self.assertIn("react-icons/fa", reason)

    def test_multiline_named_import_is_checked(self) -> None:
        valid, reason = self._valid_with('import {\n  get,\n  post\n} from "axios";')
        self.assertFalse(valid)
        self.assertIn("axios", reason)

    def test_require_and_dynamic_import_rejected(self) -> None:
        self.assertFalse(self._valid_with('const axios = require("axios");')[0])
        self.assertFalse(self._valid_with('const mod = import("axios");')[0])


if __name__ == "__main__":
    unittest.main()
