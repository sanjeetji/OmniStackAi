"""Shared local-Ollama provider construction for the opt-in intake runners.

Private to the intake package; used by ``live_run`` and ``build_run``. Reads the same
``OMNISTACKAI_OLLAMA_*`` environment as the model-fabric proofs. No secrets, no cloud.
"""

from __future__ import annotations

import os

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


def build_ollama_provider_from_env() -> tuple[OllamaProvider, str, int, float]:
    """Return (provider, model_id, max_output_tokens, request_timeout_seconds) from env."""
    base_url = os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model_id = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    context_window = _positive_int("OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS", 8_192)
    safe_input = _positive_int("OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS", 6_144)
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
