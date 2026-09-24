"""R-466: shrink-and-retry when a provider rejects a request as too large, and the compact grounding.

Groq's 8k-tokens-per-minute tier answers HTTP 413 when one request alone exceeds the limit; a full grounded
UI request is ~9k tokens. Waiting cannot fix that, so the engine shrinks the transcript (drop the echoed
output, then switch to a compact grounding) and retries — bounded by the attempt budget. Stub providers only.
"""

from __future__ import annotations

import asyncio
import re
import unittest
from types import SimpleNamespace

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    MARKER_PREFIX,
    NextjsWebAdapter,
    UiSynthesisOutcome,
    build_screen_synthesis_prompt,
    build_ui_synthesis_prompt,
    compact_grounding,
    llm_file_specs,
    repair_compiled_files,
    summarize_components,
    summarize_data_layer,
    summarize_design_tokens,
    synthesize_overview_page,
)
from omnistackai_agent_engine.codegen.archetype import detect_archetype
from omnistackai_agent_engine.codegen.auth_guard import needs_auth
from omnistackai_agent_engine.codegen.nextjs import _overview_page
from omnistackai_agent_engine.model_gateway.contracts import ChatRole
from omnistackai_agent_engine.model_gateway.errors import ProviderHTTPError, ProviderRateLimitedError
from omnistackai_agent_engine.verify import parse_tsc_output

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
_COMPACT_PROMPT_BUDGET_CHARS = 14_000


class ScriptedProvider:
    provider_id = "stub"

    def __init__(self, steps: list) -> None:
        self._steps = list(steps)
        self.requests: list = []

    async def generate(self, request):  # noqa: ANN001
        self.requests.append(request)
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return SimpleNamespace(text=step)


def _too_large() -> ProviderHTTPError:
    return ProviderHTTPError("groq returned an HTTP 413 error: Request too large for model", status_code=413)


def _ir():
    return example_ir("minimal-blog")


def _full(ir) -> dict[str, str]:
    return {
        "data_layer": summarize_data_layer(ir),
        "components": summarize_components(ir),
        "design_tokens": summarize_design_tokens(),
    }


def _roles(request) -> list[ChatRole]:  # noqa: ANN001
    return [message.role for message in request.messages]


class CompactGroundingTests(unittest.TestCase):
    def test_compact_blocks_are_smaller_and_keep_every_hook(self) -> None:
        ir = _ir()
        full, compact = _full(ir), compact_grounding(ir)
        for key in ("data_layer", "components", "design_tokens"):
            self.assertLessEqual(len(compact[key]), len(full[key]), key)
        hooks = re.compile(r"\buse\w+")
        self.assertEqual(set(hooks.findall(full["data_layer"])), set(hooks.findall(compact["data_layer"])))
        lines = compact["components"].splitlines()
        self.assertIn("AVAILABLE PRE-BUILT UI COMPONENTS", lines[0])
        entries = [line for line in lines if line.startswith("- @/components/")]
        self.assertGreater(len(entries), 50)
        self.assertTrue(all(", " not in entry for entry in entries), "compact lists one export per component")
        if needs_auth(ir):
            self.assertIn("- @/components/auth-provider: AuthProvider", entries[0])
        self.assertIn("--color-", compact["design_tokens"])

    def test_compact_prompts_fit_a_small_tier(self) -> None:
        for example in ("minimal-blog", "rideshare-favourites"):
            ir = example_ir(example)
            compact = compact_grounding(ir)
            overview = build_ui_synthesis_prompt(ir, "an app", **compact)
            self.assertLessEqual(len(overview), _COMPACT_PROMPT_BUDGET_CHARS, example)
            self.assertLess(len(overview), len(build_ui_synthesis_prompt(ir, "an app", **_full(ir))))
            for screen in ir.screens:
                page = build_screen_synthesis_prompt(screen, ir, "an app", **compact)
                self.assertLessEqual(len(page), _COMPACT_PROMPT_BUDGET_CHARS, f"{example}:{screen.id}")


class ShrinkOnTooLargeTests(unittest.TestCase):
    def _run(self, provider, *, compact=True, max_attempts=3):  # noqa: ANN001
        ir = _ir()
        outcomes: list[UiSynthesisOutcome] = []
        result = asyncio.run(synthesize_overview_page(
            ir, "a blog", provider, "m", outcomes=outcomes, max_attempts=max_attempts, **_full(ir),
            compact_grounding=compact_grounding(ir) if compact else None,
        ))
        return ir, result, outcomes

    def test_413_switches_to_the_compact_prompt(self) -> None:
        provider = ScriptedProvider([_too_large(), _VALID_PAGE])
        ir, result, outcomes = self._run(provider)
        self.assertEqual(len(provider.requests), 2)
        full_prompt = build_ui_synthesis_prompt(ir, "a blog", **_full(ir)).strip()
        compact_prompt = build_ui_synthesis_prompt(ir, "a blog", **compact_grounding(ir)).strip()
        self.assertEqual(provider.requests[0].messages[1].content, full_prompt)
        self.assertEqual(_roles(provider.requests[1]), [ChatRole.SYSTEM, ChatRole.USER])
        self.assertEqual(provider.requests[1].messages[1].content, compact_prompt)
        self.assertTrue(result.startswith('"use client";\n' + MARKER_PREFIX))
        self.assertIn("attempt 2/3", result)
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("llm", 2))

    def test_413_on_a_repair_turn_drops_the_echo_then_compacts(self) -> None:
        provider = ScriptedProvider([_INVALID_PAGE, _too_large(), _too_large(), _VALID_PAGE])
        ir, result, outcomes = self._run(provider, max_attempts=4)
        self.assertEqual(len(provider.requests), 4)
        full_prompt = build_ui_synthesis_prompt(ir, "a blog", **_full(ir)).strip()
        compact_prompt = build_ui_synthesis_prompt(ir, "a blog", **compact_grounding(ir)).strip()
        self.assertEqual(_roles(provider.requests[1]), [ChatRole.SYSTEM, ChatRole.USER, ChatRole.ASSISTANT, ChatRole.USER])
        third = provider.requests[2]
        self.assertEqual(_roles(third), [ChatRole.SYSTEM, ChatRole.USER])
        self.assertTrue(third.messages[1].content.startswith(full_prompt))
        self.assertIn("REJECTED", third.messages[1].content)
        self.assertIn("axios", third.messages[1].content)
        fourth = provider.requests[3]
        self.assertEqual(_roles(fourth), [ChatRole.SYSTEM, ChatRole.USER])
        self.assertTrue(fourth.messages[1].content.startswith(compact_prompt))
        self.assertIn("REJECTED", fourth.messages[1].content)
        self.assertIn("attempt 4/4", result)
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("llm", 4))

    def test_413_without_compact_grounding_falls_back_at_once(self) -> None:
        provider = ScriptedProvider([_too_large(), _VALID_PAGE])
        ir, result, outcomes = self._run(provider, compact=False)
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(result, _overview_page(ir))
        self.assertEqual(outcomes[0].last_reason, "ProviderHTTPError(413)")

    def test_400_context_length_is_treated_as_too_large(self) -> None:
        error = ProviderHTTPError(
            "openai returned an HTTP 400 error: This model's maximum context length is 8192 tokens", status_code=400
        )
        provider = ScriptedProvider([error, _VALID_PAGE])
        _, result, _ = self._run(provider)
        self.assertEqual(len(provider.requests), 2)
        self.assertIn("attempt 2/3", result)

    def test_other_errors_never_retry(self) -> None:
        for error, reason in (
            (ProviderHTTPError("boom", status_code=500), "ProviderHTTPError(500)"),
            (ProviderHTTPError("bad request", status_code=400), "ProviderHTTPError(400)"),
            (ProviderRateLimitedError("slow down", status_code=429, retry_after_seconds=112.0), "ProviderRateLimitedError(429)"),
        ):
            provider = ScriptedProvider([error, _VALID_PAGE])
            ir, result, outcomes = self._run(provider)
            self.assertEqual(len(provider.requests), 1, reason)
            self.assertEqual(result, _overview_page(ir))
            self.assertEqual(outcomes[0].last_reason, reason)

    def test_shrinking_is_bounded(self) -> None:
        # Nothing echoed and already compact: a second 413 has nothing left to drop -> template, 2 requests.
        provider = ScriptedProvider([_too_large(), _too_large(), _VALID_PAGE])
        ir, result, outcomes = self._run(provider)
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(result, _overview_page(ir))
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("deterministic", 2))
        self.assertEqual(outcomes[0].last_reason, "ProviderHTTPError(413)")


class AdapterCompactTests(unittest.TestCase):
    def test_adapter_supplies_the_compact_grounding(self) -> None:
        ir = _ir()
        provider = ScriptedProvider([_too_large(), _VALID_PAGE])
        outcomes: list[UiSynthesisOutcome] = []
        project = NextjsWebAdapter().generate(ir, provider=provider, prompt="a blog", model_id="m", ui_outcomes=outcomes)
        page = {f.path: f.content for f in project.files()}["app/page.tsx"]
        self.assertTrue(page.startswith('"use client";\n' + MARKER_PREFIX))
        self.assertEqual(len(provider.requests), 2)
        # R-541: the web adapter states the archetype rather than leaving it to keyword inference.
        # R-543: and that archetype is now a real one detected from the IR and the prompt together,
        # so "a blog" over a blog IR resolves to `publication`, not a generic public website.
        archetype = detect_archetype(ir, "a blog").value
        self.assertEqual(archetype, "publication")
        expected = build_ui_synthesis_prompt(
            ir, "a blog", archetype=archetype, **compact_grounding(ir)
        ).strip()
        self.assertEqual(provider.requests[1].messages[1].content, expected)
        self.assertEqual([o.mode for o in outcomes], ["llm"])


class RepairShrinkTests(unittest.TestCase):
    def test_repair_transcript_shrinks_on_413(self) -> None:
        ir = _ir()
        specs = llm_file_specs(ir, "a blog", synthesize_screens=False)
        spec = specs["app/page.tsx"]
        self.assertEqual(spec.compact_prompt, build_ui_synthesis_prompt(ir, "a blog", **compact_grounding(ir)))
        errors = {"app/page.tsx": parse_tsc_output(
            "app/page.tsx(5,11): error TS2339: Property 'refresh' does not exist on type 'UseListPosts'.\n"
        )}
        provider = ScriptedProvider([_too_large(), _too_large(), _VALID_PAGE])
        outcomes: list[UiSynthesisOutcome] = []
        changes = asyncio.run(repair_compiled_files(
            current={"app/page.tsx": "old content"}, errors_by_file=errors, specs=specs, provider=provider,
            model_id="m", max_attempts=3, outcomes=outcomes,
        ))
        self.assertEqual(len(provider.requests), 3)
        self.assertEqual(_roles(provider.requests[0]), [ChatRole.SYSTEM, ChatRole.USER, ChatRole.ASSISTANT, ChatRole.USER])
        second = provider.requests[1]
        self.assertEqual(_roles(second), [ChatRole.SYSTEM, ChatRole.USER])
        self.assertTrue(second.messages[1].content.startswith(spec.prompt.strip()))
        self.assertIn("TS2339", second.messages[1].content)
        third = provider.requests[2]
        self.assertTrue(third.messages[1].content.startswith(spec.compact_prompt.strip()))
        self.assertIn("TS2339", third.messages[1].content)
        self.assertIn("compile-repair 3/3", changes["app/page.tsx"])
        self.assertEqual((outcomes[0].mode, outcomes[0].attempts), ("llm", 3))


if __name__ == "__main__":
    unittest.main()
