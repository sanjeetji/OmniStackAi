# Current Handoff

Task ID: R-234
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `dcb7d2d`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-234) — one tier knob + every provider gets a driver

- `runtime/tier.py`: a single `OMNISTACKAI_TIER` switch (0/1 local, 2 cloud). `resolve_platform()`
  resolves the runtime + deploy providers — tier 0/1 force local runtime and no deploy; tier 2 permits
  the keyed cloud selections (`OMNISTACKAI_RUNTIME_PROVIDER`/`OMNISTACKAI_DEPLOY_PROVIDER`). Wrong-tier
  or keyless selection raises a clear error. `platform_status()`/`format_status()` summarize the tier,
  selection, and which keys are present.
- `runtime/drivers.py`: `CloudDeployProvider` (vercel/netlify/render/fly) emits a `DeployPlan` of the
  provider's official-CLI commands; `CloudSandboxProvider` (e2b/daytona/fly-machines) emits a
  `PreviewPlan` reusing the target's run commands. The key is read from env at run time and NEVER placed
  in a command or logged. `run_deploy(plan)` executes a plan opt-in (never run by verify).
- `.env.example` gained `OMNISTACKAI_TIER=0`; `task platform:status` (scripts/agent-engine.sh +
  Taskfile) prints the active tier and key presence; `docs/RUNTIME.md` documents the knob + drivers.
  The R-233 local layer (contracts, `LocalRuntimeProvider`, `run_preview`) is unchanged underneath.

## Verification

- `task verify` — pass (194 agent-engine tests; 13 new). `task platform:status` demoed tier 0
  (local/none) and tier 2 (e2b/vercel). `task security:quick`, `task env:check` — pass.
- Compose unchanged; offline `task bootstrap` unchanged. Nothing run/deployed; no key in any plan/log.
- Tracker — R-234 (Runtime) at `Phase_Roadmap!A9:M9`; MVP total 129, Done 23; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric and the **Tier 0-3 runtime/deploy
layer** — now with a **single tier switch and a driver for every provider** (local preview works;
cloud sandbox/deploy plug in by key, `task platform:status` shows what's active). 23 tracker tasks
Done; 0 cloud calls; PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action

1. **Run a Tier-0 preview end-to-end** (needs a network-capable machine: this Mac in a real Terminal,
   or a Codespace): materialize an example via the assembler, then `cd apps/web && pnpm install &&
   pnpm dev`. `task agent-engine:preview-plan -- <target>` prints the exact commands.
2. **Live-verify one cloud driver** (e.g. Vercel deploy or E2B sandbox) once a key is provided — the
   drivers now emit the exact command plans; set the key + `OMNISTACKAI_TIER=2`, select the provider,
   and run `run_deploy`/`run_preview` on a machine with that provider's CLI. Confirm the CLI flags.
3. **R-224 Next.js console upgrade** — needs npm registry access.
Native mobile / device-cloud stays deferred per Brief §25/§91 until web/backend stability.

## Next command

`task ai:status`
