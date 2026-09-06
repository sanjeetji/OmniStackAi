"""Stable, vendor-neutral records used at the model-provider boundary."""

from __future__ import annotations

import math
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

_PROVIDER_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,126}[A-Za-z0-9])?$")
_DETAIL_CODE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$")
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class CapabilityStatus(StrEnum):
    """Measured support state for an exact provider/model configuration."""

    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALL = "tool_call"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"


def validate_provider_id(value: str) -> str:
    """Validate and return a canonical platform provider identifier."""

    if not isinstance(value, str) or not _PROVIDER_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "provider_id must be 1-64 lowercase ASCII letters, digits, dots, underscores, or hyphens"
        )
    return value


def _validate_bounded_text(value: str, field_name: str, maximum_length: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and have no surrounding whitespace")
    if len(value) > maximum_length:
        raise ValueError(f"{field_name} must be at most {maximum_length} characters")
    if _CONTROL_CHARACTER_PATTERN.search(value):
        raise ValueError(f"{field_name} must not contain control characters")
    return value


def _validate_positive_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _validate_non_negative_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ModelRef:
    provider_id: str
    model_id: str

    def __post_init__(self) -> None:
        validate_provider_id(self.provider_id)
        _validate_bounded_text(self.model_id, "model_id", 256)


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    text: CapabilityStatus
    streaming: CapabilityStatus
    tool_calling: CapabilityStatus
    structured_output: CapabilityStatus
    vision: CapabilityStatus
    embeddings: CapabilityStatus

    def __post_init__(self) -> None:
        field_names = (
            "text",
            "streaming",
            "tool_calling",
            "structured_output",
            "vision",
            "embeddings",
        )
        for field_name in field_names:
            if not isinstance(getattr(self, field_name), CapabilityStatus):
                raise TypeError(f"{field_name} must be a CapabilityStatus")


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    model: ModelRef
    capabilities: ModelCapabilities
    context_window_tokens: int
    safe_input_tokens: int
    max_output_tokens: int

    def __post_init__(self) -> None:
        if not isinstance(self.model, ModelRef):
            raise TypeError("model must be a ModelRef")
        if not isinstance(self.capabilities, ModelCapabilities):
            raise TypeError("capabilities must be ModelCapabilities")
        _validate_positive_integer(self.context_window_tokens, "context_window_tokens")
        _validate_positive_integer(self.safe_input_tokens, "safe_input_tokens")
        _validate_positive_integer(self.max_output_tokens, "max_output_tokens")
        if self.safe_input_tokens + self.max_output_tokens > self.context_window_tokens:
            raise ValueError("safe input and maximum output tokens must fit the context window")


@dataclass(frozen=True, slots=True)
class Message:
    role: ChatRole
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, ChatRole):
            raise TypeError("role must be a ChatRole")
        _validate_bounded_text(self.content, "content", 1_000_000)


@dataclass(frozen=True, slots=True)
class GenerateRequest:
    request_id: str
    model: ModelRef
    messages: tuple[Message, ...]
    max_output_tokens: int
    timeout_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not _REQUEST_ID_PATTERN.fullmatch(self.request_id):
            raise ValueError("request_id must be a bounded ASCII identifier")
        if not isinstance(self.model, ModelRef):
            raise TypeError("model must be a ModelRef")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ValueError("messages must be a non-empty tuple")
        if any(not isinstance(message, Message) for message in self.messages):
            raise TypeError("messages must contain only Message values")
        _validate_positive_integer(self.max_output_tokens, "max_output_tokens")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive finite number")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0

    def __post_init__(self) -> None:
        _validate_non_negative_integer(self.input_tokens, "input_tokens")
        _validate_non_negative_integer(self.output_tokens, "output_tokens")
        _validate_non_negative_integer(self.cached_input_tokens, "cached_input_tokens")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached_input_tokens must not exceed input_tokens")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class GenerateResponse:
    request_id: str
    model: ModelRef
    text: str
    finish_reason: FinishReason
    usage: TokenUsage
    latency_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not _REQUEST_ID_PATTERN.fullmatch(self.request_id):
            raise ValueError("request_id must be a bounded ASCII identifier")
        if not isinstance(self.model, ModelRef):
            raise TypeError("model must be a ModelRef")
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        if not isinstance(self.finish_reason, FinishReason):
            raise TypeError("finish_reason must be a FinishReason")
        if not isinstance(self.usage, TokenUsage):
            raise TypeError("usage must be TokenUsage")
        _validate_non_negative_integer(self.latency_ms, "latency_ms")


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider_id: str
    status: HealthStatus
    checked_at: datetime
    detail_code: str

    def __post_init__(self) -> None:
        validate_provider_id(self.provider_id)
        if not isinstance(self.status, HealthStatus):
            raise TypeError("status must be a HealthStatus")
        if (
            not isinstance(self.checked_at, datetime)
            or self.checked_at.tzinfo is None
            or self.checked_at.utcoffset() is None
        ):
            raise ValueError("checked_at must be a timezone-aware datetime")
        if not isinstance(self.detail_code, str) or not _DETAIL_CODE_PATTERN.fullmatch(self.detail_code):
            raise ValueError("detail_code must be a lowercase machine-stable code")


@dataclass(frozen=True, slots=True)
class StreamEvent:
    request_id: str
    sequence: int
    delta: str
    done: bool
    usage: TokenUsage | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not _REQUEST_ID_PATTERN.fullmatch(self.request_id):
            raise ValueError("request_id must be a bounded ASCII identifier")
        _validate_non_negative_integer(self.sequence, "sequence")
        if not isinstance(self.delta, str):
            raise TypeError("delta must be a string")
        if not isinstance(self.done, bool):
            raise TypeError("done must be a boolean")
        if self.usage is not None and not isinstance(self.usage, TokenUsage):
            raise TypeError("usage must be TokenUsage or None")
        if self.usage is not None and not self.done:
            raise ValueError("usage is only valid on the final stream event")


@runtime_checkable
class ModelProvider(Protocol):
    """Port implemented by every local, cloud, or private model adapter."""

    @property
    def provider_id(self) -> str: ...

    async def health(self) -> ProviderHealth: ...

    async def discover_models(self) -> tuple[ModelDescriptor, ...]: ...

    async def generate(self, request: GenerateRequest) -> GenerateResponse: ...

    def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]: ...
