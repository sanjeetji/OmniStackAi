# Current Handoff

Task ID: R-008
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-008-cloud-provider-adapters`
Last verified implementation SHA: `eeade72e84c7f1ebd71dfc8c0f7c2f4db0f79677`

## Completed

- Added key-activated cloud `ModelProvider` adapters behind the shared boundary, standard-library
  HTTPS only (no vendor SDK, no external dependency):
  - `OpenAICompatibleProvider` for `openai`, `openrouter`, `groq`,
  - `AnthropicProvider` (Messages API),
  - `GeminiProvider` (generateContent).
- Each adapter maps messages, output text, finish reason, and token usage to the vendor-neutral
  records, reuses the R-006 HTTP safety pattern, reads its API key only from the environment, sends
  it only as the provider auth header, and never logs/stores/exposes it (asserted by tests).
- Added `build_gateway_from_env()`: always registers local Ollama, registers each cloud provider
  whose key is present, and selects the L3/L4 tier from `OMNISTACKAI_CLOUD_PROVIDER` (default none).
  With no key set, only Ollama is registered and L3/L4 return `no_eligible_provider`.
- Each provider has an overridable default model (`OMNISTACKAI_<PROVIDER>_MODEL`) and conservative
  shared budgets (`OMNISTACKAI_CLOUD_*`).
- Refactored the live runner to use the bootstrap, so adding a key activates that provider with no
  code change.
- 19 new offline tests (61 total) with injected fake HTTP openers; no cloud call is made.

## Verification

- `task verify` — pass (61 agent-engine tests).
- `task agent-engine:lint` — pass (compileall, no-deps contract, provider-SDK import exclusion).
- `task agent-engine:gateway:run` — pass live on local Ollama with no keys: only `ollama-local`
  registered, L1/L2 local, L3/L4 refused, generation and streaming returned output, cloud_calls=0.
- `task security:quick` and `task env:check` — pass; no key value in source, tests, or state.
- Compose scope — exactly `postgres` and `control-plane`; unchanged.
- Tracker — R-008 inserted at `Phase_Roadmap!A9:M9` (rows 9..225 shifted to 10..226, ranges extended);
  no ID lost; MVP total 113, Done 8; chart/styles/workbook byte-identical; zip verified.

## How to enable a cloud provider (no code change)

In the untracked `.env`, set one provider's key and select it, e.g.:

```
ANTHROPIC_API_KEY=...              # or OPENAI_API_KEY / GOOGLE_API_KEY / OPENROUTER_API_KEY / GROQ_API_KEY
OMNISTACKAI_CLOUD_PROVIDER=anthropic
```

Optionally override the model with `OMNISTACKAI_<PROVIDER>_MODEL`. Then `task agent-engine:gateway:run`
shows the cloud provider registered and L3/L4 routing to it; L1/L2 stay on local Ollama.

## Blockers and risks

- Cloud `stream()` currently wraps a non-streaming generation into one final event; true per-provider
  SSE streaming is deferred.
- Cloud `health()` is a config-readiness check (key present), not a live probe, to avoid billable
  calls; a real endpoint failure surfaces on the next generate as a stable platform error.
- Default cloud model ids are best-effort defaults and may need updating per provider; they are
  operator-overridable by environment variable.
- Cross-provider fallback, circuit breaking, and durable cost accounting are deferred.

## Next action

Reconstruct R-009 — candidate scope: true per-provider SSE streaming for the cloud adapters, or
cross-provider fallback and circuit breaking behind the gateway. Confirm scope before implementing.

## Next command

`task ai:status`
