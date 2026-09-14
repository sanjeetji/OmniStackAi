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

## Next boundary

R-443: Solution Pack registry packaging, export CLI, or multi-surface ecosystem pack synthesis.
