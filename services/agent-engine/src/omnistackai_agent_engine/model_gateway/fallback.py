"""A build keeps going when one provider cannot answer (founder, 2026-09-26).

`OMNISTACKAI_FALLBACK_PROVIDERS` existed, but only the tiered router read it: an app build resolved
a single provider, so when Groq's free tier said 429 the build simply failed. This wraps the build's
provider in an ordered chain — each entry with its own model — and moves to the next only for
failures a different provider can fix: rate limits, timeouts, an unreachable service, a rejected or
missing key, a server error. A bad request or a bad answer is not retried elsewhere; it would fail
the same way and cost a second provider's quota.

Streaming falls over only before the first token reaches the user. After that the text is on their
screen, and silently restarting it from another model would show them two different plans.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import GenerateRequest, ModelRef
from .errors import (
    MissingCredentialError,
    ProviderHTTPError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChainEntry:
    provider: Any
    model_id: str
    max_output_tokens: int
    #: None keeps the caller's timeout; the local model gets its own, longer one.
    timeout_seconds: float | None = None


def _worth_another_provider(error: Exception) -> bool:
    if isinstance(error, (ProviderRateLimitedError, ProviderTimeoutError, ProviderUnavailableError,
                          MissingCredentialError)):
        return True
    if isinstance(error, ProviderHTTPError):
        status = getattr(error, "status_code", None) or getattr(error, "status", None)
        if isinstance(status, int):
            return status in (401, 402, 403, 404, 408, 429) or status >= 500
        return True
    return False


class FallbackChainProvider:
    """Looks like the first provider; answers from the first one in the chain that can."""

    def __init__(self, entries: Sequence[ChainEntry]) -> None:
        if not entries:
            raise ValueError("a fallback chain needs at least one provider")
        self._entries = tuple(entries)
        self.provider_id = entries[0].provider.provider_id
        #: The provider that answered the last request, for the build record.
        self.last_provider_id: str | None = None

    @property
    def chain(self) -> tuple[str, ...]:
        return tuple(f"{e.provider.provider_id}:{e.model_id}" for e in self._entries)

    def _request_for(self, entry: ChainEntry, request: GenerateRequest) -> GenerateRequest:
        return dataclasses.replace(
            request,
            model=ModelRef(entry.provider.provider_id, entry.model_id),
            max_output_tokens=min(request.max_output_tokens, entry.max_output_tokens),
            timeout_seconds=max(request.timeout_seconds, entry.timeout_seconds or 0),
        )

    async def generate(self, request: GenerateRequest):
        last: Exception | None = None
        for index, entry in enumerate(self._entries):
            try:
                response = await entry.provider.generate(self._request_for(entry, request))
                self.last_provider_id = entry.provider.provider_id
                return response
            except Exception as error:  # noqa: BLE001 - classified below
                if not _worth_another_provider(error) or index == len(self._entries) - 1:
                    raise
                log.warning("%s could not answer (%s); trying %s", entry.provider.provider_id,
                            type(error).__name__, self._entries[index + 1].provider.provider_id)
                last = error
        raise last  # pragma: no cover - the loop always returns or raises

    async def stream(self, request: GenerateRequest) -> AsyncIterator[Any]:
        for index, entry in enumerate(self._entries):
            started = False
            try:
                async for event in entry.provider.stream(self._request_for(entry, request)):
                    if not started:
                        started = True
                        self.last_provider_id = entry.provider.provider_id
                    yield event
                return
            except Exception as error:  # noqa: BLE001 - classified below
                if started or not _worth_another_provider(error) or index == len(self._entries) - 1:
                    raise
                log.warning("%s could not stream (%s); trying %s", entry.provider.provider_id,
                            type(error).__name__, self._entries[index + 1].provider.provider_id)

    def __getattr__(self, name: str) -> Any:
        # Descriptor, profiles and the like come from the primary provider.
        return getattr(self._entries[0].provider, name)
