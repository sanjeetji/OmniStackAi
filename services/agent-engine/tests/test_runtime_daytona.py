"""Tests for the real Daytona sandbox-lifecycle driver (runtime/daytona.py, R-488).

Fully offline: every HTTP call injects a fake opener - 0 real network I/O under `task verify`. No
real DAYTONA_API_KEY exists in this environment; a real live-cloud call is out of scope here (see
the R-488 task contract's Gates & Evidence). Reuses R-486's sandbox_http.py unchanged - the third
proof that helper generalizes beyond E2B/Vercel.
"""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from omnistackai_agent_engine.runtime.contracts import SandboxHandle, SandboxLifecycleProvider
from omnistackai_agent_engine.runtime.daytona import DaytonaSandboxProvider, MissingSandboxCredentialError
from omnistackai_agent_engine.runtime.errors import RuntimeProviderError, UnsupportedRuntimeTargetError
from omnistackai_agent_engine.runtime.sandbox_http import SandboxHTTPError

_VALID_ENV = {"DAYTONA_API_KEY": "sekret-value"}


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
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.requests: list = []

    def open(self, request, timeout: float | None = None):  # noqa: ANN001
        self.requests.append(request)
        return self._responses.pop(0)


def _create_response(*, sandbox_id: str = "sbx-abc123", state: str = "started") -> _FakeResponse:
    return _FakeResponse(200, json.dumps({"id": sandbox_id, "state": state}).encode("utf-8"))


def _preview_response(*, url: str = "https://3000-sbx-abc123.proxy.daytona.works") -> _FakeResponse:
    return _FakeResponse(200, json.dumps({"url": url, "token": "preview-token"}).encode("utf-8"))


class TestDaytonaSandboxProviderContract(unittest.TestCase):
    def test_satisfies_contract(self) -> None:
        provider = DaytonaSandboxProvider()
        self.assertIsInstance(provider, SandboxLifecycleProvider)
        self.assertEqual(provider.id, "daytona")

    def test_active_reflects_key_presence(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(DaytonaSandboxProvider().active)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            self.assertTrue(DaytonaSandboxProvider().active)

    def test_create_without_a_key_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(opener.requests, [])


class TestDaytonaSandboxProviderCreate(unittest.TestCase):
    def test_create_makes_two_calls_and_returns_the_real_preview_url(self) -> None:
        opener = _FakeOpener([_create_response(), _preview_response()])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            handle = provider.create("apps/web", "nextjs-web")

        self.assertIsInstance(handle, SandboxHandle)
        self.assertEqual(handle.provider_id, "daytona")
        self.assertEqual(handle.sandbox_id, "sbx-abc123")
        self.assertEqual(handle.url, "https://3000-sbx-abc123.proxy.daytona.works")
        self.assertEqual(handle.status, "started")

        self.assertEqual(len(opener.requests), 2)
        create_request, preview_request = opener.requests
        self.assertEqual(create_request.full_url, "https://api.daytona.io/sandbox")
        self.assertEqual(create_request.get_method(), "POST")
        self.assertEqual(create_request.get_header("Authorization"), "Bearer sekret-value")
        create_body = json.loads(create_request.data.decode("utf-8"))
        self.assertIs(create_body["public"], True)

        self.assertEqual(preview_request.full_url, "https://api.daytona.io/sandbox/sbx-abc123/ports/3000/preview-url")
        self.assertEqual(preview_request.get_method(), "GET")
        self.assertNotIn("sekret-value", repr(handle))

    def test_create_uses_the_correct_port_per_target(self) -> None:
        cases = [
            ("nextjs-web", 3000),
            ("nextjs-admin", 3001),
            ("backend-python", 8000),
            ("backend-go", 8080),
        ]
        for target, expected_port in cases:
            opener = _FakeOpener([_create_response(), _preview_response()])
            provider = DaytonaSandboxProvider(opener=opener)
            with patch.dict("os.environ", _VALID_ENV, clear=True):
                provider.create("app-dir", target)
            preview_request = opener.requests[1]
            self.assertIn(f"/ports/{expected_port}/preview-url", preview_request.full_url, target)

    def test_create_rejects_an_unsupported_target_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(UnsupportedRuntimeTargetError):
                provider.create("x", "flutter")
        self.assertEqual(opener.requests, [])

    def test_create_raises_when_the_provider_omits_a_sandbox_id(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, b"{}")])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(RuntimeProviderError):
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(len(opener.requests), 1)  # never reaches the preview-url call

    def test_create_raises_when_the_preview_url_is_missing(self) -> None:
        opener = _FakeOpener([_create_response(), _FakeResponse(200, b"{}")])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(RuntimeProviderError):
                provider.create("apps/web", "nextjs-web")

    def test_create_propagates_a_provider_http_error(self) -> None:
        error_body = json.dumps({"message": "invalid API key"}).encode("utf-8")
        http_error = HTTPError("https://api.daytona.io/sandbox", 401, "Unauthorized", {}, io.BytesIO(error_body))

        class _RaisingOpener:
            def open(self, request, timeout=None):  # noqa: ANN001
                raise http_error

        provider = DaytonaSandboxProvider(opener=_RaisingOpener())
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(SandboxHTTPError) as ctx:
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(ctx.exception.status, 401)


class TestDaytonaSandboxProviderStatusAndKill(unittest.TestCase):
    def _handle(self) -> SandboxHandle:
        return SandboxHandle(
            provider_id="daytona", sandbox_id="sbx-abc123", url="https://3000-sbx-abc123.proxy.daytona.works", status="started"
        )

    def test_status_updates_from_the_state_field(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, json.dumps({"state": "stopped"}).encode("utf-8"))])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            updated = provider.status(self._handle())
        self.assertEqual(updated.status, "stopped")
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.daytona.io/sandbox/sbx-abc123")
        self.assertEqual(sent.get_method(), "GET")

    def test_status_keeps_the_existing_status_when_absent(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, b"{}")])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            updated = provider.status(self._handle())
        self.assertEqual(updated.status, "started")

    def test_kill_sends_the_documented_delete_request(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, b"")])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            provider.kill(self._handle())
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.daytona.io/sandbox/sbx-abc123")
        self.assertEqual(sent.get_method(), "DELETE")

    def test_kill_without_a_key_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = DaytonaSandboxProvider(opener=opener)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.kill(self._handle())
        self.assertEqual(opener.requests, [])


if __name__ == "__main__":
    unittest.main()
