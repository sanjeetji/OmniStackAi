import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest import TestCase

from omnistackai_agent_engine.model_gateway import (
    CapabilityStatus,
    ContextBudgetExceededError,
    DeterministicWorkNotRoutableError,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    InvalidRoutingTaskError,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelGateway,
    ModelRef,
    NoEligibleProviderError,
    ProviderHealth,
    ProviderRegistry,
    ProviderUnavailableError,
    RoutingMode,
    RoutingPolicy,
    RoutingTask,
    RoutingTier,
    StreamEvent,
    TaskComplexity,
    TokenUsage,
    ChatRole,
    estimate_input_tokens,
)

OLLAMA_PROVIDER_ID = "ollama-local"
CLOUD_PROVIDER_ID = "cloud-test"


class RecordingProvider:
    """In-memory ModelProvider that records dispatches and never touches the network."""

    def __init__(self, provider_id: str, *, healthy: bool = True) -> None:
        self._provider_id = provider_id
        self._healthy = healthy
        self.generate_calls: list[GenerateRequest] = []
        self.stream_calls: list[GenerateRequest] = []
        self.health_calls = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def health(self) -> ProviderHealth:
        self.health_calls += 1
        status = HealthStatus.HEALTHY if self._healthy else HealthStatus.UNAVAILABLE
        detail = "ok" if self._healthy else "provider_unavailable"
        return ProviderHealth(self._provider_id, status, datetime.now(UTC), detail)

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.generate_calls.append(request)
        return GenerateResponse(
            request.request_id,
            request.model,
            "dispatched",
            FinishReason.STOP,
            TokenUsage(2, 3),
            7,
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        self.stream_calls.append(request)
        yield StreamEvent(request.request_id, 0, "dis", False)
        yield StreamEvent(request.request_id, 1, "patched", True, TokenUsage(2, 3))


def _descriptor(
    provider_id: str = OLLAMA_PROVIDER_ID,
    model_id: str = "qwen2.5-coder:14b",
    *,
    text: CapabilityStatus = CapabilityStatus.UNVERIFIED,
    context_window_tokens: int = 4096,
    safe_input_tokens: int = 3072,
    max_output_tokens: int = 1024,
) -> ModelDescriptor:
    return ModelDescriptor(
        model=ModelRef(provider_id, model_id),
        capabilities=ModelCapabilities(
            text=text,
            streaming=CapabilityStatus.UNVERIFIED,
            tool_calling=CapabilityStatus.UNSUPPORTED,
            structured_output=CapabilityStatus.UNSUPPORTED,
            vision=CapabilityStatus.UNSUPPORTED,
            embeddings=CapabilityStatus.UNSUPPORTED,
        ),
        context_window_tokens=context_window_tokens,
        safe_input_tokens=safe_input_tokens,
        max_output_tokens=max_output_tokens,
    )


def _task(
    complexity: TaskComplexity,
    *,
    content: str = "implement the feature",
    max_output_tokens: int = 256,
) -> RoutingTask:
    return RoutingTask(
        request_id="req-1",
        messages=(Message(ChatRole.USER, content),),
        max_output_tokens=max_output_tokens,
        timeout_seconds=30.0,
        complexity=complexity,
        routing_mode=RoutingMode.BALANCED,
    )


def _gateway(
    *,
    local_registered: bool = True,
    local_healthy: bool = True,
    cloud_model: ModelDescriptor | None = None,
    cloud_registered: bool = False,
    cloud_healthy: bool = True,
    local_descriptor: ModelDescriptor | None = None,
) -> tuple[ModelGateway, dict[str, RecordingProvider]]:
    registry = ProviderRegistry()
    providers: dict[str, RecordingProvider] = {}
    if local_registered:
        local = RecordingProvider(OLLAMA_PROVIDER_ID, healthy=local_healthy)
        registry.register(local)
        providers[OLLAMA_PROVIDER_ID] = local
    if cloud_registered:
        cloud = RecordingProvider(CLOUD_PROVIDER_ID, healthy=cloud_healthy)
        registry.register(cloud)
        providers[CLOUD_PROVIDER_ID] = cloud
    policy = RoutingPolicy(
        local_model=local_descriptor or _descriptor(),
        cloud_model=cloud_model,
    )
    return ModelGateway(registry, policy), providers


class RoutingLadderTests(TestCase):
    def test_l0_deterministic_work_is_not_routable(self) -> None:
        gateway, _ = _gateway()
        with self.assertRaises(DeterministicWorkNotRoutableError) as raised:
            gateway.resolve(_task(TaskComplexity.L0))
        self.assertEqual(raised.exception.code, "deterministic_work_not_routable")

    def test_balanced_routes_sub_l3_work_to_local_provider(self) -> None:
        gateway, _ = _gateway()
        for complexity in (TaskComplexity.L1, TaskComplexity.L2):
            decision = gateway.resolve(_task(complexity))
            self.assertEqual(decision.tier, RoutingTier.LOCAL)
            self.assertEqual(decision.provider_id, OLLAMA_PROVIDER_ID)
            self.assertEqual(decision.model, ModelRef(OLLAMA_PROVIDER_ID, "qwen2.5-coder:14b"))
            self.assertEqual(decision.request.model, decision.model)

    def test_high_risk_work_requires_cloud_escalation_when_unconfigured(self) -> None:
        gateway, _ = _gateway()
        for complexity in (TaskComplexity.L3, TaskComplexity.L4):
            with self.assertRaises(NoEligibleProviderError) as raised:
                gateway.resolve(_task(complexity))
            self.assertEqual(raised.exception.code, "no_eligible_provider")

    def test_high_risk_work_routes_to_cloud_when_configured(self) -> None:
        gateway, _ = _gateway(
            cloud_model=_descriptor(CLOUD_PROVIDER_ID, "cloud-reasoner"),
            cloud_registered=True,
        )
        decision = gateway.resolve(_task(TaskComplexity.L3))
        self.assertEqual(decision.tier, RoutingTier.CLOUD)
        self.assertEqual(decision.provider_id, CLOUD_PROVIDER_ID)


class ProviderEligibilityTests(TestCase):
    def test_unregistered_local_provider_is_not_eligible(self) -> None:
        gateway, _ = _gateway(local_registered=False)
        with self.assertRaises(NoEligibleProviderError) as raised:
            gateway.resolve(_task(TaskComplexity.L2))
        self.assertEqual(raised.exception.code, "no_eligible_provider")

    def test_model_without_text_capability_is_not_eligible(self) -> None:
        gateway, _ = _gateway(local_descriptor=_descriptor(text=CapabilityStatus.UNSUPPORTED))
        with self.assertRaises(NoEligibleProviderError):
            gateway.resolve(_task(TaskComplexity.L2))


class ContextBudgetTests(TestCase):
    def test_estimate_is_conservative_relative_to_four_chars_per_token(self) -> None:
        message = Message(ChatRole.USER, "a" * 300)
        # Conservative estimate must not undercount a ~4-chars/token baseline.
        self.assertGreaterEqual(estimate_input_tokens((message,)), 300 // 4)

    def test_oversized_input_is_rejected_before_dispatch(self) -> None:
        gateway, providers = _gateway()
        oversized = _task(TaskComplexity.L2, content="a" * 9300)
        with self.assertRaises(ContextBudgetExceededError) as raised:
            gateway.resolve(oversized)
        self.assertEqual(raised.exception.code, "context_budget_exceeded")
        self.assertEqual(providers[OLLAMA_PROVIDER_ID].generate_calls, [])

    def test_output_over_budget_is_rejected(self) -> None:
        gateway, _ = _gateway()
        with self.assertRaises(ContextBudgetExceededError):
            gateway.resolve(_task(TaskComplexity.L2, max_output_tokens=1025))


class NoSilentFallbackTests(TestCase):
    def test_unavailable_local_provider_is_never_silently_escalated(self) -> None:
        gateway, providers = _gateway(
            local_healthy=False,
            cloud_model=_descriptor(CLOUD_PROVIDER_ID, "cloud-reasoner"),
            cloud_registered=True,
        )
        with self.assertRaises(ProviderUnavailableError) as raised:
            asyncio.run(gateway.generate(_task(TaskComplexity.L2)))
        self.assertEqual(raised.exception.code, "provider_unavailable")
        # The healthy cloud provider must not have been used as a hidden fallback.
        self.assertEqual(providers[CLOUD_PROVIDER_ID].generate_calls, [])
        self.assertEqual(providers[OLLAMA_PROVIDER_ID].generate_calls, [])


class DispatchTests(TestCase):
    def test_successful_generate_dispatches_resolved_request(self) -> None:
        gateway, providers = _gateway()
        response = asyncio.run(gateway.generate(_task(TaskComplexity.L2)))
        self.assertEqual(response.text, "dispatched")
        local = providers[OLLAMA_PROVIDER_ID]
        self.assertEqual(local.health_calls, 1)
        self.assertEqual(len(local.generate_calls), 1)
        self.assertEqual(local.generate_calls[0].model.provider_id, OLLAMA_PROVIDER_ID)

    def test_successful_stream_dispatches_resolved_request(self) -> None:
        gateway, providers = _gateway()

        async def collect() -> list[StreamEvent]:
            return [event async for event in gateway.stream(_task(TaskComplexity.L1))]

        events = asyncio.run(collect())
        self.assertEqual([event.delta for event in events], ["dis", "patched"])
        self.assertTrue(events[-1].done)
        self.assertEqual(len(providers[OLLAMA_PROVIDER_ID].stream_calls), 1)


class RoutingTaskValidationTests(TestCase):
    def test_invalid_tasks_are_rejected_with_stable_error(self) -> None:
        with self.assertRaises(InvalidRoutingTaskError):
            RoutingTask("req", (), 10, 1.0, TaskComplexity.L2)
        with self.assertRaises(InvalidRoutingTaskError):
            RoutingTask("req", (Message(ChatRole.USER, "x"),), 0, 1.0, TaskComplexity.L2)
        with self.assertRaises(InvalidRoutingTaskError):
            RoutingTask("req", (Message(ChatRole.USER, "x"),), 10, 0.0, TaskComplexity.L2)

    def test_gateway_requires_registry_and_policy(self) -> None:
        with self.assertRaises(InvalidRoutingTaskError):
            ModelGateway(object(), RoutingPolicy(local_model=_descriptor()))
        with self.assertRaises(InvalidRoutingTaskError):
            ModelGateway(ProviderRegistry(), object())
