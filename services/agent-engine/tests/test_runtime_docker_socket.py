"""Tests for the local Docker Engine API Unix-socket HTTP helper (runtime/docker_socket.py, R-489).

Fully offline: every call injects a fake connection - 0 real Docker daemon I/O under `task verify`.
"""

from __future__ import annotations

import json
import unittest

from omnistackai_agent_engine.runtime.docker_socket import (
    DockerHTTPError,
    DockerUnreachableError,
    request_json,
)


class _FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self, amount: int | None = None) -> bytes:
        return self._body


class _FakeConnection:
    """Records every request it received and returns a pre-programmed response or raises a
    pre-programmed error - mirrors the injectable-opener pattern the cloud drivers' tests use,
    adapted to http.client's request()/getresponse()/close() shape."""

    def __init__(self, responses: list | None = None, error: Exception | None = None) -> None:
        self._responses = list(responses or [])
        self._error = error
        self.requests: list = []
        self.closed_count = 0

    def request(self, method: str, path: str, body=None, headers=None) -> None:  # noqa: ANN001
        self.requests.append((method, path, body, headers))

    def getresponse(self):
        if self._error is not None:
            raise self._error
        return self._responses.pop(0)

    def close(self) -> None:
        self.closed_count += 1


class TestRequestJsonSuccess(unittest.TestCase):
    def test_post_sends_json_body_and_headers(self) -> None:
        connection = _FakeConnection([_FakeResponse(201, json.dumps({"Id": "abc123"}).encode("utf-8"))])
        status, body = request_json(
            "POST", "/v1.44/containers/create", body={"Image": "node:22-slim"}, connection=connection
        )
        self.assertEqual(status, 201)
        self.assertEqual(body, {"Id": "abc123"})
        method, path, sent_body, headers = connection.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/v1.44/containers/create")
        self.assertEqual(json.loads(sent_body.decode("utf-8")), {"Image": "node:22-slim"})
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(connection.closed_count, 1)

    def test_post_with_no_body_sends_no_content_type(self) -> None:
        connection = _FakeConnection([_FakeResponse(204, b"")])
        status, body = request_json("POST", "/v1.44/containers/x/start", connection=connection)
        self.assertEqual(status, 204)
        self.assertEqual(body, {})
        _method, _path, sent_body, headers = connection.requests[0]
        self.assertIsNone(sent_body)
        self.assertEqual(headers, {})

    def test_empty_response_decodes_to_empty_dict(self) -> None:
        connection = _FakeConnection([_FakeResponse(204, b"")])
        status, body = request_json("DELETE", "/v1.44/containers/x", connection=connection)
        self.assertEqual(status, 204)
        self.assertEqual(body, {})


class TestRequestJsonErrors(unittest.TestCase):
    def test_http_error_status_with_json_message_is_mapped(self) -> None:
        error_body = json.dumps({"message": "No such container: x"}).encode("utf-8")
        connection = _FakeConnection([_FakeResponse(404, error_body)])
        with self.assertRaises(DockerHTTPError) as ctx:
            request_json("GET", "/v1.44/containers/x/json", connection=connection)
        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(str(ctx.exception), "No such container: x")

    def test_http_error_status_with_non_json_body_falls_back(self) -> None:
        connection = _FakeConnection([_FakeResponse(500, b"not json")])
        with self.assertRaises(DockerHTTPError) as ctx:
            request_json("GET", "/v1.44/info", connection=connection)
        self.assertEqual(ctx.exception.status, 500)
        self.assertIn("500", str(ctx.exception))

    def test_connection_failure_maps_to_docker_unreachable(self) -> None:
        connection = _FakeConnection(error=OSError("connection refused"))
        with self.assertRaises(DockerUnreachableError):
            request_json("GET", "/v1.44/info", connection=connection)
        self.assertEqual(connection.closed_count, 1)

    def test_oversized_response_is_rejected(self) -> None:
        big_body = json.dumps({"padding": "x" * 100}).encode("utf-8")
        connection = _FakeConnection([_FakeResponse(200, big_body)])
        with self.assertRaises(DockerHTTPError):
            request_json("GET", "/v1.44/info", connection=connection, max_response_bytes=10)

    def test_malformed_2xx_body_is_rejected(self) -> None:
        connection = _FakeConnection([_FakeResponse(200, b"not json")])
        with self.assertRaises(DockerHTTPError):
            request_json("GET", "/v1.44/info", connection=connection)


if __name__ == "__main__":
    unittest.main()
