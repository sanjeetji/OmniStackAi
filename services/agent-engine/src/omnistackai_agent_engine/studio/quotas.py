"""PC-009: fair shares on a shared host (R-175).

One person's runaway loop must not take everyone else's builds and previews with it. The limits,
each overridable per host:

* ``OMNISTACKAI_MAX_PREVIEWS_PER_USER`` (2): a user's third running preview stops their oldest —
  they are only looking at one at a time, and refusing would feel broken;
* ``OMNISTACKAI_MAX_PREVIEWS`` (20): a full host refuses a new preview with a clear message;
* ``OMNISTACKAI_BUILDS_PER_HOUR`` (30): per user, rolling; the answer says when to try again;
* ``OMNISTACKAI_PREVIEW_IDLE_MINUTES`` (30): a preview nobody has opened for that long is stopped.
  The console's preview proxy asks for status on every request, so "opened" is exact.

Who is asking comes from the control plane (``X-OmniStack-User``), which is believed only because
the Studio requires the control plane's token for every request in a multi-user deployment. With
no user (a single operator), builds and previews are unlimited, as before.
"""

from __future__ import annotations

import contextvars
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field

#: The user the current request acts for, set by the server from X-OmniStack-User.
current_user: contextvars.ContextVar[str | None] = contextvars.ContextVar("omnistack_user", default=None)
#: PC-011: that user's plan limits, from X-OmniStack-Limits ("previews_per_user=2;builds_per_hour=30;...").
current_limits: contextvars.ContextVar[dict[str, int] | None] = contextvars.ContextVar("omnistack_limits", default=None)


def parse_limits(header: str | None) -> dict[str, int] | None:
    if not header:
        return None
    out: dict[str, int] = {}
    for part in header.split(";"):
        key, _, value = part.partition("=")
        try:
            out[key.strip()] = max(0, int(value))
        except ValueError:
            continue
    return out or None


def _plan_limit(key: str, env_name: str, default: int) -> int:
    """The user's plan limit when the control plane sent one (0 = unlimited), else the host's."""
    limits = current_limits.get()
    if limits is not None and key in limits:
        return limits[key]
    return _int(env_name, default)


class QuotaExceeded(Exception):
    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, "") or default))
    except ValueError:
        return default


@dataclass
class _Preview:
    user: str | None
    started: float
    last_seen: float = field(default=0.0)


class Quotas:
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._builds: dict[str, deque[float]] = {}
        self._previews: dict[str, _Preview] = {}

    # ── builds ──
    def admit_build(self, user: str | None) -> None:
        if not user:
            return
        limit = _plan_limit("builds_per_hour", "OMNISTACKAI_BUILDS_PER_HOUR", 30)
        now = self._clock()
        with self._lock:
            window = self._builds.setdefault(user, deque())
            while window and now - window[0] >= 3600:
                window.popleft()
            if limit and len(window) >= limit:
                retry = int(3600 - (now - window[0])) + 1
                minutes = max(1, retry // 60)
                raise QuotaExceeded(f"You have started {limit} build{'s' if limit != 1 else ''} in the last hour. "
                                    f"Try again in {minutes} minute{'s' if minutes != 1 else ''}.", retry_after=retry)
            window.append(now)

    # ── previews ──
    def admit_preview(self, user: str | None, workspace_id: str) -> list[str]:
        """Record a starting preview; return the previews to stop to make room for it."""
        now = self._clock()
        with self._lock:
            others = {ws: p for ws, p in self._previews.items() if ws != workspace_id}
            host_limit = _int("OMNISTACKAI_MAX_PREVIEWS", 20)
            evict: list[str] = []
            if user:
                mine = sorted((p.started, ws) for ws, p in others.items() if p.user == user)
                per_user = _plan_limit("previews_per_user", "OMNISTACKAI_MAX_PREVIEWS_PER_USER", 2)
                while per_user and len(mine) >= per_user:
                    evict.append(mine.pop(0)[1])
            if host_limit and len(others) - len(evict) >= host_limit:
                raise QuotaExceeded("The preview servers are full right now. Close a preview or try again "
                                    "in a few minutes.", retry_after=120)
            for ws in evict:
                self._previews.pop(ws, None)
            self._previews[workspace_id] = _Preview(user=user, started=now, last_seen=now)
            return evict

    def touch(self, workspace_id: str) -> None:
        with self._lock:
            preview = self._previews.get(workspace_id)
            if preview is not None:
                preview.last_seen = self._clock()

    def stopped(self, workspace_id: str) -> None:
        with self._lock:
            self._previews.pop(workspace_id, None)

    def idle(self) -> list[str]:
        """Previews unopened for longer than the idle limit; they are forgotten here."""
        limit = _int("OMNISTACKAI_PREVIEW_IDLE_MINUTES", 30) * 60
        if not limit:
            return []
        now = self._clock()
        with self._lock:
            stale = [ws for ws, p in self._previews.items() if now - p.last_seen > limit]
            for ws in stale:
                self._previews.pop(ws, None)
            return stale

    def usage(self, user: str | None) -> dict:
        now = self._clock()
        with self._lock:
            builds = [t for t in self._builds.get(user or "", ()) if now - t < 3600]
            return {
                "previews_running": sum(1 for p in self._previews.values() if p.user == user) if user else None,
                "previews_per_user": _int("OMNISTACKAI_MAX_PREVIEWS_PER_USER", 2),
                "builds_last_hour": len(builds) if user else None,
                "builds_per_hour": _int("OMNISTACKAI_BUILDS_PER_HOUR", 30),
                "idle_minutes": _int("OMNISTACKAI_PREVIEW_IDLE_MINUTES", 30),
            }
