"""PC-010: what a build or an edit will cost, before it starts (R-046).

The estimate is grounded in what recent tasks actually used: every finished build and edit adds its
token counts to a small local history (no prompt, no content), and the estimate is the typical and
the high end (median and 90th percentile) of the last 30 of the same kind, priced for the model
this project would use now. With no history yet it falls back to conservative defaults, and says so.
A model with no configured price is reported as unpriced — it costs nothing — rather than guessed.
"""

from __future__ import annotations

import json
import os
import statistics
import threading
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from ..model_gateway.accounting import UsageLedger, price_book_from_env
from ..model_gateway.contracts import TokenUsage

KINDS = ("build", "edit", "design")
_WINDOW = 30
_KEEP = 500
#: Conservative starting points: (median input, median output, high input, high output) tokens.
_DEFAULTS = {
    "build": (9000, 4000, 20000, 9000),
    "edit": (6000, 2500, 12000, 6000),
    # PC-098: one page-design run - up to 8 pages of ~7k input and ~4.5k output, plus repairs.
    "design": (56000, 36000, 140000, 90000),
}
_MICROS = Decimal(1_000_000)
_lock = threading.Lock()


HISTORY_ENV = "OMNISTACKAI_USAGE_HISTORY"


def default_history_path() -> Path:
    return Path.home() / ".omnistackai" / "usage-history.jsonl"


def history_path() -> Path | None:
    """Set by the Studio server at start-up; unset (tests, one-off scripts) keeps no history."""
    configured = os.environ.get(HISTORY_ENV, "").strip()
    return Path(configured).expanduser() if configured else None


def record(kind: str, ledger: UsageLedger) -> None:
    """Add one finished task's token counts (metadata only) to the history."""
    summary = ledger.summary()
    if summary.total_calls:
        record_counts(kind, summary.input_tokens, summary.output_tokens)


def record_counts(kind: str, input_tokens: int, output_tokens: int) -> None:
    if kind not in KINDS:
        return
    line = json.dumps({"kind": kind, "input_tokens": int(input_tokens), "output_tokens": int(output_tokens)})
    path = history_path()
    if path is None:
        return
    with _lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
            lines = (lines + [line])[-_KEEP:]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass


def _recent(kind: str) -> list[dict]:
    path = history_path()
    if path is None:
        return []
    try:
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []
    return [r for r in rows if isinstance(r, dict) and r.get("kind") == kind][-_WINDOW:]


def _p90(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))]


def estimate(kind: str, provider_id: str, model_id: str) -> dict:
    kind = kind if kind in KINDS else "build"
    rows = _recent(kind)
    if len(rows) >= 3:
        ins = [int(r.get("input_tokens", 0)) for r in rows]
        outs = [int(r.get("output_tokens", 0)) for r in rows]
        low = (int(statistics.median(ins)), int(statistics.median(outs)))
        high = (_p90(ins), _p90(outs))
        basis = f"the last {len(rows)} {kind}s on this platform"
    else:
        d = _DEFAULTS[kind]
        low, high = (d[0], d[1]), (d[2], d[3])
        basis = "typical figures (not enough history yet)"
    book = price_book_from_env()
    cost_low = book.cost_for(provider_id, model_id, TokenUsage(low[0], low[1]))
    cost_high = book.cost_for(provider_id, model_id, TokenUsage(high[0], high[1]))

    def micros(cost: Decimal | None) -> int:
        return int((cost * _MICROS).to_integral_value(rounding=ROUND_HALF_UP)) if cost is not None else 0

    return {"kind": kind, "provider_id": provider_id, "model_id": model_id, "priced": cost_low is not None,
            "cost_micros_low": micros(cost_low), "cost_micros_high": micros(cost_high),
            "tokens_low": {"input": low[0], "output": low[1]}, "tokens_high": {"input": high[0], "output": high[1]},
            "basis": basis}
