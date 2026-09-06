# Work Log

## 2026-09-06 — R-001

- Read `OmniStackAI_Implementation_Brief_v6.md` in full and applied the normative V6
  precedence rules.
- Created root `PROJECT_STATE.md` before source-code work.
- Inspected `Phase_Roadmap` and confirmed that its task data begins at R-010.
- Initialized Git and created `ai/R-001-monorepo-bootstrap`.
- Recorded the R-001 task contract and expected blast radius.
- Created every Section 74 directory as an implementation-free placeholder.
- Added portable agent rules, start/resume/handoff state, Taskfile commands, secret exclusions,
  CI/CODEOWNERS skeletons, and ADR-0001.
- Installed Go Task 3.53.1 and ran the canonical command interface.
- Corrected the tracked-file secret check so the permitted `.env.example` is excluded without
  weakening checks for real secret files.
- `task doctor`, `task bootstrap`, `task verify`, `task ai:status`, and `task ai:handoff` passed.
- Created implementation checkpoint `655f01fa0425e8df9022ce6bb1d2040f56b1cb73`.
- Reconstructed tracker row R-001 with founder approval, marked it Done, recorded evidence, and
  verified the workbook visually and for formula errors.

## 2026-09-06 — R-002

- Reconstructed the R-002 contract from the kickoff kit's canonical example with founder approval.
- Pinned `pgvector/pgvector:0.8.6-pg18-trixie` as the only local Compose service.
- Added loopback-only port publishing, ignored environment credentials, and a persistent named volume.
- Added transactional version 1 up/down migrations for pgvector and the migration ledger.
- Added deterministic `db:config`, `db:up`, `db:status`, `db:verify`, and `db:down` commands.
- Corrected the PostgreSQL 18 volume mount to its major-version-aware root after the live health gate
  exposed the upstream layout change.
- Verified a healthy live database, pgvector 0.8.6, migration version 1, and loopback-only binding.
- Ran `task verify` successfully and created implementation checkpoint
  `56bf4b0dea5486f8d6dcde0c7b1054249ebbb064`.

## 2026-09-06 — R-003

- Reconstructed R-003 from Brief Sections 79 and 84.1 with the founder's instruction to continue.
- Confirmed a 16 GB Apple Silicon Mac with Ollama 0.33.3 and two existing local models.
- Added environment-selected local model configuration and strict loopback endpoint validation.
- Added deterministic configuration, serve, status, discovery, pull, and inference commands.
- Kept static `task verify` independent of the running local model service.
- Verified non-loopback configuration rejection.
- Ran one live `qwen2.5-coder:14b` inference, generated 6 tokens, and made zero cloud calls.
- Created implementation checkpoint `822db27aa9c9e6ab836c28abba10f41dc27918d7`.

## 2026-09-06 — R-004

- Reconstructed R-004 as the smallest Go modular-monolith control-plane foundation permitted by
  the Stage 0 sequence; deferred Redis until an implemented workload proves it necessary.
- Used local `qwen2.5-coder:14b` for one bounded design review and made zero cloud calls.
- Added typed, fail-fast environment configuration and safe PostgreSQL URL construction.
- Added stable JSON `/healthz` liveness and bounded PostgreSQL-backed `/readyz` readiness without
  exposing raw database errors.
- Added structured logs, bounded HTTP timeouts, graceful SIGINT/SIGTERM shutdown, and a non-root
  multi-stage container image.
- Kept local Compose to exactly PostgreSQL and control-plane, both published only on loopback.
- Passed `task verify`, `go test -race ./...`, and live `task control-plane:verify`.
- Created implementation checkpoint `c44fd8d013e3ec1497ccb4ab55f1433df042aeb5`.

## 2026-09-06 — R-005

- Reconstructed R-005 from the brief's explicit provider-registry handoff example and provider
  boundary rules.
- Used local-only Balanced routing for the L2 task. Two bounded `qwen2.5-coder:14b` attempts returned
  no capturable review text; deterministic brief and repository evidence defined the implementation.
- Added immutable validated provider, model, capability, request, response, token usage, health,
  discovery, and streaming records.
- Added a runtime-checkable async `ModelProvider` protocol without vendor SDK types.
- Added a deterministic registry with platform-owned invalid, duplicate, and unknown-provider errors.
- Added Python 3.13 compile/policy commands, CI toolchain setup, and 13 standard-library unit tests.
- Preserved exactly the existing two Compose services and made zero cloud model calls.
- Created implementation checkpoint `afdc4ba9c14b231dece9533dbdd39e1e79e9ace3`.

## 2026-09-06 — R-006

- Reconstructed R-006 as the early local Ollama adapter required by the V6 MVP sequence.
- Used local-only Balanced routing: one `qwen3.5:9b` review call was inconclusive; no cloud call was made.
- Added a Python 3.13 standard-library native Ollama adapter for version health, explicitly profiled
  model discovery, non-stream chat generation, and NDJSON streaming.
- Enforced the approved loopback endpoint, disabled proxies, rejected redirects, bounded time,
  response sizes and concurrency, closed cancelled streams, and mapped failures to stable errors.
- Required an exact configured model digest before any capability can be marked verified and
  rejected tool-message requests until a separate evaluated tool-call contract exists.
- Added 15 adapter/configuration tests, bringing the agent-engine suite to 28 passing tests.
- Ran the live conformance command against `qwen2.5-coder:14b`: generation produced 4 tokens and
  streaming produced 4 events/4 tokens; cloud calls remained zero.
- Ran `task verify` successfully and created implementation checkpoint
  `8061ca3b129539ada4b0838d7d70c8acd3df1ea3`.

## 2026-09-06 — R-007

- Reconstructed R-007 as the Balanced Model Gateway router — the smallest next Stage 0/MVP dependency
  after the R-005 registry and R-006 adapter — from Brief Sections 18, 18.1, 18.2, 18.3, 84, 85, 91,
  and 92.
- Restored the declared `pnpm` (corepack, pinned `pnpm@11.19.0`) and `ripgrep` toolchains that had
  regressed from the environment; added no repository dependency. `task doctor` and `task verify`
  passed again on the R-006 baseline before any change.
- Added `ModelGateway` with a deterministic escalation ladder (L0 refused), Balanced routing (sub-L3
  to the local Ollama provider), L3/L4 escalation-required while cloud is unconfigured, a conservative
  context-budget guard, and explicit no-silent-cloud-fallback on local provider unavailability.
- Added `TaskComplexity`, `RoutingMode`, `RoutingTier`, `RoutingPolicy`, `RoutingTask`,
  `RoutingDecision`, a conservative token estimator, and three stable gateway errors. Standard-library
  only; no provider SDK, cloud call, service process, DB/Compose change, or new top-level folder.
- Added 14 offline gateway tests (42 agent-engine tests total). Routing is deterministic and needed
  zero model calls to implement or test; cloud calls remained zero.
- Ran `task verify`, `task agent-engine:lint/test`, `task security:quick`, `task env:check`, and the
  Compose scope check (exactly `postgres` and `control-plane`).
- Inserted tracker row R-007 at Phase_Roadmap row 9 by shifting rows 9..224 to 10..225 and extending
  the Dashboard, table, conditional-formatting, and data-validation ranges by one row; verified no
  ID was lost, formulas self-reference their rows, counts are correct (MVP total 112, Done 7), and
  the chart/styles/workbook parts stayed byte-identical.
- Created implementation checkpoint `9faacd23dc22c6773f9a51dc58087d557c0be391`.
- On founder instruction, added the opt-in live gateway runner (`live_gateway.py`) and
  `task agent-engine:gateway:run` to run the platform locally through the Balanced gateway, plus
  cloud-provider API-key placeholders in `.env.example` (names only) to prepare the R-008 decision.
- Live-ran the gateway on both installed models: L0 refused, L1/L2 routed to `ollama-local`, L3/L4
  refused; L2 generation and L1 stream succeeded on `qwen2.5-coder:14b` and `qwen3.5:9b`; cloud
  calls remained zero. Static `task verify` stayed network-independent and green.
