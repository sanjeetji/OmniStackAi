"""Tests for the real Vercel Sandbox driver (runtime/vercel_sandbox.py, R-487).

Fully offline: every HTTP call injects a fake opener - 0 real network I/O under `task verify`. No
real VERCEL_TOKEN/VERCEL_PROJECT_ID exist in this environment; a real live-cloud call is out of
scope here (see the R-487 task contract's Gates & Evidence). Reuses R-486's sandbox_http.py
unchanged - these tests are the proof that helper generalizes beyond E2B.
"""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from omnistackai_agent_engine.runtime.contracts import SandboxHandle, SandboxLifecycleProvider
from omnistackai_agent_engine.runtime.errors import RuntimeProviderError, UnsupportedRuntimeTargetError
from omnistackai_agent_engine.runtime.sandbox_http import SandboxHTTPError
from omnistackai_agent_engine.runtime.vercel_sandbox import (
    MissingSandboxCredentialError,
    UnsupportedSandboxRuntimeError,
    VercelSandboxProvider,
)

_VALID_ENV = {"VERCEL_TOKEN": "sekret-value", "VERCEL_PROJECT_ID": "prj_abc123"}


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


def _create_response_body(*, port: int = 3000, name: str = "omnistackai-x", status: str = "running") -> bytes:
    return json.dumps(
        {
            "routes": [{"port": port, "subdomain": "abc", "url": f"https://{name}-abc.vercel.run"}],
            "sandbox": {"name": name, "status": status},
            "session": {"id": "sbx_123", "status": status},
        }
    ).encode("utf-8")


class TestVercelSandboxProviderContract(unittest.TestCase):
    def test_satisfies_contract(self) -> None:
        provider = VercelSandboxProvider()
        self.assertIsInstance(provider, SandboxLifecycleProvider)
        self.assertEqual(provider.id, "vercel-sandbox")

    def test_active_requires_both_token_and_project_id(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(VercelSandboxProvider().active)
        with patch.dict("os.environ", {"VERCEL_TOKEN": "sekret"}, clear=True):
            self.assertFalse(VercelSandboxProvider().active)
        with patch.dict("os.environ", {"VERCEL_PROJECT_ID": "prj_1"}, clear=True):
            self.assertFalse(VercelSandboxProvider().active)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            self.assertTrue(VercelSandboxProvider().active)

    def test_create_without_a_token_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"VERCEL_PROJECT_ID": "prj_1"}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(opener.requests, [])

    def test_create_without_a_project_id_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", {"VERCEL_TOKEN": "sekret"}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(opener.requests, [])


class TestVercelSandboxProviderCreate(unittest.TestCase):
    def test_create_sends_the_documented_request_and_reads_the_real_route_url(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, _create_response_body(port=3000))])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            handle = provider.create("apps/web", "nextjs-web")

        self.assertIsInstance(handle, SandboxHandle)
        self.assertEqual(handle.provider_id, "vercel-sandbox")
        self.assertEqual(handle.url, "https://omnistackai-x-abc.vercel.run")
        self.assertEqual(handle.status, "running")
        self.assertTrue(handle.sandbox_id.startswith("omnistackai-"))

        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.vercel.com/v2/sandboxes")
        self.assertEqual(sent.get_method(), "POST")
        self.assertEqual(sent.get_header("Authorization"), "Bearer sekret-value")
        sent_body = json.loads(sent.data.decode("utf-8"))
        self.assertEqual(sent_body["runtime"], "node24")
        self.assertEqual(sent_body["ports"], [3000])
        self.assertEqual(sent_body["projectId"], "prj_abc123")
        self.assertIs(sent_body["persistent"], False)
        self.assertEqual(sent_body["name"], handle.sandbox_id)
        self.assertNotIn("sekret-value", repr(handle))

    def test_create_maps_python_target_to_the_python_runtime(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, _create_response_body(port=8000))])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            provider.create("services/api", "backend-python")
        sent_body = json.loads(opener.requests[0].data.decode("utf-8"))
        self.assertEqual(sent_body["runtime"], "python3.13")
        self.assertEqual(sent_body["ports"], [8000])

    def test_create_rejects_backend_go_with_a_specific_typed_error(self) -> None:
        opener = _FakeOpener([])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(UnsupportedSandboxRuntimeError):
                provider.create("services/api", "backend-go")
        self.assertEqual(opener.requests, [])

    def test_create_rejects_an_unsupported_target_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(UnsupportedRuntimeTargetError):
                provider.create("x", "flutter")
        self.assertEqual(opener.requests, [])

    def test_create_raises_when_no_route_matches_the_requested_port(self) -> None:
        body = json.dumps({"routes": [{"port": 9999, "url": "https://wrong.vercel.run"}]}).encode("utf-8")
        opener = _FakeOpener([_FakeResponse(200, body)])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(RuntimeProviderError):
                provider.create("apps/web", "nextjs-web")

    def test_create_propagates_a_provider_http_error(self) -> None:
        error_body = json.dumps({"message": "invalid token"}).encode("utf-8")
        http_error = HTTPError("https://api.vercel.com/v2/sandboxes", 401, "Unauthorized", {}, io.BytesIO(error_body))

        class _RaisingOpener:
            def open(self, request, timeout=None):  # noqa: ANN001
                raise http_error

        provider = VercelSandboxProvider(opener=_RaisingOpener())
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            with self.assertRaises(SandboxHTTPError) as ctx:
                provider.create("apps/web", "nextjs-web")
        self.assertEqual(ctx.exception.status, 401)


class TestVercelSandboxProviderStatusAndKill(unittest.TestCase):
    def _handle(self) -> SandboxHandle:
        return SandboxHandle(
            provider_id="vercel-sandbox", sandbox_id="omnistackai-x", url="https://omnistackai-x-abc.vercel.run", status="running"
        )

    def test_status_updates_from_the_sandbox_status_field(self) -> None:
        body = json.dumps({"sandbox": {"status": "stopped"}}).encode("utf-8")
        opener = _FakeOpener([_FakeResponse(200, body)])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            updated = provider.status(self._handle())
        self.assertEqual(updated.status, "stopped")
        self.assertEqual(updated.sandbox_id, "omnistackai-x")
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.vercel.com/v2/sandboxes/omnistackai-x")
        self.assertEqual(sent.get_method(), "GET")

    def test_status_keeps_the_existing_status_when_absent(self) -> None:
        opener = _FakeOpener([_FakeResponse(200, b"{}")])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            updated = provider.status(self._handle())
        self.assertEqual(updated.status, "running")

    def test_kill_sends_the_documented_delete_request_keyed_by_name(self) -> None:
        opener = _FakeOpener([_FakeResponse(204, b"")])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", _VALID_ENV, clear=True):
            provider.kill(self._handle())
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://api.vercel.com/v2/sandboxes/omnistackai-x")
        self.assertEqual(sent.get_method(), "DELETE")

    def test_kill_without_credentials_raises_before_any_request(self) -> None:
        opener = _FakeOpener([])
        provider = VercelSandboxProvider(opener=opener)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(MissingSandboxCredentialError):
                provider.kill(self._handle())
        self.assertEqual(opener.requests, [])


if __name__ == "__main__":
    unittest.main()
