"""PC-010: a user pays for answers that were used, within a budget they can see in advance.

Offline: providers are fakes. The live proof (a zero-balance build refused, a one-credit budget
respected, the estimate shown before a build) is recorded in the CHANGELOG entry for PC-010.
"""

import asyncio
import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelRef,
    TokenUsage,
)
from omnistackai_agent_engine.model_gateway.accounting import (
    ModelPrice,
    PriceBook,
    UsageLedger,
    billing_scope,
    discard_attempt,
    price_book_from_env,
)
from omnistackai_agent_engine.model_gateway.errors import BudgetExceededError
from omnistackai_agent_engine.model_gateway.recording import RecordingProvider

BOOK = PriceBook({("groq", None): ModelPrice("1", "1")})  # $1 per million tokens either way


class _Fake:
    provider_id = "groq"

    def __init__(self, texts=("ok",)):
        self.texts = list(texts)
        self.calls = 0

    async def generate(self, request):
        self.calls += 1
        text = self.texts[min(self.calls - 1, len(self.texts) - 1)]
        return GenerateResponse(request.request_id, request.model, text, FinishReason.STOP,
                                TokenUsage(500_000, 500_000), 1)


def _request(n: int) -> GenerateRequest:
    return GenerateRequest(f"r{n}", ModelRef("groq", "m"), (Message(ChatRole.USER, "hi"),), 64, 30)


class OnlyUsedAnswersAreBilled(TestCase):
    def test_a_discarded_retry_costs_nothing(self) -> None:
        ledger = UsageLedger(BOOK)
        provider = RecordingProvider(_Fake(), ledger)

        async def run():
            with billing_scope(ledger):
                await provider.generate(_request(1))
                discard_attempt("r1")          # the platform threw this answer away
                await provider.generate(_request(2))

        asyncio.run(run())
        self.assertEqual(ledger.summary().total_cost_usd, Decimal("2"))  # what the platform spent
        self.assertEqual(ledger.billable_cost_usd(), Decimal("1"))       # what the user pays

    def test_outside_a_task_discarding_is_harmless(self) -> None:
        discard_attempt("nothing-running")

    def test_the_ui_loop_discards_a_rejected_page(self) -> None:
        # R-465's synthesis loop: the first answer is rejected, the second is used.
        from omnistackai_agent_engine.codegen import llm_ui

        ledger = UsageLedger(BOOK)
        fake = _Fake()
        provider = RecordingProvider(fake, ledger)
        with billing_scope(ledger), \
                mock.patch.object(llm_ui, "_resolve_target", return_value=(ModelRef("groq", "m"), 1024)), \
                mock.patch.object(llm_ui, "clean_and_validate_jsx",
                                  side_effect=[(False, "", "no default export"), (True, "export default 1", "")]):
            asyncio.run(llm_ui._synthesize_file(path="app/page.tsx", prompt="p", fallback=lambda: "fallback",
                                                provider=provider, model_id="m", timeout_seconds=30,
                                                max_attempts=3, outcomes=None, log_label="page"))
        self.assertEqual(fake.calls, 2)
        self.assertEqual(len(ledger.discarded()), 1)
        self.assertEqual(ledger.billable_cost_usd(), Decimal("1"), "only the used answer is billed")


class TheBudgetIsAHardCeiling(TestCase):
    def test_no_call_after_the_budget_is_spent(self) -> None:
        ledger = UsageLedger(BOOK, budget_usd=Decimal("1"))
        fake = _Fake()
        provider = RecordingProvider(fake, ledger)
        asyncio.run(provider.generate(_request(1)))  # costs $1: the budget is now used
        with self.assertRaises(BudgetExceededError):
            asyncio.run(provider.generate(_request(2)))
        self.assertEqual(fake.calls, 1, "the refused call never reached the model")

    def test_the_charge_never_exceeds_the_budget(self) -> None:
        ledger = UsageLedger(BOOK, budget_usd=Decimal("0.5"))
        asyncio.run(RecordingProvider(_Fake(), ledger).generate(_request(1)))  # $1 of work
        self.assertEqual(ledger.billable_cost_usd(), Decimal("0.5"))

    def test_the_budget_reaches_the_studio_ledger(self) -> None:
        from omnistackai_agent_engine.studio.live_serve import _task_ledger, _usage_summary_to_dict

        ledger = _task_ledger(2_500)  # micros
        self.assertEqual(ledger.budget_usd, Decimal("0.0025"))
        usage = _usage_summary_to_dict(ledger)
        self.assertEqual(usage["budget_micros_usd"], 2500)
        self.assertEqual(usage["billable_cost_micros_usd"], 0)


class PricesAreTheOperators(TestCase):
    def test_the_build_model_has_a_price(self) -> None:
        self.assertIsNotNone(price_book_from_env().cost_for("groq", "openai/gpt-oss-120b", TokenUsage(1000, 1000)))

    def test_an_override_prices_a_provider_or_a_model(self) -> None:
        with mock.patch.dict(os.environ, {"OMNISTACKAI_MODEL_PRICES": json.dumps(
                {"nvidia:*": [0, 0], "google-gemini:gemini-3-flash-preview": [0.5, 3]})}):
            book = price_book_from_env()
        self.assertEqual(book.cost_for("nvidia", "anything", TokenUsage(10, 10)), Decimal("0"))
        self.assertEqual(book.cost_for("google-gemini", "gemini-3-flash-preview", TokenUsage(1_000_000, 0)), Decimal("0.5"))

    def test_a_bad_override_changes_nothing(self) -> None:
        with mock.patch.dict(os.environ, {"OMNISTACKAI_MODEL_PRICES": "{not json"}):
            self.assertIsNotNone(price_book_from_env().cost_for("groq", "openai/gpt-oss-120b", TokenUsage(1, 1)))


class TheEstimateComesFirst(TestCase):
    def test_defaults_until_there_is_history_then_history(self) -> None:
        from omnistackai_agent_engine.studio import estimates

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {estimates.HISTORY_ENV: str(Path(tmp) / "h.jsonl")}):
            first = estimates.estimate("build", "groq", "openai/gpt-oss-120b")
            self.assertIn("not enough history", first["basis"])
            self.assertTrue(first["priced"])
            self.assertLessEqual(first["cost_micros_low"], first["cost_micros_high"])
            for tokens in (1000, 2000, 3000, 4000):
                estimates.record_counts("build", tokens, tokens)
            grounded = estimates.estimate("build", "groq", "openai/gpt-oss-120b")
        self.assertIn("the last 4 builds", grounded["basis"])
        self.assertEqual(grounded["tokens_low"], {"input": 2500, "output": 2500})

    def test_an_unpriced_model_says_so(self) -> None:
        from omnistackai_agent_engine.studio import estimates

        self.assertFalse(estimates.estimate("edit", "openrouter", "some/free-model")["priced"])

    def test_no_history_is_kept_outside_the_studio(self) -> None:
        from omnistackai_agent_engine.studio import estimates

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(estimates.history_path())
            estimates.record_counts("build", 1, 1)  # a no-op, not a write to the home folder
