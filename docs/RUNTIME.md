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

## Turn on a cloud tier later (Tier 2/3)

1. Put the key in your environment (e.g. `E2B_API_KEY=...` or `VERCEL_TOKEN=...`) — `.env.example`
   lists the names.
2. Select it: `OMNISTACKAI_RUNTIME_PROVIDER=e2b` and/or `OMNISTACKAI_DEPLOY_PROVIDER=vercel`.

That is all — the platform picks the provider up through the registry. The provider *drivers*
(actually calling E2B/Vercel/etc.) are the next Tracker IDs; this task wires the contracts, the local
tier, and the key-activated selection so nothing else needs to change when a driver lands.

> Free-tier note: local is free forever; Codespaces/Vercel/Render/Netlify/Neon have **recurring
> monthly** free tiers; E2B/Fly/Railway/cloud credits are typically **one-time** trials. Terms change —
> verify on each provider's pricing page.
