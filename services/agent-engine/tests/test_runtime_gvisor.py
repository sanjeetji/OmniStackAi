"""Tests for the real, self-hosted gVisor sandbox driver (runtime/gvisor.py, R-489).

Fully offline: every Docker Engine API call injects a fake Unix-socket connection - 0 real Docker
daemon I/O under `task verify`. This environment does not have gVisor's `runsc` installed and
registered; a real live-daemon call is out of scope here (see the R-489 task contract's Gates &
Evidence).
"""

from __future__ import annotations

import json
import unittest

from omnistackai_agent_engine.runtime.contracts import SandboxHandle, SandboxLifecycleProvider
from omnistackai_agent_engine.runtime.docker_socket import DockerHTTPError, DockerUnreachableError
from omnistackai_agent_engine.runtime.errors import RuntimeProviderError, UnsupportedRuntimeTargetError
from omnistackai_agent_engine.runtime.gvisor import GVisorSandboxProvider


class _FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self, amount: int | None = None) -> bytes:
        return self._body


class _FakeConnection:
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.requests: list = []

    def request(self, method: str, path: str, body=None, headers=None) -> None:  # noqa: ANN001
        self.requests.append((method, path, body, headers))

    def getresponse(self):
        return self._responses.pop(0)

    def close(self) -> None:
        pass


class _RaisingConnection:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def request(self, method, path, body=None, headers=None) -> None:  # noqa: ANN001
        pass

    def getresponse(self):
        raise self._error

    def close(self) -> None:
        pass


def _info_response(*, runtimes: dict | None = None) -> _FakeResponse:
    body = {"Runtimes": runtimes if runtimes is not None else {"runc": {}, "runsc": {}}}
    return _FakeResponse(200, json.dumps(body).encode("utf-8"))


def _create_response(*, container_id: str = "abc123") -> _FakeResponse:
    return _FakeResponse(201, json.dumps({"Id": container_id}).encode("utf-8"))


def _inspect_response(*, container_port_key: str = "3000/tcp", host_port: str = "32768", status: str = "running") -> _FakeResponse:
    body = {
        "State": {"Status": status},
        "NetworkSettings": {"Ports": {container_port_key: [{"HostIp": "0.0.0.0", "HostPort": host_port}]}},
    }
    return _FakeResponse(200, json.dumps(body).encode("utf-8"))


class TestGVisorSandboxProviderContract(unittest.TestCase):
    def test_satisfies_contract(self) -> None:
        provider = GVisorSandboxProvider()
        self.assertIsInstance(provider, SandboxLifecycleProvider)
        self.assertEqual(provider.id, "gvisor")

    def test_active_true_when_runsc_is_registered(self) -> None:
        connection = _FakeConnection([_info_response()])
        provider = GVisorSandboxProvider(connection=connection)
        self.assertTrue(provider.active)

    def test_active_false_when_runsc_is_not_registered(self) -> None:
        connection = _FakeConnection([_info_response(runtimes={"runc": {}})])
        provider = GVisorSandboxProvider(connection=connection)
        self.assertFalse(provider.active)

    def test_active_false_never_raises_when_daemon_is_unreachable(self) -> None:
        provider = GVisorSandboxProvider(connection=_RaisingConnection(OSError("connection refused")))
        self.assertFalse(provider.active)


class TestGVisorSandboxProviderCreate(unittest.TestCase):
    def test_create_sends_the_real_lifecycle_sequence_and_reads_the_real_host_port(self) -> None:
        connection = _FakeConnection([_create_response(), _FakeResponse(204, b""), _inspect_response()])
        provider = GVisorSandboxProvider(connection=connection)
        handle = provider.create("apps/web", "nextjs-web")

        self.assertIsInstance(handle, SandboxHandle)
        self.assertEqual(handle.provider_id, "gvisor")
        self.assertEqual(handle.sandbox_id, "abc123")
        self.assertEqual(handle.url, "http://127.0.0.1:32768")
        self.assertEqual(handle.status, "running")

        self.assertEqual(len(connection.requests), 3)
        create_req, start_req, inspect_req = connection.requests
        self.assertEqual(create_req[1], "/v1.44/containers/create")
        create_body = json.loads(create_req[2].decode("utf-8"))
        self.assertEqual(create_body["Image"], "node:22-slim")
        self.assertEqual(create_body["HostConfig"]["Runtime"], "runsc")
        self.assertEqual(create_body["HostConfig"]["PortBindings"]["3000/tcp"], [{"HostPort": ""}])
        self.assertEqual(start_req[1], "/v1.44/containers/abc123/start")
        self.assertEqual(inspect_req[1], "/v1.44/containers/abc123/json")

    def test_create_maps_every_target_to_a_real_image_including_go(self) -> None:
        cases = [
            ("nextjs-web", "node:22-slim", "3000/tcp"),
            ("nextjs-admin", "node:22-slim", "3001/tcp"),
            ("backend-python", "python:3.13-slim", "8000/tcp"),
            ("backend-go", "golang:1.23-alpine", "8080/tcp"),
        ]
        for target, expected_image, port_key in cases:
            connection = _FakeConnection(
                [_create_response(), _FakeResponse(204, b""), _inspect_response(container_port_key=port_key)]
            )
            provider = GVisorSandboxProvider(connection=connection)
            provider.create("app-dir", target)
            create_body = json.loads(connection.requests[0][2].decode("utf-8"))
            self.assertEqual(create_body["Image"], expected_image, target)
            self.assertIn(port_key, create_body["ExposedPorts"], target)

    def test_create_rejects_an_unsupported_target_before_any_request(self) -> None:
        connection = _FakeConnection([])
        provider = GVisorSandboxProvider(connection=connection)
        with self.assertRaises(UnsupportedRuntimeTargetError):
            provider.create("x", "flutter")
        self.assertEqual(connection.requests, [])

    def test_create_raises_when_docker_omits_a_container_id(self) -> None:
        connection = _FakeConnection([_FakeResponse(201, b"{}")])
        provider = GVisorSandboxProvider(connection=connection)
        with self.assertRaises(RuntimeProviderError):
            provider.create("apps/web", "nextjs-web")
        self.assertEqual(len(connection.requests), 1)  # never reaches start/inspect

    def test_create_raises_when_no_host_port_was_assigned(self) -> None:
        connection = _FakeConnection([_create_response(), _FakeResponse(204, b""), _FakeResponse(200, b"{}")])
        provider = GVisorSandboxProvider(connection=connection)
        with self.assertRaises(RuntimeProviderError):
            provider.create("apps/web", "nextjs-web")

    def test_create_propagates_a_docker_http_error(self) -> None:
        connection = _FakeConnection([_FakeResponse(500, json.dumps({"message": "no such image"}).encode("utf-8"))])
        provider = GVisorSandboxProvider(connection=connection)
        with self.assertRaises(DockerHTTPError) as ctx:
            provider.create("apps/web", "nextjs-web")
        self.assertEqual(ctx.exception.status, 500)

    def test_create_propagates_docker_unreachable(self) -> None:
        provider = GVisorSandboxProvider(connection=_RaisingConnection(OSError("no such file or directory")))
        with self.assertRaises(DockerUnreachableError):
            provider.create("apps/web", "nextjs-web")


class TestGVisorSandboxProviderStatusAndKill(unittest.TestCase):
    def _handle(self) -> SandboxHandle:
        return SandboxHandle(provider_id="gvisor", sandbox_id="abc123", url="http://127.0.0.1:32768", status="running")

    def test_status_updates_from_the_state_field(self) -> None:
        connection = _FakeConnection([_inspect_response(status="exited")])
        provider = GVisorSandboxProvider(connection=connection)
        updated = provider.status(self._handle())
        self.assertEqual(updated.status, "exited")
        self.assertEqual(connection.requests[0][1], "/v1.44/containers/abc123/json")

    def test_status_keeps_the_existing_status_when_absent(self) -> None:
        connection = _FakeConnection([_FakeResponse(200, b"{}")])
        provider = GVisorSandboxProvider(connection=connection)
        updated = provider.status(self._handle())
        self.assertEqual(updated.status, "running")

    def test_kill_sends_kill_then_remove(self) -> None:
        connection = _FakeConnection([_FakeResponse(204, b""), _FakeResponse(204, b"")])
        provider = GVisorSandboxProvider(connection=connection)
        provider.kill(self._handle())
        self.assertEqual(len(connection.requests), 2)
        kill_req, delete_req = connection.requests
        self.assertEqual(kill_req[0], "POST")
        self.assertEqual(kill_req[1], "/v1.44/containers/abc123/kill")
        self.assertEqual(delete_req[0], "DELETE")
        self.assertEqual(delete_req[1], "/v1.44/containers/abc123")


if __name__ == "__main__":
    unittest.main()
