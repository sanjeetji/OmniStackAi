# Resume prompt (paste into any AI coding tool)

Copy everything in the block below into a fresh AI session to continue building OmniStackAI. It tells
the tool what we are building, where we are, the rules, and what to do next — and points it at the
repo's own state files, which are the real source of truth.

---

```text
You are continuing development of OmniStackAI, an AI software-engineering platform (an "Emergent-class"
builder: describe an app -> it generates a real, owned multi-platform app with verifiable engineering).

REPOSITORY
- GitHub: https://github.com/sanjeetji/OmniStackAi.git
- Local:  /Users/sanjeet_kumar/Documents/Projects/Startup/Omnistackai
- Work on and commit DIRECTLY to branch `main` (it is the ONLY branch and the GitHub default; it
  contains all work). The founder consolidated onto main and deleted per-task branches — do NOT create
  new ai/<task-id> branches; keep the Tracker-ID discipline (tag commits [R-###]). Git identity:
  user.name "sanjeetji", user.email "sk698166@gmail.com" (already the sole author on every commit).

WHAT WE ARE BUILDING (differentiators, from the brief)
One Application IR -> many targets (web/mobile/backend); verifiable engineering (compile/test/security
gates); portable source the customer owns in Git; a local + cloud model fabric optimizing cost per
VERIFIED change; native mobile later. Closest competitor: Emergent.

SOURCE OF TRUTH — READ THESE FIRST, IN ORDER (do not trust this prompt over them; they are current):
1. AGENTS.md                      (portable working agreement / rules)
2. docs/START_HERE.md
3. .ai/PROJECT_STATE.yaml         (current phase, last task, next action)
4. .ai/CURRENT_TASK.yaml          (last task contract + completion evidence)
5. .ai/HANDOFF.md                 (exact status + next action + how to resume)
6. .ai/WORK_LOG.md                (chronological history)
7. R_&_D/OmniStackAI_Implementation_Brief_v6.md  (normative architecture; Sections 77 & 92 are
   NON-NEGOTIABLE; also follow 25, 26, 27, 74, 75, 83, 84, 85, 91)
8. R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx, sheet `Phase_Roadmap` (task rows + status)
9. docs/MODEL_PROVIDER.md, docs/APPLICATION_IR.md, docs/CODEGEN.md, docs/GIT_SERVICE.md

START PROTOCOL
- Run: `task doctor` (needs pnpm+ripgrep; restore via corepack/brew if missing), `task verify`,
  `task ai:status`, `task ai:handoff`. `task verify` must stay green and network-independent.
- Confirm git branch/HEAD/clean tree. Then restate: phase, next Tracker ID, objective, blast radius.

WHAT IS ALREADY BUILT (all Python 3.13 stdlib-only, offline, in services/agent-engine; 316 tests pass)
- Model fabric: ModelProvider contract + registry; local Ollama adapter (runs any installed model via
  OMNISTACKAI_OLLAMA_MODEL); Balanced ModelGateway (deterministic escalation ladder, no silent cloud
  fallback, context-budget guard); key-activated cloud catalog — Anthropic/OpenAI/Google-Gemini/
  OpenRouter/Groq/DeepSeek/xAI(Grok)/Mistral/Together/Fireworks PLUS bring-your-own custom
  OpenAI-compatible endpoints (OMNISTACKAI_CUSTOM_PROVIDERS, no code change); spec-driven so each flows
  through registration/selection/fallback/overview/pricing; no keys set -> zero cloud calls; true SSE
  streaming; usage/cost accounting (Decimal price book); env-driven cross-provider fallback + circuit
  breaker. Run it live: `task agent-engine:gateway:run` (routes to local Ollama qwen).
- BUILDER (the product): Application IR (framework-neutral spec) + semantic validator/canonical
  normalizer + example fixtures -> FrameworkAdapter contract + in-memory GeneratedProject ->
  NextjsWebAdapter (Next.js) + PythonBackendAdapter (FastAPI) + GoBackendAdapter (Go net/http) ->
  project assembler (one IR -> a full customer monorepo: apps/web + services/api) -> git_service
  (materialize into a customer-owned Git repo with one commit). The backends also emit a real
  PostgreSQL schema (migrations/0001_init.sql via render_postgres_schema: typed columns, PK, FKs,
  many-to-many join tables), honest seed data (migrations/0002_seed.sql via render_postgres_seed from
  explicit IR Fixtures — authored INSERTs, never fabricated, emitted only when fixtures present), a
  data-access layer (Python app/db.py + app/repositories/<entity>.py;
  Go internal/store/<entity>.go) reading/writing those tables with parameterized SQL, AND wired route
  handlers (route_wiring.py: the unambiguous CRUD endpoints call the repositories — Python routers await
  them, Go handlers are methods on a Handlers struct with *sql.DB, main opens store.Open(); ambiguous
  routes stay 501), when the IR has entities + database_strategy=postgres. Auth guards (auth_guard.py):
  each auth=true endpoint enforces a bearer-credential guard (Python app/auth.py + Depends(require_auth);
  Go internal/handlers/auth.go + RequireAuth middleware) that VERIFIES a JWT (HS256) with JWT_SECRET
  from the env (Python PyJWT, Go golang-jwt; 401 invalid / 500 unset; secret never hard-coded), plus
  per-endpoint role enforcement (IR ApiEndpoint.required_roles -> Python require_roles / Go RequireRoles,
  403 when the token's roles claim lacks a required role). Sub-collection routes
  (GET /parents/{id}/children) wire to a parent-scoped filtered list when the child has exactly one FK
  relation (Python list_<table>_by_<rel>, Go List<Entity>By<Rel>); ambiguous routes stay 501.
  TRI-TARGET proven from ONE IR; all offline/deterministic (emit
  files, assert contents; no install/build/DB).
- RUNTIME/DEPLOY layer (Brief 15/51/75): RuntimeProvider/DeploymentProvider contracts;
  LocalRuntimeProvider (Tier 0/1, no keys) yields deterministic per-target preview plans + opt-in
  run_preview; key-activated cloud sandbox (e2b/daytona/fly-machines) + deploy (vercel/netlify/render/
  fly) drivers that emit real command plans (key read from env, never in a plan) + opt-in run_deploy.
  A SINGLE `OMNISTACKAI_TIER` knob (0/1 local, 2 cloud) resolves the active providers;
  `task platform:status` shows the active tier + which keys are present.
- EDIT LOOP (omnistackai_agent_engine.edit): plan_edit(old_ir, new_ir) assembles both IRs and diffs
  them into a ProjectDiff (added/modified/deleted); apply_diff writes only the delta inside a path-safe
  target; commit_edit records it as a new commit on the owned repo (via git_service.commit_all). The
  richer review surface adds diff_report(old, new), which emits hunk-level unified diffs and detects
  exact-content renames, plus unified_patch(old, new), which returns one deterministic git-style patch.
  The builder is generate -> verify -> edit -> commit, all offline.
- VERIFIABLE ENGINEERING (Brief 26/27/77): omnistackai_agent_engine.verify — a deterministic
  per-target verify plan (gate ladder install/typecheck/lint/test/build) the generated code is
  engineered to pass, classified by gate kind; verify_plans_for_ir maps one IR to the plans for its
  assembled monorepo apps (apps/web, services/api); opt-in run_verify executor (fail-fast report).
  `task agent-engine:verify-plan -- <target>` prints the ladder. Nothing installed/built/run.
- PROJECT PLAN (omnistackai_agent_engine.projectplan): build_project_plan(ir) composes the assembler
  layout + preview plans + verify gate ladders (+ optional deploy plan when a key-activated provider is
  passed) into one per-app ProjectPlan; to_dict is JSON-serializable + secret-free, render() summarizes,
  `task plan:show -- <example>` prints it. Data-only (nothing run/verified/deployed).
- Console: apps/console-web is a dependency-free static console + Python snapshot exporter. It visibly
  renders the real R-245 two-app project plan (preview + verify ladders), an R-246 five-file hunk-level
  patch produced from actual IR assemblies, and the model/cost/routing overview; `task console:serve`.

ID SCHEME (important): the workbook backlog already owns R-010..R-219 (planned agents/features). New
work uses IDs AFTER R-219: R-220 streaming, R-221 fallback, R-222 console, R-223 env-fallback,
R-224 Next.js console upgrade (DEFERRED), R-225 IR, R-226 adapter contract, R-227 Next.js adapter,
R-228 git service, R-229 Python/FastAPI backend adapter, R-230 Go backend adapter, R-231 IR
validator/normalizer + fixtures, R-232 project assembler, R-233 runtime/deploy provider layer,
R-234 tier switch + cloud provider drivers, R-235 verifiable-engineering verify plans, R-236 expanded
model-provider catalog + custom providers, R-237 IR-diff -> patch-apply edit loop, R-238
PostgreSQL schema/migration from the IR, R-239 data-access/repository layer, R-240 route wiring
(handlers call the repositories), R-241 authentication guards (enforce the IR auth flag), R-242 real JWT verification (HS256), R-243
per-endpoint role enforcement (IR required_roles), R-244 sub-collection route wiring, R-245 combined
project-plan surface, R-246 hunk-level edit diffs + rename detection, R-247 static-console builder
proof, R-248 IR fixtures -> honest migrations/0002_seed.sql. Do NOT overwrite backlog rows; continue
from R-249.

ENVIRONMENT LIMITS discovered here
- npm front-end bundlers (Next.js SWC, Vite/esbuild) FAIL to install (native-binary downloads time
  out). So building/previewing generated apps and the Next.js console upgrade (R-224) need a
  network/cloud-capable environment. No cloud model keys are set (local Ollama only).

RULES (non-negotiable)
- One Tracker ID at a time; record a Standard AI Task Contract in .ai/CURRENT_TASK.yaml and
  .ai/tasks/<id>.md BEFORE coding. Make the smallest change. Deterministic tools before model calls.
- For <L3 work use local Ollama under Balanced routing; never silently use cloud if Ollama is down.
- Never put secrets in prompts/logs/source/state/tests/commits. Product code uses the platform
  provider interfaces, not vendor SDKs. Keep `task verify` network-independent (live checks are
  separate opt-in gates). Do NOT change PostgreSQL, add top-level folders, add infra beyond the
  current stage, or start native mobile/device-cloud before web/backend stability WITHOUT founder
  approval. STOP AND ASK before: any paid cloud service, DB engine change, new top-level folder,
  new infra, native/device work, or a materially different architecture decision.
- When updating the tracker .xlsx, insert the new row above the completed block, shift rows down,
  extend the Dashboard/table/conditional-formatting/data-validation ranges, and verify no ID is lost
  and the chart/styles stay intact (see prior tracker edits / .ai/WORK_LOG.md for the exact method).
- Definition of Done (Brief 27): requirement + acceptance recorded; impact plan; affected targets
  compile/tests pass with REAL command output; security gates; cost/model trace; commit tagged with
  the Tracker ID; update .ai/CURRENT_TASK.yaml, .ai/PROJECT_STATE.yaml, .ai/WORK_LOG.md,
  .ai/HANDOFF.md, PROJECT_STATE.md, CHANGELOG.md, and the tracker row. Push the branch; verify remote
  SHA == local HEAD. Never claim unexecuted tests.

WHAT TO DO NEXT (pick with the founder; all continue the builder), continue from R-249
- Offline-doable now: deepen IR + adapter coverage — entity indexes / unique constraints flowing into
  the schema (schema_sql), and richer field validation (length/enum) into models + schema; or render
  the R-248 seed rows in the static-console builder proof. Remaining 501s are only genuinely-ambiguous
  endpoints (multi-param, no schema, >1 FK).
- Needs a network/cloud environment: run a Tier-0 preview end-to-end (materialize -> pnpm dev);
  live-verify a cloud LLM provider (set its key + OMNISTACKAI_CLOUD_PROVIDER=<id>, run
  `task agent-engine:gateway:run`) or a deploy/sandbox driver (OMNISTACKAI_TIER=2 + key); and the
  deferred R-224 Next.js console upgrade (npm registry access).
- Deferred by governance: native mobile (R-010 etc.) until web/backend stability.

Begin by reading the files above and running the start protocol, then propose the next Tracker ID
(R-249) with its task contract before writing code. Commit to main.
```
