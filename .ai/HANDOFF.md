# Current Handoff

Task ID: R-221
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-221-cross-provider-fallback`
Last verified implementation SHA: `d0ee9f75b0d124fe60f1121b7f2a70d3b73040de`

## Completed

- Added explicit, allowlist-driven cross-provider fallback plus per-provider circuit breaking to the
  Balanced gateway:
  - `RoutingPolicy.fallback` — an optional ordered chain of `ModelDescriptor`. With none configured
    the gateway behaves exactly as before (single provider).
  - `generate`/`stream` try the primary then each registered, in-budget, circuit-closed candidate.
    Fail-over is explicit (chain only) and only on retriable errors (`ProviderUnavailableError`,
    `ProviderTimeoutError`, `ProviderHTTPError`); non-retriable errors raise immediately. Streaming
    fails over only before the first event.
  - `CircuitBreaker` (`resilience.py`): opens after `failure_threshold` consecutive failures, skips
    for `cooldown_seconds`, half-opens, resets on success; injectable clock, thread-safe.
  - `AllProvidersFailedError` when the chain is exhausted; a single-provider config surfaces its own
    error. Every attempt is still recorded by the accounting ledger.

## Verification

- `task verify` — pass (86 agent-engine tests; 8 new).
- `task agent-engine:gateway:run` — pass live on local Ollama with cost summary; cloud_calls=0.
- `task security:quick`, `task env:check` — pass. Compose unchanged (`postgres`, `control-plane`).
- Tracker — R-221 at `Phase_Roadmap!A9:M9` (rows 9..228 shifted to 10..229, ranges extended); no ID
  lost; backlog intact; MVP total 116, Done 11; chart/styles/workbook byte-identical; zip verified.

## How to configure fallback / circuit breaking

```python
policy = RoutingPolicy(local_model=ollama_desc, cloud_model=anthropic_desc,
                       fallback=(anthropic_desc,))          # explicit chain after the primary
gateway = ModelGateway(registry, policy, recorder=UsageLedger(), breaker=CircuitBreaker())
```

(The env bootstrap does not yet build a fallback chain automatically — that can be wired later; the
gateway supports it now.)

## Blockers and risks

- The env bootstrap (`build_gateway_from_env`) still constructs a single-tier policy; wiring an
  env-driven fallback chain is a small follow-up, not yet done.
- Fallback/breaker verified with fake providers; live multi-provider fail-over needs real keys.

## Next action

Start **R-222** — the first Next.js console slice (the second of the two founder-requested items):
a minimal visual console under `apps/console-web` surfacing model providers/routing and the R-009
cost dashboard. Confirm data source (static config render vs. a small read API) at kickoff.

## Next command

`task ai:status`
