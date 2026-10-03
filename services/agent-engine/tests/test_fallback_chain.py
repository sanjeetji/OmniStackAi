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
        # PC-085 orders the chain by this machine's model scorecard; this test is about configured
        # order, so it must never read the real one (it broke the gate once the local 7b scored).
        "OMNISTACKAI_MODEL_SCORECARD": "/nonexistent/omnistack-test-scorecard.json",
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


class AnEmptyAnswerIsNotAnAnswer(TestCase):
    """PC-101, seen live: Groq was rate-limited, OpenRouter answered with nothing, and the build
    ended "model returned an empty response" with two providers still untried."""

    def test_generate_moves_on_from_an_empty_answer(self) -> None:
        chain = _chain(_Fake("openrouter", text="   "), _Fake("nvidia", text="from nvidia"))
        self.assertEqual(asyncio.run(chain.generate(_request())).text, "from nvidia")
        self.assertEqual(chain.last_provider_id, "nvidia")

    def test_stream_moves_on_from_an_empty_stream(self) -> None:
        async def collect(chain):
            return "".join([event.delta async for event in chain.stream(_request())])

        chain = _chain(_Fake("openrouter", text=""), _Fake("nvidia", text="from nvidia"))
        self.assertEqual(asyncio.run(collect(chain)), "from nvidia")
        self.assertEqual(chain.last_provider_id, "nvidia")

    def test_a_request_too_large_for_one_provider_goes_to_the_next(self) -> None:
        # PC-106, seen live: Groq's free tier answered 413 (over its tokens-per-minute limit).
        chain = _chain(_Fake("groq", fail=ProviderHTTPError("413", status_code=413)), _Fake("openrouter", text="ok"))
        self.assertEqual(asyncio.run(chain.generate(_request())).text, "ok")

    def test_the_last_provider_empty_answer_is_still_returned(self) -> None:
        chain = _chain(_Fake("groq", fail=ProviderTimeoutError("slow")), _Fake("ollama", text=""))
        self.assertEqual(asyncio.run(chain.generate(_request())).text, "")


class APlanThatStopsPartWayStartsAgainWithTheNextProvider(TestCase):
    """PC-106, seen live: NVIDIA timed out 120 s into its answer and the build failed, because a
    stream is never switched once text flows. The planner keeps the whole answer, so it starts over."""

    def test_the_rest_of_the_chain_after_a_provider(self) -> None:
        chain = _chain(_Fake("groq"), _Fake("openrouter"), _Fake("nvidia"))
        rest = chain.after("groq", ProviderTimeoutError("slow"))
        self.assertEqual([e.provider.provider_id for e in rest.entries], ["openrouter", "nvidia"])
        self.assertEqual([e.provider.provider_id for e in chain.after("nvidia", ProviderTimeoutError("slow")).entries],
                         ["groq", "openrouter"], "the live order: one listed earlier is still worth trying")
        self.assertIsNone(_chain(_Fake("nvidia")).after("nvidia", ProviderTimeoutError("slow")), "nothing else to try")
        self.assertIsNone(chain.after("groq", ProviderResponseError("bad")), "not a failure another can fix")

    def test_through_the_usage_ledger(self) -> None:
        """Seen live (PC-077): the build's provider is the chain wrapped in the usage ledger, which
        hid ``after`` - a NVIDIA timeout failed the build with local Ollama still untried."""
        from omnistackai_agent_engine.model_gateway.accounting import UsageLedger
        from omnistackai_agent_engine.model_gateway.recording import RecordingProvider

        chain = _chain(_Fake("nvidia"), _Fake("ollama"))
        chain.last_provider_id = "nvidia"
        recorded = RecordingProvider(chain, UsageLedger())
        self.assertEqual(recorded.last_provider_id, "nvidia")
        rest = recorded.after("nvidia", ProviderTimeoutError("slow"))
        self.assertIsInstance(rest, RecordingProvider)
        self.assertEqual(rest.provider_id, "ollama")
        recorded.last_provider_id = "ollama"
        self.assertEqual(chain.last_provider_id, "ollama", "the planner reports who answered")

    def test_the_planner_restarts_through_the_usage_ledger(self) -> None:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.intake.nl_to_ir import IntakeResult, generate_ir_stream
        from omnistackai_agent_engine.model_gateway.accounting import UsageLedger
        from omnistackai_agent_engine.model_gateway.recording import RecordingProvider
        import json

        plan = json.dumps(example_ir("minimal-blog").to_dict())
        chain = _chain(_Fake("nvidia", text='{"name": "half', fail=ProviderTimeoutError("slow"), fail_after_first_token=True),
                       _Fake("ollama", text=plan))
        recorded = RecordingProvider(chain, UsageLedger())

        async def run():
            return [item async for item in generate_ir_stream("A blog", recorded, model_id="m")]

        items = asyncio.run(run())
        self.assertIsInstance(items[-1], IntakeResult)
        self.assertEqual(chain.last_provider_id, "ollama")

    def test_the_planner_drops_the_partial_answer_and_uses_the_next_provider(self) -> None:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.intake.nl_to_ir import IntakeResult, generate_ir_stream
        import json

        plan = json.dumps(example_ir("minimal-blog").to_dict())
        chain = _chain(_Fake("openrouter", text='{"name": "half', fail=ProviderTimeoutError("slow"),
                             fail_after_first_token=True), _Fake("nvidia", text=plan))

        async def run():
            return [item async for item in generate_ir_stream("a blog", chain, model_id="m")]

        items = asyncio.run(run())
        self.assertTrue(any(isinstance(i, str) and "starting the plan again with nvidia" in i for i in items))
        result = items[-1]
        self.assertIsInstance(result, IntakeResult)
        self.assertEqual(result.ir.name, "Minimal Blog")
        self.assertEqual(chain.last_provider_id, "nvidia", "the record names who wrote the plan")
