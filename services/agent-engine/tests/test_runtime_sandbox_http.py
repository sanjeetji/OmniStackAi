"""Tests for the sandbox-lifecycle HTTP helper (runtime/sandbox_http.py, R-486).

Fully offline: every call injects a fake opener - 0 real network I/O under `task verify`.
"""

from __future__ import annotations

import io
import json
import unittest
from urllib.error import HTTPError, URLError

from omnistackai_agent_engine.runtime.sandbox_http import (
    SandboxHTTPError,
    SandboxUnreachableError,
    request_json,
)


class _FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self, amount: int | None = None) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class _FakeOpener:
    """Records every request it received and returns a pre-programmed response or raises a
    pre-programmed error - the same injectable-opener pattern model_gateway/cloud.py's own tests
    already use for offline HTTP testing."""

    def __init__(self, response: _FakeResponse | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.requests: list = []

    def open(self, request, timeout: float | None = None):  # noqa: ANN001
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class TestRequestJsonSuccess(unittest.TestCase):
    def test_post_sends_json_body_and_headers(self) -> None:
        opener = _FakeOpener(_FakeResponse(201, json.dumps({"sandboxID": "abc123"}).encode("utf-8")))
        status, body = request_json(
            "POST",
            "https://api.example.com/sandboxes",
            headers={"X-API-Key": "secret"},
            body={"templateID": "base"},
            opener=opener,
        )
        self.assertEqual(status, 201)
        self.assertEqual(body, {"sandboxID": "abc123"})
        self.assertEqual(len(opener.requests), 1)
        sent = opener.requests[0]
        self.assertEqual(sent.get_method(), "POST")
        self.assertEqual(sent.get_header("X-api-key"), "secret")
        self.assertEqual(sent.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(sent.data.decode("utf-8")), {"templateID": "base"})

    def test_delete_with_no_body_sends_no_content_type(self) -> None:
        opener = _FakeOpener(_FakeResponse(204, b""))
        status, body = request_json(
            "DELETE", "https://api.example.com/sandboxes/abc123", headers={"X-API-Key": "secret"}, opener=opener
        )
        self.assertEqual(status, 204)
        self.assertEqual(body, {})
        sent = opener.requests[0]
        self.assertEqual(sent.get_method(), "DELETE")
        self.assertIsNone(sent.data)
        self.assertIsNone(sent.get_header("Content-type"))

    def test_empty_2xx_body_decodes_to_empty_dict(self) -> None:
        opener = _FakeOpener(_FakeResponse(200, b""))
        status, body = request_json("GET", "https://api.example.com/x", headers={}, opener=opener)
        self.assertEqual(status, 200)
        self.assertEqual(body, {})


class TestRequestJsonErrors(unittest.TestCase):
    def test_http_error_with_json_body_maps_message_and_error_code(self) -> None:
        error_body = json.dumps({"message": "invalid API key", "error_code": "unauthorized"}).encode("utf-8")
        http_error = HTTPError("https://api.example.com/sandboxes", 401, "Unauthorized", {}, io.BytesIO(error_body))
        opener = _FakeOpener(error=http_error)
        with self.assertRaises(SandboxHTTPError) as ctx:
            request_json("POST", "https://api.example.com/sandboxes", headers={}, opener=opener)
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(str(ctx.exception), "invalid API key")
        self.assertEqual(ctx.exception.provider_error_code, "unauthorized")

    def test_http_error_with_non_json_body_falls_back_to_a_generic_message(self) -> None:
        http_error = HTTPError(
            "https://api.example.com/sandboxes", 500, "Internal Server Error", {}, io.BytesIO(b"not json")
        )
        opener = _FakeOpener(error=http_error)
        with self.assertRaises(SandboxHTTPError) as ctx:
            request_json("GET", "https://api.example.com/sandboxes/x", headers={}, opener=opener)
        self.assertEqual(ctx.exception.status, 500)
        self.assertIn("500", str(ctx.exception))
        self.assertIsNone(ctx.exception.provider_error_code)

    def test_url_error_maps_to_sandbox_unreachable(self) -> None:
        opener = _FakeOpener(error=URLError("connection refused"))
        with self.assertRaises(SandboxUnreachableError):
            request_json("GET", "https://api.example.com/x", headers={}, opener=opener)

    def test_timeout_maps_to_sandbox_unreachable(self) -> None:
        opener = _FakeOpener(error=TimeoutError("timed out"))
        with self.assertRaises(SandboxUnreachableError):
            request_json("GET", "https://api.example.com/x", headers={}, opener=opener)

    def test_oversized_response_is_rejected(self) -> None:
        big_body = json.dumps({"padding": "x" * 100}).encode("utf-8")
        opener = _FakeOpener(_FakeResponse(200, big_body))
        with self.assertRaises(SandboxHTTPError):
            request_json("GET", "https://api.example.com/x", headers={}, opener=opener, max_response_bytes=10)

    def test_malformed_2xx_body_is_rejected(self) -> None:
        opener = _FakeOpener(_FakeResponse(200, b"not json"))
        with self.assertRaises(SandboxHTTPError):
            request_json("GET", "https://api.example.com/x", headers={}, opener=opener)


if __name__ == "__main__":
    unittest.main()
