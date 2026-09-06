import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest import TestCase

from omnistackai_agent_engine.model_gateway import (
    AllProvidersFailedError,
    CapabilityStatus,
    ChatRole,
    CircuitBreaker,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelGateway,
    ModelRef,
    ProviderHealth,
    ProviderRegistry,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RoutingPolicy,
    RoutingTask,
    StreamEvent,
    TaskComplexity,
    TokenUsage,
    UnsupportedModelRequestError,
    UsageLedger,
)

PRIMARY = "ollama-local"
FALLBACK = "anthropic"


class FakeProvider:
    def __init__(self, provider_id: str, *, healthy: bool = True, generate_error: Exception | None = None) -> None:
        self._provider_id = provider_id
        self._healthy = healthy
        self._generate_error = generate_error
        self.health_calls = 0
        self.generate_calls = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def health(self) -> ProviderHealth:
        self.health_calls += 1
        status = HealthStatus.HEALTHY if self._healthy else HealthStatus.UNAVAILABLE
        return ProviderHealth(self._provider_id, status, datetime.now(UTC), "ok" if self._healthy else "down")

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.generate_calls += 1
        if self._generate_error is not None:
            raise self._generate_error
        return GenerateResponse(request.request_id, request.model, self._provider_id, FinishReason.STOP, TokenUsage(1, 1), 5)

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        if self._generate_error is not None:
            raise self._generate_error
        yield StreamEvent(request.request_id, 0, self._provider_id, True, TokenUsage(1, 1))


def _descriptor(provider_id: str, model_id: str) -> ModelDescriptor:
    return ModelDescriptor(
        ModelRef(provider_id, model_id),
        ModelCapabilities(
            text=CapabilityStatus.UNVERIFIED, streaming=CapabilityStatus.UNVERIFIED,
            tool_calling=CapabilityStatus.UNSUPPORTED, structured_output=CapabilityStatus.UNSUPPORTED,
            vision=CapabilityStatus.UNSUPPORTED, embeddings=CapabilityStatus.UNSUPPORTED,
        ),
        4096, 3072, 1024,
    )


PRIMARY_DESC = _descriptor(PRIMARY, "qwen2.5-coder:14b")
FALLBACK_DESC = _descriptor(FALLBACK, "claude-sonnet-5")


def _task() -> RoutingTask:
    return RoutingTask("req-1", (Message(ChatRole.USER, "hi"),), 64, 30.0, TaskComplexity.L2)


def _gateway(primary: FakeProvider, fallback: FakeProvider | None, **kw):
    registry = ProviderRegistry()
    registry.register(primary)
    fb = ()
    if fallback is not None:
        registry.register(fallback)
        fb = (FALLBACK_DESC,)
    policy = RoutingPolicy(local_model=PRIMARY_DESC, fallback=fb)
    return ModelGateway(registry, policy, **kw)


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class FallbackTests(TestCase):
    def test_retriable_failure_fails_over_to_next_candidate(self) -> None:
        primary = FakeProvider(PRIMARY, healthy=False)
        fallback = FakeProvider(FALLBACK)
        gateway = _gateway(primary, fallback)
        response = asyncio.run(gateway.generate(_task()))
        self.assertEqual(response.text, FALLBACK)
        self.assertEqual(fallback.generate_calls, 1)

    def test_non_retriable_error_does_not_fall_over(self) -> None:
        primary = FakeProvider(PRIMARY, generate_error=UnsupportedModelRequestError("no tools"))
        fallback = FakeProvider(FALLBACK)
        gateway = _gateway(primary, fallback)
        with self.assertRaises(UnsupportedModelRequestError):
            asyncio.run(gateway.generate(_task()))
        self.assertEqual(fallback.generate_calls, 0)

    def test_all_candidates_failing_raises_all_providers_failed(self) -> None:
        gateway = _gateway(FakeProvider(PRIMARY, healthy=False), FakeProvider(FALLBACK, healthy=False))
        with self.assertRaises(AllProvidersFailedError) as raised:
            asyncio.run(gateway.generate(_task()))
        self.assertEqual(raised.exception.code, "all_providers_failed")

    def test_single_provider_without_fallback_reraises_its_error(self) -> None:
        gateway = _gateway(FakeProvider(PRIMARY, healthy=False), None)
        with self.assertRaises(ProviderUnavailableError):
            asyncio.run(gateway.generate(_task()))

    def test_stream_fails_over_before_first_event(self) -> None:
        primary = FakeProvider(PRIMARY, generate_error=ProviderTimeoutError("slow"))
        fallback = FakeProvider(FALLBACK)
        gateway = _gateway(primary, fallback)

        async def run():
            return [e async for e in gateway.stream(_task())]

        events = asyncio.run(run())
        self.assertEqual(events[-1].delta, FALLBACK)
        self.assertTrue(events[-1].done)

    def test_attempts_are_all_accounted(self) -> None:
        ledger = UsageLedger()
        gateway = _gateway(FakeProvider(PRIMARY, healthy=False), FakeProvider(FALLBACK), recorder=ledger)
        asyncio.run(gateway.generate(_task()))
        records = ledger.records()
        self.assertEqual(len(records), 2)
        self.assertFalse(records[0].success)
        self.assertEqual(records[0].provider_id, PRIMARY)
        self.assertTrue(records[1].success)
        self.assertEqual(records[1].provider_id, FALLBACK)


class CircuitBreakerTests(TestCase):
    def test_open_skips_provider_and_recovers_after_cooldown(self) -> None:
        clock = _Clock()
        breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=100.0, clock=clock)
        primary = FakeProvider(PRIMARY, healthy=False)
        fallback = FakeProvider(FALLBACK)
        gateway = _gateway(primary, fallback, breaker=breaker)

        asyncio.run(gateway.generate(_task()))  # attempt 1: primary fails (count 1)
        asyncio.run(gateway.generate(_task()))  # attempt 2: primary fails (count 2 -> open)
        self.assertEqual(primary.health_calls, 2)
        self.assertEqual(breaker.state(PRIMARY), "open")

        asyncio.run(gateway.generate(_task()))  # attempt 3: primary skipped (circuit open)
        self.assertEqual(primary.health_calls, 2)  # unchanged: not tried

        clock.t = 200.0  # cooldown elapsed -> half-open
        asyncio.run(gateway.generate(_task()))  # attempt 4: primary tried again
        self.assertEqual(primary.health_calls, 3)
        self.assertEqual(fallback.generate_calls, 4)

    def test_success_resets_the_breaker(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2)
        breaker.record_failure(PRIMARY)
        breaker.record_success(PRIMARY)
        self.assertTrue(breaker.allows(PRIMARY))
        self.assertEqual(breaker.state(PRIMARY), "closed")
