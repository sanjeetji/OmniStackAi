# Solution Packs

OmniStackAI's intended generation model is:

`owned product = verified baseline pack + deterministic configuration + bounded AI delta`

R-434 implements the immutable registry for verified baseline packs. R-435 exposes an exact-compatible pack
recommendation in deterministic ecosystem planning. It still does not apply a pack, compose a configuration,
or generate an AI delta.

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

## Next boundary

A follow-up task may define the immutable declarative configuration/delta manifest that sits above a pinned
pack. Pack application and AI-generated deltas remain separate, explicit layers and must preserve the
deterministic IR, verification, ownership, and provider boundaries.
