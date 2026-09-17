"""Ledger-recording ``ModelProvider`` decorator (R-472).

The Studio's actual build/edit flow (``intake/provider_resolution.py::
resolve_generation_provider_from_env``) hands callers a **raw** ``ModelProvider`` — for the cloud
path it pulls the provider straight out of a ``ModelGateway``'s registry rather than returning the
gateway itself. That means the gateway's own accounting hook (``accounting.UsageLedger``, already
real and tested) is never exercised by a real build; today it only ever runs for
``console_snapshot``'s illustrative metadata dashboard.

``RecordingProvider`` closes that gap without touching the gateway, any provider implementation, or
any of the many existing call sites that already just do ``provider.generate(...)``: it implements
the exact same ``ModelProvider`` protocol, forwards every call to the wrapped provider unchanged,
and records the real outcome (success with real token usage, or failure) into an injected
``UsageLedger``.
"""

from __future__ import annotations

import time

from .accounting import UsageLedger
from .contracts import (
    GenerateRequest,
    GenerateResponse,
    ModelDescriptor,
    ModelProvider,
    ProviderHealth,
)
from .ollama import OLLAMA_PROVIDER_ID

# The routing ladder's tier/complexity concepts (RoutingDecision.tier/.complexity) come from
# ModelGateway's own escalation logic, which this direct-provider path never runs. "app_generation"
# is a fixed, honest label for this call class rather than a fabricated routing-ladder value.
_COMPLEXITY_LABEL = "app_generation"


class RecordingProvider:
    """A ``ModelProvider`` that forwards to ``inner`` and records every call into ``ledger``."""

    def __init__(self, inner: ModelProvider, ledger: UsageLedger) -> None:
        self._inner = inner
        self._ledger = ledger

    @property
    def provider_id(self) -> str:
        return self._inner.provider_id

    async def health(self) -> ProviderHealth:
        return await self._inner.health()

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return await self._inner.discover_models()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        tier = "local" if self._inner.provider_id == OLLAMA_PROVIDER_ID else "cloud"
        started = time.monotonic()
        try:
            response = await self._inner.generate(request)
        except Exception as error:
            self._ledger.record_call(
                request_id=request.request_id,
                provider_id=self._inner.provider_id,
                model_id=request.model.model_id,
                tier=tier,
                complexity=_COMPLEXITY_LABEL,
                usage=None,
                latency_ms=int((time.monotonic() - started) * 1000),
                success=False,
                error_code=getattr(error, "code", type(error).__name__),
            )
            raise

        self._ledger.record_call(
            request_id=response.request_id,
            provider_id=self._inner.provider_id,
            model_id=request.model.model_id,
            tier=tier,
            complexity=_COMPLEXITY_LABEL,
            usage=response.usage,
            latency_ms=response.latency_ms,
            success=True,
            finish_reason=response.finish_reason.value,
        )
        return response
