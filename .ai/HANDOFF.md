# Current Handoff

Task ID: R-231
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `f2027a6a7bc6bae37b14226838519c86657f8ff3`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-231)

- `application_ir.validate_ir(ir)` — semantic `Issue`s: unknown API schema reference = error;
  web/admin/mobile strategy vs platform mismatch = warning; `has_errors()` helper. Construction checks
  in `ir.py` are unchanged (this is additive).
- `application_ir.normalize_ir(ir)` — canonical IR (platforms in enum order; roles/entities/apis/
  screens/acceptance sorted; entity field order preserved); idempotent and lossless through `to_dict`.
- `application_ir.example_ir(name)` / `EXAMPLES` — `rideshare-favourites`, `minimal-blog`; both
  validate clean and generate via all three adapters.

## Verification

- `task verify` — pass (163 agent-engine tests; 9 new). `task agent-engine:lint`, `task security:quick` — pass.
- Compose unchanged; offline `task bootstrap` unchanged.
- Tracker — R-231 (Product) at `Phase_Roadmap!A9:M9`; MVP total 126, Done 20; chart/styles intact.

## What exists now (product) — near-term offline builder pieces are COMPLETE

- **Model fabric** (R-005..R-223): gateway, local Ollama + 5 cloud adapters, streaming, fallback +
  circuit breaker, usage/cost accounting, static console + snapshot exporter.
- **Builder** (R-225..R-231): Application IR (+ validator/normalizer/fixtures) → adapter contract →
  Next.js + FastAPI + Go adapters (tri-target from one IR) → Git service (materialize to an owned repo).

## Next action (needs a cloud/network-capable environment)

The remaining builder steps require real runtime/infra and cannot be done in this offline sandbox:
1. **Sandbox/runtime provider + instant browser preview** of a generated app (Brief §15/§51), then
   **deploy**. This is the next big UX leap and the point where generated apps actually run.
2. **R-224 Next.js console upgrade** — needs npm registry access.
Native mobile / device-cloud stays deferred per Brief §25/§91 until web/backend stability.

To continue offline instead, options include: an admin (Next.js) adapter, a React Native/Expo web
adapter, richer IR (flows/integrations/build_matrix), or a customer-repo scaffolder that assembles
multiple targets into one monorepo via the Git service.

## Next command

`task ai:status`
