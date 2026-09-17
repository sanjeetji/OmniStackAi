"""In-memory edit-session state for the OmniStackAI Studio (R-468).

Tracks, per recorded build id, the app's CURRENT ``ApplicationIR`` (so a follow-up prompt has something to
diff against) and a bounded turn history -- entirely server-only, in-memory, lost on restart, the same
idiom as `StudioBuildHistory`/`StudioPreviewManager`. The ``ApplicationIR`` itself is never JSON-serialized
or sent to the browser; ``turns_view`` is the one bounded, secret-free view exposed over HTTP.
"""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable

from ..application_ir import ApplicationIR

_DEFAULT_LIMIT = 10
_DEFAULT_MAX_TURNS = 20
_MAX_TURN_CHARS = 2_000
_VALID_ROLES = frozenset({"user", "assistant"})


class EditNotSupportedError(Exception):
    """Raised when a follow-up edit is requested for a build kind R-468 doesn't support yet.

    Solution Pack builds already have their own, separate AI-delta path at build time; multi-surface
    ("all surfaces") Ecosystem Pack builds have no single Application IR to edit. Both cases are reported
    honestly rather than silently ignored or guessed at.
    """


@dataclass(slots=True)
class SessionEntry:
    """One build's live edit session. Server-only -- never returned as JSON directly."""

    ir: ApplicationIR
    target_dir: str
    turns: deque = field(default_factory=lambda: deque(maxlen=_DEFAULT_MAX_TURNS))


class StudioSessionStore:
    """A bounded, thread-safe, in-memory map of build id -> live edit session.

    Bounded by ``limit`` sessions, evicting the least-recently-touched one (``begin``/``advance``/
    ``record_turn`` all count as a touch) -- an `OrderedDict` used as an LRU, mirroring
    `StudioBuildHistory`'s bounded-ring idiom but keyed by the same build id rather than an internal counter.
    """

    def __init__(
        self, *, limit: int = _DEFAULT_LIMIT, max_turns: int = _DEFAULT_MAX_TURNS, clock: Callable[[], float] = time.time
    ) -> None:
        self._limit = max(1, limit)
        self._max_turns = max(1, max_turns)
        self._clock = clock
        self._sessions: OrderedDict[str, SessionEntry] = OrderedDict()
        self._lock = Lock()

    def begin(self, build_id: str, ir: ApplicationIR, target_dir: str) -> None:
        """Start (or restart) a session for ``build_id`` with a fresh turn history."""
        with self._lock:
            self._sessions[build_id] = SessionEntry(ir=ir, target_dir=target_dir, turns=deque(maxlen=self._max_turns))
            self._sessions.move_to_end(build_id)
            while len(self._sessions) > self._limit:
                self._sessions.popitem(last=False)

    def get(self, build_id: str) -> SessionEntry | None:
        """Return the live session for ``build_id``, or None. Does not count as a touch (read-only)."""
        with self._lock:
            return self._sessions.get(build_id)

    def advance(self, build_id: str, new_ir: ApplicationIR) -> None:
        """Replace the tracked IR after a successful edit. A no-op if the session is gone."""
        with self._lock:
            entry = self._sessions.get(build_id)
            if entry is None:
                return
            entry.ir = new_ir
            self._sessions.move_to_end(build_id)

    def record_turn(self, build_id: str, role: str, text: str) -> None:
        """Append one bounded turn. A no-op if the session is gone; raises on an unknown role."""
        if role not in _VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(_VALID_ROLES)}: {role!r}")
        with self._lock:
            entry = self._sessions.get(build_id)
            if entry is None:
                return
            entry.turns.append({"role": role, "text": str(text)[:_MAX_TURN_CHARS], "created_at": self._clock()})
            self._sessions.move_to_end(build_id)

    def turns_view(self, build_id: str) -> dict:
        """A JSON-safe, secret-free turn list for the browser. Empty for an unknown/evicted session."""
        with self._lock:
            entry = self._sessions.get(build_id)
            if entry is None:
                return {"turns": []}
            return {"turns": [dict(turn) for turn in entry.turns]}
