"""Unit tests for the Generative LLM UI Synthesizer with Deterministic Fallback (R-462).

Exercises:
1. JSX safety and syntax validation (import whitelisting, markdown strip, balanced brackets).
2. Component and data hook prompt synthesis for domain context.
3. Successful bespoke UI synthesis through ModelProvider.
4. Graceful, silent fallback to deterministic Python template on offline / None provider.
5. Graceful fallback on ModelProvider errors, timeouts, or malformed responses.
6. Integration into NextjsWebAdapter.generate(ir, provider=..., prompt=...).
"""

import unittest
from unittest.mock import AsyncMock, patch

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
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.codegen.llm_ui import (
    ALLOWED_IMPORT_PREFIXES,
    build_screen_synthesis_prompt,
    build_ui_synthesis_prompt,
    clean_and_validate_jsx,
    synthesize_overview_page,
    synthesize_overview_page_sync,
    synthesize_screen_page,
    synthesize_screen_page_sync,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsAdminAdapter,
    NextjsWebAdapter,
    _overview_page,
    _public_home_page,
)
from omnistackai_agent_engine.model_gateway.contracts import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelProvider,
    ModelRef,
    TokenUsage,
)
from omnistackai_agent_engine.model_gateway.errors import ProviderTimeoutError


class StubModelProvider:
    """In-memory stub implementing ModelProvider for offline tests."""

    def __init__(self, response_text: str = "", should_fail: bool = False) -> None:
        self.response_text = response_text
        self.should_fail = should_fail
        self.last_request: GenerateRequest | None = None

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.last_request = request
        if self.should_fail:
            raise ProviderTimeoutError("Model timed out")
        return GenerateResponse(
            request_id=request.request_id,
            model=request.model,
            text=self.response_text,
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
            latency_ms=50,
        )


def _make_test_ir() -> ApplicationIR:
    return ApplicationIR(
        name="FleetTrack",
        description="Real-time fleet management system with driver dispatch and fuel logs",
        platforms=(Platform.WEB,),
        entities=(
            Entity(
                name="Vehicle",
                fields=(
                    Field(name="id", type=FieldType.STRING),
                    Field(name="vin", type=FieldType.STRING, required=True),
                    Field(name="model", type=FieldType.STRING),
                    Field(name="status", type=FieldType.STRING),
                ),
            ),
            Entity(
                name="FuelLog",
                fields=(
                    Field(name="id", type=FieldType.STRING),
                    Field(name="gallons", type=FieldType.FLOAT),
                    Field(name="cost", type=FieldType.FLOAT),
                ),
            ),
        ),
        # R-465: real entity-schema APIs so lib/hooks.ts actually exports useListVehicles etc. — the
        # prompt is now grounded in the generated hooks instead of hand-written (drifting) descriptions.
        apis=(
            ApiEndpoint(HttpMethod.GET, "/vehicles", auth=False, response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.POST, "/vehicles", auth=False, request_schema="Vehicle", response_schema="Vehicle"),
            ApiEndpoint(HttpMethod.GET, "/fuel-logs", auth=False, response_schema="FuelLog"),
        ),
        screens=(
            Screen(id="vehicle_list", role="user", components=("list",)),
            Screen(id="new_vehicle", role="admin", components=("form",)),
        ),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.GO,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("user"), Role("admin")),
    )


class TestJSXValidation(unittest.TestCase):
    """Test clean_and_validate_jsx safety checks."""

    def test_strips_markdown_fences(self) -> None:
        raw = '```tsx\n"use client";\nexport default function HomePage() { return <div>Fleet</div>; }\n```'
        valid, cleaned, _ = clean_and_validate_jsx(raw)
        self.assertTrue(valid)
        self.assertFalse(cleaned.startswith("```"))
        self.assertIn('"use client";', cleaned)

    def test_requires_use_client(self) -> None:
        raw = "export default function HomePage() { return <div>Missing use client</div>; }"
        valid, cleaned, reason = clean_and_validate_jsx(raw)
        # Should auto-prepend "use client" or be valid
        self.assertTrue(valid)
        self.assertTrue(cleaned.startswith('"use client";'))

    def test_rejects_empty_content(self) -> None:
        valid, _, reason = clean_and_validate_jsx("   \n  ")
        self.assertFalse(valid)
        self.assertIn("empty", reason.lower())

    def test_rejects_unapproved_external_npm_imports(self) -> None:
        raw = (
            '"use client";\n'
            'import axios from "axios";\n'
            'export default function HomePage() { return <div>Bad</div>; }'
        )
        valid, _, reason = clean_and_validate_jsx(raw)
        self.assertFalse(valid)
        self.assertIn("forbidden import", reason.lower())

    def test_allows_valid_platform_imports(self) -> None:
        raw = (
            '"use client";\n'
            'import Link from "next/link";\n'
            'import { useListVehicles } from "@/lib/hooks";\n'
            'import { StatCard } from "@/components/stat-card";\n'
            'export default function HomePage() { return <div>Good</div>; }'
        )
        valid, cleaned, _ = clean_and_validate_jsx(raw)
        self.assertTrue(valid)
        self.assertIn("useListVehicles", cleaned)


class TestPromptSynthesis(unittest.TestCase):
    """Test build_ui_synthesis_prompt context injection."""

    def test_prompt_includes_domain_entities_and_components(self) -> None:
        ir = _make_test_ir()
        prompt = build_ui_synthesis_prompt(ir, "Build fleet management with vehicle tracking")
        self.assertIn("FleetTrack", prompt)
        self.assertIn("Vehicle", prompt)
        self.assertIn("FuelLog", prompt)
        self.assertIn("useListVehicles", prompt)
        self.assertIn("StatCard", prompt)
        self.assertIn("DataGrid", prompt)
        self.assertIn("Build fleet management with vehicle tracking", prompt)


class TestOverviewPageSynthesis(unittest.TestCase):
    """Test synthesize_overview_page behavior under success and fallback conditions."""

    def test_fallback_when_provider_is_none(self) -> None:
        ir = _make_test_ir()
        # With provider=None, must return the exact deterministic template
        result = synthesize_overview_page_sync(ir, user_prompt="", provider=None)
        expected = _overview_page(ir)
        self.assertEqual(result, expected)

    def test_fallback_when_provider_fails(self) -> None:
        ir = _make_test_ir()
        failing_provider = StubModelProvider(should_fail=True)
        result = synthesize_overview_page_sync(
            ir,
            user_prompt="Build fleet app",
            provider=failing_provider,
        )
        expected = _overview_page(ir)
        self.assertEqual(result, expected)

    def test_fallback_when_model_returns_invalid_jsx(self) -> None:
        ir = _make_test_ir()
        bad_provider = StubModelProvider(
            response_text='import malicious from "hacked-pkg";\nexport default function Bad() {}'
        )
        result = synthesize_overview_page_sync(
            ir,
            user_prompt="Build fleet app",
            provider=bad_provider,
        )
        expected = _overview_page(ir)
        self.assertEqual(result, expected)

    def test_success_with_valid_model_response(self) -> None:
        ir = _make_test_ir()
        valid_custom_jsx = (
            '"use client";\n'
            'import Link from "next/link";\n'
            'import { StatCard } from "@/components/stat-card";\n'
            'import { useListVehicles } from "@/lib/hooks";\n\n'
            'export default function HomePage() {\n'
            '  const vehicles = useListVehicles({ limit: 5 });\n'
            '  return (\n'
            '    <main style={{ padding: 32 }}>\n'
            '      <h1>FleetTrack Command Center</h1>\n'
            '      <StatCard title="Active Vehicles" value="48" change="+3%" />\n'
            '    </main>\n'
            '  );\n'
            '}\n'
        )
        working_provider = StubModelProvider(response_text=valid_custom_jsx)
        result = synthesize_overview_page_sync(
            ir,
            user_prompt="Build fleet app",
            provider=working_provider,
        )
        self.assertIn("FleetTrack Command Center", result)
        self.assertIn("Active Vehicles", result)
        self.assertIn("Mode: LLM-Synthesized Bespoke UI", result)


class TestNextjsAdapterIntegration(unittest.TestCase):
    """Test NextjsWebAdapter integration with the generative UI synthesizer."""

    def test_adapter_generates_with_provider(self) -> None:
        ir = _make_test_ir()
        custom_jsx = (
            '"use client";\n'
            'import { StatCard } from "@/components/stat-card";\n'
            'export default function HomePage() { return <div>Custom Bespoke Fleet UI</div>; }\n'
        )
        provider = StubModelProvider(response_text=custom_jsx)
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir, provider=provider, prompt="Build fleet manager")
        page_file = project.get("app/page.tsx")
        self.assertIsNotNone(page_file)
        self.assertIn("Custom Bespoke Fleet UI", page_file.content)

    def test_adapter_generates_identical_deterministic_output_without_provider(self) -> None:
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project_default = adapter.generate(ir)
        project_explicit_none = adapter.generate(ir, provider=None)
        page_default = project_default.get("app/page.tsx").content
        page_none = project_explicit_none.get("app/page.tsx").content
        self.assertEqual(page_default, page_none)
        # R-541: the public app renders the landing page; the dashboard moved to the admin console.
        self.assertEqual(page_default, _public_home_page(ir))
        self.assertEqual(NextjsAdminAdapter().generate(ir).get("app/page.tsx").content, _overview_page(ir))

    def test_assemble_project_with_provider(self) -> None:
        ir = _make_test_ir()
        custom_jsx = (
            '"use client";\n'
            'import { StatCard } from "@/components/stat-card";\n'
            'export default function HomePage() { return <div>Assembled Monorepo Custom UI</div>; }\n'
        )
        provider = StubModelProvider(response_text=custom_jsx)
        from omnistackai_agent_engine.codegen.assembler import assemble_project
        project = assemble_project(ir, provider=provider, prompt="Assembled prompt")
        web_page = project.get("apps/web/app/page.tsx")
        self.assertIsNotNone(web_page)
        self.assertIn("Assembled Monorepo Custom UI", web_page.content)

    def test_assemble_project_deterministic_without_provider(self) -> None:
        ir = _make_test_ir()
        from omnistackai_agent_engine.codegen.assembler import assemble_project
        project = assemble_project(ir)
        web_page = project.get("apps/web/app/page.tsx")
        self.assertIsNotNone(web_page)
        self.assertIn("FleetTrack", web_page.content)


class TestScreenUiSynthesis(unittest.TestCase):
    def test_build_screen_synthesis_prompt(self) -> None:
        ir = _make_test_ir()
        screen = ir.screens[0]
        prompt = build_screen_synthesis_prompt(screen, ir, "Build a high-end fleet app")
        self.assertIn("Screen ID: vehicle_list", prompt)
        self.assertIn("Entity Vehicle", prompt)
        self.assertIn("useListVehicles", prompt)
        self.assertIn("AVAILABLE PRE-BUILT UI COMPONENTS", prompt)
        self.assertIn("Rating", prompt)
        self.assertIn("Toast", prompt)

    def test_synthesize_screen_page_success(self) -> None:
        ir = _make_test_ir()
        screen = ir.screens[0]
        custom_jsx = (
            '"use client";\n'
            'import { StatCard } from "@/components/stat-card";\n'
            'export default function VehicleListPage() { return <div>Bespoke Vehicles Screen</div>; }\n'
        )
        provider = StubModelProvider(response_text=custom_jsx)
        result = synthesize_screen_page_sync(screen, ir, user_prompt="Prompt", provider=provider)
        self.assertIn("// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI", result)
        self.assertIn("Bespoke Vehicles Screen", result)

    def test_synthesize_screen_page_fallback_on_provider_none(self) -> None:
        ir = _make_test_ir()
        screen = ir.screens[0]
        result = synthesize_screen_page_sync(screen, ir, provider=None)
        self.assertNotIn("// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI", result)
        self.assertIn("VehicleListPage", result)

    def test_synthesize_screen_page_fallback_on_invalid_jsx(self) -> None:
        ir = _make_test_ir()
        screen = ir.screens[0]
        invalid_jsx = 'import axios from "axios"; export default function Broken() { return <div>{; }'
        provider = StubModelProvider(response_text=invalid_jsx)
        result = synthesize_screen_page_sync(screen, ir, provider=provider)
        self.assertNotIn("// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI", result)
        self.assertIn("VehicleListPage", result)


if __name__ == "__main__":
    unittest.main()

