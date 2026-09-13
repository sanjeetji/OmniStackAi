"""Managed trusted-local preview composition for the OmniStackAI Studio (R-421/R-422).

The coordinator owns at most one ``LocalAppSession``. Process execution remains behind the
platform-owned local-run boundary and is enabled only by the explicit Studio preview command.
Previews use automatically allocated, collision-free ports (R-422), and the manager exposes
bounded status/stop/restart lifecycle controls.
"""

from __future__ import annotations

from threading import Lock
from typing import Callable

from ..localrun import LocalAppSession, start_preview_app

StartFn = Callable[..., LocalAppSession]

_PREVIEW_ERROR = (
    "Preview could not start. Stop other local app sessions, check Docker and dependencies, then retry."
)
_IDLE = {"status": "idle", "message": "No preview is running yet. Build an app to start one."}
_STOPPED = {"status": "stopped", "message": "Preview stopped."}
_EXITED = {"status": "stopped", "message": "The preview stopped running. Restart to run it again."}


class StudioPreviewManager:
    """Serialize preview replacement, own exactly one managed local app session, and expose controls."""

    def __init__(self, *, start_fn: StartFn = start_preview_app) -> None:
        self._start_fn = start_fn
        self._session: LocalAppSession | None = None
        self._last_repo_dir: str | None = None
        self._state: dict = dict(_IDLE)
        self._lock = Lock()

    def replace(self, repo_dir: str) -> dict:
        """Stop the prior preview, start ``repo_dir`` on free ports, and return a secret-free payload."""
        with self._lock:
            self._stop_locked()
            self._last_repo_dir = repo_dir
            try:
                session = self._start_fn(repo_dir, log=None)
            except Exception:
                return self._set_state({"status": "error", "message": _PREVIEW_ERROR})

            if not session.plan.has_web:
                session.stop()
                return self._set_state(
                    {
                        "status": "unavailable",
                        "message": "This generated project has no web target to preview.",
                    }
                )
            if not session.web_ready:
                session.stop()
                return self._set_state({"status": "error", "message": _PREVIEW_ERROR})

            self._session = session
            payload = {
                "status": "ready",
                "web_url": session.plan.web_url,
                "message": "The generated web application is running locally.",
            }
            if session.plan.backend_kind != "none" and session.api_ready:
                payload["api_url"] = session.plan.api_url
            return self._set_state(payload)

    def status(self) -> dict:
        """Return a bounded, secret-free snapshot of the current preview state (liveness-aware)."""
        with self._lock:
            self._refresh_locked()
            return dict(self._state)

    def _refresh_locked(self) -> None:
        """If the active preview's processes have exited on their own, stop and report it."""
        if self._session is not None and not self._session.is_alive():
            session, self._session = self._session, None
            session.stop()
            self._state = dict(_EXITED)

    def stop(self) -> dict:
        """Stop and forget the active preview; safe to call repeatedly. Returns the new state."""
        with self._lock:
            self._stop_locked()
            return self._set_state(dict(_STOPPED))

    def restart(self) -> dict:
        """Re-preview the most recently built repo; idle no-op before any build."""
        with self._lock:
            repo_dir = self._last_repo_dir
        if repo_dir is None:
            return dict(_IDLE)
        return self.replace(repo_dir)

    def _set_state(self, state: dict) -> dict:
        self._state = dict(state)
        return dict(state)

    def _stop_locked(self) -> None:
        if self._session is None:
            return
        session, self._session = self._session, None
        session.stop()
