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

## Managed Studio preview (R-421)

The local front door now offers two deliberately separate modes:

```text
task agent-engine:studio:serve
  Build-only Studio. Uses local Ollama to create the owned repository but does not execute generated code.

task agent-engine:studio:preview
  Explicit trusted-local mode. Starts local PostgreSQL, builds the repository, runs its migrations,
  backend, and Next.js web app, then embeds the actual web URL in a sandboxed Studio iframe.
```

`studio:preview` composes the existing R-419 run plan through a managed `LocalAppSession`; it does not
introduce another runtime or bypass the platform boundary. The session owns every child process, waits for
API and web readiness, stops the previous app when a new preview replaces it, and stops everything when
Studio exits. A launch failure is returned as a bounded, secret-free preview status while the successfully
generated repository remains available.

This is explicitly **trusted local execution**, not tenant isolation or a cloud sandbox. Use it only for
prompts/code you are willing to run on the current machine. Cloud-generated or otherwise untrusted code
must still use an isolated provider-backed execution plane. Static verification never invokes this mode:
`task verify` uses injected process/readiness fakes and performs no Docker, database, install, model, or
external-network work.

### Collision-free ports and lifecycle controls (R-422)

Each preview allocates its **own two distinct, currently-free loopback ports** for the generated API and
web servers (`allocate_preview_ports` holds two sockets open while reading their OS-assigned ports;
`start_preview_app` threads them through the R-419 run plan and the generated app's
`NEXT_PUBLIC_API_URL`, then delegates to the strict `start_app`). A preview therefore never fails on, or
clobbers, an existing `task agent-engine:app:run` app on `:3000`/`:8000` or a prior preview. The
`task agent-engine:app:run` CLI is unchanged (fixed `:8000`/`:3000`, best-effort readiness).

The Studio (trusted-local preview mode only) also exposes bounded lifecycle controls over its stdlib HTTP
server; the build-only Studio returns 404 for all of them:

```text
GET  /api/preview          -> current preview state (bounded, secret-free)
POST /api/preview/stop     -> stop the running preview  -> {"status":"stopped"}
POST /api/preview/restart  -> re-preview the last built repo (idle no-op before any build)
```

`StudioPreviewManager` remembers a single last repo and owns a single session; `stop` is idempotent and
`restart` re-previews the last build. The Studio page renders matching Stop/Restart controls that call these
routes and re-render the preview state with `textContent` only (no response-HTML injection).

**Live status (R-424).** `GET /api/preview` is liveness-aware: `LocalAppSession.is_alive()` is true only when
every owned background process is still running, and `StudioPreviewManager.status()` stops/forgets a preview
whose processes have exited on their own and reports a bounded "stopped" state instead of a stale "ready". The
Studio page polls `GET /api/preview` (every 5s) while a preview is running and re-renders on change; it never
reloads the embedded iframe when the preview URL is unchanged.

### Build history and re-preview (R-423)

The Studio keeps a **bounded, in-session, secret-free history** of recent builds (`StudioBuildHistory`, an
in-memory ring capped at the 10 most recent; no persistence, service, or infrastructure). Each successful
build is recorded in both Studio modes. Two routes surface it (both return 404 when their handler is not
wired):

```text
GET  /api/history          -> recent builds, newest-first (id, prompt, name, entities, file_count,
                              target_dir, commit_sha, created_at) — bounded and secret-free
POST /api/history/preview  -> {"id": "..."}  re-preview a recorded build's already-materialized repo
                              through the R-422 manager (trusted-local preview mode only)
```

`GET /api/history` is available in both build-only and preview modes; `POST /api/history/preview` (which
executes generated code) is wired only in trusted-local preview mode. The Studio page shows a **Recent
builds** list that loads on start, refreshes after each build, and re-previews a build on click, rendered
with `textContent` only.

**Per-build repo actions (R-425).** Each recent build also offers **Copy path** and **Open folder**:

```text
(client-side)              copy the recorded repo target_dir to the clipboard (both Studio modes)
POST /api/history/open  -> {"id": "..."}  open the recorded repo directory in the OS file browser
                           (macOS `open` / Windows `os.startfile` / else `xdg-open`, best-effort),
                           trusted-local preview mode only
```

Copy path is purely client-side (no server call) and works in both modes. Open folder launches a local file
browser via `_open_path` and returns a bounded, secret-free `opened`/`error` status; it is wired only in
trusted-local preview mode (build-only Studio returns 404) and, like all local execution, never runs during
`task verify` (the opener is injected/stubbed in tests).

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
