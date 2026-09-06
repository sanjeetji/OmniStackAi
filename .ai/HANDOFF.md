# Current Handoff

Task ID: R-007
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-007-balanced-model-gateway`
Last verified implementation SHA: `9faacd23dc22c6773f9a51dc58087d557c0be391`

## Completed

- Added `ModelGateway`, the platform-owned Balanced router that selects a registered `ModelProvider`
  from deterministic inputs so product/agent code never picks a provider.
- Enforced the Brief 18.1 escalation ladder: L0 deterministic work is refused; L1/L2 route to the
  local Ollama provider; L3/L4 return a stable escalation-required error while the cloud tier is
  unconfigured. High-risk work is never silently downgraded to the local model.
- Enforced no silent cloud fallback: an `UNAVAILABLE` local provider raises `ProviderUnavailableError`
  rather than escalating to an unauthorized cloud provider.
- Added a conservative, deterministic context-budget guard against the resolved model's safe-input and
  max-output budgets; requests never silently truncate.
- Added `RoutingPolicy` with a `cloud_model` slot that stays `None` at Stage 0; registering a cloud
  adapter later enables L3/L4 escalation with no gateway change.
- Added 14 offline gateway tests (42 agent-engine tests total). No provider SDK, cloud call, service
  process, database/Compose change, infrastructure, new top-level folder, or native/device work.
- Restored the declared `pnpm` and `ripgrep` toolchains (environment only; no repository dependency).
- Added an opt-in live runner (`task agent-engine:gateway:run`) that routes real work through the
  gateway to the local Ollama model, and cloud API-key placeholders in `.env.example` for R-008.

## Verification

- `task verify` — pass.
- `task agent-engine:lint` — pass (compileall, no-external-deps contract, provider-SDK import exclusion).
- `task agent-engine:test` — pass: 42 tests (14 new gateway tests).
- `task security:quick` and `task env:check` — pass.
- Compose scope — exactly `postgres` and `control-plane`; unchanged.
- `task agent-engine:gateway:run` — pass live on `qwen2.5-coder:14b` and `qwen3.5:9b`: L1/L2 routed
  to `ollama-local`, L0/L3/L4 refused, generation and streaming returned measured output, cloud_calls=0.
- Model trace — routing is deterministic; the optional live gate made 4 local calls and 0 cloud calls.
- Tracker — R-007 inserted at `Phase_Roadmap!A9:M9` (rows 9..224 shifted to 10..225); Dashboard/table/
  conditional-formatting/data-validation ranges extended by one; no ID lost; MVP total 112, Done 7;
  chart/styles/workbook parts byte-identical; zip integrity verified.

## Blockers and risks

- R-008 and R-009 remain absent from `Phase_Roadmap`; reconstruct only the next permitted task.
- The Stage 0 gateway performs a health check before each dispatch and has no cloud tier; fallback
  across providers, circuit breaking, durable cost accounting, and richer context management are
  deferred to later Tracker IDs.
- The token-budget guard is a conservative character-based estimate, not a model tokenizer; a later
  task should replace it with per-model tokenizer-aware budgeting.

## Next action

Reconstruct R-008 — the first cloud API-key `ModelProvider` adapter behind the same boundary — so
Balanced routing can escalate L3/L4. This requires an explicit founder decision on the specific paid
provider and key handling (secret-broker/reference only) before any implementation.

## Next command

`task ai:status`
