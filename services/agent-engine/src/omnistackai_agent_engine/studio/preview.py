"""Managed trusted-local preview composition for the OmniStackAI Studio (R-421).

The coordinator owns at most one ``LocalAppSession``. Process execution remains behind the
platform-owned local-run boundary and is enabled only by the explicit Studio preview command.
"""

from __future__ import annotations

from threading import Lock
from typing import Callable

from ..localrun import LocalAppSession, start_app

StartFn = Callable[..., LocalAppSession]

_PREVIEW_ERROR = (
    "Preview could not start. Stop other local app sessions, check Docker and dependencies, then retry."
)


class StudioPreviewManager:
    """Serialize preview replacement and own exactly one managed local app session."""

    def __init__(self, *, start_fn: StartFn = start_app) -> None:
        self._start_fn = start_fn
        self._session: LocalAppSession | None = None
        self._lock = Lock()

    def replace(self, repo_dir: str) -> dict:
        """Stop the prior preview, start ``repo_dir``, and return a secret-free JSON payload."""
        with self._lock:
            self._stop_locked()
            try:
                session = self._start_fn(repo_dir, log=None)
            except Exception:
                return {"status": "error", "message": _PREVIEW_ERROR}

            if not session.plan.has_web:
                session.stop()
                return {
                    "status": "unavailable",
                    "message": "This generated project has no web target to preview.",
                }
            if not session.web_ready:
                session.stop()
                return {"status": "error", "message": _PREVIEW_ERROR}

            self._session = session
            payload = {
                "status": "ready",
                "web_url": session.plan.web_url,
                "message": "The generated web application is running locally.",
            }
            if session.plan.backend_kind != "none" and session.api_ready:
                payload["api_url"] = session.plan.api_url
            return payload

    def stop(self) -> None:
        """Stop and forget the active preview; safe to call repeatedly."""
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        if self._session is None:
            return
        session, self._session = self._session, None
        session.stop()
