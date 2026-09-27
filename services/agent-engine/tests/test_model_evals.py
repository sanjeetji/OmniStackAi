"""PC-085: providers are scored on the platform's own jobs, and each job goes to the best one.

Offline: every provider here is a fake and no model is called. The live run is
`scripts/model-eval.sh`; its numbers are in the CHANGELOG entry for PC-085.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake.provider_resolution import resolve_generation_provider_from_env
from omnistackai_agent_engine.model_gateway import FinishReason, GenerateResponse, TokenUsage
from omnistackai_agent_engine.model_gateway import evals
from omnistackai_agent_engine.model_gateway.evals import Candidate, Run, rank_chain, summarize
from omnistackai_agent_engine.model_gateway.fallback import FallbackChainProvider

PLAN = json.dumps(example_ir("minimal-blog").to_dict())


class _Fake:
    def __init__(self, provider_id, text=PLAN, fail=None):
        self.provider_id, self.text, self.fail = provider_id, text, fail

    async def generate(self, request):
        if self.fail:
            raise self.fail
        return GenerateResponse(request.request_id, request.model, self.text, FinishReason.STOP, TokenUsage(1, 1), 1)


def _card(**scores):
    return {"tasks": {"plan": {k: {"runs": 3, "valid": v[0], "score": v[1]} for k, v in scores.items()}}}


class ScoringPutsQualityFirst(TestCase):
    def test_a_valid_slow_answer_beats_a_fast_invalid_one(self) -> None:
        slow_valid = summarize([Run(True, 60.0, 0.5)] * 3)
        fast_broken = summarize([Run(False, 1.0)] * 3)
        self.assertGreater(slow_valid["score"], fast_broken["score"])

    def test_among_valid_answers_faster_and_richer_win(self) -> None:
        fast = summarize([Run(True, 5.0, 0.8)] * 3)
        slow = summarize([Run(True, 90.0, 0.8)] * 3)
        self.assertGreater(fast["score"], slow["score"])
        self.assertEqual(fast["score"], 0.75 + 0.15 * 0.8 + 0.10)

    def test_a_quota_is_not_a_quality_verdict(self) -> None:
        from omnistackai_agent_engine.model_gateway.errors import ProviderRateLimitedError

        limited = asyncio.run(evals.eval_plan(
            Candidate(_Fake("google-gemini", fail=ProviderRateLimitedError("429", status_code=429)), "m", 4096, 5), "x"))
        self.assertTrue(limited.unavailable)
        summary = summarize([limited, Run(True, 5.0, 1.0)])
        self.assertEqual((summary["valid"], summary["runs"], summary["unavailable"]), (1, 1, 1))

    def test_failures_are_named(self) -> None:
        summary = summarize([Run(False, 1.0, error="ProviderTimeoutError"), Run(True, 5.0, 1.0)])
        self.assertEqual((summary["valid"], summary["runs"]), (1, 2))
        self.assertEqual(summary["errors"], ["ProviderTimeoutError"])


class RoutingFollowsTheScorecard(TestCase):
    KEYS = ["groq:gpt-oss", "google-gemini:flash", "nvidia:nemotron", "ollama-local:qwen"]

    def test_best_score_first(self) -> None:
        card = _card(**{"groq:gpt-oss": (3, 0.8), "google-gemini:flash": (3, 0.95), "nvidia:nemotron": (2, 0.6)})
        order = [self.KEYS[i] for i in rank_chain(self.KEYS, "plan", card)]
        self.assertEqual(order, ["google-gemini:flash", "groq:gpt-oss", "nvidia:nemotron", "ollama-local:qwen"])

    def test_unscored_keep_their_place_ahead_of_providers_that_always_failed(self) -> None:
        card = _card(**{"groq:gpt-oss": (0, 0.0), "nvidia:nemotron": (3, 0.7)})
        order = [self.KEYS[i] for i in rank_chain(self.KEYS, "plan", card)]
        self.assertEqual(order, ["nvidia:nemotron", "google-gemini:flash", "ollama-local:qwen", "groq:gpt-oss"])

    def test_no_scorecard_changes_nothing(self) -> None:
        self.assertEqual(rank_chain(self.KEYS, "plan", {}), [0, 1, 2, 3])

    def test_scores_for_another_job_do_not_apply(self) -> None:
        card = _card(**{"nvidia:nemotron": (3, 0.99)})
        self.assertEqual(rank_chain(self.KEYS, "code", card), [0, 1, 2, 3])

    def test_routing_can_be_fixed(self) -> None:
        card = _card(**{"nvidia:nemotron": (3, 0.99)})
        with mock.patch.dict("os.environ", {evals.ROUTING_ENV: "fixed"}):
            self.assertEqual(rank_chain(self.KEYS, "plan", card), [0, 1, 2, 3])


class TheBuildChainIsOrderedPerJob(TestCase):
    ENV = {
        "OMNISTACKAI_CLOUD_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test_key",
        "OMNISTACKAI_GROQ_MODEL": "openai/gpt-oss-120b", "GOOGLE_API_KEY": "google-test-key",
        "OMNISTACKAI_GOOGLE_MODEL": "gemini-3-flash-preview", "OMNISTACKAI_FALLBACK_PROVIDERS": "google",
    }

    def _resolve(self, card, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scorecard.json"
            evals.save_scorecard(card, path)
            with mock.patch.dict("os.environ", {**self.ENV, evals.SCORECARD_ENV: str(path)}, clear=True):
                return resolve_generation_provider_from_env(load_dotenv=False, **kwargs)

    def test_the_best_plan_model_goes_first_and_is_reported(self) -> None:
        card = {"tasks": {"plan": {"google-gemini:gemini-3-flash-preview": {"runs": 3, "valid": 3, "score": 0.9},
                                   "groq:openai/gpt-oss-120b": {"runs": 3, "valid": 3, "score": 0.8}}}}
        provider, model_id, _, _ = self._resolve(card)
        self.assertEqual(provider.chain[0], "google-gemini:gemini-3-flash-preview")
        self.assertEqual(model_id, "gemini-3-flash-preview")

    def test_code_jobs_use_code_scores(self) -> None:
        card = {"tasks": {"plan": {"google-gemini:gemini-3-flash-preview": {"runs": 3, "valid": 3, "score": 0.9}},
                          "code": {"groq:openai/gpt-oss-120b": {"runs": 2, "valid": 2, "score": 0.95}}}}
        provider, _, _, _ = self._resolve(card, task="code")
        self.assertEqual(provider.chain[0], "groq:openai/gpt-oss-120b")

    def test_a_pinned_project_is_never_rerouted(self) -> None:
        card = {"tasks": {"plan": {"google-gemini:gemini-3-flash-preview": {"runs": 3, "valid": 3, "score": 0.99}}}}
        provider, model_id, _, _ = self._resolve(card, provider_id="groq")
        self.assertNotIsInstance(provider, FallbackChainProvider)
        self.assertEqual(provider.provider_id, "groq")


class TheJobsAreMeasuredForReal(TestCase):
    def test_a_valid_plan_scores_and_a_broken_one_does_not(self) -> None:
        good = asyncio.run(evals.eval_plan(Candidate(_Fake("groq"), "m", 4096, 5), "a blog"))
        bad = asyncio.run(evals.eval_plan(Candidate(_Fake("groq", text="not json"), "m", 4096, 5), "a blog"))
        self.assertTrue(good.ok)
        self.assertGreater(good.richness, 0)
        self.assertFalse(bad.ok)

    def test_code_must_keep_its_export_and_pass_the_compiler(self) -> None:
        name, _, _ = evals.CODE_CASES[0]
        no_export = asyncio.run(evals.eval_code(Candidate(_Fake("groq", text="const x = 1;"), "m", 4096, 5),
                                                evals.CODE_CASES[0], Path("/nonexistent")))
        self.assertEqual(no_export.error, "dropped the default export")
        fixed = "```tsx\nexport default function A() { return null; }\n```"
        with mock.patch.object(evals, "typechecks", return_value=True) as check:
            run = asyncio.run(evals.eval_code(Candidate(_Fake("groq", text=fixed), "m", 4096, 5),
                                              evals.CODE_CASES[0], Path("/nm")))
        self.assertTrue(run.ok)
        self.assertEqual(check.call_args[0][1], "export default function A() { return null; }\n")
        self.assertEqual(check.call_args[0][0], name)

    def test_the_broken_cases_really_are_broken(self) -> None:
        node_modules = evals._web_node_modules()
        if node_modules is None:
            self.skipTest("the shared web type-check cache is not installed")
        for name, broken, _ in evals.CODE_CASES:
            with self.subTest(case=name):
                self.assertFalse(evals.typechecks(name, broken, node_modules))

    def test_a_correct_fix_passes(self) -> None:
        node_modules = evals._web_node_modules()
        if node_modules is None:
            self.skipTest("the shared web type-check cache is not installed")
        fixes = {
            "habit-card.tsx": ("const label: number = habit.title;", "const label: string = habit.title;",
                               "habit.streek", "habit.streak"),
            "order-list.tsx": ('setFilter("delivered")', 'setFilter("shipped")',
                               "shown.length.toUpperCase()", "String(shown.length)"),
        }
        for name, broken, _ in evals.CODE_CASES:
            a, b, c, d = fixes[name]
            with self.subTest(case=name):
                self.assertTrue(evals.typechecks(name, broken.replace(a, b).replace(c, d), node_modules))

    def test_a_damaged_scorecard_routes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scorecard.json"
            path.write_text("{not json")
            self.assertEqual(evals.load_scorecard(path), {})
