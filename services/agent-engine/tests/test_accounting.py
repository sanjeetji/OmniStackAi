import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from unittest import TestCase

from omnistackai_agent_engine.model_gateway import (
    CapabilityStatus,
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelGateway,
    ModelPrice,
    ModelRef,
    PriceBook,
    ProviderHealth,
    ProviderRegistry,
    ProviderUnavailableError,
    RoutingPolicy,
    RoutingTask,
    StreamEvent,
    TaskComplexity,
    TokenUsage,
    UsageLedger,
    UsageRecord,
)

OLLAMA = "ollama-local"


class RecordingProvider:
    def __init__(self, provider_id: str, *, healthy: bool = True) -> None:
        self._provider_id = provider_id
        self._healthy = healthy

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def health(self) -> ProviderHealth:
        status = HealthStatus.HEALTHY if self._healthy else HealthStatus.UNAVAILABLE
        return ProviderHealth(self._provider_id, status, datetime.now(UTC), "ok" if self._healthy else "down")

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return GenerateResponse(request.request_id, request.model, "ok", FinishReason.STOP, TokenUsage(10, 5), 7)

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(request.request_id, 0, "ok", True, TokenUsage(10, 5))


def _descriptor(provider_id: str = OLLAMA, model_id: str = "qwen2.5-coder:14b") -> ModelDescriptor:
    return ModelDescriptor(
        ModelRef(provider_id, model_id),
        ModelCapabilities(
            text=CapabilityStatus.UNVERIFIED, streaming=CapabilityStatus.UNVERIFIED,
            tool_calling=CapabilityStatus.UNSUPPORTED, structured_output=CapabilityStatus.UNSUPPORTED,
            vision=CapabilityStatus.UNSUPPORTED, embeddings=CapabilityStatus.UNSUPPORTED,
        ),
        4096, 3072, 1024,
    )


def _task(complexity: TaskComplexity = TaskComplexity.L2) -> RoutingTask:
    return RoutingTask("req-1", (Message(ChatRole.USER, "hi"),), 64, 30.0, complexity)


class ModelPriceTests(TestCase):
    def test_float_price_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            ModelPrice(3.0, 15.0)  # type: ignore[arg-type]

    def test_cost_is_exact_decimal(self) -> None:
        price = ModelPrice("3", "15")
        cost = price.cost_for(TokenUsage(1000, 500))
        self.assertEqual(cost, Decimal("0.010500"))

    def test_cached_input_is_priced_separately(self) -> None:
        price = ModelPrice("3", "15", cached_input_usd_per_million="0.3")
        cost = price.cost_for(TokenUsage(1000, 0, cached_input_tokens=400))
        # 600 billed @3 + 400 cached @0.3 = 0.0018 + 0.00012 = 0.00192
        self.assertEqual(cost, Decimal("0.001920"))


class PriceBookTests(TestCase):
    def test_exact_wildcard_and_unknown(self) -> None:
        book = PriceBook({
            ("openai", "gpt-4o"): ModelPrice("2.5", "10"),
            ("ollama-local", None): ModelPrice("0", "0"),
        })
        self.assertEqual(book.cost_for("openai", "gpt-4o", TokenUsage(1_000_000, 0)), Decimal("2.500000"))
        self.assertEqual(book.cost_for("ollama-local", "qwen2.5-coder:14b", TokenUsage(9, 9)), Decimal("0.000000"))
        self.assertIsNone(book.cost_for("openai", "unknown-model", TokenUsage(1, 1)))


class UsageRecordTests(TestCase):
    def _record(self, **overrides: object) -> UsageRecord:
        base = dict(
            request_id="r", provider_id="openai", model_id="gpt-4o", tier="cloud", complexity="L3",
            input_tokens=1, output_tokens=1, cached_input_tokens=0, latency_ms=1, success=True,
            finish_reason="stop", error_code=None, cost_usd=Decimal("0.0"), created_at=datetime.now(UTC),
        )
        base.update(overrides)
        return UsageRecord(**base)  # type: ignore[arg-type]

    def test_valid_record_and_no_content_fields(self) -> None:
        record = self._record()
        self.assertEqual(record.model_id, "gpt-4o")
        forbidden = {"content", "messages", "text", "prompt", "request", "payload", "api_key", "response"}
        self.assertEqual(forbidden & set(UsageRecord.__dataclass_fields__), set())

    def test_negative_tokens_and_naive_datetime_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._record(input_tokens=-1)
        with self.assertRaises(ValueError):
            self._record(created_at=datetime(2026, 1, 1))  # naive


class UsageLedgerTests(TestCase):
    def _ledger(self) -> UsageLedger:
        return UsageLedger(PriceBook({
            ("openai", "gpt-4o"): ModelPrice("2.5", "10"),
            ("ollama-local", None): ModelPrice("0", "0"),
        }))

    def test_records_success_failure_and_unpriced(self) -> None:
        ledger = self._ledger()
        ledger.record_call(request_id="a", provider_id="openai", model_id="gpt-4o", tier="cloud",
                           complexity="L3", usage=TokenUsage(1_000_000, 1_000_000), latency_ms=100, success=True)
        ledger.record_call(request_id="b", provider_id="openai", model_id="gpt-4o", tier="cloud",
                           complexity="L3", usage=None, latency_ms=20, success=False, error_code="provider_timeout")
        ledger.record_call(request_id="c", provider_id="openai", model_id="mystery", tier="cloud",
                           complexity="L3", usage=TokenUsage(10, 10), latency_ms=50, success=True)
        summary = ledger.summary()
        self.assertEqual((summary.total_calls, summary.successful_calls, summary.failed_calls), (3, 2, 1))
        self.assertEqual(summary.total_cost_usd, Decimal("12.500000"))  # 2.5 + 10 for 1M each
        self.assertEqual(summary.unpriced_calls, 1)
        self.assertEqual(summary.cost_per_successful_call_usd, Decimal("12.500000"))  # one priced success

    def test_latency_percentiles_are_deterministic(self) -> None:
        ledger = self._ledger()
        for i, latency in enumerate([10, 20, 30, 40, 100]):
            ledger.record_call(request_id=f"r{i}", provider_id="ollama-local", model_id="qwen2.5-coder:14b",
                               tier="local", complexity="L2", usage=TokenUsage(1, 1), latency_ms=latency, success=True)
        summary = ledger.summary()
        self.assertEqual(summary.latency_p50_ms, 30)
        self.assertEqual(summary.latency_p95_ms, 100)
        self.assertEqual(summary.total_cost_usd, Decimal("0.000000"))

    def test_breakdown_is_grouped_and_sorted(self) -> None:
        ledger = self._ledger()
        ledger.record_call(request_id="a", provider_id="openai", model_id="gpt-4o", tier="cloud",
                           complexity="L3", usage=TokenUsage(2, 2), latency_ms=5, success=True)
        ledger.record_call(request_id="b", provider_id="ollama-local", model_id="qwen2.5-coder:14b",
                           tier="local", complexity="L2", usage=TokenUsage(3, 3), latency_ms=6, success=True)
        breakdowns = ledger.summary().breakdowns
        self.assertEqual([(b.provider_id, b.model_id) for b in breakdowns],
                         [("ollama-local", "qwen2.5-coder:14b"), ("openai", "gpt-4o")])


class GatewayAccountingTests(TestCase):
    def _gateway(self, *, healthy: bool = True) -> tuple[ModelGateway, UsageLedger]:
        registry = ProviderRegistry()
        registry.register(RecordingProvider(OLLAMA, healthy=healthy))
        ledger = UsageLedger()
        gateway = ModelGateway(registry, RoutingPolicy(local_model=_descriptor()), recorder=ledger)
        return gateway, ledger

    def test_success_is_recorded_without_changing_response(self) -> None:
        gateway, ledger = self._gateway()
        response = asyncio.run(gateway.generate(_task()))
        self.assertEqual(response.text, "ok")
        records = ledger.records()
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].success)
        self.assertEqual((records[0].input_tokens, records[0].output_tokens), (10, 5))
        self.assertEqual(records[0].provider_id, OLLAMA)
        self.assertEqual(records[0].cost_usd, Decimal("0.000000"))  # local is free
        self.assertEqual(records[0].finish_reason, "stop")

    def test_failure_is_recorded_and_error_reraised(self) -> None:
        gateway, ledger = self._gateway(healthy=False)
        with self.assertRaises(ProviderUnavailableError):
            asyncio.run(gateway.generate(_task()))
        records = ledger.records()
        self.assertEqual(len(records), 1)
        self.assertFalse(records[0].success)
        self.assertEqual(records[0].error_code, "provider_unavailable")

    def test_stream_records_one_success(self) -> None:
        gateway, ledger = self._gateway()

        async def run():
            return [e async for e in gateway.stream(_task(TaskComplexity.L1))]

        events = asyncio.run(run())
        self.assertTrue(events[-1].done)
        self.assertEqual(len(ledger.records()), 1)
        self.assertTrue(ledger.records()[0].success)

    def test_gateway_without_recorder_records_nothing(self) -> None:
        registry = ProviderRegistry()
        registry.register(RecordingProvider(OLLAMA))
        gateway = ModelGateway(registry, RoutingPolicy(local_model=_descriptor()))
        response = asyncio.run(gateway.generate(_task()))
        self.assertEqual(response.text, "ok")
