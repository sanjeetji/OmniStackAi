"""Build a Balanced gateway from the environment.

Local Ollama is always registered as the sub-L3 tier. Each cloud provider whose API key is present
in the environment is registered too, and `OMNISTACKAI_CLOUD_PROVIDER` selects which one serves the
L3/L4 tier. With no cloud key set, only Ollama is registered and L3/L4 return the stable
no-eligible-provider outcome — the platform keeps running locally at zero cloud cost. This module
constructs providers only; it makes no network call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .accounting import UsageLedger
from .cloud import PROVIDER_SPECS, create_cloud_provider
from .contracts import CapabilityStatus, ModelCapabilities, ModelDescriptor, ModelRef
from .errors import CloudProviderSelectionError
from .gateway import ModelGateway, RoutingPolicy
from .ollama import OLLAMA_PROVIDER_ID, OllamaModelProfile, OllamaProvider
from .registry import ProviderRegistry


@dataclass(frozen=True, slots=True)
class GatewayBootstrap:
    gateway: ModelGateway
    registry: ProviderRegistry
    local_model_id: str
    registered_provider_ids: tuple[str, ...]
    cloud_tier_provider_id: str | None


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise CloudProviderSelectionError(f"{name} must be an integer") from error
    if value <= 0:
        raise CloudProviderSelectionError(f"{name} must be a positive integer")
    return value


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as error:
        raise CloudProviderSelectionError(f"{name} must be a number") from error
    if value <= 0:
        raise CloudProviderSelectionError(f"{name} must be a positive number")
    return value


def _text_capabilities() -> ModelCapabilities:
    return ModelCapabilities(
        text=CapabilityStatus.UNVERIFIED,
        streaming=CapabilityStatus.UNVERIFIED,
        tool_calling=CapabilityStatus.UNSUPPORTED,
        structured_output=CapabilityStatus.UNSUPPORTED,
        vision=CapabilityStatus.UNSUPPORTED,
        embeddings=CapabilityStatus.UNSUPPORTED,
    )


def _ollama_descriptor() -> ModelDescriptor:
    model_id = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    return ModelDescriptor(
        ModelRef(OLLAMA_PROVIDER_ID, model_id),
        _text_capabilities(),
        _int_env("OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS", 4_096),
        _int_env("OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS", 3_072),
        _int_env("OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS", 1_024),
    )


def _cloud_descriptor(provider_id: str, model_id: str) -> ModelDescriptor:
    return ModelDescriptor(
        ModelRef(provider_id, model_id),
        _text_capabilities(),
        _int_env("OMNISTACKAI_CLOUD_CONTEXT_WINDOW_TOKENS", 8_192),
        _int_env("OMNISTACKAI_CLOUD_SAFE_INPUT_TOKENS", 6_144),
        _int_env("OMNISTACKAI_CLOUD_MAX_OUTPUT_TOKENS", 1_024),
    )


def build_gateway_from_env(recorder: UsageLedger | None = None) -> GatewayBootstrap:
    """Register local Ollama plus every key-present cloud provider and select the cloud tier.

    An optional ``recorder`` is attached to the gateway so every dispatch is accounted.
    """

    ollama_descriptor = _ollama_descriptor()
    registry = ProviderRegistry()
    registry.register(
        OllamaProvider(
            base_url=os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model_profiles=(OllamaModelProfile(ollama_descriptor),),
            health_timeout_seconds=_float_env("OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS", 5.0),
            max_concurrency=_int_env("OMNISTACKAI_OLLAMA_MAX_CONCURRENCY", 1),
        )
    )

    cloud_descriptors: dict[str, ModelDescriptor] = {}
    for name, spec in PROVIDER_SPECS.items():
        api_key = os.environ.get(spec.key_env, "")
        if not api_key.strip():
            continue  # provider stays inactive until its key is supplied
        model_id = os.environ.get(spec.model_env, "") or spec.default_model
        descriptor = _cloud_descriptor(spec.provider_id, model_id)
        registry.register(
            create_cloud_provider(spec, api_key=api_key, descriptor=descriptor)
        )
        cloud_descriptors[name] = descriptor

    selection = (os.environ.get("OMNISTACKAI_CLOUD_PROVIDER", "none") or "none").strip().lower()
    cloud_model: ModelDescriptor | None = None
    cloud_tier_provider_id: str | None = None
    if selection not in ("", "none"):
        if selection not in PROVIDER_SPECS:
            raise CloudProviderSelectionError(
                f"OMNISTACKAI_CLOUD_PROVIDER must be one of none, {', '.join(sorted(PROVIDER_SPECS))}"
            )
        if selection not in cloud_descriptors:
            raise CloudProviderSelectionError(
                f"cloud provider {selection!r} is selected but {PROVIDER_SPECS[selection].key_env} is not set"
            )
        cloud_model = cloud_descriptors[selection]
        cloud_tier_provider_id = cloud_model.model.provider_id

    gateway = ModelGateway(
        registry, RoutingPolicy(local_model=ollama_descriptor, cloud_model=cloud_model), recorder=recorder
    )
    return GatewayBootstrap(
        gateway=gateway,
        registry=registry,
        local_model_id=ollama_descriptor.model.model_id,
        registered_provider_ids=registry.provider_ids(),
        cloud_tier_provider_id=cloud_tier_provider_id,
    )
