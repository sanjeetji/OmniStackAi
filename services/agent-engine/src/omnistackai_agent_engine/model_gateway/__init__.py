"""Vendor-neutral model-provider contract and registry."""

from .contracts import (
    CapabilityStatus,
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelProvider,
    ModelRef,
    ProviderHealth,
    StreamEvent,
    TokenUsage,
)
from .errors import (
    DuplicateProviderError,
    InvalidProviderError,
    ProviderRegistryError,
    UnknownProviderError,
)
from .registry import ProviderRegistry

__all__ = [
    "CapabilityStatus",
    "ChatRole",
    "DuplicateProviderError",
    "FinishReason",
    "GenerateRequest",
    "GenerateResponse",
    "HealthStatus",
    "InvalidProviderError",
    "Message",
    "ModelCapabilities",
    "ModelDescriptor",
    "ModelProvider",
    "ModelRef",
    "ProviderHealth",
    "ProviderRegistry",
    "ProviderRegistryError",
    "StreamEvent",
    "TokenUsage",
    "UnknownProviderError",
]
