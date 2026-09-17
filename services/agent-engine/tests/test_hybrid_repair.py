"""R-466: compile-level repair for LLM-written UI files (codegen/hybrid_repair.py).

Stub providers, a fake compiler runner and temp repos: 0 model calls, 0 toolchain, 0 network.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    MARKER_PREFIX,
    CompileRepairReport,
    LlmFileSpec,
    UiSynthesisOutcome,
    build_repair_diff,
    compile_and_repair,
    compile_and_repair_sync,
    compile_errors_message,
    llm_file_specs,
    repair_compiled_files,
)
from omnistackai_agent_engine.codegen.nextjs import _overview_page, _screen_page
from omnistackai_agent_engine.edit.apply import apply_diff
from omnistackai_agent_engine.edit.diff import ChangeKind
from omnistackai_agent_engine.model_gateway.contracts import ChatRole
from omnistackai_agent_engine.model_gateway.errors import ProviderHTTPError
from omnistackai_agent_engine.verify import CompileError, parse_tsc_output

_VALID_PAGE = '''"use client";
import { useListPosts } from "@/lib/hooks";

export default function Page() {
  const { items, loading } = useListPosts();
  return <main>{loading ? "..." : items.length}</main>;
}
'''
_INVALID_PAGE = '''"use client";
import axios from "axios";
export default function Page() { return <main>{axios ? 1 : 0}</main>; }
'''
_PAGE_ERRORS = "app/page.tsx(5,11): error TS2339: Property 'refresh' does not exist on type 'UseListPosts'.\n"


class SequenceStubProvider:
    provider_id = "stub"

    def __init__(self, responses: list[str], *, fail: Exception | None = None) -> None:
        self._responses = list(responses)
        self._fail = fail
        self.requests: list = []

    async def generate(self, request):  # noqa: ANN001
        self.requests.append(request)
        if self._fail is not None:
            raise self._fail
        return SimpleNamespace(text=self._responses.pop(0))


class _FakeRunner:
    def __init__(self, steps: list) -> None:
        self._steps = list(steps)
        self.calls = 0

    def __call__(self, argv, cwd, timeout_seconds):  # noqa: ANN001
        self.calls += 1
        returncode, stdout = self._steps.pop(0)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def _ir():
    return example_ir("minimal-blog")


def _errors(text: str = _PAGE_ERRORS) -> dict[str, tuple[CompileError, ...]]:
    grouped: dict[str, list[CompileError]] = {}
    for error in parse_tsc_output(text):
        grouped.setdefault(error.path, []).append(error)
    return {path: tuple(errors) for path, errors in grouped.items()}


def _fake_repo(root: str, page: str = "bad content") -> Path:
    web = Path(root) / "apps" / "web"
    (web / "app").mkdir(parents=True)
    (web / "app" / "page.tsx").write_text(page, encoding="utf-8")
    (web / "node_modules" / ".bin").mkdir(parents=True)
    (web / "node_modules" / ".bin" / "tsc").write_text("", encoding="utf-8")
    return web


class SpecTests(unittest.TestCase):
    def test_specs_reproduce_r465_files_prompts_and_fallbacks(self) -> None:
        ir = _ir()
        specs = llm_file_specs(ir, "a blog")
        expected = {"app/page.tsx", *(f"app/{screen.id}/page.tsx" for screen in ir.screens)}
        self.assertEqual(set(specs), expected)
        overview = specs["app/page.tsx"]
        self.assertIsInstance(overview, LlmFileSpec)
        self.assertIn("AVAILABLE PRE-BUILT UI COMPONENTS", overview.prompt)
        self.assertIn("useListPosts", overview.prompt)
        self.assertEqual(overview.fallback, _overview_page(ir))
        screen = ir.screens[0]
        self.assertEqual(specs[f"app/{screen.id}/page.tsx"].fallback, _screen_page(screen, ir))

    def test_screens_can_be_excluded(self) -> None:
        self.assertEqual(list(llm_file_specs(_ir(), "a blog", synthesize_screens=False)), ["app/page.tsx"])

    def test_compile_errors_message_is_bounded(self) -> None:
        errors = tuple(CompileError("app/page.tsx", i, 1, "TS2339", f"m{i}") for i in range(25))
        message = compile_errors_message(errors, max_errors=20)
        self.assertIn("25 error(s)", message)
        self.assertIn("L0:1 TS2339: m0", message)
        self.assertIn("... and 5 more", message)
        self.assertNotIn("m24", message)


class RepairFilesTests(unittest.TestCase):
    def test_model_fix_is_validated_marked_and_recorded(self) -> None:
        ir = _ir()
        specs = llm_file_specs(ir, "a blog", synthesize_screens=False)
        provider = SequenceStubProvider([_VALID_PAGE])
        outcomes: list[UiSynthesisOutcome] = []
        changes = asyncio.run(repair_compiled_files(
            current={"app/page.tsx": "const broken = 1;"}, errors_by_file=_errors(), specs=specs,
            provider=provider, model_id="m", outcomes=outcomes,
        ))
        self.assertEqual(list(changes), ["app/page.tsx"])
        self.assertTrue(changes["app/page.tsx"].startswith('"use client";\n' + MARKER_PREFIX))
        self.assertIn("compile-repair 1/2", changes["app/page.tsx"])
        self.assertEqual(len(provider.requests), 1)
        roles = [m.role for m in provider.requests[0].messages]
        self.assertEqual(roles, [ChatRole.SYSTEM, ChatRole.USER, ChatRole.ASSISTANT, ChatRole.USER])
        self.assertEqual(provider.requests[0].messages[1].content, specs["app/page.tsx"].prompt.strip())
        self.assertIn("const broken = 1;", provider.requests[0].messages[2].content)
        last = provider.requests[0].messages[3].content
        self.assertIn("REJECTED", last)
        self.assertIn("TS2339", last)
        self.assertIn("L5:11", last)
        self.assertEqual(outcomes[0].to_dict(), {
            "path": "app/page.tsx", "mode": "llm", "attempts": 1, "model_id": "m", "last_reason": "",
        })

    def test_validator_rejection_is_fed_back_then_succeeds(self) -> None:
        specs = llm_file_specs(_ir(), "a blog", synthesize_screens=False)
        provider = SequenceStubProvider([_INVALID_PAGE, _VALID_PAGE])
        outcomes: list[UiSynthesisOutcome] = []
        changes = asyncio.run(repair_compiled_files(
            current={"app/page.tsx": "x"}, errors_by_file=_errors(), specs=specs, provider=provider, outcomes=outcomes,
        ))
        self.assertIn("compile-repair 2/2", changes["app/page.tsx"])
        self.assertEqual(len(provider.requests), 2)
        second = provider.requests[1].messages
        self.assertEqual(second[-1].role, ChatRole.USER)
        self.assertIn("axios", second[-1].content)
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("llm", 2))

    def test_exhaustion_and_exceptions_fall_back_to_the_template(self) -> None:
        ir = _ir()
        specs = llm_file_specs(ir, "a blog", synthesize_screens=False)
        exhausted = SequenceStubProvider([_INVALID_PAGE, _INVALID_PAGE])
        outcomes: list[UiSynthesisOutcome] = []
        changes = asyncio.run(repair_compiled_files(
            current={"app/page.tsx": "x"}, errors_by_file=_errors(), specs=specs, provider=exhausted, outcomes=outcomes,
        ))
        self.assertEqual(changes["app/page.tsx"], _overview_page(ir))
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("deterministic", 2))
        self.assertIn("axios", outcomes[0].last_reason)

        failing = SequenceStubProvider([], fail=RuntimeError("boom"))
        outcomes = []
        changes = asyncio.run(repair_compiled_files(
            current={"app/page.tsx": "x"}, errors_by_file=_errors(), specs=specs, provider=failing, outcomes=outcomes,
        ))
        self.assertEqual(changes["app/page.tsx"], _overview_page(ir))
        self.assertEqual(len(failing.requests), 1)
        self.assertEqual(outcomes[0].last_reason, "RuntimeError")

        # An HTTP error records its status code (never its body) so an operator can tell 413 from 500.
        http = SequenceStubProvider([], fail=ProviderHTTPError("body: secret-looking payload", status_code=413))
        outcomes = []
        asyncio.run(repair_compiled_files(
            current={"app/page.tsx": "x"}, errors_by_file=_errors(), specs=specs, provider=http, outcomes=outcomes,
        ))
        self.assertEqual(outcomes[0].last_reason, "ProviderHTTPError(413)")
        self.assertNotIn("payload", json.dumps(outcomes[0].to_dict()))

    def test_deterministic_files_are_never_rewritten(self) -> None:
        specs = llm_file_specs(_ir(), "a blog", synthesize_screens=False)
        provider = SequenceStubProvider([_VALID_PAGE])
        errors = _errors("lib/hooks.ts(1,1): error TS1005: ';' expected.\n")
        changes = asyncio.run(repair_compiled_files(
            current={"lib/hooks.ts": "hooks"}, errors_by_file=errors, specs=specs, provider=provider,
        ))
        self.assertEqual(changes, {})
        self.assertEqual(provider.requests, [])

    def test_repair_diff_applies_under_apps_web(self) -> None:
        diff = build_repair_diff({"app/page.tsx": "new page"})
        self.assertEqual(diff.unchanged, ())
        self.assertEqual([(c.kind, c.path) for c in diff.changes], [(ChangeKind.MODIFIED, "apps/web/app/page.tsx")])
        with tempfile.TemporaryDirectory() as tmp:
            _fake_repo(tmp)
            report = apply_diff(diff, tmp)
            self.assertEqual(report.modified, ("apps/web/app/page.tsx",))
            self.assertEqual((Path(tmp) / "apps" / "web" / "app" / "page.tsx").read_text(encoding="utf-8"), "new page")


class CompileAndRepairTests(unittest.TestCase):
    def test_model_repair_then_clean_compile(self) -> None:
        ir = _ir()
        with tempfile.TemporaryDirectory() as tmp:
            web = _fake_repo(tmp)
            runner = _FakeRunner([(2, _PAGE_ERRORS), (0, "")])
            provider = SequenceStubProvider([_VALID_PAGE])
            outcomes: list[UiSynthesisOutcome] = []
            report = asyncio.run(compile_and_repair(
                repo_dir=tmp, ir=ir, user_prompt="a blog", provider=provider, model_id="m",
                synthesize_screens=False, outcomes=outcomes, runner=runner,
            ))
            self.assertIsInstance(report, CompileRepairReport)
            self.assertTrue(report.final_ok)
            self.assertEqual(len(report.rounds), 2)
            self.assertEqual(report.repaired, ("app/page.tsx",))
            self.assertEqual(report.reverted, ())
            self.assertEqual(report.untouched_failures, ())
            on_disk = (web / "app" / "page.tsx").read_text(encoding="utf-8")
            self.assertIn("compile-repair 1/2", on_disk)
            self.assertEqual(len(provider.requests), 1)
            self.assertIn("bad content", provider.requests[0].messages[2].content)
            self.assertEqual([o.mode for o in outcomes], ["llm"])
            json.dumps(report.to_dict())

    def test_still_failing_file_is_reverted_on_the_last_round(self) -> None:
        ir = _ir()
        with tempfile.TemporaryDirectory() as tmp:
            web = _fake_repo(tmp)
            runner = _FakeRunner([(2, _PAGE_ERRORS), (2, _PAGE_ERRORS), (0, "")])
            provider = SequenceStubProvider([_VALID_PAGE])
            outcomes: list[UiSynthesisOutcome] = []
            report = asyncio.run(compile_and_repair(
                repo_dir=tmp, ir=ir, user_prompt="a blog", provider=provider, model_id="m",
                synthesize_screens=False, outcomes=outcomes, runner=runner, max_rounds=2,
            ))
            self.assertTrue(report.final_ok)
            self.assertEqual(len(report.rounds), 3)
            self.assertEqual(report.repaired, ())
            self.assertEqual(report.reverted, ("app/page.tsx",))
            self.assertEqual((web / "app" / "page.tsx").read_text(encoding="utf-8"), _overview_page(ir))
            self.assertEqual([o.mode for o in outcomes], ["llm", "deterministic"])
            self.assertEqual(outcomes[1].last_reason, "tsc: 1 error(s)")

    def test_errors_in_deterministic_files_stop_without_model_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = _fake_repo(tmp)
            runner = _FakeRunner([(2, "lib/hooks.ts(1,1): error TS1005: ';' expected.\n")])
            provider = SequenceStubProvider([_VALID_PAGE])
            report = asyncio.run(compile_and_repair(
                repo_dir=tmp, ir=_ir(), user_prompt="a blog", provider=provider, synthesize_screens=False, runner=runner,
            ))
            self.assertFalse(report.final_ok)
            self.assertEqual(len(report.rounds), 1)
            self.assertEqual(report.untouched_failures, ("lib/hooks.ts",))
            self.assertEqual(provider.requests, [])
            self.assertEqual((web / "app" / "page.tsx").read_text(encoding="utf-8"), "bad content")

    def test_clean_first_compile_does_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _fake_repo(tmp)
            provider = SequenceStubProvider([])
            report = compile_and_repair_sync(
                repo_dir=tmp, ir=_ir(), user_prompt="a blog", provider=provider, synthesize_screens=False,
                runner=_FakeRunner([(0, "")]),
            )
            self.assertTrue(report.final_ok)
            self.assertEqual(len(report.rounds), 1)
            self.assertEqual(provider.requests, [])


if __name__ == "__main__":
    unittest.main()
