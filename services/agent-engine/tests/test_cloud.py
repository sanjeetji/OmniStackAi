import asyncio
import json
from unittest import TestCase
from urllib.error import HTTPError, URLError

from omnistackai_agent_engine.model_gateway import (
    AnthropicProvider,
    CapabilityStatus,
    ChatRole,
    GeminiProvider,
    GenerateRequest,
    HealthStatus,
    Message,
    MissingCredentialError,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
    OpenAICompatibleProvider,
    PROVIDER_SPECS,
    ProviderHTTPError,
    ProviderResponseError,
    ProviderResponseTooLargeError,
    ProviderUnavailableError,
    UnknownModelError,
    UnsupportedModelRequestError,
    create_cloud_provider,
)

FAKE_KEY = "unit-test-key-do-not-use"


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self, _n: int = -1) -> bytes:
        return self._body


class FakeOpener:
    def __init__(self, payload: dict | None = None, *, body: bytes | None = None,
                 status: int = 200, error: Exception | None = None) -> None:
        self._body = body if body is not None else json.dumps(payload or {}).encode()
        self._status = status
        self._error = error
        self.requests: list = []

    def open(self, request, timeout=None):  # noqa: ANN001
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return _FakeResponse(self._body, self._status)


def _descriptor(provider_id: str, model_id: str, *, max_output: int = 1024) -> ModelDescriptor:
    return ModelDescriptor(
        ModelRef(provider_id, model_id),
        ModelCapabilities(
            text=CapabilityStatus.UNVERIFIED,
            streaming=CapabilityStatus.UNVERIFIED,
            tool_calling=CapabilityStatus.UNSUPPORTED,
            structured_output=CapabilityStatus.UNSUPPORTED,
            vision=CapabilityStatus.UNSUPPORTED,
            embeddings=CapabilityStatus.UNSUPPORTED,
        ),
        8192,
        6144,
        max_output,
    )


def _request(provider_id: str, model_id: str, *, max_output: int = 64,
             include_system: bool = True) -> GenerateRequest:
    messages = []
    if include_system:
        messages.append(Message(ChatRole.SYSTEM, "be terse"))
    messages.append(Message(ChatRole.USER, "hello there"))
    return GenerateRequest("req-1", ModelRef(provider_id, model_id), tuple(messages), max_output, 5.0)


class OpenAICompatibleTests(TestCase):
    def _provider(self, opener: FakeOpener) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY,
            descriptor=_descriptor("openai", "gpt-4o"), base_url="https://api.openai.com/v1",
            opener=opener,
        )

    def test_generate_maps_request_and_response(self) -> None:
        opener = FakeOpener({
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        })
        provider = self._provider(opener)
        response = asyncio.run(provider.generate(_request("openai", "gpt-4o")))
        self.assertEqual(response.text, "hi")
        self.assertEqual((response.usage.input_tokens, response.usage.output_tokens), (5, 2))
        sent = opener.requests[0]
        self.assertTrue(sent.full_url.endswith("/chat/completions"))
        self.assertEqual(sent.headers["Authorization"], f"Bearer {FAKE_KEY}")
        body = json.loads(sent.data)
        self.assertEqual(body["model"], "gpt-4o")
        self.assertEqual(body["max_tokens"], 64)
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertFalse(body["stream"])

    def test_http_and_network_errors_are_stable(self) -> None:
        http = self._provider(FakeOpener(error=HTTPError("u", 500, "err", {}, None)))
        with self.assertRaises(ProviderHTTPError):
            asyncio.run(http.generate(_request("openai", "gpt-4o")))
        net = self._provider(FakeOpener(error=URLError("down")))
        with self.assertRaises(ProviderUnavailableError):
            asyncio.run(net.generate(_request("openai", "gpt-4o")))

    def test_malformed_json_is_stable(self) -> None:
        provider = self._provider(FakeOpener(body=b"not json"))
        with self.assertRaises(ProviderResponseError):
            asyncio.run(provider.generate(_request("openai", "gpt-4o")))

    def test_oversized_response_is_rejected(self) -> None:
        opener = FakeOpener(body=b"x" * 64)
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1", max_response_bytes=16, opener=opener,
        )
        with self.assertRaises(ProviderResponseTooLargeError):
            asyncio.run(provider.generate(_request("openai", "gpt-4o")))


class AnthropicTests(TestCase):
    def test_generate_maps_messages_system_and_usage(self) -> None:
        opener = FakeOpener({
            "content": [{"type": "text", "text": "hello"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 7, "output_tokens": 3},
        })
        provider = AnthropicProvider(
            provider_id="anthropic", api_key=FAKE_KEY,
            descriptor=_descriptor("anthropic", "claude-sonnet-5"),
            base_url="https://api.anthropic.com", opener=opener,
        )
        response = asyncio.run(provider.generate(_request("anthropic", "claude-sonnet-5")))
        self.assertEqual(response.text, "hello")
        self.assertEqual((response.usage.input_tokens, response.usage.output_tokens), (7, 3))
        sent = opener.requests[0]
        self.assertTrue(sent.full_url.endswith("/v1/messages"))
        self.assertEqual(sent.headers["X-api-key"], FAKE_KEY)
        self.assertIn("Anthropic-version", sent.headers)
        body = json.loads(sent.data)
        self.assertEqual(body["system"], "be terse")
        self.assertEqual([m["role"] for m in body["messages"]], ["user"])


class GeminiTests(TestCase):
    def test_generate_maps_contents_and_usage(self) -> None:
        opener = FakeOpener({
            "candidates": [{"content": {"parts": [{"text": "hey"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 4},
        })
        provider = GeminiProvider(
            provider_id="google-gemini", api_key=FAKE_KEY,
            descriptor=_descriptor("google-gemini", "gemini-1.5-pro"),
            base_url="https://generativelanguage.googleapis.com", opener=opener,
        )
        response = asyncio.run(provider.generate(_request("google-gemini", "gemini-1.5-pro")))
        self.assertEqual(response.text, "hey")
        self.assertEqual((response.usage.input_tokens, response.usage.output_tokens), (9, 4))
        sent = opener.requests[0]
        self.assertIn("/v1beta/models/gemini-1.5-pro:generateContent", sent.full_url)
        self.assertEqual(sent.headers["X-goog-api-key"], FAKE_KEY)
        body = json.loads(sent.data)
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "be terse")
        self.assertEqual(body["contents"][0]["role"], "user")


class CloudSafetyTests(TestCase):
    def test_missing_key_is_rejected(self) -> None:
        with self.assertRaises(MissingCredentialError):
            OpenAICompatibleProvider(
                provider_id="openai", api_key="", descriptor=_descriptor("openai", "gpt-4o"),
                base_url="https://api.openai.com/v1",
            )

    def test_api_key_is_not_exposed_in_repr(self) -> None:
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1",
        )
        self.assertNotIn(FAKE_KEY, repr(provider))
        self.assertNotIn(FAKE_KEY, provider.provider_id)

    def test_health_is_config_readiness(self) -> None:
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1",
        )
        health = asyncio.run(provider.health())
        self.assertIs(health.status, HealthStatus.HEALTHY)
        self.assertNotIn(FAKE_KEY, health.detail_code)

    def test_request_validation_rejects_wrong_provider_and_tool_messages(self) -> None:
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1", opener=FakeOpener({}),
        )
        with self.assertRaises(UnknownModelError):
            asyncio.run(provider.generate(_request("anthropic", "gpt-4o")))
        tool_request = GenerateRequest(
            "req-2", ModelRef("openai", "gpt-4o"),
            (Message(ChatRole.USER, "hi"), Message(ChatRole.TOOL, "result")), 32, 5.0,
        )
        with self.assertRaises(UnsupportedModelRequestError):
            asyncio.run(provider.generate(tool_request))

    def test_https_is_required(self) -> None:
        from omnistackai_agent_engine.model_gateway import InvalidProviderConfigurationError
        with self.assertRaises(InvalidProviderConfigurationError):
            OpenAICompatibleProvider(
                provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
                base_url="http://api.openai.com/v1",
            )


class _FakeStreamResponse:
    def __init__(self, lines: list[bytes], status: int = 200) -> None:
        self._lines = list(lines)
        self.status = status
        self.closed = False

    def readline(self, _n: int = -1) -> bytes:
        return self._lines.pop(0) if self._lines else b""

    def close(self) -> None:
        self.closed = True


class FakeStreamOpener:
    def __init__(self, lines: list[bytes], *, status: int = 200) -> None:
        self._lines = lines
        self._status = status
        self.requests: list = []

    def open(self, request, timeout=None):  # noqa: ANN001
        self.requests.append(request)
        return _FakeStreamResponse(self._lines, self._status)


def _collect_stream(provider, provider_id: str, model_id: str) -> list:
    async def run():
        return [e async for e in provider.stream(_request(provider_id, model_id, include_system=False))]
    return asyncio.run(run())


class StreamingTests(TestCase):
    def test_openai_streams_incrementally_with_final_usage(self) -> None:
        lines = [
            b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"lo"}}]}\n',
            b'data: {"choices":[{"finish_reason":"stop","delta":{}}]}\n',
            b'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2}}\n',
            b'data: [DONE]\n',
        ]
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1", opener=FakeStreamOpener(lines),
        )
        events = _collect_stream(provider, "openai", "gpt-4o")
        deltas = [e.delta for e in events if not e.done]
        self.assertEqual("".join(deltas), "Hello")
        self.assertTrue(events[-1].done)
        self.assertEqual((events[-1].usage.input_tokens, events[-1].usage.output_tokens), (5, 2))
        self.assertEqual([e.sequence for e in events], list(range(len(events))))

    def test_anthropic_streams_events_and_usage(self) -> None:
        lines = [
            b'event: message_start\n', b'data: {"message":{"usage":{"input_tokens":7}}}\n', b'\n',
            b'event: content_block_delta\n', b'data: {"delta":{"type":"text_delta","text":"Hi"}}\n', b'\n',
            b'event: content_block_delta\n', b'data: {"delta":{"type":"text_delta","text":" there"}}\n', b'\n',
            b'event: message_delta\n', b'data: {"usage":{"output_tokens":3}}\n', b'\n',
            b'event: message_stop\n', b'data: {}\n',
        ]
        provider = AnthropicProvider(
            provider_id="anthropic", api_key=FAKE_KEY, descriptor=_descriptor("anthropic", "claude-sonnet-5"),
            base_url="https://api.anthropic.com", opener=FakeStreamOpener(lines),
        )
        events = _collect_stream(provider, "anthropic", "claude-sonnet-5")
        self.assertEqual("".join(e.delta for e in events if not e.done), "Hi there")
        self.assertEqual((events[-1].usage.input_tokens, events[-1].usage.output_tokens), (7, 3))

    def test_gemini_streams_parts_and_usage(self) -> None:
        lines = [
            b'data: {"candidates":[{"content":{"parts":[{"text":"He"}]}}]}\n',
            b'data: {"candidates":[{"content":{"parts":[{"text":"llo"}]}}],"usageMetadata":{"promptTokenCount":9,"candidatesTokenCount":4}}\n',
        ]
        opener = FakeStreamOpener(lines)
        provider = GeminiProvider(
            provider_id="google-gemini", api_key=FAKE_KEY,
            descriptor=_descriptor("google-gemini", "gemini-1.5-pro"),
            base_url="https://generativelanguage.googleapis.com", opener=opener,
        )
        events = _collect_stream(provider, "google-gemini", "gemini-1.5-pro")
        self.assertEqual("".join(e.delta for e in events if not e.done), "Hello")
        self.assertEqual((events[-1].usage.input_tokens, events[-1].usage.output_tokens), (9, 4))
        self.assertIn(":streamGenerateContent?alt=sse", opener.requests[0].full_url)

    def test_malformed_stream_line_is_stable(self) -> None:
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1", opener=FakeStreamOpener([b'data: not-json\n']),
        )
        with self.assertRaises(ProviderResponseError):
            _collect_stream(provider, "openai", "gpt-4o")

    def test_oversized_stream_line_is_rejected(self) -> None:
        provider = OpenAICompatibleProvider(
            provider_id="openai", api_key=FAKE_KEY, descriptor=_descriptor("openai", "gpt-4o"),
            base_url="https://api.openai.com/v1", max_stream_line_bytes=16,
            opener=FakeStreamOpener([b'data: {"choices":[{"delta":{"content":"' + b'x' * 64 + b'"}}]}\n']),
        )
        with self.assertRaises(ProviderResponseTooLargeError):
            _collect_stream(provider, "openai", "gpt-4o")


class CloudFactoryTests(TestCase):
    def test_factory_builds_expected_classes(self) -> None:
        mapping = {
            "anthropic": AnthropicProvider,
            "openai": OpenAICompatibleProvider,
            "google": GeminiProvider,
            "openrouter": OpenAICompatibleProvider,
            "groq": OpenAICompatibleProvider,
        }
        for name, expected in mapping.items():
            spec = PROVIDER_SPECS[name]
            provider = create_cloud_provider(
                spec, api_key=FAKE_KEY, descriptor=_descriptor(spec.provider_id, "m"),
            )
            self.assertIsInstance(provider, expected)
            self.assertEqual(provider.provider_id, spec.provider_id)
