# Solution Packs

OmniStackAI's intended generation model is:

`owned product = verified baseline pack + deterministic configuration + bounded AI delta`

R-434 implements the immutable registry for verified baseline packs. R-435 exposes an exact-compatible pack
recommendation in deterministic ecosystem planning. R-436 adds the immutable declarative customization
manifest above that recommendation. None of these layers applies a pack or asks a model to generate a delta.

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

`SolutionPackManifest.to_json()` emits byte-stable canonical JSON. `parse_solution_pack_manifest()` strictly
rejects unknown/missing keys, invalid types/enums/targets, control characters, duplicates, excess changes,
and stale or incompatible registry pins. It re-runs exact recommendation selection for the recorded query;
a changed version, digest, or target set fails closed.

The schema intentionally contains no file path, patch, source-code blob, command, secret-value, or raw model
output field. Creating or parsing a manifest does not load/apply the pack, mutate an Application IR, generate
source, build a repository, use the network/database, or call a model.

## Next boundary

R-437 may apply only validated `configuration` intents deterministically to a fresh copy of the pinned pack
Application IR and record transparent provenance. `ai-delta` intents must remain explicitly unapplied until
a separate provider-gated task. Source generation/building remains later still; every layer must preserve
the deterministic IR, verification, ownership, and provider boundaries.
