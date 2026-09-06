# Current Handoff

Task ID: R-220
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-220-cloud-streaming`
Last verified implementation SHA: `4e31841e730a6466da55843ff352f7144dd763e9`

## Completed

- Replaced the cloud adapters' single-event stream wrapper with true incremental Server-Sent-Events
  streaming behind the same `ModelProvider` boundary:
  - Shared SSE transport in the cloud base: bounded stream-line/response sizes, finite timeout,
    redirect rejection, bounded concurrency, stable platform-owned errors, and the API key is never
    leaked in errors or events.
  - OpenAI-compatible (OpenAI/OpenRouter/Groq): incremental delta chunks with usage requested in the
    final chunk (`stream_options.include_usage`).
  - Anthropic: `message_start` / `content_block_delta` / `message_delta` / `message_stop`.
  - Gemini: `:streamGenerateContent?alt=sse`.
- Ordered `StreamEvent` deltas plus one final event with measured usage; non-streaming `generate` is
  unchanged. 5 new offline SSE tests (78 total) with injected fake streaming responses; no cloud call.

## ID scheme note (important)

The supplied workbook backlog already assigns **R-010..R-219** (R-010 = "Native iOS Agent", deferred
until web/backend stability). The genuinely-missing gap IDs R-007/R-008/R-009 were used for the
gateway/cloud-adapters/accounting. New founder-requested model-fabric tasks therefore take unique IDs
**after the last existing ID (R-219)** rather than overwriting a planned backlog row: this task is
**R-220**; the confirmed second item will be **R-221**.

## Verification

- `task verify` — pass (78 agent-engine tests).
- `task agent-engine:lint`, `task security:quick`, `task env:check` — pass; key never in source/records.
- Compose scope — exactly `postgres` and `control-plane`; unchanged.
- Tracker — R-220 inserted at `Phase_Roadmap!A9:M9` (rows 9..227 shifted to 10..228, ranges extended);
  no ID lost; backlog R-010 (Native iOS Agent) intact; MVP total 115, Done 10; chart/styles/workbook
  byte-identical; zip verified.

## Blockers and risks

- Cloud streaming is verified with mocked SSE responses; a live cloud stream needs a real key (none
  configured). Local Ollama streaming remains fully live-verified.
- Providers vary in whether they emit usage on stream; when absent, the final event carries the best
  available counts (Anthropic/Gemini accumulate; OpenAI needs include_usage, which is requested).

## Next action

Start **R-221**, the confirmed second required item. Confirm with the founder whether R-221 is
cross-provider fallback + circuit breaking (model layer) or a first Next.js console slice (front end).

## Next command

`task ai:status`
