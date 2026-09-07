# Current Handoff

Task ID: R-233
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `ae11bac55fb9d865dbc6281c26f7df260edc3477`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-233) — runtime/deploy wired for Tier 0-3

- `omnistackai_agent_engine.runtime`: `RuntimeProvider`/`DeploymentProvider` contracts,
  `PreviewPlan`/`DeployPlan`/`Command`. `LocalRuntimeProvider` (Tier 0/1) yields deterministic preview
  plans per target (Next.js :3000, FastAPI :8000, Go :8080) and an opt-in `run_preview` executor.
- Key-activated cloud specs — sandbox (`e2b`/`daytona`/`fly-machines`), deploy
  (`vercel`/`fly`/`render`/`netlify`). `build_runtime_from_env`/`build_deploy_from_env` register local
  always, activate cloud by key presence, default runtime=local / deploy=none, and error on selecting
  a keyless provider. Keys are read from env only — never logged/stored/shown.
- `.env.example` placeholders + tier selectors, `task agent-engine:preview-plan`, `docs/RUNTIME.md`.

## Verification

- `task verify` — pass (181 agent-engine tests; 12 new). `task agent-engine:preview-plan` prints the
  Tier-0 plan. `task agent-engine:lint`, `task security:quick`, `task env:check` — pass.
- Compose unchanged; offline `task bootstrap` unchanged. Nothing run/deployed; no key leak.
- Tracker — R-233 (Runtime) at `Phase_Roadmap!A9:M9`; MVP total 128, Done 22; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric and now the **Tier 0-3 runtime/deploy
layer** (local preview works; cloud sandbox/deploy plug in by key). 22 tracker tasks Done; 0 cloud
calls; PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action

1. **Run a Tier-0 preview end-to-end** (needs a network-capable machine: this Mac in a real Terminal,
   or a Codespace): materialize an example via the assembler, then `cd apps/web && pnpm install &&
   pnpm dev`. `task agent-engine:preview-plan -- <target>` prints the exact commands.
2. **Build a concrete cloud provider driver** (e.g. Vercel deploy or E2B sandbox) once a key is
   provided — the contracts + registry are ready; only the driver call is left.
3. **R-224 Next.js console upgrade** — needs npm registry access.
Native mobile / device-cloud stays deferred per Brief §25/§91 until web/backend stability.

## Next command

`task ai:status`
