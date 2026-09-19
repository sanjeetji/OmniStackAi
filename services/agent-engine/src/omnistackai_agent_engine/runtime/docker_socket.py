"""Minimal stdlib Unix-domain-socket JSON HTTP client for the local Docker Engine API (R-489).

The Docker daemon listens on a Unix socket (`/var/run/docker.sock` by default), not TCP - none of
`sandbox_http.py`'s `urllib`-based transport applies here, since `urllib` has no Unix-socket
support. This is a small, purpose-built sibling covering exactly what `GVisorSandboxProvider`
needs: no vendor SDK (`docker-py` itself is built the same way internally, via a
`http.client.HTTPConnection` subclass overriding `connect()`), a bounded response size, a finite
timeout, and stable typed errors - the same safety invariants `sandbox_http.py` already enforces
for remote HTTPS calls, applied here to a local Unix socket instead.
"""

from __future__ import annotations

import http.client
import json
import socket
from typing import Any

from .errors import RuntimeProviderError

_DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # container inspect payloads can run a few KB
_DEFAULT_TIMEOUT_SECONDS = 30.0


class DockerHTTPError(RuntimeProviderError):
    """The local Docker daemon returned a non-2xx response."""

    code = "docker_http_error"

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class DockerUnreachableError(RuntimeProviderError):
    """The local Docker daemon could not be reached at all - not running, the socket path is
    wrong, or a network-level failure occurred."""

    code = "docker_unreachable"


class _UnixSocketHTTPConnection(http.client.HTTPConnection):
    """An `HTTPConnection` that connects to a Unix domain socket instead of a TCP host:port -
    the standard stdlib idiom for talking to the Docker Engine API without a vendor SDK."""

    def __init__(self, socket_path: str, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._socket_path)


def request_json(
    method: str,
    path: str,
    *,
    socket_path: str = "/var/run/docker.sock",
    body: dict[str, Any] | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
    connection: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    """Sends one JSON request to the local Docker Engine API over its Unix socket and returns
    `(status_code, decoded_json_body)`.

    Raises `DockerHTTPError` for any non-2xx response, or `DockerUnreachableError` for a
    connection-level failure (daemon not running, wrong socket path, timeout). `connection` is
    injectable so tests never touch a real Docker daemon - the same testable-transport principle
    `sandbox_http.py`'s `opener` parameter already establishes for the three cloud drivers.
    """

    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    active_connection = connection if connection is not None else _UnixSocketHTTPConnection(socket_path, timeout_seconds)

    try:
        active_connection.request(method, path, body=payload, headers=headers)
        response = active_connection.getresponse()
        raw = response.read(max_response_bytes + 1)
        status = response.status
    except (OSError, http.client.HTTPException) as error:
        raise DockerUnreachableError(f"could not reach the local Docker daemon: {error}") from error
    finally:
        active_connection.close()

    if len(raw) > max_response_bytes:
        raise DockerHTTPError(status, "Docker daemon response exceeded the size limit")
    if status >= 400:
        message = f"Docker daemon returned HTTP {status}"
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
            if isinstance(parsed.get("message"), str) and parsed["message"]:
                message = parsed["message"]
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        raise DockerHTTPError(status, message)
    if not raw:
        return status, {}
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DockerHTTPError(status, "Docker daemon returned a malformed response") from error
