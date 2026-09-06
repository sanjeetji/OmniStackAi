"""Per-provider circuit breaker for the model gateway.

A provider that fails repeatedly is skipped for a cooldown so the gateway stops hammering a broken
endpoint and fails over to the next allowlisted candidate. Deterministic and thread-safe, with an
injectable clock for testing. No network or model dependency.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from time import monotonic


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if isinstance(failure_threshold, bool) or not isinstance(failure_threshold, int) or failure_threshold <= 0:
            raise ValueError("failure_threshold must be a positive integer")
        if isinstance(cooldown_seconds, bool) or not isinstance(cooldown_seconds, (int, float)) or cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be a positive number")
        self._threshold = failure_threshold
        self._cooldown = float(cooldown_seconds)
        self._clock = clock
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def allows(self, provider_id: str) -> bool:
        """Return True if the provider may be tried now (closed or cooled-down half-open)."""

        with self._lock:
            open_until = self._open_until.get(provider_id)
            if open_until is None:
                return True
            if self._clock() >= open_until:
                # Cooldown elapsed: half-open — allow one trial and clear the open window.
                del self._open_until[provider_id]
                return True
            return False

    def record_success(self, provider_id: str) -> None:
        with self._lock:
            self._failures.pop(provider_id, None)
            self._open_until.pop(provider_id, None)

    def record_failure(self, provider_id: str) -> None:
        with self._lock:
            count = self._failures.get(provider_id, 0) + 1
            self._failures[provider_id] = count
            if count >= self._threshold:
                self._open_until[provider_id] = self._clock() + self._cooldown

    def state(self, provider_id: str) -> str:
        """Introspection: 'open', 'half_open', or 'closed'."""

        with self._lock:
            open_until = self._open_until.get(provider_id)
            if open_until is None:
                return "half_open" if self._failures.get(provider_id) else "closed"
            return "open" if self._clock() < open_until else "half_open"
