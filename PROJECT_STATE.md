# Project State — OmniStackAI
Last updated: 2026-09-06T10:46:19+05:30 by Codex (GPT-5)

## Current Phase
Stage 0 (Founder Build Sequence, Brief Section 91) — BASIC/MVP

## Last Completed Task
Tracker ID: R-238 — PostgreSQL schema/migration generation from the IR — DONE, `task verify` (237
agent-engine tests, 11 new) passing; `render_postgres_schema(ir)` turns entities + relations into a
deterministic SQL DDL (typed columns, NOT NULL, UUID PK, foreign keys, many-to-many join tables), and
the FastAPI + Go backends emit it as `migrations/0001_init.sql` when the IR has entities and
`database_strategy=postgres` (no other emitted file changes). Byte-stable so the R-237 edit loop diffs
it; nothing connects to or runs a database; implementation checkpoint `c6a4c6e`
(R-224 Next.js console upgrade deferred — env-blocked)

## Workflow note
Founder consolidated all work onto `main` (per-task branches deleted; `main` is the default). Continue
committing directly to `main` with the Tracker-ID discipline (contract -> tests -> gates -> tracker ->
commit tagged [R-###]).

## Milestone: first end-to-end builder slice complete + multi-target
`Application IR (R-225) -> framework adapter contract (R-226) -> Next.js code adapter (R-227) -> Git
service (R-228)` now turns a structured app spec into a real Next.js app inside a customer-owned Git
repo, fully offline and tested. Remaining slice steps — sandbox run, instant browser preview, deploy —
need a cloud/network-capable environment.

## In Progress (if any)
Tracker ID: none
Files touched so far: none
Blocker: none (R-224 Next.js upgrade remains deferred — env-blocked)

## Product direction
The model fabric (R-005..R-223) is the engine. The actual product (Emergent-class app builder) starts
with the vertical slice: **Application IR (R-225)** → framework adapter contract → Next.js code adapter
→ Git service → preview/sandbox (the last needs a cloud/network-capable environment).

## ID note
The workbook backlog already assigns R-010..R-219 (R-010 = Native iOS Agent, deferred until web/backend
stability). Founder-requested work uses unique IDs after R-219: R-220 = cloud streaming (done);
R-221 = cross-provider fallback (done); R-222 = platform console slice (done); R-223 = env-driven
fallback wiring (done); R-224 = Next.js console upgrade (deferred — environment-blocked).

## Next Up (queued, in order)
1. Run a Tier-0 preview of a generated app end-to-end (needs a network-capable machine: this Mac in a
   real Terminal, or a Codespace) — the runtime layer + `task agent-engine:preview-plan` are ready
2. Build a concrete cloud provider driver (e.g. Vercel deploy or E2B sandbox) once a key is provided
3. R-224 — Next.js console upgrade — resume in an environment with reliable npm registry access
4. R-010 — Native iOS Agent (backlog; deferred until web/backend stability per Brief 25/91)
(The full offline builder AND the Tier 0-3 runtime/deploy wiring are complete: one IR ->
web+backend monorepo -> owned Git repo, plus a local preview provider and key-activated cloud
sandbox/deploy providers.)

## Decisions Made This Session
- Applied the normative V6 precedence rules and Section 91 Phase 0 sequence.
- Kept R-001 to repository/bootstrap metadata; no service, database, cloud, model, or mobile implementation was added.
- Added the V6-required `.ai/`, `.github/`, and `.cursor/` roots with explicit founder approval.
- Reconstructed only R-001 in the tracker with explicit founder approval; R-002 through R-009 remain unresolved.
- Installed the free Go Task CLI locally to exercise the canonical repository command contract.
- Reconstructed R-002 from the kickoff kit's explicit example with founder approval to continue.
- Bounded R-002 to local PostgreSQL+pgvector and migration tooling; Redis and all services remain out of scope.
- Pinned `pgvector/pgvector:0.8.6-pg18-trixie` and used PostgreSQL 18's major-version-aware data mount.
- Kept credentials in ignored `.env`; only placeholders are tracked.
- Reconstructed R-003 as the Stage 0 local Ollama foundation because it is required before cloud
  escalation and costs nothing beyond the existing laptop.
- Selected the already-pulled `qwen2.5-coder:14b` through configuration, not product hardcoding.
- Enforced loopback-only Ollama configuration and verified one real local inference with zero cloud calls.
- Reconstructed R-004 as the minimal Go control-plane foundation; Redis remains deferred until an
  implemented feature proves a cache, lease, rate-limit, or ephemeral coordination need.
- Used local `qwen2.5-coder:14b` for a bounded design review; no cloud model was called.
- Added only the control-plane as the second Compose service, with typed configuration, structured
  logs, bounded HTTP and database timeouts, graceful shutdown, and loopback-only host publishing.
- Verified stable liveness and PostgreSQL-backed readiness from the running container, plus unit and
  race-enabled tests; the container runs as the non-root `omnistackai` user.
- Reconstructed R-005 from the brief's explicit provider-registry handoff example and provider
  boundary rules; provider adapters and routing remain deferred to later Tracker IDs.
- Classified R-005 as L2. Two bounded local `qwen2.5-coder:14b` review attempts produced no
  capturable review text, so deterministic brief/repository evidence defines the task; cloud calls remain zero.
- Added immutable validated provider/model/capability/request/response/usage/health/stream records,
  a runtime-checkable async `ModelProvider` protocol, and a deterministic provider registry.
- Used only Python 3.13 standard-library functionality and added no adapter, provider SDK, runtime
  process, database change, Compose service, or infrastructure.
- Reconstructed R-006 as the smallest early Ollama provider required by the V6 MVP sequence.
- Bounded R-006 to a loopback-only native HTTP adapter, conservative model profiles, conformance
  tests, and an explicit live verifier; routing, cloud adapters, and orchestration remain deferred.
- Classified R-006 as L2. One bounded local `qwen3.5:9b` review call returned no capturable output;
  deterministic brief/repository evidence and official Ollama API documentation define the task.
- Added a standard-library-only `OllamaProvider` for native version health, allowlisted discovery,
  non-stream chat, and NDJSON streaming behind the accepted provider contract.
- Enforced Stage 0 loopback endpoints, proxy/redirect rejection, stable errors, finite timeouts,
  bounded bodies and concurrency, cancellation cleanup, output ceilings, and exact-digest evidence
  before a capability can be marked verified.
- Proved the adapter with 28 offline tests and two live `qwen2.5-coder:14b` calls: generation and
  streaming each produced 4 output tokens; no cloud provider was called.
- Reconstructed R-007 as the Balanced Model Gateway router, the third foundational model-boundary
  piece after the R-005 registry and R-006 adapter and the smallest next Stage 0/MVP dependency.
- Founder confirmed intent to support both API-key cloud providers and local Ollama, added one
  Tracker ID at a time; R-007 delivers the routing seam and defers the first cloud adapter to R-008.
- Router refuses L0 deterministic work, routes sub-L3 to local Ollama, returns escalation-required
  for L3/L4 (cloud unconfigured), guards a conservative context budget, and never silently falls
  back to a cloud model when the local provider is unavailable. Routing is deterministic; zero model
  calls were made to build or test it.
- Restored the declared `pnpm` (via corepack) and `ripgrep` toolchains that had regressed from the
  environment; no repository dependency was added. `task doctor` and `task verify` pass again.
- On founder instruction, added an opt-in live gateway runner (`task agent-engine:gateway:run`) and
  ran the platform locally through the Balanced gateway on both `qwen2.5-coder:14b` and `qwen3.5:9b`;
  added cloud API-key placeholders (names only) to `.env.example` for the R-008 provider decision.
- R-008: founder chose to configure every cloud provider (not just one), activated by API key, while
  running locally on Ollama until keys are added. Added standard-library HTTPS adapters (no vendor
  SDK) for Anthropic, OpenAI, Google Gemini, OpenRouter, and Groq behind the ModelProvider boundary,
  plus an env bootstrap that registers local Ollama always and each key-present cloud provider.
- Each cloud provider is key-activated with an overridable default model; keys are read only from the
  environment and never logged, stored, or shown. With no key, the platform stays local at zero cloud
  cost; `OMNISTACKAI_CLOUD_PROVIDER` selects the L3/L4 tier when a key is present.
- Evolved a stale R-005-era guard in `scripts/test.sh` (it forbade any provider adapter) to enforce
  the durable invariants instead — no vendor SDK import, gateway/cloud/bootstrap files exist, and
  cloud providers are opt-in defaulting to none — since cloud adapters are the sanctioned R-008 work.
- R-009: founder selected best-in-class usage & cost accounting. Added deterministic, privacy-safe
  accounting — immutable metadata-only usage records (no content/secret), a configurable Decimal
  price book (local Ollama zero, unknown unpriced), and an aggregating ledger (per-provider/model
  breakdowns, p50/p95 latency, cost per successful call). Gateway records one record per dispatch
  without altering results; the live runner prints a cost summary. Zero model calls to verify.
- R-220: founder asked to complete both true streaming and a second required item, one by one. Added
  true incremental Server-Sent-Events streaming for the cloud adapters (OpenAI-compatible, Anthropic,
  Gemini), reusing the HTTP-safety bounds; ordered delta events plus a final event with measured
  usage. Discovered the workbook backlog already owns R-010..R-219 (R-010 = Native iOS Agent), so new
  model-fabric tasks take unique IDs after R-219 (R-220 here) rather than overwriting a backlog row.

## Environment / Secrets Status
- Local Ollama: server 0.33.3 healthy on loopback; `qwen2.5-coder:14b` adapter health, discovery,
  generation, and streaming live-verified; `qwen3.5:9b` remains pulled but is not implicitly eligible
- Cloud keys configured: not inspected; no cloud provider API authorized or required for R-006
- Database: local container healthy via Colima; pgvector 0.8.6 and migration version 1 verified; no cloud database is authorized
- Control plane: local container healthy on `127.0.0.1:8080`; liveness `ok`, readiness `ready`
