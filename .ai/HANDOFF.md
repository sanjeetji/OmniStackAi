# Current Handoff

Task ID: R-245
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `891144d`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-245) — combined project-plan surface

- New `omnistackai_agent_engine.projectplan`: `build_project_plan(ir, *, deploy=None)` composes existing
  builders — `codegen.assembled_targets` (layout), `runtime.LocalRuntimeProvider.preview_plan`,
  `verify.verify_plan`, and an optional `DeploymentProvider.deploy_plan` — into one `ProjectPlan` whose
  `AppPlan` entries pair each assembled app with its preview + verify (+ deploy) plans.
- `ProjectPlan.to_dict()` is JSON-serializable and secret-free; `render()` is a readable summary;
  `task plan:show -- <example>` prints it. A deploy plan appears only when a key-activated provider is
  passed. Pure/data-only — nothing installed, run, verified, or deployed.

## Verification

- `task verify` — pass (291 agent-engine tests; 6 new). `task plan:show -- rideshare-favourites` renders
  apps/web (nextjs-web, preview :3000, gates install/typecheck/lint/build) and services/api (backend-go,
  preview :8080, gates lint/test/build). `to_dict` JSON-serializes with no key value (fake
  `VERCEL_TOKEN`). `task security:quick`, `task env:check` — pass. No network.
- Tracker — R-245 (Runtime) at `Phase_Roadmap!A9:M9`; MVP total 140, Done 34; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans), the **edit loop** (plan_edit → diff → apply → commit), a
**generated PostgreSQL schema** (migrations/0001_init.sql from IR entities + relations), a
**data-access layer** (Python repositories + Go store) over that schema, **wired handlers** (the
unambiguous CRUD endpoints call the repositories), **JWT-verified authentication guards** (each
`auth=true` endpoint verifies an HS256 token with the secret from the env), **per-endpoint role
enforcement** (IR `required_roles` → 403), **sub-collection lists** (`GET /parents/{id}/children` →
FK-filtered list), and a **combined project-plan surface** (`build_project_plan` / `task plan:show` —
preview + verify + optional deploy per app). The builder is generate (web/api with full CRUD + JWT auth
+ roles + DB schema + data access) → plan → verify → edit → commit, fully offline. 34 tracker tasks
Done; 0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-246, pick with the founder — all offline-doable)

1. **Richer edit-loop diff**: rename detection or hunk-level (line) diffs on the R-237 `ProjectDiff`,
   so edits read as focused patches rather than whole-file rewrites.
2. **IR fixtures + seed data**: add an optional fixtures field to the IR so seed rows can be emitted
   honestly (no fabricated values).
3. **Render the R-245 plan in the static console** (apps/console-web) so the plan surface is visible in
   the UI, not just the CLI.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
