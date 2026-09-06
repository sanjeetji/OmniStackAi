import asyncio
import json
import threading
import time
from collections import deque
from urllib.error import HTTPError, URLError
from unittest import IsolatedAsyncioTestCase, TestCase

from omnistackai_agent_engine.model_gateway import (
    CapabilityStatus,
    ChatRole,
    FinishReason,
    GenerateRequest,
    HealthStatus,
    InvalidProviderConfigurationError,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelProfileMismatchError,
    ModelProvider,
    ModelRef,
    OLLAMA_PROVIDER_ID,
    OllamaModelProfile,
    OllamaProvider,
    ProviderHTTPError,
    ProviderResponseError,
    ProviderResponseTooLargeError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnknownModelError,
    UnsupportedModelRequestError,
)


def capabilities(*, verified: bool = False) -> ModelCapabilities:
    text_status = CapabilityStatus.VERIFIED if verified else CapabilityStatus.UNVERIFIED
    return ModelCapabilities(
        text=text_status,
        streaming=text_status,
        tool_calling=CapabilityStatus.UNVERIFIED,
        structured_output=CapabilityStatus.UNVERIFIED,
        vision=CapabilityStatus.UNVERIFIED,
        embeddings=CapabilityStatus.UNVERIFIED,
    )


def profile(
    model_id: str = "test-model:1",
    *,
    expected_digest: str | None = None,
    verified: bool = False,
) -> OllamaModelProfile:
    return OllamaModelProfile(
        ModelDescriptor(
            ModelRef(OLLAMA_PROVIDER_ID, model_id),
            capabilities(verified=verified),
            context_window_tokens=4_096,
            safe_input_tokens=3_072,
            max_output_tokens=1_024,
        ),
        expected_digest,
    )


def request(
    model_id: str = "test-model:1",
    *,
    timeout_seconds: float = 1.0,
    max_output_tokens: int = 32,
    role: ChatRole = ChatRole.USER,
) -> GenerateRequest:
    return GenerateRequest(
        "request-1",
        ModelRef(OLLAMA_PROVIDER_ID, model_id),
        (Message(role, "reply briefly"),),
        max_output_tokens,
        timeout_seconds,
    )


def final_payload(content: str = "local response") -> dict[str, object]:
    return {
        "model": "test-model:1",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 4,
        "eval_count": 2,
    }


class FakeResponse:
    def __init__(self, body: bytes = b"", *, lines: list[bytes] | None = None) -> None:
        self.body = body
        self.lines = deque(lines or [])
        self.status = 200
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]

    def readline(self, size: int = -1) -> bytes:
        if not self.lines:
            return b""
        line = self.lines.popleft()
        return line if size < 0 else line[:size]

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class QueueOpener:
    def __init__(self, *results: FakeResponse | BaseException) -> None:
        self.results = deque(results)
        self.requests: list[tuple[object, float]] = []

    def open(self, outgoing_request: object, *, timeout: float) -> FakeResponse:
        self.requests.append((outgoing_request, timeout))
        result = self.results.popleft()
        if isinstance(result, BaseException):
            raise result
        return result


def json_response(payload: object) -> FakeResponse:
    return FakeResponse(json.dumps(payload).encode("utf-8"))


def ndjson_line(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8") + b"\n"


class OllamaConfigurationTests(TestCase):
    def test_only_stage_zero_loopback_urls_are_accepted(self) -> None:
        for base_url in (
            "https://127.0.0.1:11434",
            "http://127.0.0.1:9999",
            "http://ollama:11434",
            "http://example.com",
        ):
            with self.subTest(base_url=base_url), self.assertRaises(
                InvalidProviderConfigurationError
            ):
                OllamaProvider(base_url=base_url, model_profiles=(profile(),))

        provider = OllamaProvider(
            base_url="http://localhost:11434/", model_profiles=(profile(),)
        )
        self.assertEqual(provider.provider_id, OLLAMA_PROVIDER_ID)
        self.assertIsInstance(provider, ModelProvider)

    def test_verified_capabilities_require_an_exact_digest(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact expected model digest"):
            profile(verified=True)
        exact = profile(expected_digest="a" * 64, verified=True)
        self.assertEqual(exact.expected_digest, "a" * 64)

    def test_duplicate_profiles_are_rejected(self) -> None:
        with self.assertRaises(InvalidProviderConfigurationError):
            OllamaProvider(
                base_url="http://127.0.0.1:11434",
                model_profiles=(profile(), profile()),
            )

    def test_invalid_operational_limits_are_rejected(self) -> None:
        for limits in (
            {"health_timeout_seconds": float("inf")},
            {"max_response_bytes": True},
            {"max_stream_line_bytes": 0},
            {"max_concurrency": "1"},
        ):
            with self.subTest(limits=limits), self.assertRaises(
                InvalidProviderConfigurationError
            ):
                OllamaProvider(
                    base_url="http://127.0.0.1:11434",
                    model_profiles=(profile(),),
                    **limits,
                )


class OllamaProviderTests(IsolatedAsyncioTestCase):
    def make_provider(self, opener: object, **kwargs: object) -> OllamaProvider:
        return OllamaProvider(
            base_url="http://127.0.0.1:11434",
            model_profiles=kwargs.pop("model_profiles", (profile(),)),
            opener=opener,
            **kwargs,
        )

    async def test_health_maps_success_and_safe_failure_code(self) -> None:
        provider = self.make_provider(
            QueueOpener(json_response({"version": "0.33.3"}))
        )
        health = await provider.health()
        self.assertEqual(health.status, HealthStatus.HEALTHY)
        self.assertEqual(health.detail_code, "ok")

        unavailable = self.make_provider(
            QueueOpener(URLError("sensitive network detail"))
        )
        failed_health = await unavailable.health()
        self.assertEqual(failed_health.status, HealthStatus.UNAVAILABLE)
        self.assertEqual(failed_health.detail_code, "provider_unavailable")
        self.assertNotIn("sensitive", failed_health.detail_code)

    async def test_discovery_is_sorted_allowlisted_and_digest_checked(self) -> None:
        exact_digest = "b" * 64
        profiles = (
            profile("z-model:1"),
            profile("a-model:1", expected_digest=exact_digest, verified=True),
        )
        payload = {
            "models": [
                {"name": "unconfigured:1", "digest": "c" * 64},
                {"name": "z-model:1", "digest": "d" * 64},
                {"name": "a-model:1", "digest": exact_digest},
            ]
        }
        provider = self.make_provider(json_opener := QueueOpener(json_response(payload)), model_profiles=profiles)
        discovered = await provider.discover_models()
        self.assertEqual(
            tuple(item.model.model_id for item in discovered),
            ("a-model:1", "z-model:1"),
        )
        self.assertEqual(len(json_opener.requests), 1)

        mismatch = self.make_provider(
            QueueOpener(json_response({"models": [{"name": "a-model:1", "digest": "e" * 64}]})),
            model_profiles=(profile("a-model:1", expected_digest=exact_digest, verified=True),),
        )
        with self.assertRaises(ModelProfileMismatchError):
            await mismatch.discover_models()

    async def test_generate_maps_payload_finish_reason_usage_and_limits(self) -> None:
        opener = QueueOpener(json_response(final_payload()))
        provider = self.make_provider(opener)
        response = await provider.generate(request())

        self.assertEqual(response.text, "local response")
        self.assertEqual(response.finish_reason, FinishReason.STOP)
        self.assertEqual(response.usage.input_tokens, 4)
        self.assertEqual(response.usage.output_tokens, 2)
        outgoing, timeout = opener.requests[0]
        body = json.loads(outgoing.data.decode("utf-8"))
        self.assertEqual(outgoing.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(timeout, 1.0)
        self.assertEqual(body["options"]["num_predict"], 32)
        self.assertIs(body["stream"], False)
        self.assertEqual(body["messages"], [{"role": "user", "content": "reply briefly"}])

    async def test_unknown_oversized_and_tool_requests_fail_before_network(self) -> None:
        opener = QueueOpener()
        provider = self.make_provider(opener)
        with self.assertRaises(UnknownModelError):
            await provider.generate(request("missing:1"))
        with self.assertRaises(UnsupportedModelRequestError):
            await provider.generate(request(max_output_tokens=1_025))
        with self.assertRaises(UnsupportedModelRequestError):
            await provider.generate(request(role=ChatRole.TOOL))
        self.assertEqual(opener.requests, [])

    async def test_http_malformed_and_size_failures_are_stable(self) -> None:
        http_error = HTTPError(
            "http://127.0.0.1:11434/api/chat", 302, "redirect", {}, None
        )
        with self.assertRaises(ProviderHTTPError):
            await self.make_provider(QueueOpener(http_error)).generate(request())
        with self.assertRaises(ProviderResponseError):
            await self.make_provider(QueueOpener(FakeResponse(b"not-json"))).generate(request())
        with self.assertRaises(ProviderResponseTooLargeError):
            await self.make_provider(
                QueueOpener(FakeResponse(b"12345")), max_response_bytes=4, max_stream_line_bytes=4
            ).generate(request())

    async def test_timeout_is_bounded(self) -> None:
        class SlowOpener:
            def open(self, _request: object, *, timeout: float) -> FakeResponse:
                time.sleep(timeout + 0.05)
                return json_response(final_payload())

        provider = self.make_provider(SlowOpener())
        with self.assertRaises(ProviderTimeoutError):
            await provider.generate(request(timeout_seconds=0.01))

    async def test_stream_maps_order_and_final_usage(self) -> None:
        response = FakeResponse(
            lines=[
                ndjson_line(
                    {
                        "model": "test-model:1",
                        "message": {"role": "assistant", "content": "local "},
                        "done": False,
                    }
                ),
                ndjson_line(final_payload("stream")),
            ]
        )
        provider = self.make_provider(QueueOpener(response))
        events = [event async for event in provider.stream(request())]
        self.assertEqual([event.sequence for event in events], [0, 1])
        self.assertEqual("".join(event.delta for event in events), "local stream")
        self.assertFalse(events[0].done)
        self.assertTrue(events[1].done)
        self.assertEqual(events[1].usage.output_tokens, 2)
        self.assertTrue(response.closed)

    async def test_incomplete_and_oversized_streams_fail(self) -> None:
        incomplete = FakeResponse(
            lines=[ndjson_line({"message": {"content": "partial"}, "done": False})]
        )
        with self.assertRaises(ProviderResponseError):
            _ = [
                event
                async for event in self.make_provider(QueueOpener(incomplete)).stream(request())
            ]

        oversized = FakeResponse(lines=[b"12345\n"])
        provider = self.make_provider(
            QueueOpener(oversized), max_response_bytes=4, max_stream_line_bytes=4
        )
        with self.assertRaises(ProviderResponseTooLargeError):
            _ = [event async for event in provider.stream(request())]

    async def test_stream_network_failure_is_platform_owned(self) -> None:
        class FailedResponse(FakeResponse):
            def readline(self, _size: int = -1) -> bytes:
                raise OSError("sensitive socket detail")

        provider = self.make_provider(QueueOpener(FailedResponse()))
        with self.assertRaisesRegex(ProviderUnavailableError, "Ollama is unavailable") as raised:
            _ = [event async for event in provider.stream(request())]
        self.assertEqual(raised.exception.code, "provider_unavailable")

    async def test_concurrency_limit_applies_back_pressure(self) -> None:
        class BlockingOpener:
            def __init__(self) -> None:
                self.release = threading.Event()
                self.first_entered = threading.Event()
                self.lock = threading.Lock()
                self.active = 0
                self.max_active = 0

            def open(self, _request: object, *, timeout: float) -> FakeResponse:
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                    self.first_entered.set()
                self.release.wait(timeout=timeout)
                with self.lock:
                    self.active -= 1
                return json_response(final_payload())

        opener = BlockingOpener()
        provider = self.make_provider(opener, max_concurrency=1)
        first = asyncio.create_task(provider.generate(request()))
        second = asyncio.create_task(provider.generate(request()))
        await asyncio.to_thread(opener.first_entered.wait, 0.5)
        await asyncio.sleep(0.02)
        self.assertEqual(opener.max_active, 1)
        opener.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(opener.max_active, 1)

    async def test_stream_cancellation_closes_response_and_propagates(self) -> None:
        class BlockingResponse(FakeResponse):
            def __init__(self) -> None:
                super().__init__()
                self.read_started = threading.Event()
                self.released = threading.Event()

            def readline(self, _size: int = -1) -> bytes:
                self.read_started.set()
                self.released.wait(timeout=1)
                return b""

            def close(self) -> None:
                super().close()
                self.released.set()

        response = BlockingResponse()
        provider = self.make_provider(QueueOpener(response))
        stream = provider.stream(request(timeout_seconds=1))
        pending = asyncio.create_task(anext(stream))
        await asyncio.to_thread(response.read_started.wait, 0.5)
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending
        self.assertTrue(response.closed)
