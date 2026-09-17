"""R-466: rate-limit-aware pacing in the cloud ModelProvider adapters.

A 429 from a provider used to abort the whole hybrid flow as an opaque ProviderHTTPError. Now it is a typed
ProviderRateLimitedError carrying the status code and the parsed Retry-After hint (header seconds, an
HTTP-date, or the "try again in 6.495s" phrase Groq puts in the body), and the adapter waits (bounded,
injectable sleep) and re-sends the SAME request. Never retries any other error. 0 network calls.
"""

from __future__ import annotations

import asyncio
import io
import json
from datetime import UTC, datetime, timedelta
from unittest import TestCase
from urllib.error import HTTPError

from omnistackai_agent_engine.model_gateway import (
    CapabilityStatus,
    ChatRole,
    GenerateRequest,
    InvalidProviderConfigurationError,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
    OpenAICompatibleProvider,
    PROVIDER_SPECS,
    ProviderHTTPError,
    ProviderRateLimitedError,
    create_cloud_provider,
    parse_retry_after,
)

FAKE_KEY = "unit-test-key-do-not-use"
_GROQ_BODY = (
    '{"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` on tokens per minute (TPM): '
    'Limit 8000, Used 3809, Requested 4857. Please try again in 6.495s.","type":"tokens",'
    '"code":"rate_limit_exceeded"}}'
)
_OK_PAYLOAD = {
    "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 2},
}


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


class SequenceOpener:
    """Raise/return each scripted step in order; records every request."""

    def __init__(self, steps: list) -> None:
        self._steps = list(steps)
        self.requests: list = []

    def open(self, request, timeout=None):  # noqa: ANN001
        self.requests.append(request)
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return _FakeResponse(json.dumps(step).encode())


def _http_error(code: int, *, headers: dict | None = None, body: str = "") -> HTTPError:
    return HTTPError("https://api.example.test/v1/chat/completions", code, "err", headers or {}, io.BytesIO(body.encode()))


def _descriptor(provider_id: str, model_id: str) -> ModelDescriptor:
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
        1024,
    )


def _request() -> GenerateRequest:
    return GenerateRequest(
        "req-1", ModelRef("groq", "openai/gpt-oss-120b"),
        (Message(ChatRole.SYSTEM, "be terse"), Message(ChatRole.USER, "hello there")), 64, 5.0,
    )


class _SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _provider(opener: SequenceOpener, sleep: _SleepRecorder, **knobs) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        provider_id="groq", api_key=FAKE_KEY, descriptor=_descriptor("groq", "openai/gpt-oss-120b"),
        base_url="https://api.groq.com/openai/v1", opener=opener, sleep=sleep, **knobs,
    )


class ParseRetryAfterTests(TestCase):
    def test_header_delay_seconds(self) -> None:
        self.assertEqual(parse_retry_after({"Retry-After": "7"}), 7.0)
        self.assertEqual(parse_retry_after({"retry-after": "6.495"}), 6.495)

    def test_header_http_date_is_measured_from_now(self) -> None:
        now = datetime(2026, 9, 17, 12, 0, 0, tzinfo=UTC)
        when = (now + timedelta(seconds=30)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self.assertAlmostEqual(parse_retry_after({"Retry-After": when}, now=now), 30.0, places=3)
        past = (now - timedelta(seconds=30)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self.assertEqual(parse_retry_after({"Retry-After": past}, now=now), 0.0)

    def test_body_phrase_units(self) -> None:
        self.assertEqual(parse_retry_after({}, _GROQ_BODY), 6.495)
        self.assertEqual(parse_retry_after(None, "Please try again in 250ms."), 0.25)
        self.assertEqual(parse_retry_after({}, "try again in 1m"), 60.0)

    def test_header_wins_over_body_and_absence_is_none(self) -> None:
        self.assertEqual(parse_retry_after({"Retry-After": "3"}, _GROQ_BODY), 3.0)
        self.assertIsNone(parse_retry_after({}, "quota exceeded"))
        self.assertIsNone(parse_retry_after({"Retry-After": "soon"}, ""))


class TypedHttpErrorTests(TestCase):
    def test_429_is_a_typed_rate_limit_error_with_hint(self) -> None:
        sleep = _SleepRecorder()
        provider = _provider(SequenceOpener([_http_error(429, body=_GROQ_BODY)]), sleep, rate_limit_retries=0)
        with self.assertRaises(ProviderRateLimitedError) as raised:
            asyncio.run(provider.generate(_request()))
        error = raised.exception
        self.assertIsInstance(error, ProviderHTTPError)
        self.assertEqual(error.code, "provider_rate_limited")
        self.assertEqual(error.status_code, 429)
        self.assertEqual(error.retry_after_seconds, 6.495)
        self.assertIn("HTTP 429", str(error))
        self.assertNotIn(FAKE_KEY, str(error))
        self.assertEqual(sleep.calls, [])

    def test_other_statuses_keep_status_code_and_are_not_retried(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(500, headers={"Retry-After": "1"}, body="boom")])
        provider = _provider(opener, sleep)
        with self.assertRaises(ProviderHTTPError) as raised:
            asyncio.run(provider.generate(_request()))
        self.assertNotIsInstance(raised.exception, ProviderRateLimitedError)
        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.retry_after_seconds, 1.0)
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(sleep.calls, [])

    def test_plain_construction_still_works(self) -> None:
        error = ProviderHTTPError("legacy message")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.retry_after_seconds)

    def test_stream_open_maps_429_to_typed_error(self) -> None:
        provider = _provider(SequenceOpener([_http_error(429, headers={"Retry-After": "2"})]), _SleepRecorder())
        with self.assertRaises(ProviderRateLimitedError) as raised:
            provider._open_post_stream("/chat/completions", {}, {}, 5.0)
        self.assertEqual(raised.exception.retry_after_seconds, 2.0)


class PacingTests(TestCase):
    def test_waits_the_hinted_time_and_resends_the_same_request(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(429, headers={"Retry-After": "6.495"}), _OK_PAYLOAD])
        provider = _provider(opener, sleep)
        response = asyncio.run(provider.generate(_request()))
        self.assertEqual(response.text, "hi")
        self.assertEqual(len(opener.requests), 2)
        self.assertEqual(opener.requests[0].data, opener.requests[1].data)
        self.assertEqual(sleep.calls, [6.495 + 0.5])

    def test_body_hint_is_used_when_no_header(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(429, body=_GROQ_BODY), _OK_PAYLOAD])
        asyncio.run(_provider(opener, sleep).generate(_request()))
        self.assertEqual(sleep.calls, [6.495 + 0.5])

    def test_backoff_without_hint_then_gives_up_after_budget(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(429), _http_error(429), _http_error(429)])
        provider = _provider(opener, sleep, rate_limit_retries=2)
        with self.assertRaises(ProviderRateLimitedError):
            asyncio.run(provider.generate(_request()))
        self.assertEqual(sleep.calls, [2.0, 4.0])
        self.assertEqual(len(opener.requests), 3)

    def test_ask_above_cap_raises_immediately_without_sleeping(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(429, headers={"Retry-After": "120"}), _OK_PAYLOAD])
        provider = _provider(opener, sleep, max_retry_after_seconds=60.0)
        with self.assertRaises(ProviderRateLimitedError) as raised:
            asyncio.run(provider.generate(_request()))
        self.assertEqual(raised.exception.retry_after_seconds, 120.0)
        self.assertEqual(sleep.calls, [])
        self.assertEqual(len(opener.requests), 1)

    def test_zero_retries_disables_pacing(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(429, headers={"Retry-After": "1"}), _OK_PAYLOAD])
        with self.assertRaises(ProviderRateLimitedError):
            asyncio.run(_provider(opener, sleep, rate_limit_retries=0).generate(_request()))
        self.assertEqual(sleep.calls, [])

    def test_create_cloud_provider_forwards_the_knobs(self) -> None:
        sleep = _SleepRecorder()
        opener = SequenceOpener([_http_error(429, headers={"Retry-After": "3"}), _OK_PAYLOAD])
        provider = create_cloud_provider(
            PROVIDER_SPECS["groq"], api_key=FAKE_KEY, descriptor=_descriptor("groq", "openai/gpt-oss-120b"),
            opener=opener, rate_limit_retries=1, max_retry_after_seconds=10.0, sleep=sleep,
        )
        response = asyncio.run(provider.generate(_request()))
        self.assertEqual(response.text, "hi")
        self.assertEqual(sleep.calls, [3.5])

    def test_invalid_knobs_are_rejected(self) -> None:
        with self.assertRaises(InvalidProviderConfigurationError):
            _provider(SequenceOpener([]), _SleepRecorder(), rate_limit_retries=-1)
        with self.assertRaises(InvalidProviderConfigurationError):
            _provider(SequenceOpener([]), _SleepRecorder(), max_retry_after_seconds=0)
        with self.assertRaises(InvalidProviderConfigurationError):
            _provider(SequenceOpener([]), _SleepRecorder(), rate_limit_retries=True)
