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

from .contracts import (
    CapabilityStatus,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    Message,
    ModelDescriptor,
    ModelRef,
    StreamEvent,
)
from .errors import (
    ContextBudgetExceededError,
    DeterministicWorkNotRoutableError,
    InvalidRoutingTaskError,
    NoEligibleProviderError,
    ProviderUnavailableError,
)
from .errors import ProviderRegistryError
from .registry import ProviderRegistry

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

    def __post_init__(self) -> None:
        if not isinstance(self.local_model, ModelDescriptor):
            raise InvalidRoutingTaskError("local_model must be a ModelDescriptor")
        if self.cloud_model is not None and not isinstance(self.cloud_model, ModelDescriptor):
            raise InvalidRoutingTaskError("cloud_model must be a ModelDescriptor or None")

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

    def __init__(self, registry: ProviderRegistry, policy: RoutingPolicy) -> None:
        if not isinstance(registry, ProviderRegistry):
            raise InvalidRoutingTaskError("registry must be a ProviderRegistry")
        if not isinstance(policy, RoutingPolicy):
            raise InvalidRoutingTaskError("policy must be a RoutingPolicy")
        self._registry = registry
        self._policy = policy

    def resolve(self, task: RoutingTask) -> RoutingDecision:
        """Deterministically resolve a routing task without any network call.

        Raises a stable typed error for deterministic (L0) work, an unconfigured or unregistered
        provider tier, an ineligible model, or a context-budget overflow.
        """

        if not isinstance(task, RoutingTask):
            raise InvalidRoutingTaskError("task must be a RoutingTask")
        if task.routing_mode is not RoutingMode.BALANCED:
            raise InvalidRoutingTaskError("only balanced routing is supported at Stage 0")

        if task.complexity is TaskComplexity.L0:
            raise DeterministicWorkNotRoutableError(
                "L0 work must be answered by a deterministic tool, not a model"
            )

        tier = RoutingTier.LOCAL if task.complexity in _LOCAL_COMPLEXITIES else RoutingTier.CLOUD
        descriptor = self._policy.descriptor_for(tier)
        if descriptor is None:
            raise NoEligibleProviderError(
                f"no {tier.value} provider is configured for {task.complexity.value} work"
            )
        if descriptor.capabilities.text is CapabilityStatus.UNSUPPORTED:
            raise NoEligibleProviderError(
                f"the {tier.value} model does not support text generation"
            )

        provider_id = descriptor.model.provider_id
        try:
            self._registry.get(provider_id)
        except ProviderRegistryError as error:
            raise NoEligibleProviderError(
                f"the {tier.value} provider is not registered"
            ) from error

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
            raise ContextBudgetExceededError(
                "estimated input tokens exceed the model safe input budget"
            )
        if task.max_output_tokens > descriptor.max_output_tokens:
            raise ContextBudgetExceededError(
                "requested output tokens exceed the model max output budget"
            )

        return RoutingDecision(
            tier=tier,
            provider_id=provider_id,
            model=descriptor.model,
            request=request,
            estimated_input_tokens=estimated_input_tokens,
            complexity=task.complexity,
        )

    async def generate(self, task: RoutingTask) -> GenerateResponse:
        """Resolve, verify provider health, then dispatch a non-streaming generation."""

        decision = self.resolve(task)
        provider = self._registry.get(decision.provider_id)
        await self._require_healthy(provider, decision)
        return await provider.generate(decision.request)

    async def stream(self, task: RoutingTask) -> AsyncIterator[StreamEvent]:
        """Resolve, verify provider health, then dispatch a streaming generation."""

        decision = self.resolve(task)
        provider = self._registry.get(decision.provider_id)
        await self._require_healthy(provider, decision)
        async for event in provider.stream(decision.request):
            yield event

    @staticmethod
    async def _require_healthy(provider: object, decision: RoutingDecision) -> None:
        health = await provider.health()  # type: ignore[attr-defined]
        if health.status is not HealthStatus.HEALTHY:
            raise ProviderUnavailableError(
                f"the resolved {decision.tier.value} provider is unavailable"
            )
