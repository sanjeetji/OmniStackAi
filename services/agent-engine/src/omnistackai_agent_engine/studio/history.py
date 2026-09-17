"""Bounded, in-session build history for the OmniStackAI Studio (R-423).

A thread-safe ring of the most recent successful builds. Each entry is a bounded, secret-free
view (no DB credentials, environment, or tracebacks). In-memory only — no persistence, service,
or infrastructure. Used to render a "Recent builds" list and to re-preview a prior build.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Callable

_DEFAULT_LIMIT = 10
_MAX_PROMPT_CHARS = 400
_MAX_ENTITIES = 24
_MAX_UI_OUTCOMES = 200  # R-467: one entry per synthesized page/screen; generously bounded
# R-468: fields an in-place edit (see studio/session.py) may refresh on an existing entry -- the app's
# structure after the edit, never its identity/location (id, prompt, target_dir, created_at stay fixed).
_UPDATABLE_FIELDS = frozenset({"file_count", "commit_sha", "entities"})


class StudioBuildHistory:
    """Own a bounded ring of recent build records; expose a secret-free, JSON-safe view."""

    def __init__(self, *, limit: int = _DEFAULT_LIMIT, clock: Callable[[], float] = time.time) -> None:
        self._limit = max(1, limit)
        self._clock = clock
        self._entries: list[dict] = []  # oldest first
        self._counter = 0
        self._lock = Lock()

    def record(self, build: dict) -> str:
        """Record a successful build (from an app-build result dict) and return its id."""
        with self._lock:
            self._counter += 1
            entry = {
                "id": str(self._counter),
                "prompt": str(build.get("prompt", ""))[:_MAX_PROMPT_CHARS],
                "name": str(build.get("name", "App")),
                "entities": [str(e) for e in list(build.get("entities", []))[:_MAX_ENTITIES]],
                "file_count": int(build.get("file_count", 0) or 0),
                "target_dir": str(build.get("target_dir", "")),
                "commit_sha": str(build.get("commit_sha", ""))[:40],
                "created_at": self._clock(),
            }
            if build.get("pack_id"):
                entry["pack_id"] = str(build["pack_id"])
                entry["pack_version"] = str(build.get("pack_version", ""))
            if build.get("applied_ai_delta_change_ids"):
                entry["applied_ai_delta_change_ids"] = [
                    str(cid) for cid in build["applied_ai_delta_change_ids"]
                ]
            if build.get("ecosystem_id"):
                entry["ecosystem_id"] = str(build["ecosystem_id"])
                entry["ecosystem_version"] = str(build.get("ecosystem_version", ""))
            if build.get("surface_slug"):
                entry["surface_slug"] = str(build["surface_slug"])
            if build.get("surface_kind"):
                entry["surface_kind"] = str(build["surface_kind"])
            if build.get("is_ecosystem"):
                entry["is_ecosystem"] = bool(build["is_ecosystem"])
            if build.get("surface_count"):
                entry["surface_count"] = int(build["surface_count"])
            if "hybrid_ui_requested" in build:
                entry["hybrid_ui_requested"] = bool(build["hybrid_ui_requested"])
                entry["hybrid_ui_active"] = bool(build.get("hybrid_ui_active", False))
            if build.get("ui_outcomes") and isinstance(build["ui_outcomes"], list):
                entry["ui_outcomes"] = [
                    dict(outcome) for outcome in build["ui_outcomes"][:_MAX_UI_OUTCOMES] if isinstance(outcome, dict)
                ]
            if build.get("surfaces") and isinstance(build["surfaces"], list):
                entry["surfaces"] = [
                    {
                        "slug": str(s.get("slug", "")),
                        "app_name": str(s.get("app_name", "")),
                        "surface_kind": str(s.get("surface_kind", "")),
                        "target_dir": str(s.get("target_dir", "")),
                    }
                    for s in build["surfaces"]
                    if isinstance(s, dict)
                ]
            self._entries.append(entry)
            if len(self._entries) > self._limit:
                self._entries = self._entries[-self._limit :]
            return entry["id"]

    def list(self) -> dict:
        """Return the recent builds newest-first, as a bounded, secret-free JSON-safe payload."""
        with self._lock:
            return {"builds": [dict(entry) for entry in reversed(self._entries)]}

    def get(self, build_id: str) -> dict | None:
        """Return a copy of the recorded build with ``build_id``, or None."""
        with self._lock:
            for entry in self._entries:
                if entry["id"] == build_id:
                    return dict(entry)
            return None

    def update(self, build_id: str, patch: dict) -> bool:
        """Refresh a few bounded fields (see ``_UPDATABLE_FIELDS``) on an existing entry in place.

        Used after an in-place edit (R-468) so "Recent builds" reflects the app's current state rather
        than its stale first-build snapshot. Unknown/non-updatable keys in ``patch`` are ignored; the
        entry's position (recency order) and every other field are untouched. Returns whether an entry
        with ``build_id`` was found.
        """
        with self._lock:
            for entry in self._entries:
                if entry["id"] != build_id:
                    continue
                if "file_count" in patch:
                    entry["file_count"] = int(patch["file_count"] or 0)
                if "commit_sha" in patch:
                    entry["commit_sha"] = str(patch["commit_sha"])[:40]
                if "entities" in patch and isinstance(patch["entities"], list):
                    entry["entities"] = [str(e) for e in patch["entities"][:_MAX_ENTITIES]]
                return True
            return False

    def remove(self, build_id: str) -> bool:
        """Remove the recorded build with ``build_id``; return whether it was present."""
        with self._lock:
            before = len(self._entries)
            self._entries = [entry for entry in self._entries if entry["id"] != build_id]
            return len(self._entries) != before
