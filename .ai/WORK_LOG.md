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

## 2026-09-06 — R-008

- Reconstructed R-008 on founder instruction to configure every cloud provider (not just one),
  activated by API key, while continuing to run locally on Ollama until keys are added.
- Added standard-library HTTPS cloud adapters (no vendor SDK, no external dependency): one
  OpenAI-compatible adapter for OpenAI/OpenRouter/Groq, an Anthropic Messages adapter, and a Google
  Gemini generateContent adapter, each mapping to the vendor-neutral records with the R-006 HTTP
  safety pattern (bounded response, finite timeout, redirect rejection, stable errors).
- Kept API keys out of source/logs/records/repr: keys are read only from the environment and sent
  only as the provider auth header; a provider is registered only when its key is present.
- Added `build_gateway_from_env()` that always registers local Ollama and each key-present cloud
  provider and selects the L3/L4 tier from `OMNISTACKAI_CLOUD_PROVIDER` (default none); selecting a
  provider without its key is a clear configuration error. Refactored the live runner to use it.
- Added 19 offline tests (61 total) with injected fake HTTP openers; no cloud key set, so cloud
  calls stayed zero. Confirmed the live local run still works via the bootstrap.
- Evolved a stale R-005-era guard in `scripts/test.sh` to enforce the durable invariants (no SDK
  import, gateway/cloud/bootstrap files exist, cloud opt-in defaults to none) now that cloud adapters
  are sanctioned; added cloud key/model placeholders and shared budgets to `.env.example`.
- Inserted tracker row R-008 at Phase_Roadmap row 9 (shifted 9..225 to 10..226, ranges extended by
  one); verified no ID lost, formulas self-reference their rows, MVP total 113 / Done 8, chart/styles
  byte-identical, zip valid.
- Created implementation checkpoint `eeade72e84c7f1ebd71dfc8c0f7c2f4db0f79677`.

## 2026-09-06 — R-009

- Reconstructed R-009 as best-in-class usage and cost accounting (founder-selected) from Brief
  Sections 18.4, 23, 68, 84, 85, 90, 91, and 92.
- Added `accounting.py`: immutable metadata-only `UsageRecord` (no message content or secret), a
  `Decimal`-based `PriceBook` (exact and per-provider-wildcard lookup, local Ollama zero, unknown
  models unpriced, optional cached-input pricing) with an illustrative configurable default book,
  and a thread-safe `UsageLedger` producing overall and per-provider/model breakdowns, deterministic
  nearest-rank p50/p95 latency, unpriced-call count, and cost per successful call.
- Integrated an optional `recorder` into `ModelGateway`: exactly one record per dispatch for success
  and failure, written without altering the returned response or the raised error; threaded the
  ledger through `build_gateway_from_env` and printed a cost summary from the live runner.
- Added 13 offline accounting tests (74 total). Accounting is deterministic; zero model calls were
  needed to implement or verify. Live local run recorded 2 calls at $0.000000 with latency
  percentiles and a per-provider breakdown; cloud calls stayed zero.
- Inserted tracker row R-009 at Phase_Roadmap row 9 (shifted 9..226 to 10..227, ranges extended);
  verified no ID lost, MVP total 114 / Done 9, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `f2fc8654c6a5717e292adcdc2abb5da2fd7409c2`.

## 2026-09-06 — R-220

- Founder asked to complete both true per-provider streaming and a second required item, one by one;
  R-220 delivers streaming.
- Replaced the R-008 single-event cloud stream wrapper with real incremental Server-Sent-Events
  streaming: shared SSE transport in the cloud base (bounded lines/response, finite timeout, redirect
  rejection, stable errors, key never leaked) plus per-provider parsers — OpenAI-compatible delta
  chunks with usage in the final chunk, Anthropic message_start/content_block_delta/message_delta/
  message_stop, and Gemini streamGenerateContent SSE.
- Yielded ordered StreamEvent deltas plus a final event with measured usage; kept non-streaming
  generate unchanged. Added 5 offline SSE tests (78 total) with injected fake streaming responses; no
  cloud call was made.
- Found the workbook backlog already assigns R-010..R-219 (R-010 = Native iOS Agent). To avoid
  overwriting a planned row, new founder-requested model-fabric tasks take unique IDs after R-219;
  this task is R-220, inserted at Phase_Roadmap row 9 (rows 9..227 shifted to 10..228, ranges
  extended). Verified no ID lost, backlog R-010 intact, MVP total 115 / Done 10, chart/styles
  byte-identical, zip valid.
- Created implementation checkpoint `4e31841e730a6466da55843ff352f7144dd763e9`.

## 2026-09-06 — R-221

- Added explicit, allowlist-driven cross-provider fallback and per-provider circuit breaking to the
  Balanced gateway (founder-requested second item, part one of two).
- `RoutingPolicy` gained an optional ordered `fallback` chain; with none configured the gateway is
  byte-for-byte behaviourally unchanged (single provider). generate/stream now try the primary then
  each registered, in-budget, circuit-closed candidate.
- Fail-over is explicit (only along the chain) and only on retriable errors
  (unavailable/timeout/http); non-retriable errors raise immediately; streaming fails over only
  before the first event.
- Added `resilience.py` `CircuitBreaker`: opens after N consecutive failures, skips for a cooldown,
  half-opens, resets on success; injectable clock, thread-safe. Every attempt is still accounted.
- Added `AllProvidersFailedError` for an exhausted chain; a single-provider config still surfaces its
  own stable error. Refactored resolve() into `_resolve_tier` + `_build_decision` reused by both
  paths, keeping the existing resolve() behavior identical.
- Added 8 offline tests (86 total); deterministic, no cloud call. Confirmed the live local gateway
  still runs on Ollama.
- Inserted tracker row R-221 at Phase_Roadmap row 9 (rows 9..228 shifted to 10..229, ranges extended);
  no ID lost, backlog intact, MVP total 116 / Done 11, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `d0ee9f75b0d124fe60f1121b7f2a70d3b73040de`.

## 2026-09-06 — R-222

- Built the first platform console slice (founder-requested second item, part two of two) under
  apps/console-web.
- Added Python `overview.py` `platform_overview()` — a deterministic, metadata-only export of the
  model fabric (routing ladder, providers with active flags from env key presence, price book, usage
  summary), plus `PriceBook.entries()`; the snapshot never contains a key or secret (active is a
  boolean). 6 offline tests (92 total), including a no-secret / active-without-key assertion.
- Authored a full Next.js App-Router app, but this sandbox's network repeatedly timed out fetching
  Next's native SWC binary, so it cannot be installed/built here and a frozen install would break the
  offline task bootstrap. Pivoted to a dependency-free static console (index.html/styles.css/app.js)
  with the identical data contract and design; reverted the bootstrap change so the offline contract
  is unchanged. Next.js upgrade documented as the next step.
- Console uses safe DOM APIs (textContent only), a strict CSP meta tag, and same-origin snapshot fetch
  only. Added task console:snapshot and task console:serve; verified app.js via node --check and the
  served assets via HTTP (all 200; 6 providers / 5 price rows / 5 ladder steps).
- Inserted tracker row R-222 at Phase_Roadmap row 9 (rows 9..229 shifted to 10..230, ranges extended);
  no ID lost, backlog intact, MVP total 117 / Done 12, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `c07bbcb1b9b8c010c6d64e3a0e09ac0c855102c8`.

## 2026-09-06 — R-223

- Wired R-221 resilience into `build_gateway_from_env`: `OMNISTACKAI_FALLBACK_PROVIDERS` builds an
  ordered fallback chain from already-registered providers (`ollama` or a key-present cloud name);
  unknown or key-less names raise a clear `CloudProviderSelectionError`.
- Attached a `CircuitBreaker` (threshold/cooldown from env, safe defaults 3/30) only when a chain is
  configured, so single-provider behavior is byte-for-byte unchanged. `GatewayBootstrap` now exposes
  the chain provider ids and breaker settings.
- Extended the overview snapshot with a `resilience` block and rendered a Resilience panel in the
  console; added `.env.example` entries. No key/secret is ever included.
- Added 6 offline tests (98 total); deterministic, no cloud call. `task verify` green.
- Inserted tracker row R-223 at Phase_Roadmap row 9 (rows 9..230 shifted to 10..231, ranges
  extended); no ID lost, MVP total 118 / Done 13, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `9ec809149ab91ebaa13b88ff0a15ebd382d7a728`.

## 2026-09-06 — R-224 (deferred) and R-225

- R-224 (Next.js console upgrade): attempted the install three times (incl. standalone with a 10-min
  timeout) and once with Vite/Preact; this sandbox cannot fetch front-end bundler native binaries, so
  recorded R-224 as Deferred with a resume plan and committed no application code.
- Also showed the platform live: ran `task agent-engine:gateway:run` (local qwen routing/gen/stream +
  cost) and published the console UI as a private Artifact from the snapshot.
- R-225: began the actual product per the brief. Added the framework-neutral Application IR (Brief 9)
  under `omnistackai_agent_engine.application_ir`: immutable validated records (application, project
  strategy, roles, entities with fields/relations, APIs, screens, acceptance criteria), cross-reference
  validation, unique-id and enum checks, schema versioning, and lossless to_dict/from_dict with a
  version-rejection migration hook. Standard-library only; no codegen/agents yet.
- Added 17 offline IR tests (115 total). `task verify` green.
- Inserted tracker row R-225 (category Product) at Phase_Roadmap row 9 (rows 9..232 shifted to 10..233,
  ranges extended); no ID lost, MVP total 120 / Done 14, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `ad5e4ddf5918ddf3e4005c21a07c21601faf2ee6`.

## 2026-09-06 — R-226

- Added the code-generation boundary in `omnistackai_agent_engine.codegen`: `GeneratedFile` (safe
  relative POSIX path, bounded content) and `GeneratedProject` (immutable, path-unique,
  deterministically ordered, mergeable) — a customer project's source tree as a pure in-memory value,
  no disk writes.
- Added the `FrameworkAdapter` runtime-checkable contract (`target` + `generate(ir) -> GeneratedProject`),
  an `AdapterRegistry` with stable duplicate/unknown errors, and the `GenerationTarget` enum over MVP
  targets; adapters are selected only via the registry.
- Depends on `application_ir`; standard-library only; no code execution. 10 new offline tests
  (125 total). `task verify` green.
- Inserted tracker row R-226 (Product) at Phase_Roadmap row 9 (rows 9..233 shifted to 10..234, ranges
  extended); no ID lost, MVP total 121 / Done 15, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `f27bf416e99423d281e1c4e6f3eabc363848f95f`.

## 2026-09-06 — R-227

- Implemented the first framework code adapter: `NextjsWebAdapter` turns an Application IR into a real
  Next.js App Router TypeScript project as a GeneratedProject — entities to TS interfaces, IR APIs to
  App Router route handlers ({param}->[param], one file per route dir, a handler per method), screens
  to pages, an overview page, and config (package.json/tsconfig/next.config with security headers/
  README/.gitignore/.env.example placeholders).
- Extended the GeneratedFile path validator to allow framework route filename chars ([]()@+) while
  still rejecting absolute paths, '..', backslashes, control chars.
- Pure/deterministic; nothing installed/built/run/written to disk. The demo IR emits a 13-file
  Next.js project. 9 new offline tests (134 total); `task verify` green.
- Inserted tracker row R-227 (Product) at Phase_Roadmap row 9 (rows 9..234 -> 10..235, ranges
  extended); no ID lost, MVP total 122 / Done 16, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `1a4f8a9b8cc2ca59be32142bb6c16992cb4dbd40`.

## 2026-09-06 — R-228 (first builder slice complete)

- Added `omnistackai_agent_engine.git_service`: `materialize_project` (writes a GeneratedProject under
  a target dir, refuses path escapes and non-empty targets, sets exec bits) and `create_repository`
  (git init + stage + one commit with the customer identity via explicit env, no global git config,
  returns the commit SHA). Writes only inside the caller's target; offline; local git only.
- 6 new offline temp-dir tests (140 total). Verified the full slice end-to-end: demo IR -> 13-file
  Next.js app (NextjsWebAdapter) -> a real one-commit customer-owned Git repo. `task verify` green.
- Inserted tracker row R-228 (Product) at Phase_Roadmap row 9 (rows 9..235 -> 10..236, ranges
  extended); no ID lost, MVP total 123 / Done 17, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `28801ef396f7ead743a1d0cdc68657de23cefe1a`.

## 2026-09-06 — repo consolidation + R-229

- Founder merged all work into `main` (fast-forward from the R-001 bootstrap; 34 commits) and set
  `main` as the GitHub default; deleted all per-task ai/* branches (remote + local). Remote now has
  only `main`. Added docs/RESUME_PROMPT.md. Going forward, work is committed directly to `main`.
- R-229: added the Python (FastAPI) backend adapter (PythonBackendAdapter, target backend-python):
  entities -> Pydantic models, IR APIs -> FastAPI routers grouped by resource with typed path params
  and 501 scaffolds, app/main.py with routers + health, config, requirements, README/.gitignore/
  .env.example. Registered via AdapterRegistry. Pure/offline; no install/build/disk.
- 7 new offline tests (147 total). Proven multi-target: one IR -> 12-file Next.js web + 11-file FastAPI
  backend. `task verify` green. Tracker row R-229 (Product) inserted at row 9; MVP total 124 / Done 18.
- Implementation checkpoint `04f1e6ad03ff52522efda81845ea3ee73e736a7d`.

## 2026-09-06 — R-230

- Added the Go backend adapter (GoBackendAdapter, target backend-go): entities -> Go structs (json
  tags, optional pointers), IR APIs -> Go 1.22 method+pattern routes grouped by resource with
  r.PathValue params and 501 scaffolds, main.go with routes + /healthz + ListenAndServe, go.mod
  (go 1.22), README/.gitignore/.env.example. Generated Go and platform side are standard-library only.
- Registered via AdapterRegistry. 7 new offline tests (154 total). Proven tri-target: one IR ->
  12-file Next.js + 11-file FastAPI + 8-file Go service. `task verify` green.
- Committed directly to main (only branch). Tracker row R-230 (Product) inserted at row 9; MVP total
  125 / Done 19. Implementation checkpoint `e2515a8f1b0314ec287a02cdaf25e72a17b9da3f`.

## 2026-09-06 — R-224 (deferred)

- Attempted the Next.js console upgrade. `pnpm install` for next@15.5.4 timed out fetching the native
  SWC binary (@next/swc-darwin-arm64) three times, including a standalone install under
  apps/console-web/nextjs/ with a 10-minute fetch timeout and increased retries.
- Per "record real command evidence — never claim unexecuted tests," recorded R-224 as Deferred with a
  resume plan; committed no application code and removed the scaffold (working tree clean). The R-222
  static console remains the working slice.
- Recorded tracker row R-224 at Phase_Roadmap row 9 with status Deferred (completion 0); rows
  contiguous, ranges extended, no ID lost; MVP total 119, Done 13, Deferred 1.

## 2026-09-07 — R-234

- Added a single `OMNISTACKAI_TIER` switch (0/1 local, 2 cloud). `runtime/tier.py` resolves the runtime
  and deploy providers from the tier + explicit selectors: tier 0/1 force local runtime and no deploy;
  tier 2 permits keyed cloud selections. `resolve_platform()` returns the active providers;
  `platform_status()`/`format_status()` summarize tier, selection, and which keys are present.
- Added `runtime/drivers.py`: `CloudDeployProvider` (vercel/netlify/render/fly) emits a `DeployPlan` of
  the provider's official-CLI commands; `CloudSandboxProvider` (e2b/daytona/fly-machines) emits a
  `PreviewPlan` reusing the target's run commands. The key is read from env at run time and NEVER placed
  in a command or logged. `run_deploy(plan)` executes a plan opt-in (never run by verify).
- `bootstrap.py` gained an optional `selection` override; new exports in `runtime/__init__.py`.
  `task platform:status` (scripts/agent-engine.sh + Taskfile) prints the active tier and key presence;
  `.env.example` gained `OMNISTACKAI_TIER=0`; `docs/RUNTIME.md` documents the knob + drivers.
- 13 new stdlib offline tests (194 total): tier resolution, per-provider driver plans, no-key-in-plan
  across all providers, activation/selection errors, and the status summary. `task verify`,
  `task security:quick`, `task env:check` all pass; `task platform:status` demoed tier 0 and tier 2.
- Committed directly to main (only branch). Tracker row R-234 (Runtime) inserted at row 9; MVP total
  129 / Done 23. Implementation checkpoint `dcb7d2d`. 0 local / 0 cloud model calls; nothing run/deployed.

## 2026-09-07 — R-235

- Added the verifiable-engineering verify-plan layer (`omnistackai_agent_engine.verify`): `plans.py`
  (`VerifyStepKind` install/typecheck/lint/test/build, `VerifyStep`, `VerifyPlan` — validated,
  ladder-ordered, `gates()`, reusing the vetted `Command` primitive from runtime.contracts); `gates.py`
  (the per-target recipe table, `verify_plan`, `verify_plans_for_ir`, `run_verify`, `VerifyReport`).
- Per-target ladders: nextjs-web/nextjs-admin (pnpm install → tsc --noEmit → lint → build);
  backend-python (pip install → compileall app → pytest); backend-go (go vet → go test → go build).
  Each step classified by gate kind; commands control-free/secret-free by construction.
- Mapped one Application IR to the verify plans for its assembled monorepo apps via a new additive,
  behavior-preserving `assembled_targets(ir)` in the assembler (`assemble_project` refactored to share
  the `_plan_assembly` layout decision; output byte-identical, existing tests green).
- `run_verify(plan)` is the only executor — opt-in, fail-fast, returns a `VerifyReport` (per-step
  status + return code); never run by tests or `task verify`. Added `task agent-engine:verify-plan`.
- Docs: `docs/VERIFY.md`. 9 new stdlib offline tests (203 total): per-target plans, ladder order, gate
  classification, unknown-target error, IR→plans mapping over the rideshare + blog fixtures, plan
  safety. `task verify`, `task security:quick`, `task env:check` all pass; verify-plan demoed.
- Committed directly to main (only branch). Tracker row R-235 (Verify) inserted at row 9; MVP total
  130 / Done 24. Implementation checkpoint `cb74d0c`. 0 local / 0 cloud model calls; nothing installed/built/run.

## 2026-09-07 — R-236

- Expanded the cloud model fabric (founder request, with Dyad screenshots for reference). Added
  first-class OpenAI-compatible `CloudProviderSpec` entries for DeepSeek, xAI (Grok), Mistral, Together,
  and Fireworks alongside the existing OpenAI/Anthropic/Google/OpenRouter/Groq — all reuse
  `OpenAICompatibleProvider`, no new adapter code.
- Added a generic env-driven custom-provider path: `custom_provider_specs_from_env` reads
  `OMNISTACKAI_CUSTOM_PROVIDERS` + per-id `OMNISTACKAI_CUSTOM_<ID>_{BASE_URL,MODEL,API_KEY}` and builds
  a first-class provider with no code change; validates the id, requires an HTTPS base URL + model, and
  rejects built-in collisions. `resolve_provider_specs()` = built-ins ∪ custom.
- Made the catalog spec-driven end to end: `bootstrap.py` and `overview.py` iterate
  `resolve_provider_specs()`, so custom + new built-in providers are registered (key-activated),
  selectable as the L3/L4 cloud tier or a fallback, and listed in the metadata-only overview with
  `active` = key presence only. `accounting.py` gained illustrative default prices for the priced new
  providers (openrouter/custom stay unpriced).
- `.env.example`: new keys + model overrides + a documented custom-provider template; updated the
  `OMNISTACKAI_CLOUD_PROVIDER` allowed list. `docs/MODEL_PROVIDER.md`: R-236 catalog + custom + local
  Ollama section. Keys stay env-only — never logged, stored, returned, or placed in the overview.
- 14 new stdlib offline tests (217 total): new specs, adapter dispatch shape (key only in the auth
  header, never the URL), custom-spec parse + 4 error cases, spec merge, bootstrap registration/
  selection/fallback for built-in and custom, overview/no-key-leak, and pricing. Updated `test_overview`
  to derive the expected catalog from the spec table. `task verify` + `security:quick` + `env:check`
  pass; `platform_overview` demoed a 12-provider catalog including custom `myco`.
- Committed directly to main (only branch). Tracker row R-236 (Model Fabric) inserted at row 9; MVP
  total 131 / Done 25. Implementation checkpoint `e6326bf`. 0 local / 0 cloud model calls; no network.

## 2026-09-07 — R-237

- Added the "edit an existing app" motion — the builder step after generate + verify. New
  `omnistackai_agent_engine.edit` package: `diff.py` (`ChangeKind`, `FileChange`, `ProjectDiff`,
  `diff_projects`, `plan_edit`) and `apply.py` (`ApplyReport`, `apply_diff`, `commit_edit`).
- `diff_projects(old, new)` classifies every path as added/modified/deleted/unchanged (modified on
  content OR executable change); `plan_edit(old_ir, new_ir)` assembles both IRs via the assembler and
  diffs them, so an IR change becomes exactly the set of files to rewrite.
- `apply_diff(diff, target_dir)` writes added/modified and removes deleted files strictly inside the
  target (path escapes refused like `materialize_project`; emptied dirs pruned, never past the root),
  returns an `ApplyReport`, and leaves the directory equal to the new project. `commit_edit` applies +
  commits one commit as the customer identity via a new additive `git_service.commit_all` (git add -A
  + commit); previous history is preserved.
- 9 new stdlib offline tests (226 total): diff classification + empty diff + executable-flag change,
  plan_edit no-op and description-change (README.md modified, nothing added/deleted), apply round-trip
  (old tree -> new), path-safety refusal (`..` + missing target), and commit_edit two-commit history.
  Tests use tempdirs and the local git CLI (same pattern as the R-228 git-service tests).
- `git_service.create_repository`/`materialize_project` unchanged (additive `commit_all` only). No
  network call, no code execution, no write outside the target. `docs/EDIT_LOOP.md` added.
- Committed directly to main (only branch). Tracker row R-237 (Builder) inserted at row 9; MVP total
  132 / Done 26. Implementation checkpoint `a0a494a`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-238

- Gave the generated backend a real persistence layer. New `codegen/schema_sql.py`:
  `render_postgres_schema(ir)` renders deterministic PostgreSQL DDL from the IR entities + relations —
  one `CREATE TABLE` per entity (snake_case name), columns typed from `FieldType` (STRING/TEXT->TEXT,
  INT->BIGINT, FLOAT->DOUBLE PRECISION, BOOL->BOOLEAN, DATETIME->TIMESTAMPTZ, UUID->UUID, JSON->JSONB),
  `NOT NULL` for required fields, a UUID primary key (the entity's own `id` field if present, else a
  surrogate `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`), `<name>_id UUID REFERENCES <target>(id)`
  for many_to_one/one_to_one relations, and one deterministic join table per many_to_many pair.
- Wired both backend adapters (FastAPI and Go) to emit `migrations/0001_init.sql` exactly when the IR
  has entities and `database_strategy is DatabaseStrategy.POSTGRES` — no previously emitted file
  changes. Output is byte-stable, so the R-237 edit loop diffs the migration when the IR entities
  change. Exported `render_postgres_schema` from the codegen package.
- 11 new stdlib offline tests (237 total): type map + required->NOT NULL, surrogate vs declared PK,
  many_to_one FK column, single many_to_many join table with composite PK, determinism, the
  postgres/entities gate, and adapter emission (python + go emit; OTHER db and no-entities do not).
  No existing adapter/assembler test broke. `task verify` + `security:quick` + `env:check` pass.
- Nothing connects to or runs a database; no network. `docs/CODEGEN.md` documents the schema section.
- Committed directly to main (only branch). Tracker row R-238 (Builder) inserted at row 9; MVP total
  133 / Done 27. Implementation checkpoint `c6a4c6e`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-239

- Gave the generated backends a real data-access layer over the R-238 schema. New
  `codegen/data_access.py`: `python_data_access_files(ir, slug)` emits `app/db.py` (an async psycopg
  connection helper reading DATABASE_URL, dict rows) + `app/repositories/<entity>.py` per entity with
  `list/get/create/delete`; `go_data_access_files(ir, slug)` emits `internal/store/store.go` (a
  database/sql opener via the pgx driver) + `internal/store/<entity>.go` per entity with
  `List/Get/Create/Delete` scanning into the generated `models.<Entity>` structs.
- Every query value is parameterized (`%s` for psycopg, `$N` for pgx); only fixed IR-derived table/
  column identifiers appear inline (no value interpolation). An id-only entity creates via
  `DEFAULT VALUES`. `schema_sql` gained a public `table_name`.
- Wired both backends to append the data-access files and the DB dependency (psycopg in
  requirements.txt / pgx require in go.mod) exactly when `ir.entities and database_strategy is POSTGRES`
  — same gate as the migration; no previously emitted file (other than requirements.txt / go.mod)
  changed. The R-237 edit loop diffs the repositories when entities change.
- 7 new stdlib offline tests (244 total): python emission + valid-Python parse + parameterization, go
  emission + module import path + struct scan, gating (no db / no entities), id-only DEFAULT VALUES, and
  determinism. No existing test broke. `task verify` + `security:quick` + `env:check` pass.
- Nothing connects to or queries a database; no network. `docs/CODEGEN.md` + `docs/PROGRESS.md` updated.
- Committed directly to main (only branch). Tracker row R-239 (Builder) inserted at row 9; MVP total
  134 / Done 28. Implementation checkpoint `f6792fa`. 0 local / 0 cloud model calls.
