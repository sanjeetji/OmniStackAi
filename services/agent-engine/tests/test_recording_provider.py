"""Unit tests for RecordingProvider (R-472) - real per-call usage/cost accounting."""

import unittest
from datetime import UTC, datetime

from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    DEFAULT_PRICE_BOOK,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelDescriptor,
    ModelProviderError,
    ModelRef,
    ProviderHealth,
    HealthStatus,
    StreamEvent,
    TokenUsage,
    UsageLedger,
)
from omnistackai_agent_engine.model_gateway.ollama import OLLAMA_PROVIDER_ID
from omnistackai_agent_engine.model_gateway.recording import RecordingProvider


def _request(request_id: str = "req-1", model: ModelRef | None = None) -> GenerateRequest:
    return GenerateRequest(
        request_id=request_id,
        model=model or ModelRef("groq", "llama-3.3-70b-versatile"),
        messages=(Message(ChatRole.USER, "hello"),),
        max_output_tokens=256,
        timeout_seconds=30.0,
    )


class StubProvider:
    """A ModelProvider that always succeeds with a known token usage - never touches the network."""

    def __init__(self, provider_id: str = "groq") -> None:
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def health(self) -> ProviderHealth:
        return ProviderHealth(self._provider_id, HealthStatus.HEALTHY, datetime.now(UTC), "ok")

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return GenerateResponse(
            request.request_id,
            request.model,
            "generated text",
            FinishReason.STOP,
            TokenUsage(100, 50),
            42,
        )

    async def stream(self, request: GenerateRequest):
        yield StreamEvent(request.request_id, 0, "generated ", False)
        yield StreamEvent(request.request_id, 1, "text", True, TokenUsage(100, 50))


class FailingProvider:
    """A ModelProvider whose generate() always raises - never touches the network."""

    provider_id = "groq"

    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.provider_id, HealthStatus.UNAVAILABLE, datetime.now(UTC), "down")

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        error = ModelProviderError("boom")
        error.code = "provider_unavailable"
        raise error

    async def stream(self, request: GenerateRequest):
        yield StreamEvent(request.request_id, 0, "partial", False)
        error = ModelProviderError("boom")
        error.code = "provider_unavailable"
        raise error


class RecordingProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_call_is_recorded_with_real_usage(self) -> None:
        ledger = UsageLedger()
        provider = RecordingProvider(StubProvider(), ledger)

        response = await provider.generate(_request())

        self.assertEqual(response.text, "generated text")
        self.assertEqual(len(ledger), 1)
        record = ledger.records()[0]
        self.assertEqual(record.provider_id, "groq")
        self.assertEqual(record.model_id, "llama-3.3-70b-versatile")
        self.assertEqual(record.tier, "cloud")
        self.assertTrue(record.success)
        self.assertEqual(record.input_tokens, 100)
        self.assertEqual(record.output_tokens, 50)
        self.assertEqual(
            record.cost_usd,
            DEFAULT_PRICE_BOOK.cost_for("groq", "llama-3.3-70b-versatile", TokenUsage(100, 50)),
        )
        self.assertGreater(record.cost_usd, 0)

    async def test_local_ollama_calls_are_recorded_as_zero_cost(self) -> None:
        ledger = UsageLedger()
        provider = RecordingProvider(
            StubProvider(OLLAMA_PROVIDER_ID), ledger
        )

        await provider.generate(_request(model=ModelRef(OLLAMA_PROVIDER_ID, "llama3.2")))

        record = ledger.records()[0]
        self.assertEqual(record.provider_id, OLLAMA_PROVIDER_ID)
        self.assertEqual(record.tier, "local")
        self.assertEqual(record.cost_usd, 0)

    async def test_failed_call_is_recorded_and_the_error_still_propagates(self) -> None:
        ledger = UsageLedger()
        provider = RecordingProvider(FailingProvider(), ledger)

        with self.assertRaises(ModelProviderError):
            await provider.generate(_request())

        self.assertEqual(len(ledger), 1)
        record = ledger.records()[0]
        self.assertFalse(record.success)
        self.assertEqual(record.error_code, "provider_unavailable")
        self.assertEqual(record.input_tokens, 0)
        self.assertIsNone(record.cost_usd)

    async def test_successful_stream_is_recorded_with_real_usage(self) -> None:
        """R-484: RecordingProvider.stream() must exist and record real usage - the original gap
        this test guards against is exactly the one the R-484 live smoke test hit: streaming
        through a real build call always wraps the provider in RecordingProvider for usage
        tracking, so a RecordingProvider with no .stream() breaks every real streamed build."""
        ledger = UsageLedger()
        provider = RecordingProvider(StubProvider(), ledger)

        deltas = []
        async for event in provider.stream(_request()):
            deltas.append(event.delta)

        self.assertEqual("".join(deltas), "generated text")
        self.assertEqual(len(ledger), 1)
        record = ledger.records()[0]
        self.assertEqual(record.provider_id, "groq")
        self.assertEqual(record.model_id, "llama-3.3-70b-versatile")
        self.assertEqual(record.tier, "cloud")
        self.assertTrue(record.success)
        self.assertEqual(record.input_tokens, 100)
        self.assertEqual(record.output_tokens, 50)
        self.assertEqual(
            record.cost_usd,
            DEFAULT_PRICE_BOOK.cost_for("groq", "llama-3.3-70b-versatile", TokenUsage(100, 50)),
        )
        self.assertGreater(record.cost_usd, 0)

    async def test_local_ollama_stream_is_recorded_as_zero_cost(self) -> None:
        ledger = UsageLedger()
        provider = RecordingProvider(StubProvider(OLLAMA_PROVIDER_ID), ledger)

        async for _event in provider.stream(_request(model=ModelRef(OLLAMA_PROVIDER_ID, "llama3.2"))):
            pass

        record = ledger.records()[0]
        self.assertEqual(record.provider_id, OLLAMA_PROVIDER_ID)
        self.assertEqual(record.tier, "local")
        self.assertEqual(record.cost_usd, 0)

    async def test_failed_stream_is_recorded_and_the_error_still_propagates(self) -> None:
        ledger = UsageLedger()
        provider = RecordingProvider(FailingProvider(), ledger)

        with self.assertRaises(ModelProviderError):
            async for _event in provider.stream(_request()):
                pass

        self.assertEqual(len(ledger), 1)
        record = ledger.records()[0]
        self.assertFalse(record.success)
        self.assertEqual(record.error_code, "provider_unavailable")
        self.assertEqual(record.input_tokens, 0)
        self.assertIsNone(record.cost_usd)

    async def test_stream_events_pass_through_unchanged(self) -> None:
        ledger = UsageLedger()
        provider = RecordingProvider(StubProvider(), ledger)

        events = [event async for event in provider.stream(_request())]

        self.assertEqual(len(events), 2)
        self.assertFalse(events[0].done)
        self.assertTrue(events[1].done)
        self.assertEqual(events[1].usage, TokenUsage(100, 50))

    async def test_health_and_discover_models_and_provider_id_pass_through_unchanged(self) -> None:
        ledger = UsageLedger()
        inner = StubProvider()
        provider = RecordingProvider(inner, ledger)

        self.assertEqual(provider.provider_id, inner.provider_id)
        health = await provider.health()
        self.assertEqual(health.provider_id, inner.provider_id)
        self.assertEqual(await provider.discover_models(), ())
        self.assertEqual(len(ledger), 0)  # health/discover_models are not billable generation calls


if __name__ == "__main__":
    unittest.main()
