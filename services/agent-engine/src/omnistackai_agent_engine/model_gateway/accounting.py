"""Deterministic, privacy-safe usage and cost accounting for the model gateway.

Every gateway dispatch produces one immutable, metadata-only :class:`UsageRecord` — provider, model,
tier, complexity, token counts, latency, finish reason, and success/error code. No message content,
response text, request payload, or secret is ever stored (Brief 90). A configurable :class:`PriceBook`
computes an exact USD estimate with :class:`decimal.Decimal`; local Ollama is zero and unknown models
are recorded as unpriced rather than guessed. :class:`UsageLedger` aggregates the records so the
platform can optimize cost per successful accepted change (Brief 18.4, 68, 92.15).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from .contracts import TokenUsage, validate_provider_id

_MILLION = Decimal(1_000_000)
_CENT = Decimal("0.000001")  # micro-dollar precision


def _to_decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int) and not isinstance(value, bool):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except ArithmeticError as error:
            raise ValueError(f"{field_name} must be a valid decimal string") from error
    else:
        raise TypeError(f"{field_name} must be a Decimal, int, or decimal string (never a float)")
    if result < 0:
        raise ValueError(f"{field_name} must not be negative")
    return result


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """USD price per one million tokens for one model configuration."""

    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cached_input_usd_per_million: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_usd_per_million", _to_decimal(self.input_usd_per_million, "input_usd_per_million"))
        object.__setattr__(self, "output_usd_per_million", _to_decimal(self.output_usd_per_million, "output_usd_per_million"))
        if self.cached_input_usd_per_million is not None:
            object.__setattr__(
                self, "cached_input_usd_per_million",
                _to_decimal(self.cached_input_usd_per_million, "cached_input_usd_per_million"),
            )

    def cost_for(self, usage: TokenUsage) -> Decimal:
        cached = usage.cached_input_tokens if self.cached_input_usd_per_million is not None else 0
        billed_input = usage.input_tokens - cached
        total = (
            Decimal(billed_input) / _MILLION * self.input_usd_per_million
            + Decimal(usage.output_tokens) / _MILLION * self.output_usd_per_million
        )
        if cached:
            total += Decimal(cached) / _MILLION * self.cached_input_usd_per_million  # type: ignore[operator]
        return total.quantize(_CENT, rounding=ROUND_HALF_UP)


class PriceBook:
    """Maps (provider_id, model_id) to a :class:`ModelPrice`, with a per-provider wildcard fallback."""

    def __init__(self, prices: dict[tuple[str, str | None], ModelPrice] | None = None) -> None:
        self._prices: dict[tuple[str, str | None], ModelPrice] = {}
        for (provider_id, model_id), price in (prices or {}).items():
            validate_provider_id(provider_id)
            if not isinstance(price, ModelPrice):
                raise TypeError("price must be a ModelPrice")
            self._prices[(provider_id, model_id)] = price

    def get(self, provider_id: str, model_id: str) -> ModelPrice | None:
        return self._prices.get((provider_id, model_id)) or self._prices.get((provider_id, None))

    def entries(self) -> tuple[tuple[str, str | None, ModelPrice], ...]:
        """Return all configured prices, deterministically ordered, for read-only introspection."""

        return tuple(
            (provider_id, model_id, price)
            for (provider_id, model_id), price in sorted(
                self._prices.items(), key=lambda item: (item[0][0], item[0][1] or "")
            )
        )

    def cost_for(self, provider_id: str, model_id: str, usage: TokenUsage) -> Decimal | None:
        price = self.get(provider_id, model_id)
        return None if price is None else price.cost_for(usage)


# Illustrative, operator-configurable defaults (USD per 1M tokens). Cloud prices change over time and
# should be overridden per deployment; OpenRouter is intentionally unpriced (it varies by model).
DEFAULT_PRICE_BOOK = PriceBook(
    {
        ("ollama-local", None): ModelPrice("0", "0"),
        ("anthropic", "claude-sonnet-5"): ModelPrice("3", "15"),
        ("openai", "gpt-4o"): ModelPrice("2.5", "10"),
        ("google-gemini", "gemini-1.5-pro"): ModelPrice("1.25", "5"),
        ("groq", "llama-3.3-70b-versatile"): ModelPrice("0.59", "0.79"),
        ("deepseek", "deepseek-chat"): ModelPrice("0.27", "1.10"),
        ("xai", "grok-2-latest"): ModelPrice("2", "10"),
        ("mistral", "mistral-large-latest"): ModelPrice("2", "6"),
        ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"): ModelPrice("0.88", "0.88"),
        ("fireworks", "accounts/fireworks/models/llama-v3p3-70b-instruct"): ModelPrice("0.9", "0.9"),
        # openrouter and custom providers are intentionally unpriced (they vary by model).
    }
)


@dataclass(frozen=True, slots=True)
class UsageRecord:
    """Immutable, metadata-only evidence of one model dispatch. Never holds content or secrets."""

    request_id: str
    provider_id: str
    model_id: str
    tier: str
    complexity: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    latency_ms: int
    success: bool
    finish_reason: str | None
    error_code: str | None
    cost_usd: Decimal | None
    created_at: datetime

    def __post_init__(self) -> None:
        validate_provider_id(self.provider_id)
        for name in ("model_id", "tier", "complexity"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("input_tokens", "output_tokens", "cached_input_tokens", "latency_ms"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if not isinstance(self.success, bool):
            raise TypeError("success must be a boolean")
        if self.finish_reason is not None and not isinstance(self.finish_reason, str):
            raise TypeError("finish_reason must be a string or None")
        if self.error_code is not None and not isinstance(self.error_code, str):
            raise TypeError("error_code must be a string or None")
        if self.cost_usd is not None and not isinstance(self.cost_usd, Decimal):
            raise TypeError("cost_usd must be a Decimal or None")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class UsageBreakdown:
    provider_id: str
    model_id: str
    calls: int
    successful_calls: int
    failed_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    unpriced_calls: int


@dataclass(frozen=True, slots=True)
class UsageSummary:
    total_calls: int
    successful_calls: int
    failed_calls: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: Decimal
    unpriced_calls: int
    cost_per_successful_call_usd: Decimal | None
    latency_p50_ms: int
    latency_p95_ms: int
    breakdowns: tuple[UsageBreakdown, ...] = field(default_factory=tuple)


def _percentile(sorted_values: list[int], percentile: int) -> int:
    if not sorted_values:
        return 0
    rank = max(1, -(-percentile * len(sorted_values) // 100))  # nearest-rank, ceil
    return sorted_values[min(rank, len(sorted_values)) - 1]


class UsageLedger:
    """Thread-safe append-only ledger of :class:`UsageRecord` with deterministic aggregation."""

    def __init__(self, price_book: PriceBook | None = None) -> None:
        self._price_book = price_book if price_book is not None else DEFAULT_PRICE_BOOK
        self._records: list[UsageRecord] = []
        self._lock = threading.Lock()

    def record_call(
        self,
        *,
        request_id: str,
        provider_id: str,
        model_id: str,
        tier: str,
        complexity: str,
        usage: TokenUsage | None,
        latency_ms: int,
        success: bool,
        finish_reason: str | None = None,
        error_code: str | None = None,
    ) -> UsageRecord:
        cost = self._price_book.cost_for(provider_id, model_id, usage) if (success and usage is not None) else None
        record = UsageRecord(
            request_id=request_id,
            provider_id=provider_id,
            model_id=model_id,
            tier=tier,
            complexity=complexity,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            cached_input_tokens=usage.cached_input_tokens if usage else 0,
            latency_ms=latency_ms,
            success=success,
            finish_reason=finish_reason,
            error_code=error_code,
            cost_usd=cost,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            self._records.append(record)
        return record

    def records(self) -> tuple[UsageRecord, ...]:
        with self._lock:
            return tuple(self._records)

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)

    def summary(self) -> UsageSummary:
        records = self.records()
        groups: dict[tuple[str, str], list[UsageRecord]] = {}
        for record in records:
            groups.setdefault((record.provider_id, record.model_id), []).append(record)

        breakdowns = tuple(
            _breakdown(provider_id, model_id, group)
            for (provider_id, model_id), group in sorted(groups.items())
        )
        successful = [r for r in records if r.success]
        priced = [r for r in successful if r.cost_usd is not None]
        total_cost = sum((r.cost_usd for r in priced), Decimal("0"))
        latencies = sorted(r.latency_ms for r in records)
        cost_per_successful = (
            (total_cost / Decimal(len(priced))).quantize(_CENT, rounding=ROUND_HALF_UP)
            if priced else None
        )
        return UsageSummary(
            total_calls=len(records),
            successful_calls=len(successful),
            failed_calls=len(records) - len(successful),
            input_tokens=sum(r.input_tokens for r in records),
            output_tokens=sum(r.output_tokens for r in records),
            total_cost_usd=total_cost,
            unpriced_calls=sum(1 for r in successful if r.cost_usd is None),
            cost_per_successful_call_usd=cost_per_successful,
            latency_p50_ms=_percentile(latencies, 50),
            latency_p95_ms=_percentile(latencies, 95),
            breakdowns=breakdowns,
        )


def _breakdown(provider_id: str, model_id: str, group: list[UsageRecord]) -> UsageBreakdown:
    successful = [r for r in group if r.success]
    return UsageBreakdown(
        provider_id=provider_id,
        model_id=model_id,
        calls=len(group),
        successful_calls=len(successful),
        failed_calls=len(group) - len(successful),
        input_tokens=sum(r.input_tokens for r in group),
        output_tokens=sum(r.output_tokens for r in group),
        cost_usd=sum((r.cost_usd for r in group if r.cost_usd is not None), Decimal("0")),
        unpriced_calls=sum(1 for r in successful if r.cost_usd is None),
    )
