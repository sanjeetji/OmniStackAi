"""Builds fall over to the next provider instead of failing (founder, 2026-09-26).

Order: Groq gpt-oss-120b -> Gemini -> OpenRouter (free nemotron) -> NVIDIA -> local Ollama.
Proven live: with Groq's key deliberately wrong, Groq answered 401 and Gemini answered in 2.2 s.

The rules held here: move on only for failures another provider can fix; never switch in the middle
of a stream the user is already reading; each provider uses its own model; a fallback without a key
is skipped, not fatal; a project that pinned a model gets exactly that model.
"""

import asyncio
from unittest import TestCase, mock

from omnistackai_agent_engine.intake.provider_resolution import resolve_generation_provider_from_env
from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelRef,
    StreamEvent,
    TokenUsage,
)
from omnistackai_agent_engine.model_gateway.errors import (
    ProviderHTTPError,
    ProviderRateLimitedError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from omnistackai_agent_engine.model_gateway.fallback import ChainEntry, FallbackChainProvider


class _Fake:
    def __init__(self, provider_id, *, fail=None, text="ok", fail_after_first_token=False):
        self.provider_id = provider_id
        self.fail = fail
        self.text = text
        self.fail_after_first_token = fail_after_first_token
        self.seen = []

    async def generate(self, request):
        self.seen.append(request)
        if self.fail:
            raise self.fail
        return GenerateResponse(request.request_id, request.model, self.text, FinishReason.STOP, TokenUsage(1, 1), 1)

    async def stream(self, request):
        self.seen.append(request)
        if self.fail and not self.fail_after_first_token:
            raise self.fail
        yield StreamEvent(request.request_id, 0, self.text, False)
        if self.fail:
            raise self.fail
        yield StreamEvent(request.request_id, 1, "", True)


def _request():
    return GenerateRequest("r1", ModelRef("groq", "primary"), (Message(ChatRole.USER, "hi"),), 64, 30)


def _chain(*providers):
    return FallbackChainProvider([ChainEntry(p, f"{p.provider_id}-model", 64) for p in providers])


class ItMovesOnForFailuresAnotherProviderCanFix(TestCase):
    def test_rate_limit_timeout_bad_key_and_server_errors(self) -> None:
        for error in (ProviderRateLimitedError("429", status_code=429), ProviderTimeoutError("slow"),
                      ProviderHTTPError("401", status_code=401), ProviderHTTPError("503", status_code=503)):
            with self.subTest(error=type(error).__name__):
                second = _Fake("google-gemini", text="from gemini")
                chain = _chain(_Fake("groq", fail=error), second)
                response = asyncio.run(chain.generate(_request()))
                self.assertEqual(response.text, "from gemini")
                self.assertEqual(chain.last_provider_id, "google-gemini")

    def test_each_provider_is_asked_with_its_own_model(self) -> None:
        second = _Fake("google-gemini")
        asyncio.run(_chain(_Fake("groq", fail=ProviderTimeoutError("slow")), second).generate(_request()))
        self.assertEqual(second.seen[0].model, ModelRef("google-gemini", "google-gemini-model"))

    def test_a_bad_answer_is_not_retried_elsewhere(self) -> None:
        second = _Fake("google-gemini")
        chain = _chain(_Fake("groq", fail=ProviderResponseError("garbled")), second)
        with self.assertRaises(ProviderResponseError):
            asyncio.run(chain.generate(_request()))
        self.assertEqual(second.seen, [])

    def test_the_last_failure_surfaces(self) -> None:
        chain = _chain(_Fake("groq", fail=ProviderTimeoutError("a")), _Fake("google-gemini", fail=ProviderTimeoutError("b")))
        with self.assertRaises(ProviderTimeoutError):
            asyncio.run(chain.generate(_request()))


class StreamingNeverSwitchesMidway(TestCase):
    def _collect(self, chain):
        async def run():
            return [e.delta async for e in chain.stream(_request())]

        return asyncio.run(run())

    def test_before_the_first_token_it_falls_over(self) -> None:
        chain = _chain(_Fake("groq", fail=ProviderRateLimitedError("429", status_code=429)), _Fake("google-gemini", text="G"))
        self.assertEqual(self._collect(chain), ["G", ""])

    def test_after_the_first_token_it_raises(self) -> None:
        second = _Fake("google-gemini", text="G")
        chain = _chain(_Fake("groq", text="partial", fail=ProviderTimeoutError("cut"), fail_after_first_token=True), second)
        with self.assertRaises(ProviderTimeoutError):
            self._collect(chain)
        self.assertEqual(second.seen, [], "the user already saw Groq's text; another model must not continue it")


class ResolutionBuildsTheChainFromSettings(TestCase):
    ENV = {
        "OMNISTACKAI_CLOUD_PROVIDER": "groq",
        "GROQ_API_KEY": "gsk_test_key",
        "OMNISTACKAI_GROQ_MODEL": "openai/gpt-oss-120b",
        "GOOGLE_API_KEY": "google-test-key",
        "OMNISTACKAI_GOOGLE_MODEL": "gemini-3-flash-preview",
        "OMNISTACKAI_FALLBACK_PROVIDERS": "google,openrouter,nvidia,ollama",
        "OMNISTACKAI_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OMNISTACKAI_OLLAMA_MODEL": "qwen2.5-coder:7b",
    }

    def test_in_order_skipping_providers_without_a_key(self) -> None:
        with mock.patch.dict("os.environ", self.ENV, clear=True):
            provider, model_id, _, _ = resolve_generation_provider_from_env(load_dotenv=False)
        self.assertEqual(model_id, "openai/gpt-oss-120b")
        self.assertEqual(provider.chain, (
            "groq:openai/gpt-oss-120b",
            "google-gemini:gemini-3-flash-preview",
            # openrouter and nvidia have no key in this environment: skipped, not fatal
            "ollama-local:qwen2.5-coder:7b",
        ))

    def test_a_pinned_project_model_gets_no_substitutes(self) -> None:
        with mock.patch.dict("os.environ", self.ENV, clear=True):
            provider, _, _, _ = resolve_generation_provider_from_env(load_dotenv=False, provider_id="groq")
        self.assertFalse(isinstance(provider, FallbackChainProvider))
