# Current Handoff

Task ID: R-232
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `cf28cb0f46ae1f66b9f87b59232eceb2a113b508`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-232) — one IR → a complete customer-owned monorepo

- `codegen.assemble_project(ir, registry=None)` assembles one Application IR into a single
  `customer-monorepo` `GeneratedProject`: web (`web_strategy == nextjs`) under `apps/web`, backend
  (`backend_strategy` go/python) under `services/api`, a root `README.md` (lists assembled apps and
  anything not yet assembled — node backend, admin, mobile) and a root `.gitignore`.
- `codegen.default_registry()` preloads the Next.js/Python/Go adapters.
- **End-to-end proven:** one IR → `assemble_project` → `git_service.create_repository` produces a
  24-file customer-owned monorepo repo (`apps/web` Next.js + `services/api` Go) in one commit.

## Verification

- `task verify` — pass (169 agent-engine tests; 6 new). `task agent-engine:lint`, `task security:quick` — pass.
- Compose unchanged; offline `task bootstrap` unchanged.
- Tracker — R-232 (Product) at `Phase_Roadmap!A9:M9`; MVP total 127, Done 21; chart/styles intact.

## Product state — the full offline builder is complete

`prompt/spec → Application IR (+ validate/normalize/fixtures) → adapters (Next.js web + FastAPI + Go)
→ customer-project assembler → Git service → a customer-owned monorepo repository.` Plus the model
fabric (gateway, local + 5 cloud adapters, streaming, fallback+breaker, cost accounting, console).
21 tracker tasks Done; 0 cloud calls; PostgreSQL/Compose untouched.

## Next action — the next leap needs a network/cloud-capable environment

Everything buildable/verifiable offline is done. The next real steps require running generated code:
1. **Sandbox/runtime + instant browser preview** of a generated app (Brief §15/§51), then **deploy**.
   - **Tier 0 (free):** normal internet (this Mac in a real Terminal, or the sandbox network unblocked)
     → install a generated Next.js app and preview locally at `http://127.0.0.1:3000`.
   - **Tier 2 (paid, productized):** a sandbox provider (E2B/Daytona/Fly) + a host (Vercel/Fly) + API
     tokens (as secret references) for hosted preview/deploy.
2. **R-224 Next.js console upgrade** — needs npm registry access.
Native mobile / device-cloud stays deferred per Brief §25/§91 until web/backend stability.

Offline alternatives if preferred: admin (Next.js) adapter, richer IR (flows/integrations/build
matrix), or a Node/Express backend adapter.

## Next command

`task ai:status`
