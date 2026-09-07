# Verifiable engineering — verify plans (Brief §26/§27/§77)

OmniStackAI's differentiator is not "generate code" — it is **verifiable** engineering: every generated
target ships with the exact ladder of gate commands it is engineered to pass. That ladder is a
**verify plan**: pure, validated data (like the runtime preview/deploy plans), so the platform can
reason about verification offline and run it deterministically when a toolchain is available.

Package: `omnistackai_agent_engine.verify` (standard library only; the planning code runs nothing).

## The gate ladder

Every step is classified by a `VerifyStepKind`, and a plan's steps are always in ladder order:

```
install  →  typecheck  →  lint  →  test  →  build
```

`plan.gates()` reports which kinds a target has. Per target today:

| Target | install | typecheck | lint | test | build |
|--------|---------|-----------|------|------|-------|
| `nextjs-web` / `nextjs-admin` | `pnpm install` | `pnpm exec tsc --noEmit` | `pnpm run lint` | — | `pnpm run build` |
| `backend-python` (FastAPI) | `pip install -r requirements.txt` | `python -m compileall app` | — | `python -m pytest -q` | — |
| `backend-go` (net/http) | — | — | `go vet ./...` | `go test ./...` | `go build ./...` |

A freshly generated project passes its install/typecheck/build gates on generation; the test/lint
gates strengthen as the customer's code grows. The recipe table in `verify/gates.py` is the single
source of truth for "what verifiable means" per target.

## From one IR to the whole monorepo

`verify_plans_for_ir(ir)` returns a verify plan for every app the IR assembles, each bound to its
monorepo directory — consistent with the assembler (`apps/web`, `services/api`). One IR therefore
yields both the code **and** the proof-of-correctness commands for the whole customer repo.

## Use it

```
# see a target's gate ladder:
task agent-engine:verify-plan -- backend-go
task agent-engine:verify-plan -- nextjs-web

# then, on a machine with the toolchain, run it (opt-in — never run by task verify):
#   run_verify(plan) executes the ladder fail-fast and returns a VerifyReport
#   (per-step status + return code; stops at the first non-zero exit).
```

`run_verify` is the only part that executes anything, and it is opt-in. `task verify` (the platform's
own Stage 0 gate) stays network-independent and never installs, builds, or runs generated code.
