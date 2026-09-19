"""Tests for the real E2B sandbox-lifecycle driver (runtime/e2b.py, R-486).

Fully offline: every HTTP call injects a fake opener - 0 real network I/O under `task verify`. No
real E2B_API_KEY exists in this environment; a real live-cloud call is out of scope here (see the
R-486 task contract's Gates & Evidence).
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from omnistackai_agent_engine.runtime.contracts import SandboxHandle, SandboxLifecycleProvider
from omnistackai_agent_engine.runtime.e2b import E2BSandboxProvider, MissingSandboxCredentialError
from omnistackai_agent_engine.runtime.errors import RuntimeProviderError, UnsupportedRuntimeTargetError
from omnistackai_agent_engine.runtime.sandbox_http import SandboxHTTPError


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


class TestE2BSandboxProviderContract(unittest.TestCase):
    def test_satisfies_contract(self) -> None:
        provider = E2BSandboxProvider()
        self.assertIsInstance(provider, SandboxLifecycleProvider)
        self.assertEqual(provider.id, "e2b")

    def test_active_reflects_key_presence(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(E2BSandboxProvider().active)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            self.assertTrue(E2BSandboxProvider().active)

    def test_create_without_a_key_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(opener.requests, [])


class TestE2BSandboxProviderCreate(unittest.TestCase):
    def test_create_sends_the_documented_request_and_builds_the_public_url(self) -> None:
        opener = _FakeOpener([_FakeResponse(201, json.dumps({"sandboxID": "sbx-abc123"}).encode("utf-8"))])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret-value"}, clear=True):
            handle = provider.create("apps/web", "nextjs-web")

        self.assertIsInstance(handle, SandboxHandle)
        self.assertEqual(handle.provider_id, "e2b")
        self.assertEqual(handle.sandbox_id, "sbx-abc123")
        self.assertEqual(handle.url, "https://3000-sbx-abc123.e2b.app")
        self.assertEqual(handle.status, "running")

        self.assertEqual(len(opener.requests), 1)
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.e2b.app/sandboxes")
        self.assertEqual(sent.get_method(), "POST")
        self.assertEqual(sent.get_header("X-api-key"), "sekret-value")
        sent_body = json.loads(sent.data.decode("utf-8"))
        self.assertEqual(sent_body["templateID"], "base")
        self.assertIn("timeout", sent_body)
        # the key value must never surface anywhere reachable from the handle itself
        self.assertNotIn("sekret-value", repr(handle))

    def test_create_uses_the_correct_port_per_target(self) -> None:
        cases = [
            ("nextjs-web", 3000),
            ("nextjs-admin", 3001),
            ("backend-python", 8000),
            ("backend-go", 8080),
        ]
        for target, expected_port in cases:
            opener = _FakeOpener([_FakeResponse(201, json.dumps({"sandboxID": "sbx-1"}).encode("utf-8"))])
            provider = E2BSandboxProvider(opener=opener)
            with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
                handle = provider.create("app-dir", target)
            self.assertEqual(handle.url, f"https://{expected_port}-sbx-1.e2b.app", target)

    def test_create_uses_a_configured_template_id_override(self) -> None:
        opener = _FakeOpener([_FakeResponse(201, json.dumps({"sandboxID": "sbx-1"}).encode("utf-8"))])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict(
            "os.environ", {"E2B_API_KEY": "sekret", "E2B_TEMPLATE_ID": "custom-omnistackai-template"}, clear=True
        ):
            provider.create("apps/web", "nextjs-web")
        sent_body = json.loads(opener.requests[0].data.decode("utf-8"))
        self.assertEqual(sent_body["templateID"], "custom-omnistackai-template")

    def test_create_rejects_an_unsupported_target_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            with self.assertRaises(UnsupportedRuntimeTargetError):
                provider.create("x", "flutter")
        self.assertEqual(opener.requests, [])

    def test_create_raises_when_the_provider_omits_a_sandbox_id(self) -> None:
        opener = _FakeOpener([_FakeResponse(201, b"{}")])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            with self.assertRaises(RuntimeProviderError):
                provider.create("apps/web", "nextjs-web")

    def test_create_propagates_a_provider_http_error(self) -> None:
        from urllib.error import HTTPError
        import io

        error_body = json.dumps({"message": "invalid API key", "error_code": "unauthorized"}).encode("utf-8")
        http_error = HTTPError("https://api.e2b.app/sandboxes", 401, "Unauthorized", {}, io.BytesIO(error_body))

        class _RaisingOpener:
            def open(self, request, timeout=None):  # noqa: ANN001
                raise http_error

        provider = E2BSandboxProvider(opener=_RaisingOpener())
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            with self.assertRaises(SandboxHTTPError) as ctx:
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(ctx.exception.provider_error_code, "unauthorized")


class TestE2BSandboxProviderStatusAndKill(unittest.TestCase):
    def _handle(self) -> SandboxHandle:
        return SandboxHandle(provider_id="e2b", sandbox_id="sbx-1", url="https://3000-sbx-1.e2b.app", status="running")

    def test_status_updates_from_a_recognized_state_field(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, json.dumps({"state": "paused"}).encode("utf-8"))])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            updated = provider.status(self._handle())
        self.assertEqual(updated.status, "paused")
        self.assertEqual(updated.sandbox_id, "sbx-1")
        self.assertEqual(updated.url, "https://3000-sbx-1.e2b.app")
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.e2b.app/sandboxes/sbx-1")
        self.assertEqual(sent.get_method(), "GET")

    def test_status_keeps_the_existing_status_when_the_response_has_no_state_field(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, b"{}")])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            updated = provider.status(self._handle())
        self.assertEqual(updated.status, "running")

    def test_kill_sends_the_documented_delete_request(self) -> None:
        opener = _FakeOpener([_FakeResponse(204, b"")])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"E2B_API_KEY": "sekret"}, clear=True):
            provider.kill(self._handle())
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.e2b.app/sandboxes/sbx-1")
        self.assertEqual(sent.get_method(), "DELETE")

    def test_kill_without_a_key_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = E2BSandboxProvider(opener=opener)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.kill(self._handle())
        self.assertEqual(opener.requests, [])


if __name__ == "__main__":
    unittest.main()
