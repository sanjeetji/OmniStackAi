# Current Handoff

Task ID: R-006
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-006-ollama-provider-adapter`
Last verified implementation SHA: `8061ca3b129539ada4b0838d7d70c8acd3df1ea3`

## Completed

- Added `OllamaProvider` behind the accepted vendor-neutral ModelProvider protocol.
- Added native loopback version health, explicitly profiled pulled-model discovery, non-stream chat,
  and NDJSON streaming with vendor-neutral records.
- Enforced loopback-only URLs, no environment proxy, redirect rejection, explicit timeouts, bounded
  response/line sizes, concurrency back-pressure, cancellation cleanup, and stable safe errors.
- Required exact model-digest evidence before a capability may be marked verified; unprofiled pulled
  models are not eligible by name alone.
- Added a network-independent test suite and an opt-in live local conformance command.
- Added no third-party SDK, cloud provider, router, service process, database/Compose change,
  infrastructure, or native/device work.

## Verification

- `task verify` — pass.
- `task agent-engine:lint` — pass.
- `task agent-engine:test` — pass: 28 tests.
- `task agent-engine:ollama:verify` — pass against `qwen2.5-coder:14b`: configured discovery,
  generation 4 tokens, stream 4 events/4 tokens, cloud calls 0.
- Compose scope — exactly `postgres` and `control-plane`; unchanged.
- Provider SDK import and secret-policy checks — pass.
- Model trace — one inconclusive local design review plus two successful local conformance calls;
  zero cloud calls and zero paid usage.
- Tracker row `Phase_Roadmap!A9:M9` — R-006 completion evidence recorded.
- Dashboard formulas include roadmap row 224; formula-error and stale-reference scans passed.

## Blockers and risks

- R-007 through R-009 are absent from `Phase_Roadmap`; reconstruct only the next permitted task from
  the Stage 0/MVP dependency order.
- Tool calls, structured output, vision, embeddings, routing, fallback, and capability promotion are
  not yet implemented. They require explicit profiles, measured evidence, and separate Tracker IDs.
- Cancellation closes the response and propagates immediately, while a standard-library worker
  thread may remain alive only until its bounded socket timeout completes.

## Next action

Define reconstructed R-007 from the next permitted Stage 0/MVP dependency, record its contract and
tracker status, and do not broaden it into routing, orchestration, cloud providers, or infrastructure.

## Next command

`task ai:status`
