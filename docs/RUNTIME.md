# Runtime (preview/sandbox) & deployment (Brief §15/§51/§75)

Running and previewing a generated app sits behind platform-owned provider contracts so the platform
never hard-codes a vendor. It is designed as tiers: **local works with no keys**; **cloud providers
plug in by adding a key.**

Package: `omnistackai_agent_engine.runtime` (standard library only; nothing is run or deployed by the
planning code).

## Tiers

| Tier | Provider | Keys | What it does |
|------|----------|------|--------------|
| **0** | `local` (your Mac) | none | install + run a generated app; preview at a loopback URL |
| **1** | `local` on a cloud dev box (Codespace/VM) | none | same, off your machine |
| **2/3** | `e2b` / `daytona` / `fly-machines` (sandbox), `vercel` / `fly` / `render` / `netlify` (deploy) | one key each | run untrusted code in a sandbox / host a real deploy |

## How it works

- `LocalRuntimeProvider.preview_plan(app_dir, target)` returns a deterministic `PreviewPlan`: the
  install/run `Command`s and the local URL. Targets: `nextjs-web` (:3000), `nextjs-admin` (:3001),
  `backend-python` (uvicorn :8000), `backend-go` (:8080).
- `run_preview(plan)` executes the plan (Tier 0/1) — needs the toolchain + internet; never run by
  tests or `task verify`.
- `build_runtime_from_env()` / `build_deploy_from_env()` register `local` always and mark each cloud
  provider **active** only when its key env is set; `OMNISTACKAI_RUNTIME_PROVIDER` /
  `OMNISTACKAI_DEPLOY_PROVIDER` select one (selecting a keyless cloud provider is a clear error).
  Keys are read from the env only — never logged, stored, or returned.

## Use it now (Tier 0, free)

```
# see the exact commands for a target:
task agent-engine:preview-plan -- nextjs-web

# then, in a generated project on a machine with the toolchain + internet:
cd apps/web && pnpm install && pnpm dev     # -> http://127.0.0.1:3000
```

## Switching tiers — one knob (R-234)

`OMNISTACKAI_TIER` is the single switch; change it in `.env` and the resolved providers change:

- `OMNISTACKAI_TIER=0` or `1` → runtime `local`, no deploy (free; runs on your Mac / a Codespace).
- `OMNISTACKAI_TIER=2` → uses the cloud selections `OMNISTACKAI_RUNTIME_PROVIDER` (sandbox) and
  `OMNISTACKAI_DEPLOY_PROVIDER` (host), each of which must have its key set.

See what's active at any time:

```
task platform:status
# Tier:         2
# Runtime:      e2b
# Deploy:       vercel
# Sandbox keys: e2b
# Deploy keys:  vercel
```

`resolve_platform()` returns the resolved runtime + deploy provider objects; selecting a cloud provider
without its key (or at tier 0/1) raises a clear error.

## Combined project plan (R-245)

`projectplan.build_project_plan(ir)` composes one per-app view for the whole assembled monorepo: each
`AppPlan` pairs an assembled app (label / directory / target) with its **preview** plan (how to run it
locally), its **verify** gate ladder, and — only when a key-activated `DeploymentProvider` is passed —
its **deploy** plan. `ProjectPlan.to_dict()` is JSON-serializable (secret-free) for the console;
`render()` is a readable summary. See it:

```
task plan:show -- rideshare-favourites
# - web (Next.js)  [nextjs-web]  (apps/web)
#     preview -> http://127.0.0.1:3000   (pnpm install / pnpm dev)
#     verify gates: install, typecheck, lint, build
# - backend (go)   [backend-go]  (services/api)
#     preview -> http://127.0.0.1:8080   (go run .)
#     verify gates: lint, test, build
```

It only builds plans — nothing is installed, run, verified, or deployed, and no key value is included.

## Provider drivers (R-234)

Every provider has a driver that produces a real command plan; the key is read from the environment by
the CLI at run time and never appears in a plan:

- **Deploy** (`DeployPlan` via `run_deploy`): `vercel` (`vercel deploy --prod`), `netlify`
  (`netlify deploy --build --prod`), `render` (`render deploys create --wait`), `fly`
  (`fly launch` + `fly deploy`).
- **Sandbox** (`PreviewPlan`): `e2b`, `daytona`, `fly-machines` — reuse the target's run commands and
  report the provider's URL; the provider CLI/SDK provisions the sandbox and syncs files at run time.

Turn a cloud tier on: (1) put the key in `.env` (`VERCEL_TOKEN=…`, `E2B_API_KEY=…`, …); (2) set
`OMNISTACKAI_TIER=2` and the selection(s). The exact CLI flags follow each provider's current CLI —
confirm on first live run (`run_preview`/`run_deploy` execute the plan on a machine with the CLI + key).

> Free-tier note: local is free forever; Codespaces/Vercel/Render/Netlify/Neon have **recurring
> monthly** free tiers; E2B/Fly/Railway/cloud credits are typically **one-time** trials. Terms change —
> verify on each provider's pricing page.
