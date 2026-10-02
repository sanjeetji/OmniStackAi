"""PC-126: what the platform knows about each model provider right now, shared by every job.

Measured by the PC-122 benchmark: with the free tiers' quotas spent, every page and every build asked
Gemini, then OpenRouter, then NVIDIA again - each answering 429 after four retries (about 30 s) -
before reaching a provider that could answer. Each chain remembered a spent provider only for its own
run, and a build's chain did not remember at all. So the platform remembers, for everyone:

* **rate-limited** - out until the provider's own retry hint, or a minute;
* **a daily quota spent** - out until it resets (the next 08:00 UTC: midnight in California, where
  Gemini's and most free tiers' days end);
* **unavailable** (5xx, timeouts) - out for 30 s;
* **refused the key** (401/402/403) - out for an hour: a key does not fix itself.

A chain skips a provider that is out and goes straight to the next - local Ollama is always last and
never marked out by a cloud's limits. When every provider is out, the one back soonest is tried
anyway: a stale mark must never stop a build. Kept in the file ``OMNISTACKAI_MODEL_HEALTH_FILE``
names - ``scripts/omnistack.sh`` and the benchmark point it at ``~/.omnistackai/model-health.json``,
so the Studio, chat edits and benchmark runs share it. Unset (tests, one-off scripts), nothing is
remembered and every provider is available: a mark is advisory and never a secret.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PATH_ENV = "OMNISTACKAI_MODEL_HEALTH_FILE"
RATE_LIMITED_SECONDS = 60.0
UNAVAILABLE_SECONDS = 30.0
REFUSED_KEY_SECONDS = 3600.0
_LOCAL = ("ollama", "local")
_lock = threading.Lock()


DEFAULT_FILE = Path.home() / ".omnistackai" / "model-health.json"


def _path() -> Path | None:
    value = (os.environ.get(PATH_ENV) or "").strip()
    return Path(value).expanduser() if value else None


def _read() -> dict[str, dict[str, Any]]:
    path = _path()
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data: dict[str, dict[str, Any]]) -> None:
    path = _path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass  # advisory: a read-only home must not fail a build


def _key(provider_id: str) -> str:
    provider_id = (provider_id or "").lower()
    return "google" if provider_id in ("google-gemini", "gemini") else provider_id


def next_daily_reset(now: float | None = None) -> float:
    current = datetime.fromtimestamp(now if now is not None else time.time(), tz=timezone.utc)
    reset = current.replace(hour=8, minute=0, second=0, microsecond=0)
    if reset <= current:
        reset += timedelta(days=1)
    return reset.timestamp()


def classify(error: BaseException) -> tuple[str, float] | None:
    """(state, seconds) for an error that says the provider is out for a while; None otherwise."""
    from .errors import (
        MissingCredentialError,
        ProviderHTTPError,
        ProviderRateLimitedError,
        ProviderTimeoutError,
        ProviderUnavailableError,
    )

    text = str(error)
    status = getattr(error, "status_code", None)
    if status == 413:
        # Groq's free tier answers 413 for a request over its tokens-per-minute limit (PC-106):
        # out for a minute, like any other per-minute limit.
        return "rate_limited", RATE_LIMITED_SECONDS
    if isinstance(error, ProviderRateLimitedError) or status == 429:
        if re.search(r"PerDay|per day|daily|quota", text, re.I) and "minute" not in text.lower():
            return "quota", max(60.0, next_daily_reset() - time.time())
        hinted = getattr(error, "retry_after_seconds", None)
        return "rate_limited", float(min(max(hinted or RATE_LIMITED_SECONDS, 5.0), 3600.0))
    if isinstance(error, MissingCredentialError) or status in (401, 402, 403):
        return "refused_key", REFUSED_KEY_SECONDS
    if isinstance(error, (ProviderUnavailableError, ProviderTimeoutError, TimeoutError)) or (
            isinstance(error, ProviderHTTPError) and isinstance(status, int) and status >= 500):
        return "unavailable", UNAVAILABLE_SECONDS
    return None


def note_failure(provider_id: str, error: BaseException, now: float | None = None) -> str | None:
    """Remember why ``provider_id`` cannot answer, when the error says it will not for a while."""
    if _key(provider_id) in _LOCAL:
        return None
    found = classify(error)
    if found is None:
        return None
    state, seconds = found
    now = time.time() if now is None else now
    with _lock:
        data = _read()
        data[_key(provider_id)] = {"state": state, "until": now + seconds, "since": now, "why": str(error)[:200]}
        _write(data)
    return state


def note_success(provider_id: str) -> None:
    with _lock:
        data = _read()
        if data.pop(_key(provider_id), None) is not None:
            _write(data)


def out_until(provider_id: str, now: float | None = None) -> float:
    """When ``provider_id`` is back (0.0: it is available now)."""
    if _key(provider_id) in _LOCAL:
        return 0.0
    mark = _read().get(_key(provider_id))
    now = time.time() if now is None else now
    if not mark or float(mark.get("until", 0)) <= now:
        return 0.0
    return float(mark["until"])


def is_available(provider_id: str, now: float | None = None) -> bool:
    return out_until(provider_id, now) == 0.0


def order(provider_ids: list[str], now: float | None = None) -> list[int]:
    """Indices to try: the available ones in their order, then the rest by when they are back."""
    now = time.time() if now is None else now
    backs = [out_until(p, now) for p in provider_ids]
    ready = [i for i, back in enumerate(backs) if back == 0.0]
    waiting = sorted((i for i, back in enumerate(backs) if back), key=lambda i: backs[i])
    return ready + waiting


def snapshot(now: float | None = None) -> dict[str, dict[str, Any]]:
    """Every provider that is out now: its state, seconds until it is back, and why."""
    now = time.time() if now is None else now
    return {name: {"state": m.get("state"), "back_in_seconds": round(float(m["until"]) - now), "why": m.get("why", "")}
            for name, m in _read().items() if float(m.get("until", 0)) > now}
