"""Opt-in live run of the Balanced Model Gateway.

Builds the gateway from the environment (local Ollama always, plus any cloud provider whose API key
is set), prints the deterministic routing decision for every complexity level, then dispatches an L2
generation and an L1 stream to the resolved local provider. With no cloud key set this runs entirely
on local Ollama and makes zero cloud calls. Excluded from static `task verify`.
"""

from __future__ import annotations

import asyncio
import os

from .bootstrap import build_gateway_from_env
from .errors import ModelGatewayError, ProviderUnavailableError
from .gateway import ModelGateway, RoutingTask, TaskComplexity
from .contracts import ChatRole, Message


def _print_ladder(gateway: ModelGateway, timeout: float) -> None:
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
            outcome = f"-> {decision.tier.value} provider {decision.provider_id} ({decision.model.model_id})"
        except ModelGatewayError as error:
            outcome = f"-> refused ({error.code})"
        print(f"  {complexity.value}: {outcome}")


async def _run() -> None:
    request_timeout = float(os.environ.get("OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS", "300") or "300")
    boot = build_gateway_from_env()
    gateway = boot.gateway

    print(f"Registered providers: {', '.join(boot.registered_provider_ids)}")
    print(f"Local tier: {boot.local_model_id}")
    print(f"Cloud L3/L4 tier: {boot.cloud_tier_provider_id or 'none (set an API key and OMNISTACKAI_CLOUD_PROVIDER to enable)'}\n")

    _print_ladder(gateway, request_timeout)

    prompt = os.environ.get(
        "OMNISTACKAI_GATEWAY_PROMPT", "Reply with exactly: gateway routed to local model"
    )
    output_limit = min(int(os.environ.get("OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS", "1024") or "1024"), 32)

    try:
        response = await gateway.generate(
            RoutingTask(
                request_id="r008-live-generate",
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
                request_id="r008-live-stream",
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

    print(f"\nPlatform is running via the Balanced gateway on local Ollama "
          f"(model={boot.local_model_id}); cloud_calls=0.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
