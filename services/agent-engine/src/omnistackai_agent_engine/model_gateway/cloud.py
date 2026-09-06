"""Key-activated cloud ModelProvider adapters built on the Python standard library.

One OpenAI-compatible adapter serves OpenAI, OpenRouter, and Groq (shared chat-completions schema);
Anthropic uses its Messages API and Google uses its generateContent API. Every adapter reads its API
key only from configuration passed in by the bootstrap, sends it only as the provider auth header,
and never places the key in logs, errors, records, or its repr. No vendor SDK and no external
dependency are used. HTTP safety (bounded response, finite timeout, redirect rejection, stable
platform-owned errors) mirrors the R-006 Ollama adapter.
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, OpenerDirector, ProxyHandler, Request, build_opener

from .contracts import (
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
    MissingCredentialError,
    ModelProviderError,
    ProviderHTTPError,
    ProviderResponseError,
    ProviderResponseTooLargeError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnknownModelError,
    UnsupportedModelRequestError,
)

_DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024

_OPENAI_FINISH = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "tool_calls": FinishReason.TOOL_CALL,
    "function_call": FinishReason.TOOL_CALL,
}
_ANTHROPIC_FINISH = {
    "end_turn": FinishReason.STOP,
    "stop_sequence": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "tool_use": FinishReason.TOOL_CALL,
}
_GEMINI_FINISH = {
    "STOP": FinishReason.STOP,
    "MAX_TOKENS": FinishReason.LENGTH,
}


class _RejectRedirects(HTTPRedirectHandler):
    """Reject HTTP redirects so an auth header is never replayed to another host."""

    def redirect_request(self, request: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise HTTPError(request.full_url, code, "redirect rejected", headers, None)


@dataclass(frozen=True, slots=True)
class CloudProviderSpec:
    """Static description of a supported cloud provider and its Stage 0 defaults."""

    provider_id: str
    kind: str  # "openai" | "anthropic" | "gemini"
    base_url: str
    key_env: str
    model_env: str
    default_model: str


PROVIDER_SPECS: dict[str, CloudProviderSpec] = {
    "anthropic": CloudProviderSpec(
        "anthropic", "anthropic", "https://api.anthropic.com",
        "ANTHROPIC_API_KEY", "OMNISTACKAI_ANTHROPIC_MODEL", "claude-sonnet-5",
    ),
    "openai": CloudProviderSpec(
        "openai", "openai", "https://api.openai.com/v1",
        "OPENAI_API_KEY", "OMNISTACKAI_OPENAI_MODEL", "gpt-4o",
    ),
    "google": CloudProviderSpec(
        "google-gemini", "gemini", "https://generativelanguage.googleapis.com",
        "GOOGLE_API_KEY", "OMNISTACKAI_GOOGLE_MODEL", "gemini-1.5-pro",
    ),
    "openrouter": CloudProviderSpec(
        "openrouter", "openai", "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY", "OMNISTACKAI_OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet",
    ),
    "groq": CloudProviderSpec(
        "groq", "openai", "https://api.groq.com/openai/v1",
        "GROQ_API_KEY", "OMNISTACKAI_GROQ_MODEL", "llama-3.3-70b-versatile",
    ),
}


class _HttpCloudProvider:
    """Base cloud adapter: shared HTTP, request validation, and dispatch."""

    kind = "cloud"

    def __init__(
        self,
        *,
        provider_id: str,
        api_key: str,
        descriptor: ModelDescriptor,
        base_url: str,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
        max_stream_line_bytes: int = 1024 * 1024,
        max_concurrency: int = 4,
        opener: OpenerDirector | Any | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise MissingCredentialError(f"{provider_id} requires a non-empty API key")
        if not isinstance(descriptor, ModelDescriptor):
            raise InvalidProviderConfigurationError("descriptor must be a ModelDescriptor")
        if descriptor.model.provider_id != provider_id:
            raise InvalidProviderConfigurationError("descriptor provider_id must match the adapter")
        if not base_url.startswith("https://"):
            raise InvalidProviderConfigurationError("cloud base URL must use HTTPS")
        if isinstance(max_response_bytes, bool) or not isinstance(max_response_bytes, int) or max_response_bytes <= 0:
            raise InvalidProviderConfigurationError("max response bytes must be positive")
        if isinstance(max_stream_line_bytes, bool) or not isinstance(max_stream_line_bytes, int) or max_stream_line_bytes <= 0:
            raise InvalidProviderConfigurationError("max stream line bytes must be positive")
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or max_concurrency <= 0:
            raise InvalidProviderConfigurationError("max concurrency must be positive")

        self._provider_id = provider_id
        self.__api_key = api_key
        self._descriptor = descriptor
        self._base_url = base_url.rstrip("/")
        self._max_response_bytes = max_response_bytes
        self._max_stream_line_bytes = max_stream_line_bytes
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._opener = opener or build_opener(ProxyHandler({}), _RejectRedirects())

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _auth_key(self) -> str:
        return self.__api_key

    async def health(self) -> ProviderHealth:
        # Config-readiness health: a key is present. Avoids a billable network probe; a real
        # endpoint failure surfaces on the next generate call as a stable platform error.
        status = HealthStatus.HEALTHY if self.__api_key.strip() else HealthStatus.UNAVAILABLE
        detail = "ok" if status is HealthStatus.HEALTHY else "missing_credential"
        return ProviderHealth(self._provider_id, status, datetime.now(UTC), detail)

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return (self._descriptor,)

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self._validate_request(request)
        path, headers, payload = self._build(request)
        started_at = monotonic()
        response = await self._post_json(path, headers, payload, request.timeout_seconds)
        text, finish_reason, usage = self._parse(response, request)
        latency_ms = max(0, int((monotonic() - started_at) * 1000))
        return GenerateResponse(request.request_id, request.model, text, finish_reason, usage, latency_ms)

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        """Stream tokens incrementally by parsing the provider's Server-Sent-Events response."""

        self._validate_request(request)
        path, headers, payload = self._build_stream(request)
        deadline = monotonic() + request.timeout_seconds
        async with self._semaphore:
            response = await self._run_blocking(
                lambda: self._open_post_stream(path, headers, payload, self._remaining(deadline)),
                self._remaining(deadline),
            )
            try:
                async for event in self._consume_sse(request, self._iter_sse(response, deadline)):
                    yield event
            finally:
                try:
                    await asyncio.shield(asyncio.to_thread(response.close))
                except Exception:
                    pass

    def _build_stream(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def _consume_sse(self, request: GenerateRequest, sse: AsyncIterator[tuple[str | None, str]]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError

    def _open_post_stream(self, path: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: float) -> Any:
        merged = {"Accept": "text/event-stream", "Content-Type": "application/json", **headers}
        request = Request(
            f"{self._base_url}{path}", data=json.dumps(payload).encode("utf-8"), method="POST", headers=merged
        )
        try:
            response = self._opener.open(request, timeout=timeout_seconds)
            status = getattr(response, "status", 200)
            if not isinstance(status, int) or not 200 <= status < 300:
                response.close()
                raise ProviderHTTPError(f"{self._provider_id} returned a non-success status")
            return response
        except HTTPError as error:
            raise ProviderHTTPError(f"{self._provider_id} returned an HTTP error") from error
        except (socket.timeout, TimeoutError) as error:
            raise ProviderTimeoutError(f"{self._provider_id} request timed out") from error
        except (URLError, OSError) as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                raise ProviderTimeoutError(f"{self._provider_id} request timed out") from error
            raise ProviderUnavailableError(f"{self._provider_id} is unavailable") from error

    async def _iter_sse(self, response: Any, deadline: float) -> AsyncIterator[tuple[str | None, str]]:
        total = 0
        event_type: str | None = None
        while True:
            raw = await self._run_blocking(
                lambda: response.readline(self._max_stream_line_bytes + 1), self._remaining(deadline)
            )
            if not isinstance(raw, bytes):
                raise ProviderResponseError(f"{self._provider_id} stream bytes are invalid")
            if not raw:
                return
            if len(raw) > self._max_stream_line_bytes:
                raise ProviderResponseTooLargeError(f"{self._provider_id} stream line exceeded the configured limit")
            total += len(raw)
            if total > self._max_response_bytes:
                raise ProviderResponseTooLargeError(f"{self._provider_id} stream exceeded the configured limit")
            try:
                line = raw.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError as error:
                raise ProviderResponseError(f"{self._provider_id} stream is not valid UTF-8") from error
            if line == "":
                event_type = None
                continue
            if line.startswith(":"):
                continue  # SSE comment / keep-alive
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
                continue
            if line.startswith("data:"):
                yield event_type, line[len("data:"):].strip()

    def _stream_json(self, data: str) -> dict[str, Any]:
        try:
            obj = json.loads(data)
        except json.JSONDecodeError as error:
            raise ProviderResponseError(f"{self._provider_id} returned malformed stream JSON") from error
        if not isinstance(obj, dict):
            raise ProviderResponseError(f"{self._provider_id} stream event must be a JSON object")
        return obj

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ProviderTimeoutError(f"{self._provider_id} request timed out")
        return remaining

    def _validate_request(self, request: GenerateRequest) -> None:
        if request.model.provider_id != self._provider_id:
            raise UnknownModelError("request targets a different provider")
        if request.model.model_id != self._descriptor.model.model_id:
            raise UnknownModelError("model is not configured for this provider")
        if request.max_output_tokens > self._descriptor.max_output_tokens:
            raise UnsupportedModelRequestError("requested output exceeds the configured model profile")
        if any(message.role is ChatRole.TOOL for message in request.messages):
            raise UnsupportedModelRequestError(
                "tool messages require a separately evaluated tool-calling contract"
            )

    # Subclasses implement these two methods.
    def _build(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def _parse(self, payload: dict[str, Any], request: GenerateRequest) -> tuple[str, FinishReason, TokenUsage]:
        raise NotImplementedError

    async def _post_json(
        self, path: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        async with self._semaphore:
            return await self._run_blocking(
                lambda: self._post_json_sync(path, headers, payload, timeout_seconds), timeout_seconds
            )

    def _post_json_sync(
        self, path: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        merged = {"Accept": "application/json", "Content-Type": "application/json", **headers}
        request = Request(
            f"{self._base_url}{path}", data=json.dumps(payload).encode("utf-8"), method="POST", headers=merged
        )
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if not isinstance(status, int) or not 200 <= status < 300:
                    raise ProviderHTTPError(f"{self._provider_id} returned a non-success status")
                raw = response.read(self._max_response_bytes + 1)
        except HTTPError as error:
            raise ProviderHTTPError(f"{self._provider_id} returned an HTTP error") from error
        except (socket.timeout, TimeoutError) as error:
            raise ProviderTimeoutError(f"{self._provider_id} request timed out") from error
        except (URLError, OSError) as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                raise ProviderTimeoutError(f"{self._provider_id} request timed out") from error
            raise ProviderUnavailableError(f"{self._provider_id} is unavailable") from error
        if not isinstance(raw, bytes):
            raise ProviderResponseError(f"{self._provider_id} response bytes are invalid")
        if len(raw) > self._max_response_bytes:
            raise ProviderResponseTooLargeError(f"{self._provider_id} response exceeded the configured limit")
        return self._decode_json_object(raw)

    def _decode_json_object(self, raw: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderResponseError(f"{self._provider_id} returned malformed JSON") from error
        if not isinstance(payload, dict):
            raise ProviderResponseError(f"{self._provider_id} response must be a JSON object")
        return payload

    async def _run_blocking(self, operation: Callable[[], Any], timeout_seconds: float) -> Any:
        try:
            return await asyncio.wait_for(asyncio.to_thread(operation), timeout=timeout_seconds)
        except TimeoutError as error:
            raise ProviderTimeoutError(f"{self._provider_id} request timed out") from error
        except (URLError, OSError) as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                raise ProviderTimeoutError(f"{self._provider_id} request timed out") from error
            raise ProviderUnavailableError(f"{self._provider_id} is unavailable") from error

    @staticmethod
    def _require_int(value: Any, provider_id: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ProviderResponseError(f"{provider_id} token usage is invalid")
        return value


class OpenAICompatibleProvider(_HttpCloudProvider):
    """Adapter for OpenAI, OpenRouter, Groq, and other OpenAI chat-completions endpoints."""

    def _build(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self._auth_key()}"}
        payload = {
            "model": request.model.model_id,
            "messages": [{"role": m.role.value, "content": m.content} for m in request.messages],
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        return "/chat/completions", headers, payload

    def _parse(self, payload: dict[str, Any], request: GenerateRequest) -> tuple[str, FinishReason, TokenUsage]:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderResponseError(f"{self._provider_id} response has no choices")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderResponseError(f"{self._provider_id} response message is invalid")
        finish_raw = choices[0].get("finish_reason")
        finish = _OPENAI_FINISH.get(finish_raw, FinishReason.STOP)
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            raise ProviderResponseError(f"{self._provider_id} usage is invalid")
        return (
            message["content"],
            finish,
            TokenUsage(
                self._require_int(usage.get("prompt_tokens"), self._provider_id),
                self._require_int(usage.get("completion_tokens"), self._provider_id),
            ),
        )


    def _build_stream(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        path, headers, payload = self._build(request)
        payload = {**payload, "stream": True, "stream_options": {"include_usage": True}}
        return path, headers, payload

    async def _consume_sse(self, request: GenerateRequest, sse: AsyncIterator[tuple[str | None, str]]) -> AsyncIterator[StreamEvent]:
        sequence = 0
        usage: TokenUsage | None = None
        async for _event_type, data in sse:
            if data == "[DONE]":
                break
            obj = self._stream_json(data)
            for choice in obj.get("choices") or []:
                if not isinstance(choice, dict):
                    continue
                delta = (choice.get("delta") or {}).get("content")
                if isinstance(delta, str) and delta:
                    yield StreamEvent(request.request_id, sequence, delta, False)
                    sequence += 1
            reported = obj.get("usage")
            if isinstance(reported, dict):
                usage = TokenUsage(
                    self._require_int(reported.get("prompt_tokens", 0), self._provider_id),
                    self._require_int(reported.get("completion_tokens", 0), self._provider_id),
                )
        yield StreamEvent(request.request_id, sequence, "", True, usage)


class AnthropicProvider(_HttpCloudProvider):
    """Adapter for the Anthropic Messages API."""

    def _build(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        headers = {"x-api-key": self._auth_key(), "anthropic-version": "2023-06-01"}
        system = "\n\n".join(m.content for m in request.messages if m.role is ChatRole.SYSTEM)
        conversation = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
            if m.role in (ChatRole.USER, ChatRole.ASSISTANT)
        ]
        if not conversation:
            raise UnsupportedModelRequestError("a user or assistant message is required")
        payload: dict[str, Any] = {
            "model": request.model.model_id,
            "max_tokens": request.max_output_tokens,
            "messages": conversation,
        }
        if system:
            payload["system"] = system
        return "/v1/messages", headers, payload

    def _parse(self, payload: dict[str, Any], request: GenerateRequest) -> tuple[str, FinishReason, TokenUsage]:
        blocks = payload.get("content")
        if not isinstance(blocks, list):
            raise ProviderResponseError(f"{self._provider_id} response content is invalid")
        text = "".join(
            block["text"] for block in blocks
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
        )
        finish = _ANTHROPIC_FINISH.get(payload.get("stop_reason"), FinishReason.STOP)
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            raise ProviderResponseError(f"{self._provider_id} usage is invalid")
        return (
            text,
            finish,
            TokenUsage(
                self._require_int(usage.get("input_tokens"), self._provider_id),
                self._require_int(usage.get("output_tokens"), self._provider_id),
            ),
        )


    def _build_stream(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        path, headers, payload = self._build(request)
        payload = {**payload, "stream": True}
        return path, headers, payload

    async def _consume_sse(self, request: GenerateRequest, sse: AsyncIterator[tuple[str | None, str]]) -> AsyncIterator[StreamEvent]:
        sequence = 0
        input_tokens = 0
        output_tokens = 0
        async for event_type, data in sse:
            obj = self._stream_json(data)
            if event_type == "message_start":
                usage = (obj.get("message") or {}).get("usage") or {}
                input_tokens = self._require_int(usage.get("input_tokens", 0), self._provider_id)
            elif event_type == "content_block_delta":
                delta = obj.get("delta") or {}
                text = delta.get("text")
                if delta.get("type") == "text_delta" and isinstance(text, str) and text:
                    yield StreamEvent(request.request_id, sequence, text, False)
                    sequence += 1
            elif event_type == "message_delta":
                usage = obj.get("usage") or {}
                if "output_tokens" in usage:
                    output_tokens = self._require_int(usage.get("output_tokens", 0), self._provider_id)
            elif event_type == "message_stop":
                break
        yield StreamEvent(request.request_id, sequence, "", True, TokenUsage(input_tokens, output_tokens))


class GeminiProvider(_HttpCloudProvider):
    """Adapter for the Google Gemini generateContent API."""

    def _build(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        headers = {"x-goog-api-key": self._auth_key()}
        system = "\n\n".join(m.content for m in request.messages if m.role is ChatRole.SYSTEM)
        contents = [
            {"role": "model" if m.role is ChatRole.ASSISTANT else "user", "parts": [{"text": m.content}]}
            for m in request.messages
            if m.role in (ChatRole.USER, ChatRole.ASSISTANT)
        ]
        if not contents:
            raise UnsupportedModelRequestError("a user or assistant message is required")
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": request.max_output_tokens},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        path = f"/v1beta/models/{quote(request.model.model_id, safe='')}:generateContent"
        return path, headers, payload

    def _parse(self, payload: dict[str, Any], request: GenerateRequest) -> tuple[str, FinishReason, TokenUsage]:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
            raise ProviderResponseError(f"{self._provider_id} response has no candidates")
        content = candidates[0].get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise ProviderResponseError(f"{self._provider_id} response parts are invalid")
        text = "".join(p["text"] for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str))
        finish = _GEMINI_FINISH.get(candidates[0].get("finishReason"), FinishReason.STOP)
        usage = payload.get("usageMetadata")
        if not isinstance(usage, dict):
            raise ProviderResponseError(f"{self._provider_id} usage is invalid")
        return (
            text,
            finish,
            TokenUsage(
                self._require_int(usage.get("promptTokenCount"), self._provider_id),
                self._require_int(usage.get("candidatesTokenCount"), self._provider_id),
            ),
        )


    def _build_stream(self, request: GenerateRequest) -> tuple[str, dict[str, str], dict[str, Any]]:
        path, headers, payload = self._build(request)
        stream_path = path.replace(":generateContent", ":streamGenerateContent?alt=sse")
        return stream_path, headers, payload

    async def _consume_sse(self, request: GenerateRequest, sse: AsyncIterator[tuple[str | None, str]]) -> AsyncIterator[StreamEvent]:
        sequence = 0
        input_tokens = 0
        output_tokens = 0
        async for _event_type, data in sse:
            obj = self._stream_json(data)
            for candidate in obj.get("candidates") or []:
                if not isinstance(candidate, dict):
                    continue
                parts = (candidate.get("content") or {}).get("parts") or []
                text = "".join(
                    p["text"] for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)
                )
                if text:
                    yield StreamEvent(request.request_id, sequence, text, False)
                    sequence += 1
            usage = obj.get("usageMetadata")
            if isinstance(usage, dict):
                input_tokens = self._require_int(usage.get("promptTokenCount", input_tokens), self._provider_id)
                output_tokens = self._require_int(usage.get("candidatesTokenCount", output_tokens), self._provider_id)
        yield StreamEvent(request.request_id, sequence, "", True, TokenUsage(input_tokens, output_tokens))


_KIND_TO_CLASS: dict[str, type[_HttpCloudProvider]] = {
    "openai": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


def create_cloud_provider(
    spec: CloudProviderSpec,
    *,
    api_key: str,
    descriptor: ModelDescriptor,
    base_url: str | None = None,
    max_concurrency: int = 4,
    opener: OpenerDirector | Any | None = None,
) -> _HttpCloudProvider:
    """Construct the adapter for a spec's provider kind."""

    try:
        provider_class = _KIND_TO_CLASS[spec.kind]
    except KeyError as error:
        raise InvalidProviderConfigurationError(f"unsupported cloud provider kind: {spec.kind}") from error
    return provider_class(
        provider_id=spec.provider_id,
        api_key=api_key,
        descriptor=descriptor,
        base_url=base_url or spec.base_url,
        max_concurrency=max_concurrency,
        opener=opener,
    )
