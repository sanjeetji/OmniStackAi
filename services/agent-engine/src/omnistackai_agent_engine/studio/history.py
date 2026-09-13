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

    def remove(self, build_id: str) -> bool:
        """Remove the recorded build with ``build_id``; return whether it was present."""
        with self._lock:
            before = len(self._entries)
            self._entries = [entry for entry in self._entries if entry["id"] != build_id]
            return len(self._entries) != before
