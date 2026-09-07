# Current Handoff

Task ID: R-230
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `e2515a8f1b0314ec287a02cdaf25e72a17b9da3f`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-230) — tri-target from one IR

- `GoBackendAdapter` (`codegen/backend_go.py`, target `backend-go`): entities → Go structs (json tags,
  optional pointers); IR APIs → Go 1.22 method+pattern routes grouped by resource
  (`internal/handlers/<segment>.go`, `r.PathValue` params, 501 scaffolds); `main.go` registers routes
  + `GET /healthz` and serves; `go.mod` (`go 1.22`); README/.gitignore/.env.example. Generated Go and
  the platform side are standard-library only.
- **One Application IR now emits three targets:** a 12-file Next.js web app (R-227), an 11-file FastAPI
  backend (R-229), and an 8-file Go net/http service (R-230). Any can be materialized into a
  customer-owned Git repo (R-228).

## Verification

- `task verify` — pass (154 agent-engine tests; 7 new). `task agent-engine:lint`, `task security:quick` — pass.
- Compose unchanged; offline `task bootstrap` unchanged.
- Tracker — R-230 (Product) at `Phase_Roadmap!A9:M9`; MVP total 125, Done 19; chart/styles intact.

## What exists now (product)

- **Model fabric** (R-005..R-223): gateway, local Ollama + 5 cloud adapters (key-activated), streaming,
  fallback + circuit breaker, usage/cost accounting, static console + snapshot exporter.
- **Builder** (R-225..R-230): Application IR → adapter contract → Next.js + FastAPI + Go adapters
  (multi-target) → Git service (materialize into a customer-owned repo).

## Next action (resume here)

Pick one and continue on `main`:
1. **R-231 = IR validator/normalizer + example IR fixtures** — offline-doable now; hardens the IR and
   gives realistic sample specs to drive the adapters.
2. **Sandbox/runtime provider + instant browser preview + deploy** (Brief §15/§51) — needs a
   cloud/network-capable environment (this sandbox can't install front-end toolchains or run apps).
3. **R-224 Next.js console upgrade** — needs npm registry access.
Native mobile / device-cloud stays deferred per Brief §25/§91 until web/backend stability.

## Next command

`task ai:status`
