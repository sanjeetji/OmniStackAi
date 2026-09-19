"""Small, safe, stdlib-only JSON HTTP helper for sandbox-lifecycle drivers (R-486).

Shared by every real cloud sandbox driver this sequence adds (E2B first; Vercel Sandbox/Daytona
follow in R-487/R-488) - a purpose-built, much smaller sibling of model_gateway/cloud.py's own HTTP
safety net (that file is LLM-completion-specific: streaming, retry-after pacing, finish-reason
mapping - none of which a create/status/kill sandbox call needs). Enforces the same safety
invariants every other cloud call in this codebase already does: a bounded response size, a finite
timeout, and redirect rejection (an auth header must never be replayed to another host).
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener

from .errors import RuntimeProviderError

_DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024  # 1 MiB - a sandbox lifecycle response is tiny
_DEFAULT_TIMEOUT_SECONDS = 30.0


class SandboxHTTPError(RuntimeProviderError):
    """A sandbox provider's HTTP call returned a non-2xx status. Carries the real status code and,
    when the provider reported one, its own machine-readable `error_code` - never a raw traceback."""

    code = "sandbox_http_error"

    def __init__(self, status: int, message: str, *, provider_error_code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.provider_error_code = provider_error_code


class SandboxUnreachableError(RuntimeProviderError):
    """The sandbox provider could not be reached at all (DNS, connection refused, timeout)."""

    code = "sandbox_unreachable"


class _RejectRedirects(HTTPRedirectHandler):
    """Reject HTTP redirects so an auth header (e.g. X-API-Key) is never replayed to another host."""

    def redirect_request(
        self, request: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise HTTPError(request.full_url, code, "redirect rejected", headers, None)


def _default_opener() -> OpenerDirector:
    return build_opener(_RejectRedirects())


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
    opener: OpenerDirector | None = None,
) -> tuple[int, dict[str, Any]]:
    """Sends one JSON HTTP request and returns `(status_code, decoded_json_body)`.

    Raises `SandboxHTTPError` for any non-2xx response (parsing the provider's own JSON error body
    when present), or `SandboxUnreachableError` for a network-level failure. A body-less 2xx
    response (e.g. a 204 on kill) decodes to `{}`, never an error. `opener` is injectable so tests
    never touch the real network - the same testable-transport pattern `model_gateway/cloud.py`'s
    adapters already use.
    """

    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = dict(headers)
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=payload, method=method, headers=request_headers)
    active_opener = opener if opener is not None else _default_opener()

    try:
        with active_opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read(max_response_bytes + 1)
            status = response.status
    except HTTPError as error:
        raw = error.read(max_response_bytes + 1)[:max_response_bytes]
        status = error.code
        message = f"sandbox provider returned HTTP {status}"
        provider_error_code: str | None = None
        try:
            parsed_error = json.loads(raw.decode("utf-8")) if raw else {}
            if isinstance(parsed_error.get("message"), str) and parsed_error["message"]:
                message = parsed_error["message"]
            if isinstance(parsed_error.get("error_code"), str):
                provider_error_code = parsed_error["error_code"]
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        raise SandboxHTTPError(status, message, provider_error_code=provider_error_code) from error
    except URLError as error:
        raise SandboxUnreachableError(f"could not reach the sandbox provider: {error.reason}") from error
    except TimeoutError as error:
        raise SandboxUnreachableError("sandbox provider request timed out") from error

    if len(raw) > max_response_bytes:
        raise SandboxHTTPError(status, "sandbox provider response exceeded the size limit")
    if not raw:
        return status, {}
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SandboxHTTPError(status, "sandbox provider returned a malformed response") from error
