"""Opt-in live intake proof: compile a prompt into an Application IR via local Ollama.

Excluded from static repository verification (`task verify` never imports/runs this).
Run it with a real local Ollama model:

    task agent-engine:intake:run -- "Build a simple blog with posts and comments"

It builds an Ollama provider from the same OMNISTACKAI_OLLAMA_* environment used by
the model-fabric proofs, compiles the description into a validated IR, and prints the
IR JSON. No secrets, no cloud; requires a running local Ollama.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from ..model_gateway.contracts import (
    CapabilityStatus,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
)
from ..model_gateway.ollama import (
    OLLAMA_PROVIDER_ID,
    OllamaModelProfile,
    OllamaProvider,
)
from .errors import IntakeError
from .nl_to_ir import generate_ir

_DEFAULT_PROMPT = "Build a simple blog with posts and comments."


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as error:
        raise SystemExit(f"{name} must be a positive integer") from error
    if value <= 0:
        raise SystemExit(f"{name} must be a positive integer")
    return value


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError as error:
        raise SystemExit(f"{name} must be a positive number") from error
    if value <= 0:
        raise SystemExit(f"{name} must be a positive number")
    return value


def _build_provider() -> tuple[OllamaProvider, str, int, float]:
    base_url = os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model_id = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    context_window = _positive_int("OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS", 4_096)
    safe_input = _positive_int("OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS", 3_072)
    max_output = _positive_int("OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS", 2_048)
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
    return provider, model_id, max_output, request_timeout


async def _run(prompt: str) -> None:
    provider, model_id, max_output, request_timeout = _build_provider()
    result = await generate_ir(
        prompt,
        provider,
        model_id=model_id,
        max_output_tokens=max_output,
        timeout_seconds=request_timeout,
    )
    print(f"Prompt: {prompt}")
    print(f"Model:  {OLLAMA_PROVIDER_ID}/{model_id}")
    print("--- Application IR ---")
    print(json.dumps(result.ir.to_dict(), indent=2, sort_keys=True))
    if result.issues:
        print("--- Warnings ---")
        for issue in result.issues:
            print(f"  [{issue.severity}] {issue.location}: {issue.message}")


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    try:
        asyncio.run(_run(prompt))
    except IntakeError as error:
        raise SystemExit(
            f"Intake failed: {error}\n"
            "The local model did not return a valid Application IR. Try a clearer, more specific "
            "description, or a stronger local model (OMNISTACKAI_OLLAMA_MODEL)."
        ) from error


if __name__ == "__main__":
    main()
