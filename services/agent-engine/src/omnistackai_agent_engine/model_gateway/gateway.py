"""Deterministic Balanced Model Gateway router over the ModelProvider boundary.

The gateway is the only component that decides which registered ``ModelProvider`` serves a
request. Product/domain code submits a :class:`RoutingTask` describing the work — its complexity
and messages — and never names a provider or model (Brief 18, 18.3, 84; non-negotiable 92.4).

Stage 0 policy (Brief 18.1 escalation ladder, 84 routing policy):

- ``L0`` deterministic work is refused: a deterministic tool must answer instead of a model.
- ``L1``/``L2`` (sub-L3) route to the configured local tier (the loopback Ollama provider).
- ``L3``/``L4`` route to the cloud tier, which is unconfigured at Stage 0 and therefore returns a
  stable escalation-required error. High-risk work is never silently downgraded to the local model,
  and an unavailable local provider is never silently escalated to an unauthorized cloud provider
  (non-negotiable 92.4).

A conservative, deterministic token estimate guards each request against the resolved model's
safe-input and max-output budgets rather than silently truncating (Brief 85, 18.2; non-negotiable
92.6). Routing is fully deterministic and requires no model call to run or to test.
"""

from __future__ import annotations

import math
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic

from .accounting import UsageLedger
from .contracts import (
    CapabilityStatus,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    Message,
    ModelDescriptor,
    ModelRef,
    StreamEvent,
    TokenUsage,
)
from .errors import (
    AllProvidersFailedError,
    ContextBudgetExceededError,
    DeterministicWorkNotRoutableError,
    InvalidRoutingTaskError,
    ModelGatewayError,
    ModelProviderError,
    NoEligibleProviderError,
    ProviderHTTPError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .errors import ProviderRegistryError
from .registry import ProviderRegistry
from .resilience import CircuitBreaker

_RETRIABLE_ERRORS = (ProviderUnavailableError, ProviderTimeoutError, ProviderHTTPError)

# Conservative estimator: assume more tokens per request than a typical ~4 chars/token tokenizer
# would, so the budget guard never under-counts and lets an oversized Context Pack through.
_CHARS_PER_TOKEN = 3
_PER_MESSAGE_OVERHEAD_TOKENS = 4


class TaskComplexity(StrEnum):
    """LLM escalation-ladder level for a unit of work (Brief 18.1)."""

    L0 = "L0"  # deterministic engine work; not routable to a model
    L1 = "L1"  # small/cheap model work
    L2 = "L2"  # coding model work
    L3 = "L3"  # strong reasoning model work
    L4 = "L4"  # independent reviewer/model work


class RoutingMode(StrEnum):
    """Provider-selection policy. Stage 0 supports Balanced only."""

    BALANCED = "balanced"


class RoutingTier(StrEnum):
    """Resolved provider tier for a routing decision."""

    LOCAL = "local"
    CLOUD = "cloud"


_LOCAL_COMPLEXITIES = frozenset({TaskComplexity.L1, TaskComplexity.L2})
_CLOUD_COMPLEXITIES = frozenset({TaskComplexity.L3, TaskComplexity.L4})


def estimate_input_tokens(messages: tuple[Message, ...]) -> int:
    """Return a conservative deterministic token estimate for request messages."""

    total = 0
    for message in messages:
        total += _PER_MESSAGE_OVERHEAD_TOKENS
        total += -(-len(message.content) // _CHARS_PER_TOKEN)  # ceil division
    return total


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Deterministic tier-to-model policy resolved without any network call.

    ``local_model`` is the descriptor used for sub-L3 work. ``cloud_model`` stays ``None`` at
    Stage 0; when a cloud adapter is registered by a later Tracker ID, populating it enables L3/L4
    escalation with no gateway change.
    """

    local_model: ModelDescriptor
    cloud_model: ModelDescriptor | None = None
    fallback: tuple[ModelDescriptor, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.local_model, ModelDescriptor):
            raise InvalidRoutingTaskError("local_model must be a ModelDescriptor")
        if self.cloud_model is not None and not isinstance(self.cloud_model, ModelDescriptor):
            raise InvalidRoutingTaskError("cloud_model must be a ModelDescriptor or None")
        if not isinstance(self.fallback, tuple) or any(
            not isinstance(descriptor, ModelDescriptor) for descriptor in self.fallback
        ):
            raise InvalidRoutingTaskError("fallback must be a tuple of ModelDescriptor")

    def descriptor_for(self, tier: RoutingTier) -> ModelDescriptor | None:
        if tier is RoutingTier.LOCAL:
            return self.local_model
        return self.cloud_model


@dataclass(frozen=True, slots=True)
class RoutingTask:
    """Provider-agnostic description of a unit of model work."""

    request_id: str
    messages: tuple[Message, ...]
    max_output_tokens: int
    timeout_seconds: float
    complexity: TaskComplexity
    routing_mode: RoutingMode = RoutingMode.BALANCED

    def __post_init__(self) -> None:
        if not isinstance(self.complexity, TaskComplexity):
            raise InvalidRoutingTaskError("complexity must be a TaskComplexity")
        if not isinstance(self.routing_mode, RoutingMode):
            raise InvalidRoutingTaskError("routing_mode must be a RoutingMode")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise InvalidRoutingTaskError("messages must be a non-empty tuple")
        if any(not isinstance(message, Message) for message in self.messages):
            raise InvalidRoutingTaskError("messages must contain only Message values")
        if isinstance(self.max_output_tokens, bool) or not isinstance(self.max_output_tokens, int) or self.max_output_tokens <= 0:
            raise InvalidRoutingTaskError("max_output_tokens must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise InvalidRoutingTaskError("timeout_seconds must be a positive finite number")


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Deterministic outcome of resolving a routing task to a provider and request."""

    tier: RoutingTier
    provider_id: str
    model: ModelRef
    request: GenerateRequest
    estimated_input_tokens: int
    complexity: TaskComplexity


class ModelGateway:
    """Selects a registered provider for a routing task and dispatches the model call."""

    def __init__(
        self,
        registry: ProviderRegistry,
        policy: RoutingPolicy,
        *,
        recorder: UsageLedger | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        if not isinstance(registry, ProviderRegistry):
            raise InvalidRoutingTaskError("registry must be a ProviderRegistry")
        if not isinstance(policy, RoutingPolicy):
            raise InvalidRoutingTaskError("policy must be a RoutingPolicy")
        if recorder is not None and not isinstance(recorder, UsageLedger):
            raise InvalidRoutingTaskError("recorder must be a UsageLedger or None")
        if breaker is not None and not isinstance(breaker, CircuitBreaker):
            raise InvalidRoutingTaskError("breaker must be a CircuitBreaker or None")
        self._registry = registry
        self._policy = policy
        self._recorder = recorder
        self._breaker = breaker

    def resolve(self, task: RoutingTask) -> RoutingDecision:
        """Deterministically resolve a routing task without any network call.

        Raises a stable typed error for deterministic (L0) work, an unconfigured or unregistered
        provider tier, an ineligible model, or a context-budget overflow.
        """

        if not isinstance(task, RoutingTask):
            raise InvalidRoutingTaskError("task must be a RoutingTask")
        if task.routing_mode is not RoutingMode.BALANCED:
            raise InvalidRoutingTaskError("only balanced routing is supported at Stage 0")

        tier, descriptor = self._resolve_tier(task)
        if descriptor is None:
            raise NoEligibleProviderError(
                f"no {tier.value} provider is configured for {task.complexity.value} work"
            )
        return self._build_decision(task, tier, descriptor)

    def _resolve_tier(self, task: RoutingTask) -> tuple[RoutingTier, ModelDescriptor | None]:
        if task.complexity is TaskComplexity.L0:
            raise DeterministicWorkNotRoutableError(
                "L0 work must be answered by a deterministic tool, not a model"
            )
        tier = RoutingTier.LOCAL if task.complexity in _LOCAL_COMPLEXITIES else RoutingTier.CLOUD
        return tier, self._policy.descriptor_for(tier)

    def _build_decision(
        self, task: RoutingTask, tier: RoutingTier, descriptor: ModelDescriptor
    ) -> RoutingDecision:
        if descriptor.capabilities.text is CapabilityStatus.UNSUPPORTED:
            raise NoEligibleProviderError(f"the {tier.value} model does not support text generation")
        provider_id = descriptor.model.provider_id
        try:
            self._registry.get(provider_id)
        except ProviderRegistryError as error:
            raise NoEligibleProviderError(f"the {tier.value} provider is not registered") from error
        try:
            request = GenerateRequest(
                request_id=task.request_id,
                model=descriptor.model,
                messages=task.messages,
                max_output_tokens=task.max_output_tokens,
                timeout_seconds=task.timeout_seconds,
            )
        except (TypeError, ValueError) as error:
            raise InvalidRoutingTaskError("routing task does not form a valid request") from error
        estimated_input_tokens = estimate_input_tokens(task.messages)
        if estimated_input_tokens > descriptor.safe_input_tokens:
            raise ContextBudgetExceededError("estimated input tokens exceed the model safe input budget")
        if task.max_output_tokens > descriptor.max_output_tokens:
            raise ContextBudgetExceededError("requested output tokens exceed the model max output budget")
        return RoutingDecision(
            tier=tier,
            provider_id=provider_id,
            model=descriptor.model,
            request=request,
            estimated_input_tokens=estimated_input_tokens,
            complexity=task.complexity,
        )

    def _candidates(self, task: RoutingTask) -> list[RoutingDecision]:
        """Ordered, buildable dispatch candidates: the primary then the explicit fallback chain."""

        if not self._policy.fallback:
            return [self.resolve(task)]  # unchanged single-provider behavior
        if not isinstance(task, RoutingTask):
            raise InvalidRoutingTaskError("task must be a RoutingTask")
        if task.routing_mode is not RoutingMode.BALANCED:
            raise InvalidRoutingTaskError("only balanced routing is supported at Stage 0")
        tier, primary = self._resolve_tier(task)
        descriptors = ([primary] if primary is not None else []) + list(self._policy.fallback)
        decisions: list[RoutingDecision] = []
        first_error: ModelGatewayError | None = None
        for descriptor in descriptors:
            try:
                decisions.append(self._build_decision(task, tier, descriptor))
            except (NoEligibleProviderError, ContextBudgetExceededError) as error:
                first_error = first_error or error
        if not decisions:
            raise first_error or NoEligibleProviderError("no eligible provider is configured")
        return decisions

    async def generate(self, task: RoutingTask) -> GenerateResponse:
        """Dispatch a non-streaming generation, failing over across the explicit candidate chain.

        Each attempt (success or failure) is recorded when a recorder is configured; a non-retriable
        error is raised immediately; a retriable one advances to the next allowlisted, registered,
        circuit-closed candidate. The returned response and raised error are never altered.
        """

        decisions = self._candidates(task)
        last_error: ModelProviderError | None = None
        for decision in decisions:
            if self._breaker is not None and not self._breaker.allows(decision.provider_id):
                continue
            provider = self._registry.get(decision.provider_id)
            started_at = monotonic()
            try:
                await self._require_healthy(provider, decision)
                response = await provider.generate(decision.request)
            except ModelProviderError as error:
                self._record_failure(decision, error, self._elapsed_ms(started_at))
                if self._breaker is not None:
                    self._breaker.record_failure(decision.provider_id)
                if isinstance(error, _RETRIABLE_ERRORS):
                    last_error = error
                    continue
                raise
            self._record(decision, response.usage, response.latency_ms, True, response.finish_reason.value)
            if self._breaker is not None:
                self._breaker.record_success(decision.provider_id)
            return response
        raise self._exhausted(decisions, last_error)

    async def stream(self, task: RoutingTask) -> AsyncIterator[StreamEvent]:
        """Dispatch a streaming generation with fail-over before the first event.

        Fail-over follows the explicit candidate chain only while no event has been yielded; once
        streaming has begun, a mid-stream error propagates. Each attempt is recorded when configured.
        """

        decisions = self._candidates(task)
        last_error: ModelProviderError | None = None
        for decision in decisions:
            if self._breaker is not None and not self._breaker.allows(decision.provider_id):
                continue
            provider = self._registry.get(decision.provider_id)
            started_at = monotonic()
            final_usage = None
            emitted = False
            try:
                await self._require_healthy(provider, decision)
                async for event in provider.stream(decision.request):
                    emitted = True
                    if event.done:
                        final_usage = event.usage
                    yield event
            except ModelProviderError as error:
                self._record_failure(decision, error, self._elapsed_ms(started_at))
                if self._breaker is not None:
                    self._breaker.record_failure(decision.provider_id)
                if not emitted and isinstance(error, _RETRIABLE_ERRORS):
                    last_error = error
                    continue
                raise
            self._record(decision, final_usage, self._elapsed_ms(started_at), True, None)
            if self._breaker is not None:
                self._breaker.record_success(decision.provider_id)
            return
        raise self._exhausted(decisions, last_error)

    def _exhausted(
        self, decisions: list[RoutingDecision], last_error: ModelProviderError | None
    ) -> Exception:
        if len(decisions) == 1 and last_error is not None:
            return last_error  # single provider: surface its own stable error unchanged
        error = AllProvidersFailedError("all configured providers were unavailable or failed")
        error.__cause__ = last_error
        return error

    def _record(
        self,
        decision: RoutingDecision,
        usage: TokenUsage | None,
        latency_ms: int,
        success: bool,
        finish_reason: str | None,
    ) -> None:
        if self._recorder is None:
            return
        self._recorder.record_call(
            request_id=decision.request.request_id,
            provider_id=decision.provider_id,
            model_id=decision.model.model_id,
            tier=decision.tier.value,
            complexity=decision.complexity.value,
            usage=usage,
            latency_ms=latency_ms,
            success=success,
            finish_reason=finish_reason,
        )

    def _record_failure(self, decision: RoutingDecision, error: ModelProviderError, latency_ms: int) -> None:
        if self._recorder is None:
            return
        self._recorder.record_call(
            request_id=decision.request.request_id,
            provider_id=decision.provider_id,
            model_id=decision.model.model_id,
            tier=decision.tier.value,
            complexity=decision.complexity.value,
            usage=None,
            latency_ms=latency_ms,
            success=False,
            error_code=getattr(error, "code", "model_provider_error"),
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, int((monotonic() - started_at) * 1000))

    @staticmethod
    async def _require_healthy(provider: object, decision: RoutingDecision) -> None:
        health = await provider.health()  # type: ignore[attr-defined]
        if health.status is not HealthStatus.HEALTHY:
            raise ProviderUnavailableError(
                f"the resolved {decision.tier.value} provider is unavailable"
            )
