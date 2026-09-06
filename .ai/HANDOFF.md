# Current Handoff

Task ID: R-009
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-009-usage-cost-accounting`
Last verified implementation SHA: `f2fc8654c6a5717e292adcdc2abb5da2fd7409c2`

## Completed

- Added deterministic, privacy-safe usage and cost accounting for the model gateway:
  - `UsageRecord`: immutable, metadata-only (provider, model, tier, complexity, token counts,
    latency, finish reason, success/error code) — never message content, response text, or a secret.
  - `PriceBook`: exact `Decimal` cost with exact and per-provider-wildcard lookup; local Ollama is
    zero; unknown models are unpriced; cached input can be priced separately. `DEFAULT_PRICE_BOOK`
    ships illustrative, operator-configurable cloud prices.
  - `UsageLedger`: thread-safe append with overall and per-provider/model breakdowns, deterministic
    p50/p95 latency, unpriced-call count, and cost per successful call.
- `ModelGateway` takes an optional `recorder`; it writes exactly one record per dispatch for success
  and failure without altering the returned response or the raised error (accounting is
  observational). `build_gateway_from_env(recorder=...)` threads a ledger through, and the live
  runner prints a cost summary.
- 13 new offline tests (74 total). Deterministic; no model call needed to verify.

## Verification

- `task verify` — pass (74 agent-engine tests).
- `task agent-engine:lint` — pass (compileall, no-deps contract, provider-SDK import exclusion).
- `task agent-engine:gateway:run` — pass live on local Ollama: recorded 2 successful calls,
  total_cost $0.000000, p50/p95 latency, per-provider breakdown; cloud_calls=0.
- `task security:quick` and `task env:check` — pass; no secret/content in records or state.
- Compose scope — exactly `postgres` and `control-plane`; unchanged.
- Tracker — R-009 inserted at `Phase_Roadmap!A9:M9` (rows 9..226 shifted to 10..227, ranges extended);
  no ID lost; MVP total 114, Done 9; chart/styles/workbook byte-identical; zip verified.

## Blockers and risks

- The ledger is in-memory (per process); durable/persistent cost storage and reporting are deferred.
- Default cloud prices are illustrative and must be overridden per deployment; unknown models are
  reported as unpriced.
- Cloud `health()` remains a config-readiness check and cloud `stream()` remains a single-event
  wrapper (from R-008); true per-provider streaming is deferred.

## Next action

Reconstruct R-010 with founder confirmation. The workbook's R-010 is "Native iOS Agent," which must
not begin before web/backend stability (Brief 25, 91) — recommend reordering to a nearer MVP
dependency such as true per-provider SSE streaming or cross-provider fallback/circuit breaking.

## Next command

`task ai:status`
