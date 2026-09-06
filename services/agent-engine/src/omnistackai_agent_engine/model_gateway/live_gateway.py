"""Opt-in live run of the Balanced Model Gateway against local Ollama.

Demonstrates the platform routing real work through `ModelGateway`: the deterministic escalation
ladder is printed for every complexity level, then an L2 generation and an L1 stream are dispatched
to the local Ollama provider resolved from the registry. Excluded from static `task verify`, which
stays network-independent.
"""

from __future__ import annotations

import asyncio
import os

from .contracts import (
    CapabilityStatus,
    ChatRole,
    HealthStatus,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
)
from .errors import ModelGatewayError, ProviderUnavailableError
from .gateway import ModelGateway, RoutingPolicy, RoutingTask, TaskComplexity
from .ollama import OLLAMA_PROVIDER_ID, OllamaModelProfile, OllamaProvider
from .registry import ProviderRegistry


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise SystemExit(f"{name} must be a positive integer") from error
    if value <= 0:
        raise SystemExit(f"{name} must be a positive integer")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except ValueError as error:
        raise SystemExit(f"{name} must be a positive number") from error
    if value <= 0:
        raise SystemExit(f"{name} must be a positive number")
    return value


def _build_gateway() -> tuple[ModelGateway, ModelDescriptor, float]:
    base_url = os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model_id = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    context_window = _positive_int("OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS", 4_096)
    safe_input = _positive_int("OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS", 3_072)
    max_output = _positive_int("OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS", 1_024)
    request_timeout = _positive_float("OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS", 300.0)
    health_timeout = _positive_float("OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS", 5.0)
    max_concurrency = _positive_int("OMNISTACKAI_OLLAMA_MAX_CONCURRENCY", 1)

    descriptor = ModelDescriptor(
        ModelRef(OLLAMA_PROVIDER_ID, model_id),
        ModelCapabilities(
            text=CapabilityStatus.UNVERIFIED,
            streaming=CapabilityStatus.UNVERIFIED,
            tool_calling=CapabilityStatus.UNVERIFIED,
            structured_output=CapabilityStatus.UNVERIFIED,
            vision=CapabilityStatus.UNVERIFIED,
            embeddings=CapabilityStatus.UNVERIFIED,
        ),
        context_window,
        safe_input,
        max_output,
    )
    provider = OllamaProvider(
        base_url=base_url,
        model_profiles=(OllamaModelProfile(descriptor),),
        health_timeout_seconds=health_timeout,
        max_concurrency=max_concurrency,
    )
    registry = ProviderRegistry()
    registry.register(provider)
    # Stage 0 Balanced policy: local tier only; no cloud provider is configured or called.
    gateway = ModelGateway(registry, RoutingPolicy(local_model=descriptor, cloud_model=None))
    return gateway, descriptor, request_timeout


def _print_ladder(gateway: ModelGateway, model_id: str, timeout: float) -> None:
    print("Balanced routing decisions (deterministic, no model call):")
    for complexity in TaskComplexity:
        task = RoutingTask(
            request_id=f"probe-{complexity.value.lower()}",
            messages=(Message(ChatRole.USER, "route probe"),),
            max_output_tokens=16,
            timeout_seconds=timeout,
            complexity=complexity,
        )
        try:
            decision = gateway.resolve(task)
            outcome = f"-> {decision.tier.value} provider {decision.provider_id} ({model_id})"
        except ModelGatewayError as error:
            outcome = f"-> refused ({error.code})"
        print(f"  {complexity.value}: {outcome}")


async def _run() -> None:
    gateway, descriptor, request_timeout = _build_gateway()
    model_id = descriptor.model.model_id
    output_limit = min(descriptor.max_output_tokens, 32)

    _print_ladder(gateway, model_id, request_timeout)

    prompt = os.environ.get(
        "OMNISTACKAI_GATEWAY_PROMPT", "Reply with exactly: gateway routed to local model"
    )

    try:
        response = await gateway.generate(
            RoutingTask(
                request_id="r007-live-generate",
                messages=(Message(ChatRole.USER, prompt),),
                max_output_tokens=output_limit,
                timeout_seconds=request_timeout,
                complexity=TaskComplexity.L2,
            )
        )
    except ProviderUnavailableError as error:
        raise SystemExit(
            f"Local provider is unavailable ({error.code}); no cloud fallback is configured. "
            "Start Ollama and retry."
        ) from error

    if not response.text.strip() or response.usage.output_tokens < 1:
        raise SystemExit("Gateway generation did not return measured output")
    print(f"\nL2 generate -> {response.model.provider_id}: {response.text.strip()!r} "
          f"({response.usage.output_tokens} output tokens, {response.latency_ms} ms)")

    events = [
        event
        async for event in gateway.stream(
            RoutingTask(
                request_id="r007-live-stream",
                messages=(Message(ChatRole.USER, "Reply with exactly: gateway streaming works"),),
                max_output_tokens=output_limit,
                timeout_seconds=request_timeout,
                complexity=TaskComplexity.L1,
            )
        )
    ]
    if not events or not events[-1].done or events[-1].usage is None:
        raise SystemExit("Gateway streaming did not return a complete response")
    streamed = "".join(event.delta for event in events).strip()
    print(f"L1 stream   -> {streamed!r} ({len(events)} events, "
          f"{events[-1].usage.output_tokens} output tokens)")

    print(f"\nPlatform is running on local Ollama via the Balanced gateway: "
          f"model={model_id}, local provider healthy, cloud_calls=0.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
