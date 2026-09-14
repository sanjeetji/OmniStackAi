# Solution Packs

OmniStackAI's intended generation model is:

`owned product = verified baseline pack + deterministic configuration + bounded AI delta`

R-434 implements the first, deliberately small part of that model: an immutable registry for verified
baseline packs. It does not yet compose ecosystem surfaces or generate an AI delta.

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

## Next boundary

A follow-up task may expose exact compatible pack recommendations to ecosystem planning. Pack
configuration and AI-generated deltas remain separate, explicit layers and must preserve the deterministic
IR, verification, ownership, and provider boundaries.
