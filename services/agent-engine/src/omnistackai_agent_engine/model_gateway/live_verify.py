"""Opt-in local Ollama conformance proof; excluded from static repository verification."""

from __future__ import annotations

import asyncio
import os

from .contracts import (
    CapabilityStatus,
    ChatRole,
    GenerateRequest,
    HealthStatus,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
)
from .ollama import OLLAMA_PROVIDER_ID, OllamaModelProfile, OllamaProvider


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


def _provider() -> tuple[OllamaProvider, str, int, float]:
    base_url = os.environ.get(
        "OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
    )
    model_id = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    context_window = _positive_int("OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS", 4_096)
    safe_input = _positive_int("OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS", 3_072)
    max_output = _positive_int("OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS", 1_024)
    request_timeout = _positive_float(
        "OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS", 300.0
    )
    health_timeout = _positive_float(
        "OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS", 5.0
    )
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
    return provider, model_id, min(max_output, 24), request_timeout


async def _verify() -> None:
    provider, model_id, output_limit, request_timeout = _provider()
    health = await provider.health()
    if health.status is not HealthStatus.HEALTHY:
        raise SystemExit(f"Ollama health failed: {health.detail_code}")

    discovered = await provider.discover_models()
    if tuple(item.model.model_id for item in discovered) != (model_id,):
        raise SystemExit("Configured Ollama model was not discovered as an eligible profile")

    model = ModelRef(OLLAMA_PROVIDER_ID, model_id)
    response = await provider.generate(
        GenerateRequest(
            "r006-live-generate",
            model,
            (Message(ChatRole.USER, "Reply with exactly: local generation works"),),
            output_limit,
            request_timeout,
        )
    )
    if not response.text.strip() or response.usage.output_tokens < 1:
        raise SystemExit("Ollama generation did not return non-empty measured output")

    events = [
        event
        async for event in provider.stream(
            GenerateRequest(
                "r006-live-stream",
                model,
                (Message(ChatRole.USER, "Reply with exactly: local streaming works"),),
                output_limit,
                request_timeout,
            )
        )
    ]
    if (
        not events
        or not events[-1].done
        or events[-1].usage is None
        or events[-1].usage.output_tokens < 1
        or not "".join(event.delta for event in events).strip()
    ):
        raise SystemExit("Ollama streaming did not return a complete measured response")

    print(
        "Local Ollama adapter conformance passed: "
        f"model={model_id} discovered=1 generation_tokens={response.usage.output_tokens} "
        f"stream_events={len(events)} stream_tokens={events[-1].usage.output_tokens} "
        "cloud_calls=0."
    )


def main() -> None:
    asyncio.run(_verify())


if __name__ == "__main__":
    main()
