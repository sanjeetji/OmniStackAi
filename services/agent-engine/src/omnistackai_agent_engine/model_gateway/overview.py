"""Deterministic, metadata-only platform overview for the console.

Exports a JSON-serializable snapshot of the model fabric — routing ladder, providers (local plus
every supported cloud option, with an active flag derived only from API-key presence), the price
book, and a usage/cost summary. It never includes an API key or any secret: a provider's key state is
a boolean, never the value. Consumed by the Next.js console (apps/console-web).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .accounting import DEFAULT_PRICE_BOOK, PriceBook, UsageLedger
from .cloud import resolve_provider_specs
from .ollama import OLLAMA_PROVIDER_ID

_DEFAULT_OUTPUT = "apps/console-web/data/overview.json"


def _empty_usage() -> dict[str, object]:
    return {
        "totalCalls": 0,
        "successfulCalls": 0,
        "failedCalls": 0,
        "inputTokens": 0,
        "outputTokens": 0,
        "totalCostUsd": "0",
        "unpricedCalls": 0,
        "costPerSuccessfulCallUsd": None,
        "latencyP50Ms": 0,
        "latencyP95Ms": 0,
        "breakdowns": [],
    }


def _usage_dict(ledger: UsageLedger) -> dict[str, object]:
    summary = ledger.summary()
    return {
        "totalCalls": summary.total_calls,
        "successfulCalls": summary.successful_calls,
        "failedCalls": summary.failed_calls,
        "inputTokens": summary.input_tokens,
        "outputTokens": summary.output_tokens,
        "totalCostUsd": str(summary.total_cost_usd),
        "unpricedCalls": summary.unpriced_calls,
        "costPerSuccessfulCallUsd": (
            str(summary.cost_per_successful_call_usd)
            if summary.cost_per_successful_call_usd is not None
            else None
        ),
        "latencyP50Ms": summary.latency_p50_ms,
        "latencyP95Ms": summary.latency_p95_ms,
        "breakdowns": [
            {
                "providerId": b.provider_id,
                "modelId": b.model_id,
                "calls": b.calls,
                "successfulCalls": b.successful_calls,
                "failedCalls": b.failed_calls,
                "inputTokens": b.input_tokens,
                "outputTokens": b.output_tokens,
                "costUsd": str(b.cost_usd),
                "unpricedCalls": b.unpriced_calls,
            }
            for b in summary.breakdowns
        ],
    }


def platform_overview(
    ledger: UsageLedger | None = None, price_book: PriceBook | None = None
) -> dict[str, object]:
    """Return a metadata-only overview of the model fabric. Never contains secrets."""

    book = price_book if price_book is not None else DEFAULT_PRICE_BOOK

    providers: list[dict[str, object]] = [
        {
            "providerId": OLLAMA_PROVIDER_ID,
            "tier": "local",
            "kind": "local",
            "defaultModel": os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b"),
            "active": True,
            "keyEnv": None,
        }
    ]
    for spec in resolve_provider_specs().values():
        providers.append(
            {
                "providerId": spec.provider_id,
                "tier": "cloud",
                "kind": spec.kind,
                "defaultModel": os.environ.get(spec.model_env, "") or spec.default_model,
                # active reflects only whether the key is configured; the value is never included.
                "active": bool(os.environ.get(spec.key_env, "").strip()),
                "keyEnv": spec.key_env,
            }
        )

    selection = (os.environ.get("OMNISTACKAI_CLOUD_PROVIDER", "none") or "none").strip().lower()

    routing_ladder = [
        {"level": "L0", "tier": None, "action": "deterministic tool — not routed to a model"},
        {"level": "L1", "tier": "local", "action": "small/cheap work → local Ollama"},
        {"level": "L2", "tier": "local", "action": "coding work → local Ollama"},
        {"level": "L3", "tier": "cloud", "action": "hard reasoning → selected cloud provider"},
        {"level": "L4", "tier": "cloud", "action": "critical/review → selected cloud provider"},
    ]

    price_rows = [
        {
            "providerId": provider_id,
            "modelId": model_id or "*",
            "inputPerMTokUsd": str(price.input_usd_per_million),
            "outputPerMTokUsd": str(price.output_usd_per_million),
        }
        for provider_id, model_id, price in book.entries()
    ]

    from .bootstrap import fallback_provider_ids_from_env  # local import avoids any import-order concern

    fallback_chain = list(fallback_provider_ids_from_env())
    breaker_enabled = bool(fallback_chain)
    resilience = {
        "fallbackChain": fallback_chain,
        "circuitBreaker": {
            "enabled": breaker_enabled,
            "failureThreshold": _positive_int_env("OMNISTACKAI_CIRCUIT_FAILURE_THRESHOLD", 3) if breaker_enabled else None,
            "cooldownSeconds": _positive_float_env("OMNISTACKAI_CIRCUIT_COOLDOWN_SECONDS", 30.0) if breaker_enabled else None,
        },
    }

    return {
        "note": "Static, metadata-only snapshot exported from the model gateway. Contains no API keys or secrets.",
        "routingMode": "balanced",
        "cloudTierSelected": None if selection in ("", "none") else selection,
        "routingLadder": routing_ladder,
        "providers": providers,
        "priceBook": price_rows,
        "resilience": resilience,
        "usage": _usage_dict(ledger) if ledger is not None else _empty_usage(),
    }


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    try:
        value = int(raw) if raw else default
    except ValueError:
        return default
    return value if value > 0 else default


def _positive_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    try:
        value = float(raw) if raw else default
    except ValueError:
        return default
    return value if value > 0 else default


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(_DEFAULT_OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(platform_overview(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote platform overview snapshot to {output}")


if __name__ == "__main__":
    main()
