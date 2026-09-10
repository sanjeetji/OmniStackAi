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

WHAT IS ALREADY BUILT (platform generators are Python 3.13 stdlib-only, offline, in services/agent-engine; 944 tests pass)
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
  many-to-many join tables, Field.unique UNIQUE columns, Entity.indexes CREATE [UNIQUE] INDEX
  statements, and Field.validation max_length->VARCHAR(n)/enum->CHECK/numeric min->CHECK(col>=n)/
  max->CHECK(col<=n)), honest seed data
  (migrations/0002_seed.sql via render_postgres_seed from
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
  Top-level boolean/enum collection filters are end-to-end: generated Next.js controls use an
  allowlisted hook filters map, reset pagination, flatten exact field/value pairs into the R-282 backend
  query parameters, and deep-link valid filter state; server-returned rows are rendered directly (R-283).
  FK-scoped LIST_BY endpoints now accept the same allowlisted boolean/enum filters across generated
  FastAPI, Go, and OpenAPI (R-284): relation scope remains mandatory, list/count share predicates, all
  values are parameterized, and Go preserves relation ID as $1 before search/filter/pagination args.
  Generated Next.js subcollection hooks and both parent collection/detail views now consume those
  scoped filters (R-285): typed IR-allowlisted filter state is flattened into LIST_BY query params,
  filter changes reset pagination, boolean/enum controls and filtered-empty recovery are rendered in
  both views, and server-returned child rows are never page-locally re-filtered.
  Every generated LIST_BY hook is now race-safe (R-286): superseded requests are aborted before
  missing-parent handling, the internal signal cannot be overridden by caller options, aborted
  completions cannot mutate newer state, and effect cleanup cancels in-flight work. The `use<Entity>`
  single-record detail hook is likewise race-safe (R-287), and the generated mutation hooks
  (useCreate/useUpdate/useDelete) dedupe concurrent in-flight submits (R-288) — so ALL generated request
  paths (LIST, LIST_BY, detail GET, and create/update/delete) resist duplicate/racing requests. Generated
  search is consistent too: the subcollection search is now live + debounced (R-289), matching the
  top-level collection search. Collection deletes are optimistic (R-290): single/batch removals hide rows
  instantly and roll back with an error toast on failure, reconciled on refetch; subcollection child
  deletes are optimistic too (R-291). Every data-loading state renders layout-preserving skeleton
  placeholders instead of plain "Loading..." text (R-292: collection table, subcollection lists, detail
  main; R-293: form edit-mode initial load + detail record-selector list). The generated app also ships
  the Next.js App Router resilience quartet (R-294): app/error.tsx + app/global-error.tsx error boundaries
  with reset(), app/not-found.tsx 404, and app/loading.tsx route-level Suspense skeleton fallback. And
  every data-fetch error state now offers recovery: the collection list, the detail main, and both
  subcollection lists each render a "Retry" button that calls the relevant refetch() (R-280 + R-295).
  The generated Next.js web application is also fully accessible (R-296): semantic `role="alert"` and
  `aria-live="assertive"` on error banners, `aria-label="Search <plural>"` on collection/subcollection search
  inputs, `aria-sort="ascending|descending|none"` on sortable table headers, `<nav aria-label="Pagination">`
  and labelled Previous/Next buttons for page controls, and `role="status"` on empty states.
  Collection screens also provide power-user keyboard navigation and shortcuts (R-297): pressing `/`
  outside input/textarea/select/contenteditable focuses the collection search input and prevents character
  insertion, pressing `Escape` in search clears active search state and blurs, and pressing `Escape` outside
  text inputs clears all active filters.
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
proof, R-248 IR fixtures -> honest migrations/0002_seed.sql, R-249 schema indexes + unique constraints,
R-250 field validation (max_length/enum) -> schema + Pydantic, R-251 field validation for Go
(go-playground validate:"..." struct tags) + numeric min/max -> schema CHECK + Pydantic ge/le, R-252
enforce the Go validate tags at request time (validator/v10 + validate.go + validateStruct -> 400).
R-253 PATCH handlers, R-254 structured JSON validation error bodies, R-255 limit/offset pagination,
R-256 PUT handlers, R-257 typed Next.js API client (lib/api.ts) + backend CORS, R-258 sort/order,
R-259 X-Total-Count header, R-260 OpenAPI 3.1 spec, R-261 q keyword search, R-262 React hooks
(lib/hooks.ts). Then the interactive Next.js web-app build-out: R-263 interactive screen components,
R-264 field-level validation feedback, R-265 subcollection master-detail, R-266 edit mode, R-267 FK
selectors, R-268 subcollection delete, R-269 page-size + empty-state CTAs, R-270 bulk delete, R-271 CSV
export, R-272 detail deep-linking, R-273 nav shell/navbar, R-274 form CTAs, R-275 dashboard, R-276
record selector + prev/next, R-277 dirty-state guard, R-278 boolean/enum filters, R-279 toast system,
R-280 deep-linked collection list state (URL sync of sort/order/q/page/pageSize) + debounced,
race-safe search (AbortController refetch), R-281 pagination/sort/search controls on the subcollection
master-detail lists (driven by the existing useList<Child>By<Parent> hook), R-282 server-side
boolean/enum field filters on top-level LIST endpoints (?field= across Go + FastAPI + OpenAPI, whitelisted
and parameterized like sort/search), R-283 generated Next.js collection controls wired to those server
filters (allowlisted hook state, pagination reset, URL sync, no page-local filtering), R-284 server-side
boolean/enum field filters on FK-scoped LIST_BY endpoints (FastAPI + Go + OpenAPI; relation ID first,
parameterized search/filter values; shared list/count predicates), R-285 generated Next.js subcollection
controls/hooks wired to scoped server filters (both parent views; no page-local filtering), R-286
race-safe generated LIST_BY hooks (AbortController; stale state writes blocked), R-287 race-safe
generated `use<Entity>` detail GET hooks (AbortController; internal signal after caller options; stale
success/AbortError/loading writes blocked; id-change/unmount cleanup aborts), R-288 deduplicated
generated mutation hooks (useCreate/useUpdate/useDelete concurrent submission guard), R-289 live debounced
subcollection search, R-290 optimistic collection delete, R-291 optimistic subcollection child delete,
R-292 generated collection/subcollection/detail loading skeleton placeholders, R-293 form edit-mode and
record-selector loading skeletons, R-294 App Router resilience quartet (error.tsx, global-error.tsx,
not-found.tsx, loading.tsx), R-295 consistent error retry across all generated data-fetching views,
R-296 generated web app accessibility pass (semantic ARIA roles, live regions, table sort state, and
accessible search/pagination controls), R-297 collection keyboard navigation & shortcuts ('/' to focus,
'Escape' to clear), R-298 detail screen keyboard navigation & shortcuts (ArrowLeft/Right, 'e' edit, Escape),
R-299 form screen keyboard shortcuts (Cmd+Enter, Cmd+S, Escape), R-300 form input constraints, native
HTML validation & live character counters, and R-301 search input clear affordances & form screen first-field
autofocus. Do NOT overwrite backlog rows; continue from R-302.
NOTE: the execution tracker was reconciled on 2026-09-09 (R-253..R-279 rows had drifted and were
backfilled); keep it current going forward. It now has 301 unique rows: 90 Done, 1 Deferred, 210 Not
Started; MVP is 90/196 (45.9%). The earlier reported R-251 MVP baseline of 145 was one low—direct recount
is 146, and R-252..R-301 added 50 rows. The summary above is current through R-301; Git, state files,
tests, and CHANGELOG remain the executable/detail sources of truth.

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

WHAT TO DO NEXT (pick with the founder; all continue the builder), continue from R-300
- Offline-doable now: continue the generated Next.js web application robustness/UX increments —
  e.g. optimistic create/update reflection in the collection list, or a reusable EmptyState/error component to
  DRY the screens, or form field character counters and live validation hints.
  Reuse the proven patterns, preserve public hook signatures, and add focused generation tests first.
- Now unblocked (a Groq API key is available): live-verify the model fabric end-to-end with Groq through
  the Balanced gateway (real cloud inference + cost accounting). Set GROQ_API_KEY in the gitignored .env
  (NEVER in chat/commits/source) and run `task agent-engine:gateway:run` with OMNISTACKAI_CLOUD_PROVIDER=
  groq; note this AI sandbox may block outbound calls to api.groq.com, so it may need a real machine.
- Needs a network/cloud environment: run a Tier-0 preview end-to-end (materialize -> pnpm dev);
  live-verify a cloud LLM provider (set its key + OMNISTACKAI_CLOUD_PROVIDER=<id>, run
  `task agent-engine:gateway:run`) or a deploy/sandbox driver (OMNISTACKAI_TIER=2 + key); and the
  deferred R-224 Next.js console upgrade (npm registry access).
- Deferred by governance: native mobile (R-010 etc.) until web/backend stability.

Begin by reading the files above and running the start protocol, then propose the next Tracker ID
(R-300) with its task contract before writing code. Commit to main.
```


