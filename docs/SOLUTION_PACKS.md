# Solution Packs

OmniStackAI's intended generation model is:

`owned product = verified baseline pack + deterministic configuration + bounded AI delta`

R-434 implements the immutable registry for verified baseline packs. R-435 exposes an exact-compatible pack
recommendation in deterministic ecosystem planning. R-436 adds the immutable declarative customization
manifest above that recommendation. R-437 applies its first allowlisted deterministic configuration subset
to a fresh pinned-pack IR. R-438 defines bounded typed AI-delta proposals and the local ModelProvider boundary.
R-439 safely applies validated AI-delta proposals to Application IR with semantic validation and provenance.

## Registered baselines

Each descriptor references an existing Application IR example. It does not copy generated source or
restate the IR. The descriptor pins the IR's canonical SHA-256 and exact assembled targets so a changed
baseline cannot silently keep the same version.

| Pack | Version | Exact domains | Selected capabilities | Targets |
| --- | --- | --- | --- | --- |
| `minimal-blog` | `1.0.0` | `blog-cms`, `content-publishing` | content publishing, comments, fixtures, admin web, Python backend | Next.js web + Python backend |
| `rideshare-favourites` | `1.0.0` | `rideshare` | marketplace, favourites, authenticated actions, Go backend | Next.js web + Go backend |

Registry construction fails closed if a descriptor is malformed, duplicated, missing its referenced IR,
or has drifted from its IR digest, assembled targets, or verification plans. Loading a pack returns a fresh,
validated Application IR.

## Deterministic inspection

List the registry:

```bash
task agent-engine:solution-packs
```

Select by exact domain and a required-capability subset:

```bash
task agent-engine:solution-packs -- --domain rideshare --capability favourites
```

The selector chooses the newest compatible semantic version deterministically. An unsupported domain or
capability returns a JSON `null` selection; the platform does not fabricate a fallback. These commands do
not build a repository, call a model, access the network, connect to a database, or run generated code.

## Planning recommendations

`task agent-engine:ecosystem:plan -- "<business description>"` now reports one transparent Solution Pack
recommendation. Compatibility requires:

1. The classifier's exact domain.
2. Any explicitly required capability tags.
3. Every framework target derived from the Application IR project plans already selected for the ecosystem.

The query and result are serialized under `solution_pack_recommendation`. A selection contains only its pack
id, version, pinned IR digest, and targets. A miss is explicitly `no-exact-match`; no semantic capability is
guessed from entity names or prose.

For example, the current blog-CMS ecosystem uses Next.js plus Python and recommends
`minimal-blog@1.0.0`. The current rideshare ecosystem also uses Python, so it does not recommend the
Go-backed `rideshare-favourites` baseline. That baseline remains selectable when a caller explicitly asks
for its compatible Next.js/Go target set.

## Declarative customization manifests

`create_solution_pack_manifest()` accepts only a selected `SolutionPackRecommendation`. The resulting
frozen manifest pins all facts needed to reproduce the choice:

- baseline pack id, semantic version, and canonical Application IR SHA-256;
- exact domain, required capabilities, and required framework targets from the recommendation query; and
- at most 32 frozen semantic changes, canonically ordered by unique change id.

Each `SolutionPackChange` declares a `configuration` or `ai-delta` source, an `add`/`update`/`remove`
operation, one typed area, an area-compatible semantic target such as `entity:Post`, `field:Post.status`, or
`screen:EditorialWorkflow`, a bounded summary, and 1–8 bounded acceptance criteria. Areas are limited to
project metadata, the data model, APIs, screens, design, and capabilities. These are reviewable intentions,
not executable mutations.

R-437 advances the manifest schema from 1.0 to 1.1 with an optional typed `desired_text`. It is accepted only
for a `configuration` + `update` + `project` change targeting `project:name` (≤128 characters) or
`project:description` (≤4000 characters). Values are explicit; summaries and acceptance criteria are never
parsed as configuration. AI-delta entries and all other targets cannot carry `desired_text`. Strict parsing
continues to accept and losslessly serialize R-436 schema 1.0 documents; their unvalued project configuration
cannot be applied until explicitly upgraded.

`SolutionPackManifest.to_json()` emits byte-stable canonical JSON. `parse_solution_pack_manifest()` strictly
rejects unknown/missing keys, invalid types/enums/targets, control characters, duplicates, excess changes,
and stale or incompatible registry pins. It re-runs exact recommendation selection for the recorded query;
a changed version, digest, or target set fails closed.

The schema intentionally contains no file path, patch, source-code blob, command, secret-value, or raw model
output field. Creating or parsing a manifest does not load/apply the pack, mutate an Application IR, generate
source, build a repository, use the network/database, or call a model.

## Deterministic configuration application

`apply_solution_pack_manifest()` revalidates the exact recommendation pin, preflights all configuration
entries, rejects duplicate writes, then loads a fresh baseline IR. In this first allowlist it applies only
explicit project-name and project-description updates. Any add/remove operation or entity/API/screen/design/
capability configuration fails closed before a result is returned.

The derived IR is reconstructed immutably and must pass `validate_ir`. A frozen
`SolutionPackApplicationResult` records the pack id/version/base digest, canonical derived digest, sorted
applied configuration IDs, explicitly unapplied AI-delta IDs, and the complete derived IR. Repeated application
is byte-stable. Empty and AI-only manifests preserve the base digest, and registry baselines remain unchanged.
This layer performs no source generation, build, network/database work, or model call.

## Bounded typed AI-delta proposal schema

`generate_ai_delta_proposal()` provides an explicit opt-in model boundary for converting pending manifest
AI-delta intents into validated `AIDeltaProposal` data. When a manifest has zero AI-delta changes, the provider
is completely bypassed and 0 calls are made.

When pending AI-delta items exist, the prompt teaches the model by providing the base Solution Pack metadata,
existing entities, APIs, screens, and the exact set of pending change intents. The untrusted JSON output is
strictly parsed by `parse_ai_delta_proposal()`:
- Rejecting credential-bearing fields (`password`, `secret`, `token`, `jwt`, `api_key`).
- Rejecting collisions with existing base IR entities, APIs, or screens.
- Enforcing structural validity on entities (required UUID `id` field, valid field types and relation kinds).
- Restricting outputs to bounded `AIDeltaProposal` records without mutating the base IR, generating source,
  or invoking cloud models.

## Safe AI-delta proposal application
 
`apply_solution_pack_manifest()` accepts an optional `proposal: AIDeltaProposal | None = None`.
When `proposal` is `None`, existing configuration application behavior is strictly preserved.
 
When `proposal` is provided:
- Revalidates pins: `proposal.pack_id`, `proposal.pack_version`, and `proposal.base_ir_sha256` must match the manifest.
- Revalidates change IDs: all `proposal.addressed_change_ids` must correspond to pending `ai-delta` changes in `manifest.changes`.
- Revalidates collisions: proposed entity names, API endpoints, and screen IDs must not collide with the base IR.
- Revalidates relation targets: all relations in proposed entities must target declared base or proposed entities.
- Immutably merges entities, APIs, and screens with allowlisted configuration updates into a fresh derived `ApplicationIR`.
- Ensures the derived IR is `validate_ir`-clean; any error fails closed with `SolutionPackError`.
- Records `applied_ai_delta_change_ids` and remaining `unapplied_ai_delta_change_ids` in `SolutionPackApplicationResult`.
- Application is byte-stable, repeatable, and offline (0 model calls).

## Project builder and CLI

`build_solution_pack_project()` assembles a Solution Pack derived `ApplicationIR` into an owned Git repository on disk:
- Accepts either a `SolutionPackApplicationResult` or a `SolutionPackManifest` (with optional `AIDeltaProposal`).
- Verifies domain and pack compatibility, compiles target projects via `assemble_project()`, and initializes an owned Git repository with complete initial commit via `create_repository()`.
- Computes deterministic target verification plans (`verify_plans_for_ir`) and records complete provenance:
  - `pack_id`, `pack_version`, `base_ir_sha256`, `derived_ir_sha256`
  - `applied_configuration_change_ids`, `applied_ai_delta_change_ids`, `unapplied_ai_delta_change_ids`
  - `target_dir`, `file_count`, `commit_sha`, and `verify_targets`.
- Serializes byte-stable, deterministically formatted metadata via `SolutionPackBuildResult.to_json()`.
- Wires seamlessly into `plan_ecosystem()` and `build_ecosystem()` to replace the customer web surface IR with the pack-derived IR while preserving all other ecosystem services.
- Exposes CLI via `python3 -m omnistackai_agent_engine.solution_packs.build_cli` and `task agent-engine:solution-pack:build`.
- 100% offline verification in `task verify` (0 model calls).

## Studio integration and UI controls

R-441 and R-442 wire Solution Pack selection, customization, AI-delta feature modifications, and provenance into the Studio:
- HTTP API: `GET /api/solution-packs` returns the registered packs; `POST /api/solution-packs/recommend` returns domain classification and matching pack recommendation.
- Build options: `POST /api/build` accepts `pack_id`, `pack_version`, `custom_name`, `custom_description`, `configuration_changes`, `ai_features`, and `ai_delta_prompt`.
- Zero-model baseline builds: when building with a Solution Pack and no AI features, `live_serve.py` uses `create_solution_pack_manifest`, `apply_solution_pack_manifest`, and `build_solution_pack_project` to deterministically create the repository and record full provenance without any model calls.
- Bounded AI-delta modifications: when `ai_features` are specified, `live_serve.py` formulates typed `ai-delta` `SolutionPackChange` intents, calls `generate_ai_delta_proposal`, safely derives the Application IR with `apply_solution_pack_manifest`, and records `applied_ai_delta_change_ids` in provenance.
- Studio web UI: includes a Solution Pack dropdown, real-time recommendation banner, customization inputs, AI Feature Modifications input (`#ai-features`), verified badges, AI delta chips, and full provenance rendering while strictly preserving 0 external resource links in HTML.
- History: records `pack_id`, `pack_version`, and `applied_ai_delta_change_ids` in `StudioBuildHistory`.

## Packaging, verification, and export CLI

R-443 introduces portable, byte-stable Solution Pack bundles and command-line lifecycle management:
- Bundle format: `SolutionPackPackage` encapsulates `schema_version` (`"1.0"`), metadata (`pack_id`, `version`, `display_name`, `description`, `domains`, `capabilities`, `targets`, `verify_targets`), `ir_sha256`, canonical `ir_dict`, `verify_plans`, and `package_sha256` checksum.
- Integrity verification: `parse_solution_pack_package()` and `verify_package()` strictly validate schema, semver, fields, embedded Application IR via `validate_ir`, confirm canonical `ir_sha256` digest matching, and verify the whole-package SHA-256 integrity hash, failing closed on tampering or corruption with `SolutionPackError`.
- Dynamic registration: `SolutionPackRegistry.register_package(pkg)` registers verified packages dynamically with duplicate ID and target/digest consistency checks.
- CLI operations:
  ```bash
  # Export pack to canonical JSON
  task agent-engine:solution-pack:package -- export --pack minimal-blog --output minimal-blog.pack.json

  # Verify package integrity
  task agent-engine:solution-pack:package -- verify minimal-blog.pack.json

  # Inspect package metadata
  task agent-engine:solution-pack:package -- inspect minimal-blog.pack.json
  ```
- 100% offline verification in `task verify` (0 model calls).

## Multi-surface ecosystem pack synthesis

R-444 synthesizes multi-surface ecosystems from Solution Packs and packages them into verified bundles:
- Package format: `EcosystemPackPackage` encapsulates `schema_version` (`"1.0"`), `ecosystem_id`, `version`, `display_name`, `description`, `domain`, `base_pack_id`, a collection of `EcosystemSurfacePackage` objects (`surface_kind`, `app_name`, `slug`, `ir_sha256`, canonical `ir_dict`, `verify_targets`), and whole-ecosystem `package_sha256` checksum.
- Synthesis semantics: `synthesize_surface_ir()` derives surface-specific Application IRs from the pack's unified entity model, scoping entity visibility, mutation authority, actor roles, APIs, and screens per surface while preserving relational dependencies, strategy, and semantic correctness.
- Ecosystem planner integration: `plan_ecosystem()` synthesizes secondary surfaces using the pack's authoritative data model when `pack_result` is provided, marking synthesized secondary surfaces with `is_synthesized=True`.
- Integrity verification: `parse_ecosystem_pack_package()` and `verify_ecosystem_pack()` strictly validate schema, semver, fields, embedded Application IRs across all surfaces via `validate_ir`, confirm surface `ir_sha256` digest matching, and verify whole-package SHA-256 integrity, failing closed on tampering or corruption with `SolutionPackError`.
- CLI operations:
  ```bash
  # Synthesize ecosystem pack from baseline pack
  task agent-engine:solution-pack:ecosystem -- synthesize --pack minimal-blog --output minimal-blog-eco.pack.json

  # Verify ecosystem pack integrity
  task agent-engine:solution-pack:ecosystem -- verify minimal-blog-eco.pack.json

  # Inspect ecosystem pack surfaces and metadata
  task agent-engine:solution-pack:ecosystem -- inspect minimal-blog-eco.pack.json

  # Materialize all multi-surface repositories to disk
  task agent-engine:solution-pack:ecosystem -- build minimal-blog-eco.pack.json --out-dir /tmp/ecosystem-repos
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem pack registry integration and Studio multi-surface selection

R-445 introduces centralized registry management for ecosystem packs, catalog discovery, and Studio multi-surface selection:
- Registry model: `EcosystemPackRegistry` manages `EcosystemPack` descriptors (`ecosystem_id`, `version`, `display_name`, `description`, `domain`, `base_pack_id`, `surfaces`, `package_sha256`, `package`), offering `list_packs()`, `get()`, `select()`, `recommend()`, `register_package()`, and `load_surface_ir()`.
- Built-in baselines: Pre-registers `minimal-blog-ecosystem` and `rideshare-favourites-ecosystem` via `DEFAULT_ECOSYSTEM_PACK_REGISTRY`. Utilizes `_LazyEcosystemPackRegistry` to break circular dependency cycles during module import.
- Studio discovery & recommendation: HTTP endpoints `GET /api/ecosystem-packs` (catalog listing) and `POST /api/ecosystem-packs/recommend` (domain-based recommendations).
- Studio build & live runner: `POST /api/build` in `server.py` and `live_serve.py` accepts `ecosystem_id`, `ecosystem_version`, and `surface_slug` to build an individual surface (using `load_surface_ir()`) or compile the complete multi-surface ecosystem with 0 model calls.
- Studio history: Tracks `ecosystem_id`, `ecosystem_version`, `surface_slug`, `surface_kind`, and `is_ecosystem` in `StudioBuildHistory`.
- Studio web UI: Features single-app vs ecosystem tabs (`#tab-single`, `#tab-ecosystem`), ecosystem selector (`#eco-select`), surface selector (`#surface-select`), surface cards (`#surface-cards`), real-time recommendations, and history chips, strictly maintaining 0 external network requests (no external http/https/src/link/fonts).
- CLI catalog discovery:
  ```bash
  # Discover registered ecosystem packs
  task agent-engine:solution-pack:ecosystem -- catalog

  # Output in JSON format
  task agent-engine:solution-pack:ecosystem -- catalog --json
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem Studio live multi-surface preview and process orchestration

R-446 enhances Studio live preview and process orchestration to coordinate multi-surface business ecosystems:
- Lifecycle orchestration: `StudioPreviewManager` (`studio/preview.py`) coordinates multi-surface ecosystems via `replace_ecosystem(ecosystem_id, surfaces, active_surface_slug=None)`, `switch_surface(surface_slug)`, `stop(surface_slug=None)`, and `restart(surface_slug=None)`.
- Multi-session process management: Maintains an internal multi-session map (`_sessions: dict[str, LocalAppSession]`), dynamically allocating collision-free loopback ports for each surface to prevent port conflicts across surfaces.
- Thread safety & deadlock elimination: Uses `threading.RLock` to eliminate reentrant synchronization deadlocks during composite lifecycle operations (e.g., `restart` delegating to `replace`).
- Liveness awareness: Continuous status inspection (`status()`) tracks whether background processes are running across all active surfaces, reporting live state changes without stale status indicators.
- Studio HTTP endpoints: Extended `POST /api/preview/switch` (surface switching), `POST /api/preview/stop` (per-surface/global stop), `POST /api/preview/restart` (per-surface/global restart), and `POST /api/history/preview` (surface-targeted re-preview).
- Studio Web UI: Renders `#preview-surface-tabs` surface switcher bar in the preview header, live running indicators (pulsing dots), surface kind badges, and 1-click surface switching without iframe flicker, strictly maintaining 0 external network requests.
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem multi-surface cross-app auth and unified state binding

R-447 formalizes cross-app authentication, shared security boundaries, and unified data/lifecycle state binding across multi-surface ecosystems:
- Cross-app authentication: `EcosystemAuthContract` defines shared JWT parameters (algorithm `HS256`, secret reference, issuer, audience, TTL, and role bindings). `CrossAppAuthMatrix` specifies role isolation and surface access permissions.
- Python 3.13 stdlib-only JWT engine: `mint_ecosystem_token` and `verify_ecosystem_token` provide deterministic HMAC-SHA256 token minting and signature verification using only `hmac`, `hashlib`, `base64`, and `json` (0 external dependencies, no PyJWT).
- Deterministic demo tokens: `generate_surface_tokens` produces per-surface test JWTs for automated test suites and instant Studio preview testing.
- Unified state binding: `EcosystemStateBinding` formalizes shared entities (`SharedEntityBinding`), lifecycle state flows (`EntityStateFlow`, `StateTransition` with role-gated `can_transition`), cross-app endpoint bindings (`CrossAppEndpointBinding`), and per-surface environment variables (`SurfaceEnvBinding`).
- Deterministic synthesis: `synthesize_ecosystem_auth` and `synthesize_ecosystem_state` derive valid contracts from any ecosystem plan or pack surfaces with surface kind role affinity matching.
- Studio integration: `StudioPreviewManager` injects `active_role` and `active_token` into preview status/payloads, and exposes `get_ecosystem_auth()` and `get_ecosystem_state()`. The Studio HTTP server exposes `GET /api/ecosystem/auth` and `GET /api/ecosystem/state`.
- Studio web UI: Renders `#preview-auth-info` with active role badge and 1-click "Copy Demo JWT" button, strictly maintaining 0 external network requests.
- CLI auth & state inspection:
  ```bash
  # Inspect cross-app auth contract
  task agent-engine:solution-pack:ecosystem -- auth minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- auth minimal-blog-ecosystem --json

  # Inspect unified state binding
  task agent-engine:solution-pack:ecosystem -- state minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- state minimal-blog-ecosystem --json
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem cross-surface webhook and event bridge

R-448 introduces automated cross-surface event dispatch, HMAC-SHA256 signature verification, and webhook delivery orchestration across multi-surface ecosystems:
- Cross-surface event contracts: `EcosystemWebhookSubscription` defines event delivery pipelines with `WebhookRetryPolicy`, pattern matching (`entity.action` or `*`), secret references, and target endpoints. `EcosystemEventPayload` defines canonical event structures with idempotency keys.
- Python 3.13 stdlib-only HMAC-SHA256 engine: `sign_webhook_payload` and `verify_webhook_signature` compute and verify `sha256=<hex>` signatures using `hmac.compare_digest` with zero external dependencies.
- In-process event bridge: `EcosystemEventBridge` coordinates cross-surface routing, subscription management, event dispatching, and bounded delivery logging (max 100 entries).
- Deterministic contract synthesis: `synthesize_ecosystem_events` derives cross-surface subscriptions linking surfaces that write shared entities to surfaces that read them.
- Package bundling & registry access: `EcosystemPackPackage` validates event bridge contracts with whole-package SHA-256 integrity checks; `EcosystemPackRegistry` and `EcosystemPack` expose `get_event_bridge`.
- Studio preview & server: `StudioPreviewManager` tracks event bridge status, exposes `get_ecosystem_events()` and `dispatch_ecosystem_event()`, and injects `has_events`, `event_count`, and `subscription_count` into preview payloads. Studio HTTP server exposes `GET /api/ecosystem/events` and `POST /api/ecosystem/events/dispatch`.
- Studio web UI: Renders `#preview-events-info` with subscription count badges, an event simulation panel ("Simulate Event"), and live delivery log table, strictly maintaining 0 external network requests.
- CLI event bridge inspection:
  ```bash
  # Inspect event bridge subscriptions and deliveries
  task agent-engine:solution-pack:ecosystem -- events minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- events minimal-blog-ecosystem --json
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem cross-surface telemetry, audit trails, and distributed tracing

R-449 introduces cross-surface distributed tracing, audit logging, and telemetry contract orchestration across multi-surface ecosystems:
- Cross-surface telemetry contracts: `EcosystemTelemetryContract`, `TelemetrySamplingPolicy`, and `TracedSurface` define unified tracing topology, propagation headers (`X-OmniStack-Trace-Id`), instrumented operations, and audit-emitting surfaces.
- Canonical telemetry and audit records: `TelemetrySpan` defines span attributes with parent linkage and deterministic digests; `AuditTrailEntry` defines actor-attributed audit logs; `DistributedTrace` assembles spans across surfaces.
- Python 3.13 stdlib-only deterministic ID generation: Trace IDs and span IDs use stdlib `uuid` + `hashlib` with 0 external dependencies and 100% offline determinism.
- In-process telemetry collector: `EcosystemTelemetryCollector` coordinates span lifecycles (`start_span`, `finish_span`), audit recording, and bounded ring-buffer storage (max 500 spans / 500 audit entries).
- Deterministic contract synthesis: `synthesize_ecosystem_telemetry` derives traced surfaces, cross-surface operations, and audit actions from ecosystem definitions.
- Package bundling & registry access: `EcosystemPackPackage` bundles and validates telemetry contracts with whole-package SHA-256 integrity checks; `EcosystemPackRegistry` and `EcosystemPack` expose telemetry contracts.
- Studio preview & server: `StudioPreviewManager` tracks telemetry collector, injects `has_telemetry` and `span_count` into preview payloads, and exposes `get_ecosystem_telemetry()`. Studio HTTP server exposes `GET /api/ecosystem/telemetry`.
- Studio web UI: Renders `#preview-telemetry-info` with span counts and surface badges, strictly maintaining 0 external network requests.
- CLI telemetry inspection:
  ```bash
  # Inspect ecosystem pack telemetry contract
  task agent-engine:solution-pack:ecosystem -- telemetry minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- telemetry minimal-blog-ecosystem --json
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem multi-surface export, deployment manifest, and live gateway orchestration

R-450 introduces unified multi-surface deployment manifests, Docker Compose generation, and reverse-proxy live gateway orchestration across multi-surface ecosystems:
- Deployment contracts: `GatewayRoute` defines route path prefixes, target surfaces, target ports, strip prefix flags, and allowed HTTP methods. `SurfaceDeploymentSpec` defines container image naming, build contexts, Dockerfile paths, exposed container ports, host port mappings, environment variable bindings, and resource limits. `EcosystemDeploymentManifest` encapsulates the complete multi-surface deployment topology (`ecosystem_id`, `version`, `gateway_port`, `routes`, `surfaces`, `network_name`, `compose_version`).
- Python 3.13 stdlib-only Docker Compose generator: `generate_docker_compose()` outputs byte-stable, valid Docker Compose YAML (version `3.8`) for all ecosystem surfaces, a PostgreSQL service (when database strategy is postgres), shared bridge networks, volume definitions, health checks, and depends_on constraints with 0 external dependencies (zero PyYAML).
- In-process HTTP live gateway: `EcosystemLiveGateway` provides a thread-safe, non-blocking HTTP reverse proxy using stdlib `http.server.ThreadingHTTPServer` and `urllib.request`. Features longest-prefix route matching (`match_gateway_route`), request proxying, response header forwarding, and tracing header injection (`X-OmniStack-Surface`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-OmniStack-Gateway`).
- Deterministic contract synthesis: `synthesize_ecosystem_deployment` automatically derives non-colliding host ports (starting from 3000 for web/admin/mobile surfaces, 8000 for APIs), route paths (`/` for consumer web, `/<slug>` for other surfaces, `/api` for APIs), container names, and environment variable bindings.
- Package bundling & registry access: `EcosystemPackPackage` bundles `deployment_manifest` with canonical whole-package SHA-256 integrity checks; `EcosystemPackRegistry` and `EcosystemPack` expose `get_deployment_manifest`.
- Studio preview & server: `StudioPreviewManager` tracks deployment manifest and live gateway lifecycle, exposes `get_ecosystem_deployment()` and `to_compose_yaml()`, and injects `has_deployment`, `gateway_url`, and `gateway_routes` into preview payloads. Studio HTTP server exposes `GET /api/ecosystem/deployment` and `GET /api/ecosystem/deployment/compose`.
- Studio web UI: Renders `#preview-deployment-info` with route listing, target surface badges, gateway URL links, and 1-click "Copy Docker Compose YAML" affordance, strictly maintaining 0 external network requests.
- CLI deployment & Compose export:
  ```bash
  # Inspect deployment manifest
  task agent-engine:solution-pack:ecosystem -- deploy minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- deploy minimal-blog-ecosystem --json

  # Export Docker Compose YAML specification
  task agent-engine:solution-pack:ecosystem -- deploy minimal-blog-ecosystem --compose
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem cross-surface data sync, conflict resolution, and offline-first sync protocol

R-451 introduces canonical cross-surface data sync models, deterministic conflict resolution algorithms, and offline-first sync protocols across multi-surface ecosystems:
- Cross-surface sync contracts: `SyncEntitySpec` defines sync entity configurations including resolution strategy (`last_write_wins`, `source_of_truth`, `field_merge`), authority surface, sync surfaces, and immutable fields. `SyncMutation` defines individual entity mutations (`insert`, `update`, `delete`) with client sequence numbers, data dictionaries, base versions, and SHA-256 mutation hashes. `SyncConflict` logs detected concurrent update conflicts with resolution records. `SyncCheckpoint` captures per-surface sync positions. `EcosystemSyncContract` formalizes the overall sync topology.
- Deterministic conflict resolution algorithms: `resolve_sync_conflict` implements three zero-dependency conflict resolution strategies:
  - `last_write_wins`: Compares ISO timestamps of conflicting mutations, resolving in favor of the latest write (using SHA-256 hash as stable tie-breaker).
  - `source_of_truth`: Prioritizes mutations from the designated authoritative surface (e.g. admin or core API surface) over secondary client surfaces.
  - `field_merge`: Performs granular field-level merges between concurrent mutations, preserving non-overlapping changes while enforcing immutable field protections and authoritative field defaults.
- In-process thread-safe sync engine: `EcosystemSyncEngine` maintains mutation journals, current entity states, bounded conflict logs (max 500 entries), and surface checkpoints using `threading.RLock`. Exposes `push_mutations()` with base-version conflict detection, `pull_changes()` for incremental synchronization, and `simulate_conflict()` for live demonstration.
- Deterministic contract synthesis: `synthesize_ecosystem_sync` automatically derives sync entity specifications, authority mappings, and strategy assignments from ecosystem surfaces and entity definitions.
- Package bundling & registry access: `EcosystemPackPackage` bundles `sync_contract` with canonical whole-package SHA-256 integrity verification; `EcosystemPackRegistry` and `EcosystemPack` expose `get_sync_contract`.
- Studio preview & server: `StudioPreviewManager` tracks sync contracts and engine state, injecting `has_sync`, `sync_entity_count`, `sync_conflict_count`, and `sync_version` into preview payloads, and exposing `get_ecosystem_sync()`, `push_sync_mutations()`, `pull_sync_changes()`, and `simulate_sync_conflict()`. Studio HTTP server exposes `GET /api/ecosystem/sync`, `POST /api/ecosystem/sync/push`, `GET /api/ecosystem/sync/pull`, and `POST /api/ecosystem/sync/simulate`.
- Studio web UI: Renders `#preview-sync-info` with entity chips, conflict/version badges, and 1-click "Simulate Conflict" and "Refresh Sync" buttons, strictly maintaining 0 external network requests.
- CLI data sync inspection:
  ```bash
  # Inspect ecosystem pack data sync contract
  task agent-engine:solution-pack:ecosystem -- sync minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- sync minimal-blog-ecosystem --json
  ```
- 100% offline verification in `task verify` (0 model calls).

## Ecosystem multi-surface CI/CD workflow & GitHub Actions orchestration

R-452 introduces canonical multi-surface CI/CD workflow contracts, deterministic GitHub Actions workflow generation, DAG dependency validation, and pipeline simulation across multi-surface ecosystems:
- CI/CD workflow contracts: `CIJobStep` defines individual execution steps (`name`, `uses`, `run`, `working_directory`, `env`, `with_args`). `CIJob` defines individual CI jobs (`job_id`, `name`, `surface_slug`, `runs_on`, `needs`, `steps`, `services`, `env`). `CIWorkflow` encapsulates workflow triggers (`push`, `pull_request`, `workflow_dispatch`), jobs, and environments. `EcosystemCICDContract` formalizes the overall CI/CD configuration (`ecosystem_id`, `version`, `workflows`, `surfaces_covered`, `required_gates`).
- Deterministic Python 3.13 stdlib-only GitHub Actions YAML generator: `generate_github_actions_workflow` and `to_workflow_yaml` generate byte-stable, valid GitHub Actions YAML specifications with zero external dependencies (no PyYAML). Supports triggers, runs-on, needs matrices, service containers (e.g. PostgreSQL with Alpine image and health checks), step arguments, working directories, and environment variables.
- In-process DAG validator & pipeline simulator: `EcosystemCICDEngine` implements Kahn's algorithm for topological sorting and cycle detection (`validate_dag`, `topological_sort`). Exposes deterministic dry-run pipeline simulation (`simulate_pipeline_run`) computing job ordering, simulated step durations, exit codes, and gate validation offline.
- Deterministic contract synthesis: `synthesize_ecosystem_cicd` automatically derives surface verification jobs according to surface runtime (Node.js/pnpm for web/admin surfaces, Python/pip + PostgreSQL service for FastAPI APIs, Go + PostgreSQL service for Go backends), and links an overarching `ecosystem-integration` verification job that runs after all surface jobs pass.
- Package bundling & registry access: `EcosystemPackPackage` bundles `cicd_contract` with whole-package SHA-256 integrity verification; `EcosystemPackRegistry` and `EcosystemPack` expose `get_cicd_contract`.
- Studio preview & server: `StudioPreviewManager` tracks CI/CD contracts and simulation engines, injecting `has_cicd`, `cicd_workflow_count`, `cicd_job_count`, and `cicd_status` into preview payloads, and exposing `get_ecosystem_cicd()`, `to_workflow_yaml()`, and `simulate_cicd_run()`. Studio HTTP server exposes `GET /api/ecosystem/cicd`, `GET /api/ecosystem/cicd/yaml`, and `POST /api/ecosystem/cicd/simulate`.
- Studio web UI: Renders `#preview-cicd-info` with workflow triggers, job chips, and 1-click "Copy GitHub Actions YAML", "Simulate Pipeline", and "Refresh CI/CD" buttons, strictly maintaining 0 external network requests.
- CLI CI/CD inspection:
  ```bash
  # Inspect ecosystem pack CI/CD contract
  task agent-engine:solution-pack:ecosystem -- cicd minimal-blog-ecosystem
  task agent-engine:solution-pack:ecosystem -- cicd minimal-blog-ecosystem --json

  # Export GitHub Actions YAML workflow
  task agent-engine:solution-pack:ecosystem -- cicd minimal-blog-ecosystem --yaml

  # Simulate pipeline run (DAG validation + step simulation)
  task agent-engine:solution-pack:ecosystem -- cicd minimal-blog-ecosystem --simulate
  ```
- 100% offline verification in `task verify` (0 model calls).

## Next boundary

R-453: Solution Pack Ecosystem Comprehensive Multi-Surface Health Check, Smoke Testing, and Canary Verification.


