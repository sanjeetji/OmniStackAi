"""PC-126: a provider that is out (a spent quota, a limit, an outage) is skipped by every job until it is back.

Measured by the PC-122 benchmark: with the free tiers spent, every page and build asked the same spent
providers again, each answering 429 after four retries, before reaching one that could answer.
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.model_gateway import health
from omnistackai_agent_engine.model_gateway.errors import (
    ProviderHTTPError,
    ProviderRateLimitedError,
    ProviderUnavailableError,
)


class _Health(TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {health.PATH_ENV: str(Path(self.tmp.name) / "health.json")})
        patcher.start()
        self.addCleanup(patcher.stop)


class WhatIsRemembered(_Health):
    def test_states_and_how_long(self) -> None:
        now = time.time()
        self.assertEqual(health.classify(ProviderRateLimitedError("slow down", status_code=429, retry_after_seconds=12))[0], "rate_limited")
        self.assertEqual(health.classify(ProviderRateLimitedError("slow down", status_code=429, retry_after_seconds=12))[1], 12.0)
        state, seconds = health.classify(ProviderRateLimitedError("Quota exceeded: GenerateRequestsPerDayPerProjectPerModel", status_code=429))
        self.assertEqual(state, "quota")
        self.assertAlmostEqual(now + seconds, health.next_daily_reset(), delta=5)
        self.assertEqual(health.classify(ProviderUnavailableError("down")), ("unavailable", 30.0))
        self.assertEqual(health.classify(ProviderHTTPError("no credit", status_code=402))[0], "refused_key")
        self.assertIsNone(health.classify(ValueError("a bad answer is not the provider being out")))
        self.assertEqual(health.classify(ProviderHTTPError("rate_limit_exceeded", status_code=413)), ("rate_limited", 60.0),
                         "Groq's per-minute token limit")

    def test_marks_expire_and_success_clears(self) -> None:
        health.note_failure("groq", ProviderRateLimitedError("x", status_code=429, retry_after_seconds=30), now=1000.0)
        self.assertFalse(health.is_available("groq", now=1010.0))
        self.assertTrue(health.is_available("groq", now=1031.0))
        health.note_failure("groq", ProviderUnavailableError("x"))
        health.note_success("groq")
        self.assertTrue(health.is_available("groq"))

    def test_local_is_never_marked_out(self) -> None:
        self.assertIsNone(health.note_failure("ollama", ProviderUnavailableError("busy")))
        self.assertTrue(health.is_available("ollama"))

    def test_google_has_one_name(self) -> None:
        health.note_failure("google-gemini", ProviderRateLimitedError("x", status_code=429))
        self.assertFalse(health.is_available("google"))

    def test_order_puts_the_out_last_by_when_they_are_back(self) -> None:
        health.note_failure("a", ProviderUnavailableError("x"), now=1000.0)  # back at 1030
        health.note_failure("b", ProviderRateLimitedError("x", status_code=429, retry_after_seconds=10), now=1000.0)  # 1010
        self.assertEqual(health.order(["a", "b", "c"], now=1005.0), [2, 1, 0])

    def test_unset_remembers_nothing(self) -> None:
        with mock.patch.dict(os.environ, {health.PATH_ENV: ""}):
            health.note_failure("groq", ProviderUnavailableError("x"))
            self.assertTrue(health.is_available("groq"))


def _request():
    from omnistackai_agent_engine.model_gateway.contracts import ChatRole, GenerateRequest, Message, ModelRef

    return GenerateRequest("r1", ModelRef("groq", "m"), (Message(ChatRole.USER, "hi"),), 100, 10)


class _Provider:
    def __init__(self, provider_id: str, error: Exception | None = None) -> None:
        self.provider_id, self.error, self.calls = provider_id, error, 0

    async def generate(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(text=f"from {self.provider_id}")


class TheBuildChainSkipsWhatIsOut(_Health):
    def _request(self):
        return _request()

    def test_a_spent_provider_is_asked_once_not_every_time(self) -> None:
        from omnistackai_agent_engine.model_gateway.fallback import ChainEntry, FallbackChainProvider

        spent = _Provider("groq", ProviderRateLimitedError("Requests per day exceeded", status_code=429))
        good = _Provider("nvidia")
        chain = lambda: FallbackChainProvider([ChainEntry(spent, "m", 100), ChainEntry(good, "n", 100)])  # noqa: E731
        request = self._request()
        for _ in range(3):  # three builds, each with its own chain, as in the Studio
            self.assertEqual(asyncio.run(chain().generate(request)).text, "from nvidia")
        self.assertEqual(spent.calls, 1, "found out once; the next builds go straight to nvidia")
        self.assertEqual(good.calls, 3)

    def test_when_everything_is_out_the_soonest_back_is_still_tried(self) -> None:
        from omnistackai_agent_engine.model_gateway.fallback import ChainEntry, FallbackChainProvider

        health.note_failure("groq", ProviderUnavailableError("x"))
        groq = _Provider("groq")
        request = self._request()
        self.assertEqual(asyncio.run(FallbackChainProvider([ChainEntry(groq, "m", 100)]).generate(request)).text, "from groq")
        self.assertTrue(health.is_available("groq"), "answering clears the mark")


class PageDesignToo(_Health):
    def test_a_daily_quota_is_not_waited_out(self) -> None:
        from omnistackai_agent_engine.studio.page_design import ChainProvider

        health.note_failure("google-gemini", ProviderRateLimitedError("GenerateRequestsPerDay", status_code=429))
        waits = []
        gemini, nvidia = _Provider("google-gemini"), _Provider("nvidia")

        async def sleep(seconds):
            waits.append(seconds)

        chain = ChainProvider([(gemini, "g"), (nvidia, "n")], waits=(20.0, 40.0), sleep=sleep)
        answer = asyncio.run(chain.generate(_request()))
        self.assertEqual(answer.text, "from nvidia")
        self.assertEqual((gemini.calls, waits), (0, []), "no call and no waiting for a provider out until tomorrow")


class PaidKeysRaiseQualityWithoutCodeChanges(TestCase):
    def test_a_paid_key_leads_the_page_chain_only_when_set(self) -> None:
        from omnistackai_agent_engine.model_gateway import routing

        clean = {k: "" for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OMNISTACKAI_PAGE_CHAIN", "OMNISTACKAI_PAGE_PROVIDER")}
        with mock.patch.dict(os.environ, clean):
            self.assertNotIn("anthropic", [p for p, _ in routing.page_chain()])
        with mock.patch.dict(os.environ, {**clean, "ANTHROPIC_API_KEY": "sk-test"}):
            self.assertEqual(routing.page_chain()[0], ("anthropic", "claude-sonnet-5-5"))

    def test_the_report_never_prints_a_key(self) -> None:
        from omnistackai_agent_engine.model_gateway import routing

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-secret-value", "OMNISTACKAI_PAGE_CHAIN": ""}):
            self.assertNotIn("sk-secret-value", routing.report())


class NoWaitingWhileAnotherCanAnswer(_Health):
    """Measured in PC-125's benchmark run: each page waited a spent provider's minute out (20 + 40 + 60 s)
    before trying the next one."""

    def test_a_per_minute_limit_passes_to_the_next_provider_at_once(self) -> None:
        from omnistackai_agent_engine.studio.page_design import ChainProvider

        waits = []

        async def sleep(seconds):
            waits.append(seconds)

        limited = _Provider("google-gemini", ProviderRateLimitedError("per minute", status_code=429))
        chain = ChainProvider([(limited, "g"), (_Provider("nvidia"), "n")], waits=(20.0, 40.0), sleep=sleep)
        self.assertEqual(asyncio.run(chain.generate(_request())).text, "from nvidia")
        self.assertEqual((limited.calls, waits), (1, []))

    def test_the_last_provider_left_is_waited_for(self) -> None:
        from omnistackai_agent_engine.studio.page_design import ChainProvider

        waits = []

        async def sleep(seconds):
            waits.append(seconds)

        class OnceLimited(_Provider):
            async def generate(self, request):
                self.calls += 1
                if self.calls == 1:
                    raise ProviderRateLimitedError("per minute", status_code=429)
                return SimpleNamespace(text="from gemini")

        chain = ChainProvider([(OnceLimited("google-gemini"), "g")], waits=(20.0,), sleep=sleep)
        self.assertEqual(asyncio.run(chain.generate(_request())).text, "from gemini")
        self.assertEqual(waits, [20.0])


class APaidKeyLeadsEveryJob(TestCase):
    """PC-127 (open from M1): adding a paid key is the whole change - plans and pages both use it first."""

    CLEAN = {k: "" for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "XAI_API_KEY", "MISTRAL_API_KEY",
                             "OMNISTACKAI_PAGE_CHAIN", "OMNISTACKAI_PAGE_PROVIDER", "OMNISTACKAI_PREFER_LOCAL",
                             "OMNISTACKAI_PAID_LEADS")}

    def test_plans(self) -> None:
        from omnistackai_agent_engine.intake.provider_resolution import paid_lead, resolve_generation_provider_from_env
        from omnistackai_agent_engine.model_gateway import routing

        env = {**self.CLEAN, "DEEPSEEK_API_KEY": "sk-test", "OMNISTACKAI_CLOUD_PROVIDER": "groq",
               "GROQ_API_KEY": "gsk-test", "OMNISTACKAI_FALLBACK_PROVIDERS": "ollama"}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(paid_lead(), "deepseek")
            provider, model, _out, _t = resolve_generation_provider_from_env(load_dotenv=False)
            chain = list(getattr(provider, "chain", ()))
            self.assertTrue(chain[0].startswith("deepseek:"), chain)
            self.assertTrue(any(c.startswith("groq:") for c in chain), "the free tier is still the fallback")
            self.assertEqual(routing.plan_chain()[0][0], "deepseek")
        with mock.patch.dict(os.environ, {**env, "OMNISTACKAI_PAID_LEADS": "0"}):
            self.assertIsNone(paid_lead())

    def test_no_paid_key_no_change(self) -> None:
        from omnistackai_agent_engine.intake.provider_resolution import paid_lead

        with mock.patch.dict(os.environ, self.CLEAN):
            self.assertIsNone(paid_lead())

    def test_pages(self) -> None:
        from omnistackai_agent_engine.model_gateway import routing

        with mock.patch.dict(os.environ, {**self.CLEAN, "DEEPSEEK_API_KEY": "sk-test"}):
            self.assertEqual(routing.page_chain()[0][0], "deepseek")
