"""A dependency-free (stdlib ``http.server``) web server for the OmniStackAI Studio.

Serves the chat-to-create page at ``GET /`` and handles ``POST /api/build``. The build
function is INJECTED (``build_fn(prompt) -> dict``) so the HTTP layer is fully testable
offline against an in-memory stub; the live local-Ollama wiring lives in ``live_serve``.
No web framework, no external dependencies.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from .page import STUDIO_HTML

BuildFn = Callable[[str], dict]

_MAX_BODY_BYTES = 64 * 1024


def _make_handler(build_fn: BuildFn) -> type[BaseHTTPRequestHandler]:
    class StudioHandler(BaseHTTPRequestHandler):
        server_version = "OmniStackAIStudio/1.0"

        def log_message(self, *args) -> None:  # keep the console quiet
            return

        def _send(self, code: int, content_type: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_json(self, code: int, payload: dict) -> None:
            self._send(code, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", STUDIO_HTML.encode("utf-8"))
            elif self.path == "/healthz":
                self._send_json(200, {"status": "ok"})
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found")

        def do_POST(self) -> None:  # noqa: N802 (http.server API)
            if self.path != "/api/build":
                self._send_json(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length > _MAX_BODY_BYTES:
                self._send_json(413, {"error": "request body too large"})
                return
            raw = self.rfile.read(length) if length else b""
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
                prompt = str(data.get("prompt", "")).strip()
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                self._send_json(400, {"error": "invalid JSON body"})
                return
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return
            try:
                result = build_fn(prompt)
            except Exception as error:  # surface any build failure as a clean 502
                self._send_json(502, {"error": str(error)})
                return
            self._send_json(200, result)

    return StudioHandler


def create_studio_server(
    build_fn: BuildFn, *, host: str = "127.0.0.1", port: int = 4173
) -> ThreadingHTTPServer:
    """Create (but do not start) a studio server bound to ``host``/``port``.

    Pass ``port=0`` for an ephemeral port (used by tests). Call ``serve_forever()`` to run.
    """
    return ThreadingHTTPServer((host, port), _make_handler(build_fn))
