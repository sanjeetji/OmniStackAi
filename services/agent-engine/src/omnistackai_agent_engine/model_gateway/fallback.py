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
            # PC-106: 413 too - Groq's free tier answers it for a request over its per-minute token
            # limit ("rate_limit_exceeded"), which the next provider accepts.
            return status in (401, 402, 403, 404, 408, 413, 429) or status >= 500
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
    def entries(self) -> tuple[ChainEntry, ...]:
        return self._entries

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

    def _ordered(self) -> list[tuple[int, ChainEntry]]:
        """PC-126: providers known to be out (a spent quota, a limit, an outage) are tried last."""
        from . import health

        order = health.order([e.provider.provider_id for e in self._entries])
        skipped = [self._entries[i].provider.provider_id for i in order if not health.is_available(self._entries[i].provider.provider_id)]
        if skipped:
            log.info("skipping for now (out): %s", ", ".join(skipped))
        return [(i, self._entries[i]) for i in order]

    async def generate(self, request: GenerateRequest):
        from . import health

        last: Exception | None = None
        ordered = self._ordered()
        for position, (_index, entry) in enumerate(ordered):
            is_last = position == len(ordered) - 1
            try:
                response = await entry.provider.generate(self._request_for(entry, request))
                # PC-101: a provider that answers with nothing is no better than one that failed
                # (seen live: a build ended "model returned an empty response" with providers left).
                if not (getattr(response, "text", "") or "").strip() and not is_last:
                    log.warning("%s answered with nothing; trying %s", entry.provider.provider_id,
                                ordered[position + 1][1].provider.provider_id)
                    continue
                self.last_provider_id = entry.provider.provider_id
                health.note_success(entry.provider.provider_id)
                return response
            except Exception as error:  # noqa: BLE001 - classified below
                health.note_failure(entry.provider.provider_id, error)
                if not _worth_another_provider(error) or is_last:
                    raise
                status = getattr(error, "status_code", None)
                log.warning("%s could not answer (%s%s); trying %s", entry.provider.provider_id,
                            type(error).__name__, f" {status}" if status else "",
                            ordered[position + 1][1].provider.provider_id)
                last = error
        raise last  # pragma: no cover - the loop always returns or raises

    async def stream(self, request: GenerateRequest) -> AsyncIterator[Any]:
        from . import health

        ordered = self._ordered()
        for position, (_index, entry) in enumerate(ordered):
            started = False
            held: list[Any] = []  # events before the first text, dropped if this provider says nothing
            last_entry = position == len(ordered) - 1
            try:
                async for event in entry.provider.stream(self._request_for(entry, request)):
                    if not started and not getattr(event, "delta", "") and not last_entry:
                        held.append(event)
                        continue
                    if not started:
                        started = True
                        self.last_provider_id = entry.provider.provider_id
                        for early in held:
                            yield early
                        held = []
                    yield event
                if not started and not last_entry:
                    log.warning("%s streamed nothing; trying %s", entry.provider.provider_id,
                                ordered[position + 1][1].provider.provider_id)
                    continue
                health.note_success(entry.provider.provider_id)
                return
            except Exception as error:  # noqa: BLE001 - classified below
                health.note_failure(entry.provider.provider_id, error)
                if started or not _worth_another_provider(error) or last_entry:
                    raise
                log.warning("%s could not stream (%s); trying %s", entry.provider.provider_id,
                            type(error).__name__, ordered[position + 1][1].provider.provider_id)

    def after(self, provider_id: str | None, error: Exception) -> "FallbackChainProvider | None":
        """The rest of the chain after ``provider_id``, when ``error`` is one another provider can fix.

        PC-106: a stream is never switched once text is flowing - the reader has seen it. A caller
        that keeps the whole answer (the planner parses it as one JSON document) can instead start
        the request again with this, discarding what it had.
        """
        if not _worth_another_provider(error):
            return None
        from . import health

        ids = [e.provider.provider_id for e in self._entries]
        if provider_id not in ids:
            return None
        # The live order (PC-126), not the configured one: a provider listed earlier that is
        # answering is still worth trying, and the one that just failed is left out.
        rest = [self._entries[i] for i in health.order(ids) if ids[i] != provider_id]
        return FallbackChainProvider(rest) if rest else None

    def __getattr__(self, name: str) -> Any:
        # Descriptor, profiles and the like come from the primary provider.
        return getattr(self._entries[0].provider, name)
