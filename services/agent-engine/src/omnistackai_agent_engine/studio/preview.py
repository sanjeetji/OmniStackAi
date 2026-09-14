"""Managed trusted-local preview composition for the OmniStackAI Studio (R-421/R-422/R-446).

The coordinator owns managed ``LocalAppSession`` instances. Process execution remains behind the
platform-owned local-run boundary and is enabled only by the explicit Studio preview command.
Previews use automatically allocated, collision-free ports (R-422). Supports single-app preview
and multi-surface ecosystem preview orchestration (R-446) with on-demand surface switching,
independent process management, and bounded status/stop/restart controls.
"""

from __future__ import annotations

from threading import RLock
from typing import Callable

from ..localrun import LocalAppSession, start_preview_app
from ..solution_packs.ecosystem_auth import (
    CrossAppAuthMatrix,
    EcosystemAuthContract,
    generate_surface_tokens,
    synthesize_ecosystem_auth,
)
from ..solution_packs.ecosystem_state import (
    EcosystemStateBinding,
    synthesize_ecosystem_state,
)

StartFn = Callable[..., LocalAppSession]

_PREVIEW_ERROR = (
    "Preview could not start. Stop other local app sessions, check Docker and dependencies, then retry."
)
_IDLE = {"status": "idle", "message": "No preview is running yet. Build an app to start one."}
_STOPPED = {"status": "stopped", "message": "Preview stopped."}
_EXITED = {"status": "stopped", "message": "The preview stopped running. Restart to run it again."}


class StudioPreviewManager:
    """Serialize preview replacement, manage local app sessions, and expose controls."""

    def __init__(self, *, start_fn: StartFn = start_preview_app) -> None:
        self._start_fn = start_fn
        self._session: LocalAppSession | None = None
        self._last_repo_dir: str | None = None
        self._state: dict = dict(_IDLE)
        self._lock = RLock()

        # Multi-surface ecosystem state (R-446/R-447)
        self._is_ecosystem = False
        self._ecosystem_id: str | None = None
        self._surfaces: list[dict] = []
        self._active_surface: str | None = None
        self._sessions: dict[str, LocalAppSession] = {}
        self._auth_contract: EcosystemAuthContract | None = None
        self._state_binding: EcosystemStateBinding | None = None
        self._demo_tokens: dict[str, str] = {}

    def replace(self, repo_dir: str) -> dict:
        """Stop prior previews, start single app ``repo_dir`` on free ports, and return state."""
        with self._lock:
            self._stop_locked()
            self._is_ecosystem = False
            self._ecosystem_id = None
            self._surfaces = []
            self._active_surface = None
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

    def replace_ecosystem(
        self,
        ecosystem_id: str,
        surfaces: list[dict],
        active_surface_slug: str | None = None,
        auth_contract: EcosystemAuthContract | None = None,
        state_binding: EcosystemStateBinding | None = None,
    ) -> dict:
        """Stop prior previews, register ecosystem surfaces, and start the active surface."""
        with self._lock:
            self._stop_locked()
            self._is_ecosystem = True
            self._ecosystem_id = ecosystem_id
            self._surfaces = [dict(s) for s in surfaces]
            self._sessions = {}

            if not self._surfaces:
                return self._set_state({"status": "error", "message": "No surfaces provided in ecosystem."})

            if auth_contract is not None:
                self._auth_contract = auth_contract
            else:
                self._auth_contract = synthesize_ecosystem_auth(ecosystem_id, self._surfaces)

            if state_binding is not None:
                self._state_binding = state_binding
            else:
                self._state_binding = synthesize_ecosystem_state(ecosystem_id, self._surfaces)

            self._demo_tokens = generate_surface_tokens(self._auth_contract)

            # Determine initial active surface
            chosen_slug = active_surface_slug
            if not chosen_slug or not any(s["slug"] == chosen_slug for s in self._surfaces):
                customer_surface = next(
                    (s for s in self._surfaces if s.get("surface_kind") == "customer_web"),
                    None,
                )
                chosen_slug = customer_surface["slug"] if customer_surface else self._surfaces[0]["slug"]

            self._active_surface = chosen_slug
            return self._launch_surface_locked(chosen_slug)

    def switch_surface(self, surface_slug: str) -> dict:
        """Switch active preview to ``surface_slug``, launching it on demand if not running."""
        with self._lock:
            if not self._is_ecosystem:
                return self._set_state({"status": "error", "message": "No ecosystem preview is active."})

            target_surface = next((s for s in self._surfaces if s["slug"] == surface_slug), None)
            if target_surface is None:
                return self._set_state(
                    {"status": "error", "message": f"Surface '{surface_slug}' not found in ecosystem."}
                )

            self._active_surface = surface_slug
            existing_session = self._sessions.get(surface_slug)
            if existing_session is not None and existing_session.is_alive():
                return self._build_ecosystem_payload_locked()

            return self._launch_surface_locked(surface_slug)

    def _launch_surface_locked(self, surface_slug: str) -> dict:
        surface = next((s for s in self._surfaces if s["slug"] == surface_slug), None)
        if surface is None:
            return self._set_state(
                {"status": "error", "message": f"Surface '{surface_slug}' not found in ecosystem."}
            )

        repo_dir = surface["target_dir"]
        self._last_repo_dir = repo_dir

        if surface_slug in self._sessions:
            sess = self._sessions.pop(surface_slug)
            sess.stop()

        try:
            session = self._start_fn(repo_dir, log=None)
        except Exception:
            return self._build_ecosystem_payload_locked(error_surface=surface_slug)

        if not session.plan.has_web:
            session.stop()
            return self._build_ecosystem_payload_locked(
                error_surface=surface_slug,
                error_msg="Surface has no web target to preview.",
            )
        if not session.web_ready:
            session.stop()
            return self._build_ecosystem_payload_locked(error_surface=surface_slug)

        self._sessions[surface_slug] = session
        return self._build_ecosystem_payload_locked()

    def status(self) -> dict:
        """Return a bounded, secret-free snapshot of the current preview state (liveness-aware)."""
        with self._lock:
            self._refresh_locked()
            if self._is_ecosystem:
                return self._build_ecosystem_payload_locked()
            return dict(self._state)

    def _refresh_locked(self) -> None:
        """If any active preview processes have exited on their own, stop and report them."""
        if self._session is not None and not self._session.is_alive():
            session, self._session = self._session, None
            session.stop()
            self._state = dict(_EXITED)

        if self._is_ecosystem:
            for slug, session in list(self._sessions.items()):
                if not session.is_alive():
                    del self._sessions[slug]
                    session.stop()

    def stop(self, surface_slug: str | None = None) -> dict:
        """Stop preview session(s). If ``surface_slug`` is given, stops only that surface."""
        with self._lock:
            if self._is_ecosystem and surface_slug:
                if surface_slug in self._sessions:
                    sess = self._sessions.pop(surface_slug)
                    sess.stop()
                return self._build_ecosystem_payload_locked()

            self._stop_locked()
            return self._set_state(dict(_STOPPED))

    def restart(self, surface_slug: str | None = None) -> dict:
        """Restart preview session(s)."""
        with self._lock:
            if self._is_ecosystem:
                target_slug = surface_slug or self._active_surface
                if not target_slug:
                    return dict(_IDLE)
                if target_slug in self._sessions:
                    sess = self._sessions.pop(target_slug)
                    sess.stop()
                return self._launch_surface_locked(target_slug)

            repo_dir = self._last_repo_dir
            if repo_dir is None:
                return dict(_IDLE)
            return self.replace(repo_dir)

    def _build_ecosystem_payload_locked(
        self,
        error_surface: str | None = None,
        error_msg: str | None = None,
    ) -> dict:
        surface_statuses = []
        for s in self._surfaces:
            slug = s["slug"]
            sess = self._sessions.get(slug)
            is_active = (slug == self._active_surface)
            is_ready = sess is not None and sess.is_alive() and sess.web_ready
            status_str = "ready" if is_ready else ("error" if slug == error_surface else "stopped")
            surface_statuses.append({
                "slug": slug,
                "app_name": s.get("app_name", slug),
                "surface_kind": s.get("surface_kind", "web"),
                "status": status_str,
                "is_active": is_active,
                "web_url": sess.plan.web_url if is_ready else None,
                "api_url": sess.plan.api_url if (is_ready and sess.api_ready) else None,
            })

        active_surface_info = next(
            (s for s in self._surfaces if s["slug"] == self._active_surface),
            None,
        )
        active_sess = self._sessions.get(self._active_surface or "") if self._active_surface else None
        active_ready = active_sess is not None and active_sess.is_alive() and active_sess.web_ready

        # Resolve active auth role and demo token
        active_role = None
        active_token = None
        if self._auth_contract and self._active_surface:
            for r in self._auth_contract.roles:
                if r.surface_slug == self._active_surface:
                    active_role = r.role_id
                    break
            active_token = self._demo_tokens.get(self._active_surface)

        if error_surface and error_surface == self._active_surface:
            payload = {
                "status": "error",
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "active_surface": self._active_surface,
                "active_role": active_role,
                "active_token": active_token,
                "has_auth": self._auth_contract is not None,
                "has_state": self._state_binding is not None,
                "message": error_msg or _PREVIEW_ERROR,
                "surfaces": surface_statuses,
            }
        elif active_ready and active_sess is not None and active_surface_info is not None:
            payload = {
                "status": "ready",
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "active_surface": self._active_surface,
                "active_role": active_role,
                "active_token": active_token,
                "has_auth": self._auth_contract is not None,
                "has_state": self._state_binding is not None,
                "web_url": active_sess.plan.web_url,
                "message": f"The generated {active_surface_info['app_name']} is running locally.",
                "surfaces": surface_statuses,
            }
            if active_sess.plan.backend_kind != "none" and active_sess.api_ready:
                payload["api_url"] = active_sess.plan.api_url
        else:
            payload = {
                "status": "stopped" if any(s["status"] == "ready" for s in surface_statuses) else (
                    self._state.get("status", "stopped")
                ),
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "active_surface": self._active_surface,
                "active_role": active_role,
                "active_token": active_token,
                "has_auth": self._auth_contract is not None,
                "has_state": self._state_binding is not None,
                "message": f"Preview for {self._active_surface or 'surface'} stopped.",
                "surfaces": surface_statuses,
            }

        return self._set_state(payload)

    def _set_state(self, state: dict) -> dict:
        self._state = dict(state)
        return dict(state)

    def _stop_locked(self) -> None:
        if self._session is not None:
            session, self._session = self._session, None
            session.stop()
        for session in self._sessions.values():
            session.stop()
        self._sessions.clear()
        self._auth_contract = None
        self._state_binding = None
        self._demo_tokens.clear()

    def get_ecosystem_auth(self) -> dict:
        """Inspect the active ecosystem's auth contract, role matrix, and surface demo tokens."""
        with self._lock:
            if not self._is_ecosystem or not self._auth_contract:
                return {"is_ecosystem": False, "auth_contract": None, "tokens": {}}
            matrix = CrossAppAuthMatrix.from_contract(self._auth_contract)
            safe_contract = dict(self._auth_contract.to_dict())
            safe_contract["jwt_secret"] = "***"
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "auth_contract": safe_contract,
                "matrix": matrix.to_dict(),
                "active_surface": self._active_surface,
                "tokens": dict(self._demo_tokens),
            }

    def get_ecosystem_state(self) -> dict:
        """Inspect the active ecosystem's unified state binding."""
        with self._lock:
            if not self._is_ecosystem or not self._state_binding:
                return {"is_ecosystem": False, "state_binding": None}
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "state_binding": self._state_binding.to_dict(),
                "active_surface": self._active_surface,
            }
