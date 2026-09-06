"""Loopback-only Ollama adapter for the platform-owned ModelProvider boundary."""

from __future__ import annotations

import asyncio
import json
import math
import re
import socket
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    build_opener,
)

from .contracts import (
    CapabilityStatus,
    ChatRole,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    ModelDescriptor,
    ProviderHealth,
    StreamEvent,
    TokenUsage,
)
from .errors import (
    InvalidProviderConfigurationError,
    ModelProfileMismatchError,
    ModelProviderError,
    ProviderHTTPError,
    ProviderResponseError,
    ProviderResponseTooLargeError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnknownModelError,
    UnsupportedModelRequestError,
)

OLLAMA_PROVIDER_ID = "ollama-local"
_ALLOWED_BASE_URLS = frozenset(
    {"http://127.0.0.1:11434", "http://localhost:11434"}
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FINISH_REASONS = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "tool_call": FinishReason.TOOL_CALL,
    "tool_calls": FinishReason.TOOL_CALL,
}


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        raise HTTPError(request.full_url, code, "redirect rejected", headers, None)


@dataclass(frozen=True, slots=True)
class OllamaModelProfile:
    """Explicit eligibility and capability evidence for one exact local model."""

    descriptor: ModelDescriptor
    expected_digest: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ModelDescriptor):
            raise TypeError("descriptor must be a ModelDescriptor")
        if self.descriptor.model.provider_id != OLLAMA_PROVIDER_ID:
            raise ValueError(f"descriptor provider_id must be {OLLAMA_PROVIDER_ID}")
        if self.expected_digest is not None and not _DIGEST_PATTERN.fullmatch(
            self.expected_digest
        ):
            raise ValueError("expected_digest must be a lowercase 64-character hex digest")
        capabilities = self.descriptor.capabilities
        statuses = (
            capabilities.text,
            capabilities.streaming,
            capabilities.tool_calling,
            capabilities.structured_output,
            capabilities.vision,
            capabilities.embeddings,
        )
        if self.expected_digest is None and CapabilityStatus.VERIFIED in statuses:
            raise ValueError("verified capabilities require an exact expected model digest")


class OllamaProvider:
    """Native Ollama API adapter restricted to the Stage 0 loopback endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        model_profiles: tuple[OllamaModelProfile, ...],
        health_timeout_seconds: float = 5.0,
        max_response_bytes: int = 4 * 1024 * 1024,
        max_stream_line_bytes: int = 1024 * 1024,
        max_concurrency: int = 1,
        opener: OpenerDirector | Any | None = None,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        if normalized_url not in _ALLOWED_BASE_URLS:
            raise InvalidProviderConfigurationError(
                "Stage 0 Ollama must use the approved loopback endpoint"
            )
        if not model_profiles:
            raise InvalidProviderConfigurationError("at least one model profile is required")
        if (
            isinstance(health_timeout_seconds, bool)
            or not isinstance(health_timeout_seconds, (int, float))
            or not math.isfinite(health_timeout_seconds)
            or health_timeout_seconds <= 0
        ):
            raise InvalidProviderConfigurationError("health timeout must be positive")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes <= 0
            or isinstance(max_stream_line_bytes, bool)
            or not isinstance(max_stream_line_bytes, int)
            or max_stream_line_bytes <= 0
        ):
            raise InvalidProviderConfigurationError("response limits must be positive")
        if max_stream_line_bytes > max_response_bytes:
            raise InvalidProviderConfigurationError(
                "stream line limit must not exceed the total response limit"
            )
        if (
            isinstance(max_concurrency, bool)
            or not isinstance(max_concurrency, int)
            or max_concurrency <= 0
        ):
            raise InvalidProviderConfigurationError("max concurrency must be positive")

        profiles: dict[str, OllamaModelProfile] = {}
        for profile in model_profiles:
            model_id = profile.descriptor.model.model_id
            if model_id in profiles:
                raise InvalidProviderConfigurationError(
                    f"duplicate Ollama model profile: {model_id}"
                )
            profiles[model_id] = profile

        self._base_url = normalized_url
        self._profiles = profiles
        self._health_timeout_seconds = float(health_timeout_seconds)
        self._max_response_bytes = max_response_bytes
        self._max_stream_line_bytes = max_stream_line_bytes
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._opener = opener or build_opener(ProxyHandler({}), _RejectRedirects())

    @property
    def provider_id(self) -> str:
        return OLLAMA_PROVIDER_ID

    async def health(self) -> ProviderHealth:
        detail_code = "ok"
        status = HealthStatus.HEALTHY
        try:
            payload = await self._request_json(
                "GET", "/api/version", None, self._health_timeout_seconds
            )
            version = payload.get("version")
            if not isinstance(version, str) or not version or len(version) > 128:
                raise ProviderResponseError("Ollama version response is invalid")
        except ModelProviderError as error:
            status = HealthStatus.UNAVAILABLE
            detail_code = error.code
        return ProviderHealth(self.provider_id, status, datetime.now(UTC), detail_code)

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        payload = await self._request_json(
            "GET", "/api/tags", None, self._health_timeout_seconds
        )
        entries = payload.get("models")
        if not isinstance(entries, list):
            raise ProviderResponseError("Ollama model list is invalid")

        pulled: dict[str, str | None] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ProviderResponseError("Ollama model entry is invalid")
            model_id = entry.get("name") or entry.get("model")
            digest = entry.get("digest")
            if not isinstance(model_id, str) or not model_id:
                raise ProviderResponseError("Ollama model identifier is invalid")
            if digest is not None and not isinstance(digest, str):
                raise ProviderResponseError("Ollama model digest is invalid")
            if model_id in pulled and pulled[model_id] != digest:
                raise ProviderResponseError("Ollama returned conflicting model entries")
            pulled[model_id] = digest

        descriptors: list[ModelDescriptor] = []
        for model_id in sorted(self._profiles):
            if model_id not in pulled:
                continue
            profile = self._profiles[model_id]
            if (
                profile.expected_digest is not None
                and pulled[model_id] != profile.expected_digest
            ):
                raise ModelProfileMismatchError(
                    "pulled model digest does not match its configured profile"
                )
            descriptors.append(profile.descriptor)
        return tuple(descriptors)

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self._validate_request(request)
        started_at = monotonic()
        payload = await self._request_json(
            "POST",
            "/api/chat",
            self._chat_payload(request, stream=False),
            request.timeout_seconds,
        )
        text, finish_reason, usage = self._parse_final_chat(payload, request)
        latency_ms = max(0, int((monotonic() - started_at) * 1000))
        return GenerateResponse(
            request.request_id,
            request.model,
            text,
            finish_reason,
            usage,
            latency_ms,
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        self._validate_request(request)
        deadline = monotonic() + request.timeout_seconds
        async with self._semaphore:
            response = await self._run_blocking(
                lambda: self._open_stream(self._chat_payload(request, stream=True), self._remaining(deadline)),
                self._remaining(deadline),
            )
            total_bytes = 0
            sequence = 0
            completed = False
            try:
                while True:
                    raw_line = await self._run_blocking(
                        lambda: response.readline(self._max_stream_line_bytes + 1),
                        self._remaining(deadline),
                    )
                    if not isinstance(raw_line, bytes):
                        raise ProviderResponseError("Ollama stream bytes are invalid")
                    if not raw_line:
                        break
                    if len(raw_line) > self._max_stream_line_bytes:
                        raise ProviderResponseTooLargeError(
                            "Ollama stream line exceeded the configured limit"
                        )
                    total_bytes += len(raw_line)
                    if total_bytes > self._max_response_bytes:
                        raise ProviderResponseTooLargeError(
                            "Ollama stream exceeded the configured limit"
                        )
                    if not raw_line.strip():
                        continue
                    payload = self._decode_json_object(raw_line)
                    if payload.get("model") != request.model.model_id:
                        raise ProviderResponseError("Ollama stream model is invalid")
                    message = payload.get("message")
                    done = payload.get("done")
                    if not isinstance(message, dict) or not isinstance(done, bool):
                        raise ProviderResponseError("Ollama stream event is invalid")
                    delta = message.get("content")
                    if not isinstance(delta, str):
                        raise ProviderResponseError("Ollama stream content is invalid")
                    usage = None
                    if done:
                        self._finish_reason(payload)
                        usage = self._usage(payload)
                        completed = True
                    yield StreamEvent(request.request_id, sequence, delta, done, usage)
                    sequence += 1
                    if done:
                        break
                if not completed:
                    raise ProviderResponseError("Ollama stream ended before a final event")
            finally:
                try:
                    await asyncio.shield(asyncio.to_thread(response.close))
                except Exception:
                    pass

    def _validate_request(self, request: GenerateRequest) -> None:
        if request.model.provider_id != self.provider_id:
            raise UnknownModelError("request targets a different provider")
        profile = self._profiles.get(request.model.model_id)
        if profile is None:
            raise UnknownModelError("model is not configured for this provider")
        if request.max_output_tokens > profile.descriptor.max_output_tokens:
            raise UnsupportedModelRequestError(
                "requested output exceeds the configured model profile"
            )
        if any(message.role is ChatRole.TOOL for message in request.messages):
            raise UnsupportedModelRequestError(
                "tool messages require a separately evaluated tool-calling contract"
            )

    @staticmethod
    def _chat_payload(request: GenerateRequest, *, stream: bool) -> dict[str, Any]:
        return {
            "model": request.model.model_id,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "stream": stream,
            "think": False,
            "options": {"num_predict": request.max_output_tokens},
        }

    def _parse_final_chat(
        self, payload: dict[str, Any], request: GenerateRequest
    ) -> tuple[str, FinishReason, TokenUsage]:
        if payload.get("done") is not True or payload.get("model") != request.model.model_id:
            raise ProviderResponseError("Ollama final chat response is invalid")
        message = payload.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderResponseError("Ollama chat message is invalid")
        return message["content"], self._finish_reason(payload), self._usage(payload)

    @staticmethod
    def _finish_reason(payload: dict[str, Any]) -> FinishReason:
        reason = payload.get("done_reason")
        try:
            return _FINISH_REASONS[reason]
        except (KeyError, TypeError) as error:
            raise ProviderResponseError("Ollama finish reason is unsupported") from error

    @staticmethod
    def _usage(payload: dict[str, Any]) -> TokenUsage:
        input_tokens = payload.get("prompt_eval_count")
        output_tokens = payload.get("eval_count")
        if (
            isinstance(input_tokens, bool)
            or not isinstance(input_tokens, int)
            or input_tokens < 0
            or isinstance(output_tokens, bool)
            or not isinstance(output_tokens, int)
            or output_tokens < 0
        ):
            raise ProviderResponseError("Ollama token usage is invalid")
        return TokenUsage(input_tokens, output_tokens)

    async def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        async with self._semaphore:
            return await self._run_blocking(
                lambda: self._request_json_sync(method, path, payload, timeout_seconds),
                timeout_seconds,
            )

    def _request_json_sync(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = self._request(method, path, payload)
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if not isinstance(status, int) or not 200 <= status < 300:
                    raise ProviderHTTPError("Ollama returned a non-success status")
                raw = response.read(self._max_response_bytes + 1)
        except HTTPError as error:
            raise ProviderHTTPError("Ollama returned an HTTP error") from error
        except (socket.timeout, TimeoutError) as error:
            raise ProviderTimeoutError("Ollama request timed out") from error
        except (URLError, OSError) as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                raise ProviderTimeoutError("Ollama request timed out") from error
            raise ProviderUnavailableError("Ollama is unavailable") from error
        if not isinstance(raw, bytes):
            raise ProviderResponseError("Ollama response bytes are invalid")
        if len(raw) > self._max_response_bytes:
            raise ProviderResponseTooLargeError(
                "Ollama response exceeded the configured limit"
            )
        return self._decode_json_object(raw)

    def _open_stream(self, payload: dict[str, Any], timeout_seconds: float) -> Any:
        request = self._request("POST", "/api/chat", payload)
        try:
            response = self._opener.open(request, timeout=timeout_seconds)
            status = getattr(response, "status", 200)
            if not isinstance(status, int) or not 200 <= status < 300:
                response.close()
                raise ProviderHTTPError("Ollama returned a non-success status")
            return response
        except HTTPError as error:
            raise ProviderHTTPError("Ollama returned an HTTP error") from error
        except (socket.timeout, TimeoutError) as error:
            raise ProviderTimeoutError("Ollama request timed out") from error
        except (URLError, OSError) as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                raise ProviderTimeoutError("Ollama request timed out") from error
            raise ProviderUnavailableError("Ollama is unavailable") from error

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None
    ) -> Request:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        return Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    @staticmethod
    def _decode_json_object(raw: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderResponseError("Ollama returned malformed JSON") from error
        if not isinstance(payload, dict):
            raise ProviderResponseError("Ollama response must be a JSON object")
        return payload

    @staticmethod
    async def _run_blocking(operation: Callable[[], Any], timeout_seconds: float) -> Any:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(operation), timeout=timeout_seconds
            )
        except TimeoutError as error:
            raise ProviderTimeoutError("Ollama request timed out") from error
        except (URLError, OSError) as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                raise ProviderTimeoutError("Ollama request timed out") from error
            raise ProviderUnavailableError("Ollama is unavailable") from error

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ProviderTimeoutError("Ollama request timed out")
        return remaining
