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
8. R_&_D/OmniStackAI_OS_Master_Architecture_Specification.md (AI Software Creation OS Master Architecture Spec & 3-Plane Model)
9. R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx, sheet `Phase_Roadmap` (task rows + status)
10. docs/MODEL_PROVIDER.md, docs/APPLICATION_IR.md, docs/CODEGEN.md, docs/GIT_SERVICE.md

START PROTOCOL
- Run: `task doctor` (needs pnpm+ripgrep; restore via corepack/brew if missing), `task verify`,
  `task ai:status`, `task ai:handoff`. `task verify` must stay green and network-independent.
- Confirm git branch/HEAD/clean tree. Then restate: phase, next Tracker ID, objective, blast radius.

WHAT IS ALREADY BUILT (platform generators are Python 3.13 stdlib-only, offline, in services/agent-engine; 3,603 tests pass)
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
  PostgreSQL schema (migrations/0001_init.sql via render_postgres_schema: safely quoted identifiers,
  stable FK dependency ordering, typed columns, PK, FKs,
  many-to-many join tables, Field.unique UNIQUE columns, Entity.indexes CREATE [UNIQUE] INDEX
  statements, and Field.validation max_length->VARCHAR(n)/enum->CHECK/numeric min->CHECK(col>=n)/
  max->CHECK(col<=n)), honest seed data
  (migrations/0002_seed.sql via render_postgres_seed from
  explicit IR Fixtures — authored INSERTs, never fabricated, safely quoted and dependency ordered,
  emitted only when fixtures present), a
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
HTML validation & live character counters, R-301 search input clear affordances & form screen first-field
autofocus, R-302 collection status badges & detail copy affordances, R-303 overview interactive entity links &
health badge, R-304 accessible modal confirmation dialog (replacing window.confirm()), R-305
accessible keyboard shortcuts help modal & global discovery affordance (`?` hotkey, `<kbd>` cheatsheet),
R-306 accessible breadcrumb navigation component & screen hierarchy (WAI-ARIA 1.2 breadcrumbs),
R-307 accessible EmptyState component & screen zero-state integrations, R-308 collection screen JSON data
export & bulk selection export controls, R-309 accessible reusable Pagination component (components/pagination.tsx),
R-310 accessible reusable Tabs component (components/tabs.tsx), R-311 generated collection table display density toggle,
R-312 accessible reusable Badge component (components/badge.tsx), R-313 collection table column visibility dropdown & selector controls,
R-314 accessible reusable Tooltip component (components/tooltip.tsx), R-315 accessible reusable Card component (components/card.tsx),
R-316 accessible reusable Alert & Notification component (components/alert.tsx), R-317 accessible reusable
Skeleton Loader component (components/skeleton.tsx), R-318 accessible reusable Drawer / Sheet component (components/drawer.tsx), R-319 accessible reusable Avatar component (components/avatar.tsx), R-320 accessible reusable Toggle Switch component (components/toggle.tsx), R-321 accessible reusable Accordion component (components/accordion.tsx), R-322 accessible reusable Dropdown Menu component (components/dropdown-menu.tsx), R-323 accessible reusable Popover component (components/popover.tsx), R-324 Design Tokens & CSS Custom Properties theming engine (styles/tokens.css), R-325 Theme Switcher / Mode Toggle component (components/theme-toggle.tsx), R-326 accessible reusable Dialog / Modal component (components/dialog.tsx), R-327 accessible reusable Form Controls & Input Primitives suite (components/form-controls.tsx), R-328 accessible reusable Date Picker & Calendar component (components/date-picker.tsx), R-329 accessible reusable Data Grid / Table component (components/data-grid.tsx), R-330 accessible reusable Command Palette / Search Menu component (components/command-palette.tsx), R-331 accessible reusable Slider & Range component (components/slider.tsx), R-332 accessible reusable Progress & Spinner component (components/progress.tsx), R-333 accessible reusable Rating & Review component (components/rating.tsx), R-334 accessible reusable Stepper / Multi-step Wizard component (components/stepper.tsx), R-335 accessible reusable File Upload / Dropzone component (components/file-upload.tsx), R-336 accessible reusable Timeline / Activity Feed component (components/timeline.tsx), R-337 accessible futuristic Stat & Metric KPI Card component (components/stat-card.tsx), R-338 accessible reusable Hierarchical Tree View component (components/tree-view.tsx), R-339 accessible futuristic Tag & Chip Input Tokenizer component (components/tag-input.tsx), R-340 accessible futuristic Code Block & Syntax Presentation component (components/code-block.tsx), R-341 accessible futuristic Radial Gauge & Activity Rings component (components/radial-gauge.tsx), R-342 accessible futuristic Segmented Control & Mode Switcher component (components/segmented-control.tsx), R-343 accessible futuristic Carousel & Slider Showcase component (components/carousel.tsx), R-344 accessible futuristic Resizable Panels & Splitter component (components/resizable.tsx), R-345 accessible futuristic Color Picker & Palette Swatch component (components/color-picker.tsx), R-346 accessible futuristic PIN & OTP Code Input component (components/pin-input.tsx), R-347 Speed Dial & Floating Action Button component (components/speed-dial.tsx), R-348 Accessible Futuristic Reusable Context Menu Suite (components/context-menu.tsx), R-349 Accessible Futuristic Reusable Hover Card Suite (components/hover-card.tsx), R-350 Accessible Futuristic Reusable Scroll Area Suite (components/scroll-area.tsx), R-351 Accessible Futuristic Reusable Collapsible Component (components/collapsible.tsx), R-310 accessible reusable Tabs component (components/tabs.tsx), R-311 generated collection table display density toggle,
R-312 accessible reusable Badge component (components/badge.tsx), R-313 collection table column visibility dropdown & selector controls,
R-314 accessible reusable Tooltip component (components/tooltip.tsx), R-315 accessible reusable Card component (components/card.tsx),
R-316 accessible reusable Alert & Notification component (components/alert.tsx), R-317 accessible reusable
Skeleton Loader component (components/skeleton.tsx), R-318 accessible reusable Drawer / Sheet component (components/drawer.tsx), R-319 accessible reusable Avatar component (components/avatar.tsx), R-320 accessible reusable Toggle Switch component (components/toggle.tsx), R-321 accessible reusable Accordion component (components/accordion.tsx), R-322 accessible reusable Dropdown Menu component (components/dropdown-menu.tsx), R-323 accessible reusable Popover component (components/popover.tsx), R-324 Design Tokens & CSS Custom Properties theming engine (styles/tokens.css), R-325 Theme Switcher / Mode Toggle component (components/theme-toggle.tsx), R-326 accessible reusable Dialog / Modal component (components/dialog.tsx), R-327 accessible reusable Form Controls & Input Primitives suite (components/form-controls.tsx), R-328 accessible reusable Date Picker & Calendar component (components/date-picker.tsx), R-329 accessible reusable Data Grid / Table component (components/data-grid.tsx), R-330 accessible reusable Command Palette / Search Menu component (components/command-palette.tsx), R-331 accessible reusable Slider & Range component (components/slider.tsx), R-332 accessible reusable Progress & Spinner component (components/progress.tsx), R-333 accessible reusable Rating & Review component (components/rating.tsx), R-334 accessible reusable Stepper / Multi-step Wizard component (components/stepper.tsx), R-335 accessible reusable File Upload / Dropzone component (components/file-upload.tsx), R-336 accessible reusable Timeline / Activity Feed component (components/timeline.tsx), R-337 accessible futuristic Stat & Metric KPI Card component (components/stat-card.tsx), R-338 accessible reusable Hierarchical Tree View component (components/tree-view.tsx), R-339 accessible futuristic Tag & Chip Input Tokenizer component (components/tag-input.tsx), R-340 accessible futuristic Code Block & Syntax Presentation component (components/code-block.tsx), R-341 accessible futuristic Radial Gauge & Activity Rings component (components/radial-gauge.tsx), R-342 accessible futuristic Segmented Control & Mode Switcher component (components/segmented-control.tsx), R-343 accessible futuristic Carousel & Slider Showcase component (components/carousel.tsx), R-344 accessible futuristic Resizable Panels & Splitter component (components/resizable.tsx), R-345 accessible futuristic Color Picker & Palette Swatch component (components/color-picker.tsx), R-346 accessible futuristic PIN & OTP Code Input component (components/pin-input.tsx), R-347 Speed Dial & Floating Action Button component (components/speed-dial.tsx), R-348 Accessible Futuristic Reusable Context Menu Suite (components/context-menu.tsx), R-349 Accessible Futuristic Reusable Hover Card Suite (components/hover-card.tsx), R-350 Accessible Futuristic Reusable Scroll Area Suite (components/scroll-area.tsx), R-351 Accessible Futuristic Reusable Collapsible Component (components/collapsible.tsx), R-352 Accessible Futuristic Reusable Aspect Ratio Viewport Container Component (components/aspect-ratio.tsx), R-353 Accessible Futuristic Reusable Separator Component (components/separator.tsx), R-354 Accessible Futuristic Reusable Keyboard Keycap Component (components/kbd.tsx), R-355 Accessible Futuristic Reusable Radio Group Suite (components/radio-group.tsx), R-356 Accessible Futuristic Reusable Checkbox & Checkbox Group Primitive (components/checkbox.tsx), R-357 Accessible Futuristic Reusable Announcement Banner & Callout Suite (components/banner.tsx), and R-358 Accessible Futuristic Reusable Searchable Combobox & Autocomplete Primitive (components/combobox.tsx).
Do NOT overwrite backlog rows; continue from R-457.
NOTE (updated 2026-09-15, R-457): The execution tracker now covers ALL 457 tasks
(246 Done, 1 Deferred, 210 Not Started; MVP 246/352 = 69.9%; overall 246/457 = 53.8%). All completed
tasks through R-457 are formally tracked in the Phase_Roadmap sheet, so the workbook is the single
authoritative tracker.
Tasks R-359..R-415 are 57 reusable UI-component suites (110 components total), R-416..R-419 are four
front-door bricks, R-420 is generated-SQL hardening, R-421..R-426 are Studio preview lifecycle controls,
R-427..R-429 are generated-app compile fixes, R-430..R-457 are the first twenty-eight differentiating-spine
bricks (Scope Compiler through Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts).
Git, state files (.ai/), CHANGELOG, and docs/PROGRESS.md remain the executable/detail sources of truth.
Current through R-498; `task verify` = 3,738 tests (agent-engine) + the Go control-plane's own suite +
the Next.js console's typecheck/lint/build. R-416 added prompt-to-IR intake, R-417 materialized a generated
owned repo, R-418 added the local chat studio, R-419 added turnkey local run, and R-420 fixed the two
SQL defects found by live execution. R-421 added an explicit `task agent-engine:studio:preview` mode:
one managed generated-app session, API/web readiness, replacement/shutdown cleanup, port-collision
protection, and the actual Next.js URL embedded in a sandboxed iframe. R-422 made the preview allocate
distinct free loopback ports per run (never fixed 3000/8000, so no collision with an existing `app:run`
app or a prior preview) via `start_preview_app`, and added bounded `StudioPreviewManager` status/stop/
restart exposed as `GET /api/preview` + `POST /api/preview/stop|restart` (trusted-local only; build-only
404s). R-423 added a bounded in-session build history (`studio/history.py` `StudioBuildHistory`, secret-free
ring capped at 10) exposed as `GET /api/history`, plus `POST /api/history/preview {id}` to re-preview a
recorded build's already-materialized repo (trusted-local only) and a "Recent builds" list on the page.
R-424 added live preview status: `LocalAppSession.is_alive()` and a liveness-aware
`StudioPreviewManager.status()` that reports a preview whose processes exited as "stopped" (not stale
"ready"), plus page polling of `GET /api/preview` (5s) that re-renders on change without reloading an
unchanged iframe. R-425 added per-build repo actions to the Recent builds list: a client-side "Copy path"
(clipboard write of the recorded repo `target_dir`, both modes) and an "Open folder" action
(`POST /api/history/open {id}` -> OS file browser via `_open_path`, trusted-local only). R-426 added
`StudioBuildHistory.remove(id)` and `POST /api/history/delete {id}` (in-memory only, wired in both modes,
returns the refreshed `{removed, builds}`) plus a per-build "Remove" action on the page. R-427 fixed a
generated-code bug found by running a generated app through the preview: 14 f-string templates in
codegen/nextjs.py emitted single-brace `style={ ... }` (invalid JSX -> web app HTTP 500); fixed to
`style={{{{ ... }}}}` (valid `style={{ ... }}`) with a regression test (test_generated_screen_styles.py)
forbidding single-brace object-literal styles. `task verify` never caught it because it checks generated
code as strings and never compiles the TSX. R-428 then closed that gap for the whole generated app: it
added an OPT-IN typecheck gate (`task agent-engine:web-typecheck` -> builder-demo + `pnpm install
--ignore-scripts` + `tsc --noEmit`; kept OUT of `task verify` so verify stays offline/deterministic) and
fixed every run-blocking bug the gate revealed in codegen/nextjs.py: over-braced arrow handlers in the
f-string search input (`=> {{ ... }}}}` -> `=> { ... }}`), a pdf-viewer raw-string that emitted a literal
`\n` (TS1127), and 24 nested-screen import sites using `../components`/`../lib` -> `@/components`/`@/lib`
(the generated tsconfig `@/*` alias resolves from any depth). A regression test
(test_generated_tsx_compile.py) forbids all three classes across both example IRs. A generated minimal-blog
now serves `/`, `/post_list`, `/post_editor` at HTTP 200 (were 500). R-429 then made a generated app pass
strict `tsc --noEmit` with ZERO errors (was 84 on minimal-blog): fixed 8 type-error classes at
codegen/nextjs.py + the generated tsconfig — G0 `skipLibCheck: true`; G1 context-menu duplicate exports; G2
`displayName` on sub-component aliases (`typeof XInner & { displayName?: string }`); G3 typed compounds for
color-picker/pin-input (`…Base` cast to `typeof …Base & { Sub: … }`); G4 `Omit` the conflicting inherited DOM
attribute in Banner/Carousel/Checkbox/CodeBlock(+CopyButton)Props; G5 element ref annotations
`React.RefObject<T>` (was `<T | null>`); G6 terminal `variant` default `"default"`->`"minimal"`; G7
`SplitDiffRow.isUnchanged`; G8 the `api` object gains the `…WithCount` methods + hooks forward a fresh
`requestParams` with `...options` first. Extended the gate to assert a clean exit -> `task
agent-engine:web-typecheck -- minimal-blog` and `-- rideshare-favourites` both report PASSED (0 errors).
Generated apps are no longer blocked from a production `next build`. `studio:serve` remains build-only.
R-430 then BEGAN THE DIFFERENTIATING SPINE (founder-approved pivot): the Ecosystem Scope Compiler
(intake/scope_compiler.py, Python 3.13 stdlib only, deterministic). `propose_ecosystem(prompt)` classifies a
business prompt against a curated 10-domain DOMAIN_LIBRARY (weighted keywords, stable tie-break) and returns
a framework-neutral ScopeProposal: detected domain (+confidence +matched keywords), actors, the multi-surface
app ecosystem (customer app + merchant/driver/admin portals), Complete/Customer-only/Custom build-scope
options, and <=3 materiality questions (single-app `custom-application` fallback on no match). Pure/offline
(0 model/network), so it runs under `task verify`. See it: `task agent-engine:scope:propose -- "Create a food
delivery app ..."` -> food-delivery -> Customer Ordering App + Merchant Portal + Courier Dispatch App +
Super-Admin Dashboard. Competitors turn that prompt into one customer screen; this proposes the whole
platform. R-431 then MADE IT REAL (intake/ecosystem.py): it maps each proposed AppSurface to a
validate_ir-clean ApplicationIR (a curated per-domain DOMAIN_ENTITIES model + a deterministic CRUD deriver
that WIRES to real repositories), and `build_ecosystem` materializes the chosen build scope as MULTIPLE owned
Git repos from one prompt (reusing build_app_from_ir). `task agent-engine:ecosystem:plan -- "<prompt>"` shows
the per-app IRs (deterministic, writes nothing); `task agent-engine:ecosystem:build -- "<prompt>"` writes one
owned repo per surface. The original R-431 food-delivery proof built 4 apps, each with 3 entities / 17 APIs /
6 screens; all four pass `tsc --noEmit` clean (that proof exposed + fixed 4 generator compile bugs
in codegen/nextjs.py for FK-editor / multi-subcollection / filterable-child shapes). All 90 extended tasks
(R-359..R-448) are now formally recorded in Phase_Roadmap (added 2026-09-14, task compilation audit).
R-432 added the third spine brick: an explicit local-model refinement layer for prompts
that R-430 classifies as `custom-application`. Curated domains bypass the provider; unknown-domain output is
strictly bounded/validated (including credential-field and FK-collision guards) and then flows through the
same deterministic R-431 planner. `task agent-engine:ecosystem:refine -- "Build apiary operations software
…"` produced Beekeeper Dashboard + Admin Panel with 4 entities, 23 wired APIs, and 8 screens per app; no
cloud fallback. Verification remains offline and makes 0 real model calls.
R-433 added the fourth spine brick: all ten curated domains now have deterministic readable/writable entity
policies per surface; refined domains use conservative name matching with a safe complete-model fallback.
Relation dependencies stay read-only, each IR declares only its actor role, only writable entities receive
editors/mutations, and each mutation requires that role. Food delivery now produces materially different
Customer/Merchant/Courier/Admin IRs; the plan JSON exposes roles, permissions, and writable entities.
R-434 added the fifth spine brick and first Solution Pack foundation: frozen version-1.0.0 descriptors for
the existing verified `minimal-blog` and `rideshare-favourites` Application IR examples. Each descriptor
pins exact domains/capabilities, canonical IR SHA-256, and assembled targets; registry construction fails
closed on malformed, duplicate, missing, invalid, or drifted definitions and verifies target ladders.
Selection is deterministic, requires an exact domain plus capability subset, chooses the newest compatible
version, and returns no match rather than fabricating a fallback. `task agent-engine:solution-packs` lists or
selects the JSON registry with no build, model, network, database, or live execution.
R-435 added the sixth spine brick: registry selection now supports required framework targets and every
EcosystemPlan derives those targets from its already-planned surface IR project plans. A frozen,
JSON-safe recommendation records the canonical query and only selected pack id/version/digest/targets or
explicit `no-exact-match`; it never applies the pack. Blog-CMS Next.js/Python recommends
`minimal-blog@1.0.0`. Today's rideshare Next.js/Python plan honestly reports no match because the registered
rideshare baseline is Go-backed. The CLI and plan JSON expose this decision; generated output is unchanged.
R-436 added the seventh spine brick: an immutable, stdlib-only `SolutionPackManifest` can be created only
from a selected exact recommendation and pins its pack id/version/canonical IR digest plus the exact query.
At most 32 frozen changes declare configuration or AI-delta source, add/update/remove operation, one of six
semantic areas, an area-compatible semantic target, bounded summary, and 1-8 acceptance criteria. Changes
are canonical by unique ID; canonical JSON is byte-stable. Strict parsing rejects unknown/missing keys,
malformed/unbounded values, controls, duplicates, noncanonical order, and registry/query/version/digest
drift. The schema has no executable path/patch/source/command/model-output/secret field; it applies nothing,
mutates no IR, and makes no model call.
R-437 added the eighth spine brick: current manifest schema 1.1 adds explicit bounded `desired_text` only for
configuration/update of `project:name` or `project:description`; legacy R-436 schema 1.0 remains strictly and
losslessly readable. `apply_solution_pack_manifest` revalidates the exact recommendation pin, preflights all
configuration and duplicate targets, loads a fresh baseline IR, applies only those two allowlisted fields
immutably, and requires validate_ir-clean output. Frozen canonical provenance records base/derived digests,
applied configuration IDs, pending AI-delta IDs, and the derived IR. Unsupported configuration fails closed;
AI-delta intent is never applied; repeated application is byte-stable; baselines remain unchanged; 0 calls.
R-438 added the ninth spine brick: defined the strict bounded typed AI-delta proposal schema
(`AIDeltaProposal`) and explicit opt-in local `ModelProvider` boundary. Manifests with zero AI deltas
bypass the provider completely with 0 calls; pending AI-delta intents generate a bounded prompt and strictly
parse untrusted JSON into validated entity/API/screen/capability proposal data, rejecting credential-bearing
fields, collisions with base IR, and unregistered change IDs; no cloud fallback, IR mutation, source
generation, or build.
R-439 added the tenth spine brick: safely applying validated AI-delta proposals to Application IRs with
strict collision detection, relation verification, and complete applied/unapplied AI delta provenance.
R-440 added the eleventh spine brick: verified multi-repo builder pipelines and project generation with
Solution Pack derived IRs via `build_solution_pack_project()` and ecosystem planner integration.
R-441 added the twelfth spine brick: live Studio integration and UI controls for Solution Pack selection,
customization, and provenance with 0 external resource links in HTML.
R-442 added the thirteenth spine brick: Studio AI-delta feature modification controls above Solution Packs,
enabling natural-language feature additions with bounded model proposals, safe IR derivation, and full
provenance tracking in Studio history and UI.
R-443 added the fourteenth spine brick: Solution Pack packaging, verification, and export CLI, enabling
portable, canonical, byte-stable SolutionPackPackage bundles, strict integrity verification, export/inspect CLI,
and dynamic package registry ingestion.
R-444 added the fifteenth spine brick: Solution Pack Multi-Surface Ecosystem Pack Synthesis, enabling portable
`EcosystemPackPackage` bundles with multiple surface packages, surface-specific Application IR synthesis scoping
entity visibility, mutation authority, actor roles, APIs, and screens per surface, and CLI synthesize/verify/inspect/build.
R-445 added the sixteenth spine brick: Solution Pack Ecosystem Pack Registry Integration, Catalog Discovery, and Studio
Multi-Surface Selection, providing immutable EcosystemPackRegistry, pre-registered baselines (`minimal-blog-ecosystem`,
`rideshare-favourites-ecosystem`), Studio discovery/recommendation endpoints, Studio single vs ecosystem tabs, multi-surface
selection/building with 0 model calls, and ecosystem catalog CLI.
R-446 added the seventeenth spine brick: Solution Pack Ecosystem Studio Live Multi-Surface Preview and Process Orchestration,
providing multi-surface ecosystem preview lifecycle in StudioPreviewManager (`replace_ecosystem`, `switch_surface`, per-surface
and global `stop` & `restart`), multi-session management (`_sessions: dict[str, LocalAppSession]`), collision-free loopback port
allocation per surface, liveness-aware status tracking, `threading.RLock` deadlock prevention, Studio HTTP endpoints
(`POST /api/preview/switch`, scoped stop/restart/re-preview), and Studio Web UI `#preview-surface-tabs` switcher bar with live
status indicators and 0 external network requests.
R-447 added the eighteenth spine brick: Solution Pack Ecosystem Multi-Surface Cross-App Auth and Unified State Binding,
providing canonical `EcosystemRoleBinding`, `EcosystemAuthContract`, `CrossAppAuthMatrix`, Python 3.13 stdlib-only deterministic
HS256 JWT minting/verifying (`mint_ecosystem_token`, `verify_ecosystem_token`), demo token generation, `EcosystemStateBinding`
with entity lifecycle state flows and role-gated transitions, Studio preview auth/state injection and endpoints, and CLI auth/state subcommands.
R-448 added the nineteenth spine brick: Solution Pack Ecosystem Cross-Surface Webhook and Event Bridge, providing canonical
`WebhookRetryPolicy`, `EcosystemWebhookSubscription`, `EcosystemEventPayload`, `WebhookDeliveryRecord`, `EcosystemEventBridgeContract`,
Python 3.13 stdlib-only HMAC-SHA256 signing and verification (`sign_webhook_payload`, `verify_webhook_signature`) with constant-time
`hmac.compare_digest`, in-process `EcosystemEventBridge` with bounded delivery logging (max 100 entries), deterministic contract synthesis
(`synthesize_ecosystem_events`), Studio preview event bridge tracking and endpoints (`GET /api/ecosystem/events`, `POST /api/ecosystem/events/dispatch`),
Studio Web UI `#preview-events-info` container with subscription count badges, event simulation panel ("Simulate Event"), and live delivery log table,
and CLI events inspection subcommand.

ENVIRONMENT LIMITS
- Inside the AI sandbox only: large native-binary downloads (Next.js SWC, Vite/esbuild) can time out, so
  `task verify` never runs pnpm/npm and stays fully offline. This is NOT a limit on the founder's Mac:
  this session PROVED `pnpm install` + running the generated app work there (node 25, pnpm 11, go 1.27,
  python 3.13, docker, ollama all installed). Building/previewing generated apps and the R-224 Next.js
  console upgrade are therefore doable locally now.
- A Groq API key lives in the gitignored `.env` for later cloud use; the active mode is Tier 0 (fully
  local, Ollama only) — `task platform:status` confirms.

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

WHAT TO DO NEXT
- LATEST (2026-09-22): R-528 (RideNow part 3/4: driver PWA) is done. Next: R-529 admin/ops app +
  template.json + screenshots + publish `ride-now`. The master plan is in .ai/tasks/R-526.md.
  Earlier: R-527 (rider app + shared package).
  Earlier: R-525 (T-4 code-edit agent). Earlier: R-524 (chat edits work on Gemini).
  Earlier: R-523 (T-3 marketplace UI) is done. Earlier: R-522 (Google
  provider runs builds; .env model gemini-3-flash-preview) is done. Earlier: R-521 (core-loop hotfix: generated apps run again) is done; see
  .ai/tasks/R-521.md. Always run ./scripts/smoke-core.sh (17 checks incl.
  the generated preview) after generator changes. Earlier: R-520 (T-2 multi-app preview) is done.
  Earlier: R-519 (T-1 template format + registry) is done; see .ai/tasks/R-519.md and
  templates/catalog/README.md. Earlier: R-518 (T-0 Stabilise the core) is done; see .ai/tasks/R-518.md. Phase T,
  the Template Marketplace (7 categories, 10 hand-built golden-repo templates), is approved. Next is
  T-1: template format + registry (templates/catalog/<slug>/template.json + repo/, loader in
  studio/templates.py, control-plane GET /templates, GET /templates/{slug}, POST /templates/{slug}/use).
  Before claiming the core works, run ./scripts/smoke-core.sh against ./scripts/omnistack.sh up.
- R-430 through R-453 are DONE — the DIFFERENTIATING SPINE now proposes a curated multi-app ecosystem,
  materializes it as multiple owned repos, and can explicitly refine an unknown domain through local Ollama
  before using the same deterministic planner. R-433 then gives each surface a bounded read/write entity
  policy, relation-safe dependencies, one actor role, and role-gated mutations. R-434 registers immutable,
  versioned, digest-pinned verified baselines; R-435 exposes exact target-aware recommendations or no-match
  in ecosystem planning; R-436 captures bounded configuration/AI-delta intent in a strict pinned manifest;
  R-437 applies explicit allowlisted project metadata to a fresh validated IR with provenance and leaves
  AI-delta intent pending; R-438 converts pending manifest AI-delta intents into strict validated proposal
  data via an opt-in local ModelProvider boundary (0 calls when no AI-delta changes exist); R-439 safely
  applies validated AI-delta proposals to Application IR with pin/collision/relation revalidation, immutable
  merging, semantic validation, and byte-stable provenance tracking; R-440 compiles Solution Pack derived
  IRs into owned Git repositories with verification gate ladders and transparent ecosystem builder integration;
  R-441 integrates Solution Pack discovery, recommendation, selection, customization, and provenance
  into the Studio UI, HTTP server, and live build pipeline; R-442 wires Studio AI-delta feature modification
  controls above Solution Packs; R-443 introduces portable SolutionPackPackage bundles, strict integrity
  verification, export/inspect CLI, and dynamic registry ingestion; R-444 introduces multi-surface Ecosystem
  Pack synthesis, portable `EcosystemPackPackage` bundles, and multi-repo ecosystem builds; R-445 introduces
  Ecosystem Pack Registry integration, catalog discovery, and Studio multi-surface selection; R-446
  introduces multi-surface process orchestration, dynamic collision-free port allocation, live surface switching,
  and Studio Web UI surface tabs; R-447 introduces cross-app authentication contracts, stdlib-only JWT token
  generation and verification, unified state bindings with role-gated lifecycle flows, Studio preview auth injection,
  and CLI auth/state inspection; R-448 introduces cross-surface webhook and event bridges with HMAC-SHA256 signing;
  R-449 introduces cross-surface distributed tracing, audit trails, and telemetry collectors; R-450
  introduces multi-surface export, deployment manifests, stdlib Docker Compose YAML generation, and HTTP reverse-proxy live gateway orchestration;
  R-451 introduces cross-surface data sync, conflict resolution algorithms (last-write-wins, source-of-truth, field-merge),
  offline-first sync engine, Studio sync endpoints/UI badges, and CLI sync subcommand;
  R-452 introduces multi-surface CI/CD workflow contracts, deterministic Python stdlib GitHub Actions YAML generation,
  in-process DAG cycle validation, pipeline dry-run simulation, Studio preview CI/CD endpoints and UI container, and CLI cicd subcommand;
  and R-453 introduces comprehensive multi-surface health check probes, end-to-end smoke test specifications, canary verification rules,
  in-process dry-run evaluation engine, Studio preview verification endpoints and UI panel, and CLI verify-suite subcommand;
  and R-454 introduces multi-surface disaster recovery contracts, backup targets, snapshot manifests, sequential recovery plans,
  rollback triggers, in-process dry-run simulation engine, Studio preview DR endpoints and UI panel, and CLI recovery subcommand;
  and R-455 introduces multi-surface capacity planning contracts, resource quotas, unit economics cost models,
  in-process workload scaling simulation engine, Studio preview capacity endpoints and UI panel, and CLI capacity subcommand;
  and R-456 introduces multi-surface alerting contracts, alert rules, incident remediation runbooks, multi-tier escalation policies,
  in-process metric evaluation and incident simulation engine, Studio preview alerting endpoints and UI panel, and CLI alerting subcommand;
  and R-457 introduces multi-surface SLA, SLO, and error budget contracts, deterministic stdlib synthesis,
  in-process metric evaluation and multi-window burn rate calculation, SLA compliance simulation, Studio preview SLA endpoints and emerald UI panel, and CLI sla subcommand;
  and R-458 introduces multi-surface governance contracts, compliance policies (SOC 2, GDPR, ISO 27001), data classifications,
  cryptographic audit evidence items, in-process compliance evaluation and multi-scenario audit simulation, Studio preview governance endpoints and indigo UI panel, and CLI governance subcommand;
  and R-459 introduces multi-surface documentation, architecture runbooks, and aggregated OpenAPI 3.1 specifications,
  deterministic stdlib synthesis, in-process Markdown bundle rendering, keyword/tag search with relevance scoring,
  OpenAPI route aggregation with collision detection, documentation export simulation, Studio preview docs endpoints and sky-blue UI panel, and CLI docs subcommand;
  and R-460 introduces Next.js Codegen End-to-End Route Handler Synthesis & Interactive CRUD Form Submission,
  replacing 501 `not_implemented` route stubs with real backend proxy handlers, scoping `X-Frame-Options: DENY`
  to production in `next.config.mjs` to unblock Studio iframe previews, and connecting forms and routes for real data persistence;
  and R-461 introduces Full-Stack Production Authentication Engine,
  rendering a PostgreSQL `users` table and admin seed row, FastAPI auth router (`/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`)
  using `hashlib.pbkdf2_hmac` with zero external dependencies, Next.js `AuthProvider` context and `useAuth()` hook,
  responsive login and registration pages, navbar auth status controls, and `lib/api.ts` Bearer token auto-attachment with localStorage fallback;
  R-462 added an opt-in LLM UI synthesizer, R-463 hardened auth, R-464 completed platform features (search/filter UI,
  audit timestamps, RBAC row-ownership, S3 upload field); and **R-465 (2026-09-17) grounded the HYBRID UI engine** —
  the founder-approved direction after an honest competitive assessment: the LLM writes the modern UI over the
  deterministic typed data layer (the prompt embeds the REAL generated lib/types.ts / lib/hooks.ts / lib/api.ts
  parsed from the same generators — the R-462 seed had hallucinated `refresh()`/`page` params — plus the real
  component exports and design-token names), with a bounded validation->feedback->retry loop in one
  `_synthesize_file` core (retry only on validator rejection, never on exceptions; deterministic template fallback;
  JSON-safe secret-free `UiSynthesisOutcome` per file; hardened import whitelist), an explicit `synthesize_screens`
  flag threaded generate -> assemble_project -> build_app_from_ir/prompt (default off; default output byte-identical;
  the never-set env gate removed), and the opt-in `task agent-engine:ui:synthesize` (see docs/HYBRID_UI.md).
- R-466 (2026-09-17) made the compiler the last word and the gateway rate-limit-aware: `verify/compile.py` captures
  `tsc --noEmit --pretty false` into per-file `CompileError`s (+ `ensure_web_dependencies`); `codegen/hybrid_repair.py`
  feeds each LLM-written file's errors back through R-465's corrective channel (validator-gated, template fallback,
  outcome per file, deterministic files never rewritten), applies a `ProjectDiff` via `edit/apply_diff`, recompiles
  and reverts what still fails (`compile_and_repair(_sync)` → `CompileRepairReport`); `model_gateway` types HTTP 429
  as `ProviderRateLimitedError` with a parsed `Retry-After` and the cloud adapter waits and re-sends the same request,
  bounded by `OMNISTACKAI_RATE_LIMIT_RETRIES` / `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS` (`.env.example`); `llm_ui`'s
  `_Transcript` shrinks a too-large request (drop the echo, then `compact_grounding(ir)`); outcomes carry the HTTP
  status of failed calls. The CLI's Step 3/3 type-checks, repairs, reverts and commits. Live (Groq free tier): the
  3-step CLI ran end-to-end with the fallback repo compiling at 0 errors; pacing verified live (`Retry-After: 112`
  honoured, above the 60s cap); the limiter was tokens per DAY — the daily budget was spent, so a full live proof of
  a model-written page that compiles is still pending (see docs/HYBRID_UI.md).
- R-467 (2026-09-17) brought the hybrid engine into the actual Studio a user opens in a browser: a read-only
  file browser (new `studio/files.py`, `edit/apply.py`-style path safety; `GET /api/build/{id}/files` +
  `GET /api/build/{id}/file?path=...`, wired in build-only mode too) and a `hybrid_ui` toggle on `/api/build`
  that threads `synthesize_screens`/`ui_outcomes` into the plain-prompt and Ecosystem Pack build paths (the
  Solution Pack path has no such parameter on `build_solution_pack_project` and says so honestly via
  `hybrid_ui_active: false`). `page.py` gained a clickable file list + viewer pane and a "Hybrid UI
  (experimental)" checkbox, still zero external assets. Found and fixed while implementing: a missing
  `ApplicationIR` import (latent `NameError`) in `live_serve.py`'s ecosystem branch, and — more importantly —
  a LIVE, ACTIVE violation of the "0 model/network calls under `task verify`" constraint: with real Groq
  credentials now in the gitignored `.env`, four pre-existing Studio test call sites that never mocked
  `resolve_generation_provider_from_env` were making real network calls (confirmed by timing: one unmocked
  test cost 23.5s of real Groq traffic). All four now mock it explicitly.
- R-468 (2026-09-17) added multi-turn "continue editing this app": new `intake/app_delta.py` is a generic,
  non-pack-coupled sibling of `solution_packs/ai_delta.py` — a follow-up prompt proposes a bounded, validated
  delta (new entities/apis/screens only), merged onto the tracked IR by tuple concatenation (mirroring
  `solution_packs/application.py`'s merge exactly), with a validate→feedback→retry loop mirroring R-465's
  `_synthesize_file`. `edit/diff.py::plan_edit` + `edit/apply.py::commit_edit` (already proven end-to-end by
  `test_edit_loop.py`) turn the delta into a real second git commit on the same owned repo — **zero changes**
  to `edit/`, `git_service/`, or `application_ir/`. New `studio/session.py`'s bounded, server-only
  `StudioSessionStore` tracks each editable build's current IR + turn history; new
  `POST /api/build/{id}/edit` / `GET /api/build/{id}/turns`, wired unconditionally; `page.py` gets a small
  chat box. v1 is additive-only; Solution Pack and "all surfaces" Ecosystem builds get an honest
  `EditNotSupportedError` rather than a silent no-op. Found and fixed while implementing (via the
  end-to-end tests, not a live run): neither this module nor `ai_delta.py` validated a proposed screen's
  `role` against the base IR's real declared roles — fixed at both the parse layer (gets the retry benefit)
  and the merge layer (defense in depth).
- FOUNDER DECISION (2026-09-17): advance from the Stage-0 static console (`apps/console-web`) and stdlib
  Studio prototype toward the real commercial platform Implementation Brief Section 33 always specified —
  a Next.js console over a Go control-plane (Auth/Orgs/Billing), hosted, multi-user. Full decision record
  and phased Tracker-ID sequence: `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`. The hybrid engine
  and Studio (R-465-R-468) stay as the agent-engine's own local proof harness, not the product UI.
- R-469 (2026-09-17, done) built Phase A — control-plane foundation: users, auth, plans, credits. Two
  roles only (`super_admin`, `user` — access gated entirely by `plan`, reusing the Brief Section 22 tier
  names `free`/`developer`/`pro`/`agency`/`enterprise`, `byok` an add-on flag); every signup gets `free`
  plus a starting credit grant in an append-only `credit_ledger`. New migration `000002_users_auth_billing`
  applied by a new self-healing embedded migration runner (`migrations` package, replays every idempotent
  migration on every boot). Password hashing is PBKDF2-HMAC-SHA256 on Go stdlib only — zero new `go.mod`
  dependency. New `POST /auth/register`/`/login`/`/logout` + `GET /auth/me` on `internal/auth`, backed by
  the real PostgreSQL `internal/users.Store`; login failure is a generic 401 with no email-enumeration
  timing leak. `go test` all green; `task verify` 3,593 OK; a real Docker Compose + PostgreSQL smoke test
  proved register → login → me → logout → me-after-logout end to end.
- R-470 (2026-09-17, done) built Phase B — replaced the static `apps/console-web` with a real Next.js
  (App Router, TypeScript) app: `/login`/`/register` pages, an authenticated `/` home page (profile +
  credit balance), `/fabric` carrying the old model/cost overview forward on the same
  `data/overview.json` contract. Session handling is a server-side cookie proxy (`app/api/auth/*` Route
  Handlers set/clear an `httpOnly` cookie) - the raw token never reaches client-side JS, no CORS needed.
  No new UI dependency beyond React/Next.js. Found and fixed five real ecosystem-compatibility issues
  (pnpm fetch timeouts fixed via a new root `.npmrc`; `typescript@7` not yet supported by
  `typescript-eslint`, pinned to `6.0.3`; an ESLint `FlatCompat` crash fixed by importing
  `eslint-config-next`'s native flat-config export directly; pnpm 11.19 moved build-script
  allowlisting to `pnpm-workspace.yaml`; and a `Secure`-cookie-over-HTTP bug that would have silently
  broken login in a real browser, caught by inspecting the raw `Set-Cookie` header rather than trusting
  status codes). `task verify` 3,593 OK; a real Docker Compose control-plane + a real `next start`
  server proved the full register -> home -> fabric -> logout -> login round trip live, twice (the
  second run after the cookie fix).
- R-471 (2026-09-17, done) fixed a real bug the founder hit trying the R-470 console live: opening
  `http://127.0.0.1:4321/register` and submitting the form did nothing. Root cause in the dev server's
  own log: Next.js 16 blocks cross-origin access to its dev/HMR resources by default and treats
  `127.0.0.1`/`localhost` as different origins, so client JS never hydrated and the form fell back to a
  native GET submission (fields in the URL, no visible error). Fixed with `allowedDevOrigins` in
  `next.config.ts`; verified as far as possible without a real browser (fetched the actual client JS
  chunk with the real origin header - 200, warning gone). Also added a required Name field to
  registration (`full_name`, new additive migration `000003`) - explicitly declined Gender/Age (no
  function in this product's roadmap, unnecessary PII). Renumbered the kickoff doc's Phase C from R-471
  to R-472.
- R-472 (2026-09-18, done) built Phase C: the control-plane's new `POST /jobs/build` authenticates the
  caller (`auth.RequireUser`, factored out of `handleMe`), forwards the request body verbatim to the
  agent-engine's real plain-prompt build path, and debits real credits from the actual dollar cost the
  agent-engine reports via a new `users.Store.DebitCredits` (row-locked `SELECT ... FOR UPDATE`, clamped
  so `credit_balance` never goes negative - v1 policy is never block a build, only clamp the charge).
  Correction found while researching: that build path returned a **raw** `ModelProvider`, bypassing the
  gateway's own real-but-previously-demo-only `UsageLedger` entirely - closed with a new, additive
  `model_gateway.RecordingProvider` decorator (zero changes to any existing provider or call site),
  threaded through a new optional `usage_ledger` param on `resolve_generation_provider_from_env` and
  surfaced as an additive `usage` key (`cost_micros_usd` as an int, not a decimal string) from
  `studio/live_serve.py`'s plain-prompt `_build`. A real bug was caught by the new tests before any
  commit (`RecordingProvider` initially recorded the wrong provider/model identity - the response's own
  echoed field instead of the actually-dispatched provider). A real infrastructure bug was found only by
  the live smoke test: the control-plane's global 15s `http.Server.WriteTimeout` was silently killing
  `/jobs/build`'s connection before a real, multi-minute build finished - fixed with a per-request
  `http.ResponseController.SetWriteDeadline` instead of loosening the server-wide timeout. Compose
  networking: added `OMNISTACKAI_AGENT_ENGINE_URL` (containers default to `host.docker.internal:4173`)
  + `extra_hosts: host-gateway` so the containerized control-plane can reach the host-run agent-engine
  Studio server. `task verify` 3,603 OK (agent-engine) + full control-plane `go test` green (7 new
  `internal/jobs` cases, `creditsForUsage`/`clampCharge` table tests). Live: a real Docker
  Postgres+control-plane, a real local Ollama build via `POST /jobs/build` produced a real 161-file
  "Task Tracker" repo with `usage.cost_micros_usd: 0`/`credits_spent: 0` (correct - local usage is
  credit-exempt by price, not a special case); since a free build has nothing to debit, `DebitCredits`'s
  row-locked/clamped SQL path was proven separately against the same live Postgres with a throwaway,
  never-committed `go run` program (`100 -> 63 -> 0`, clamped, never negative), independently confirmed
  via a real `GET /auth/me`.
- R-473 (2026-09-18, done) built Phase D's first slice: a logged-in user can now open
  `apps/console-web`'s new `/studio` page, type a prompt, click Build, and get a real app built
  through R-472's real Job API, with the console showing the real post-debit credit balance.
  Deliberately scoped small - no file browser, live preview, or chat yet - matching how the
  agent-engine's own hybrid-UI engine shipped across four separate gated Tracker IDs (R-465-R-468)
  rather than one large task; those capabilities (and Solution Pack/Ecosystem selection, Model
  Provider settings, a Problems tab) are named follow-ups, not silently dropped. New
  `app/studio/page.tsx` (auth-gated, mirrors `app/page.tsx`) + `app/studio/studio-form.tsx` (prompt
  textarea, Build button, a real pending state since builds take real time, result panel, error
  banner) + `app/api/jobs/build/route.ts` (server-side proxy: reads the session cookie, 401s
  locally with no upstream call if absent, forwards to the control-plane with the bearer token
  attached, never exposed to client JS). `lib/control-plane.ts` gained `BuildJobResponse`/
  `buildApp()` following the existing `login`/`registerAccount` pattern. No control-plane or
  agent-engine changes - R-472 already built the real backend this task's UI calls. `task verify`
  3,603 OK; console `typecheck`/`lint`/`build` clean. Live: a real Docker control-plane, a real
  agent-engine Studio server on local Ollama, and a real `next start` console proved `/studio`'s
  auth gate (307 signed out, 200 signed in with the real credit balance) and
  `POST /api/jobs/build`'s local 401 with no cookie; a real build attempt hit a genuine, unforced
  local-model IR-validation failure, honestly proxied through as a real 502 (an authentic live
  proof of the error-banner path, not a synthetic test); a retry succeeded for real - a genuine
  157-file "Recipe Box" repo with every field matching exactly what the UI renders.
- The founder asked to see the platform running before continuing Phase D (2026-09-18): brought up
  the real Docker control-plane + real agent-engine Studio server + real `next start` console for a
  live walkthrough (register -> home -> Studio build -> fabric overview), then, per "Left it as
  running and continue," kept building the next Phase D slice on that same running stack.
- R-474 (2026-09-18, done) built the console's file browser: R-473's build result panel listed
  filenames as inert text; each is now a button showing real generated file content in a read-only
  viewer. Bridges the agent-engine's existing, real, path-safe read-only file endpoints
  (`studio/files.py`, R-467) through two new authenticated control-plane proxy routes -
  `GET /jobs/build/{id}/files` / `GET /jobs/build/{id}/file?path=...` - the same generic-proxy shape
  R-472 established; no agent-engine changes, no credit debit (browsing isn't billable). New
  `listBuildFiles()`/`readBuildFile()` clients, two new dynamic Route Handlers, and a `FileBrowser`
  component in `studio-form.tsx` (binary-file guard included). A shared `writeAuthError` helper
  replaces three copies of the same auth-error mapping. Honest, named limitation not fixed here: the
  Studio server has no per-user build scoping (unchanged from R-467) - any authenticated caller who
  knows a build id can browse its files; real isolation needs the Studio server to become
  multi-tenant-aware. `task verify` 3,603 OK; control-plane `go test` all green (15 in
  `internal/jobs`); console `typecheck`/`lint`/`build` clean (13 routes). Live, against the
  founder's own already-running stack (only the control-plane and console restarted to pick up the
  code, Postgres and the Studio server's build history left untouched): built a real 158-file app
  via real Groq cloud, then proved the file browser end to end - real file content read from the
  real repo on disk, an unknown-build 404 and a path-traversal 400 both proxied through from the
  agent-engine unchanged.
- The founder asked directly whether the doc's original 6-task Phase D sketch gets this platform to
  "exact" Lovable/Dyad/Emergent parity - honest answer recorded in the kickoff doc: closer, not
  exact (still missing real-time streaming and per-user backend multi-tenancy). Asked to continue
  the roadmap anyway. Turning the sketch into an executable plan went through full plan-mode
  discipline (2026-09-19): two Explore agents researched the real console-web frontend and the real
  agent-engine/control-plane backend (not the doc's assumptions), a Plan agent designed a
  task-by-task sequence, and the most consequential claims were independently verified by reading
  the actual source - confirmed `_build()` never records a chat turn though `_edit()` does;
  `_edit()` has no `usage_ledger` at all (every edit today debits 0 credits regardless of real
  cost); the live-preview API's build-scoped route returns an unusual `200 {"status":"error"}` for
  an unknown build, not a 404; no compile-error endpoint exists anywhere in the Studio path today.
  Two decisions asked of the founder directly, both honored: Problems (compile errors) gets built
  for real via its own task (R-480) rather than a placeholder - this took the roadmap from six
  tasks to seven; Files and Code stay as two separate real tabs, not one. Plan approved via
  `ExitPlanMode` (saved at `/Users/sanjeet_kumar/.claude/plans/hi-fancy-shannon.md`).
- R-475 (2026-09-19, done) built Studio visual foundation, the first of the seven: new
  `app/studio/layout.tsx` takes over `/studio`'s auth gate and persistent top-bar chrome (brand,
  back link, sign-out) later tasks build on. `globals.css` gained additive design tokens
  (`--radius-sm/md/lg` replacing inconsistent inline values, `--surface-2`, an accent chip
  background, a CSS-only `.spinner`, `.pill--accent`) mirrored into the existing dark-mode media
  query. New hand-rolled `studio-icons.tsx` rather than a new npm dependency. `studio-form.tsx`
  restyled only, zero logic change. No backend changes. `task verify` 3,603 OK; console
  `typecheck`/`lint`/`build` clean. Live (Colima had stopped since the prior session, restarted):
  real control-plane + real agent-engine Studio server + a fresh `next start` proved the auth gate
  now correctly lives in `layout.tsx`, the new shell renders correctly with a real credit pill, and
  `/`, `/fabric`, `/login`, `/register` all remain structurally unaffected. Confirmed no new npm
  dependency was added.
- R-476 (2026-09-19, done) built the backend multi-turn edit bridge, second of the seven: new
  control-plane routes `POST /jobs/build/{id}/edit`/`GET /jobs/build/{id}/turns` mirroring
  `POST /jobs/build`'s exact proxy+debit shape, with the shared "forward, decode, debit, inject"
  logic extracted out of `handleBuild` into a `proxyAndDebit` helper both handlers reuse. Also fixed
  two real, verified Python gaps found during planning: `_edit()` had no `usage_ledger` at all (every
  edit debited 0 credits regardless of real cost); `_build()` never recorded its own chat turn (only
  `_edit()` did). Both fixed by mirroring `_build()`'s own existing pattern. A no-op edit still
  charges real credits (the model call happened even with an empty diff) - locked in by a dedicated
  test. `task verify` 3,604 OK; control-plane `go test` all green (25 tests, 10 new). Live (real
  Docker control-plane + a freshly restarted real agent-engine Studio server - Python doesn't
  hot-reload, and the first attempt against the stale process usefully reproduced the exact bug this
  task fixes): a real build's own turn now appears in `/turns` before any edit; a real edit produced
  a genuine second git commit and, for the first time, a real `"usage"` key on the edit response.
  Both came back `credits_spent: 0` honestly - this environment's real configured cloud model has no
  price-book entry, a pre-existing fact unrelated to this task; the "debits a nonzero charge"
  behavior is proven by the new unit tests instead.
- R-477 (2026-09-19, done) built the console chat UI, third of the seven: replaced the one-shot
  form with a persistent multi-turn thread on R-475's shell, wired to R-476's new routes; `buildId`
  null vs. set decides build-vs-edit. New `studio-chat.tsx` + `studio-workspace.tsx` (the latter
  holding the `BuildResult`/`FileBrowser` pieces moved out of the retired `studio-form.tsx`,
  generalized to a `WorkspaceSnapshot`). `buildId` persists in the URL so a refresh hydrates chat
  text history from `/turns` - the workspace panel does not rehydrate, an honest, named
  simplification. A real finding, verified by source read before implementation: `GET /turns` does
  not 404 for an unknown build (`{"turns": []}` instead) - only `_edit()`'s `BuildNotFoundError` is
  a real 404, so the "session no longer available" recovery is wired there, not to hydration.
  `task verify` 3,604 OK; console `typecheck`/`lint`/`build` clean (14 routes, 2 new). Live: real
  control-plane + real agent-engine Studio server + fresh `next start` proved build -> turns
  hydration -> follow-up edit with a refreshed file list, then the agent-engine Studio server was
  killed and restarted mid-test to simulate a real stale session - the edit-triggered 404 recovery
  and the turns-hydration honest-empty-thread finding both confirmed live, then a fresh build proved
  the full recovery loop.
- R-478 (2026-09-19, done) built the backend live preview proxy, fourth of the seven: four new
  control-plane routes proxying the agent-engine's existing trusted-local preview control surface
  verbatim - `GET /jobs/preview`/`POST /jobs/preview/stop`/`POST /jobs/preview/restart` (the
  singleton surface) plus `POST /jobs/build/{id}/preview` (the build-scoped one, server-constructing
  its own `{"id": id}` body rather than trusting the caller's). All auth-required, no credit debit,
  zero agent-engine changes. Verified, not assumed: an unknown build's build-scoped preview route
  returns a real 200 `{"status":"error"}`, not a 404 - the proxy forwards it unchanged. New
  `defaultPreviewTimeout` (60s) applied to both `handleBuildPreview` and `handlePreviewRestart`
  (both can trigger a real cold start - added to restart during implementation once that was clear).
  `task verify` 3,604 OK; control-plane `go test` all green (38 tests, 13 new). Live: real
  control-plane rebuilt + real agent-engine Studio server in preview mode proved a real build
  auto-starting a real preview, real status/stop/restart/build-preview proxying, the 200-with-error
  shape confirmed live for an unknown build, unchanged credit balance across all four calls, and
  uniform 404s against build-only mode.
- R-479 (2026-09-19, done) built the console live preview UI, fifth of the seven: an iframe
  rendering the real running generated app, wired to R-478's four routes. Preview start is
  synchronous, so polling's job is crash detection (5s interval while `status: "ready"`), not
  progress-watching. New `studio-preview.tsx` triggers a re-preview whenever `buildId` becomes real
  or a `previewVersion` counter (bumped after every edit, since `_edit()` never restarts the
  preview) changes; a 404 renders an honest disabled message; manual Restart/Stop reuse icons that
  existed unused since R-475. Every `PreviewStatus` shape verified by reading `preview.py` directly.
  `task verify` 3,604 OK; console `typecheck`/`lint`/`build` clean (18 routes, 4 new). Live: real
  control-plane + real agent-engine Studio server in preview mode proved build -> real iframe-ready
  preview (fetched the real `web_url` directly, got genuine HTML) -> edit -> real re-preview on a
  new port -> the real preview OS process was killed directly to simulate an external crash, and
  the next poll correctly reported "stopped" -> manual Restart/Stop both worked -> build-only mode
  produced the uniform honest 404 disabled state.
- R-480 (2026-09-19, done) built backend Problems/compile-report support, sixth of the seven: real
  compile-error reporting for the first time in this codebase. New `studio/problems.py` mirrors
  `files.py`'s shape: resolves `apps/web`, raises `NoWebTargetError` if no web app, remaps
  `verify/compile.py`'s real `compile_web_project()`'s `VerifyError` into a clear
  `ToolchainNotInstalledError`. On-demand, not automatic. `StudioProblemsStore` is a bounded
  per-build-id LRU cache mirroring `StudioSessionStore`. New control-plane routes
  `POST`/`GET /jobs/build/{id}/problems`, no credit debit, a new `defaultProblemsTimeout` (90s), a
  new 409 status for "toolchain not installed." `task verify` 3,625 OK (21 new tests, no real
  toolchain needed); control-plane `go test` all green (45 tests, 7 new). Live: build-only mode with
  no toolchain produced real 409/404, no crash; hit two real, pre-existing environment issues along
  the way (a generated-migration collision, a 500ing preview page) worked through honestly; preview
  mode with a real installed toolchain surfaced 10 genuine TypeScript errors via a real `tsc` run in
  an LLM-synthesized page - real compiler output that also explained the runtime 500; a repeated GET
  returned the byte-identical cached report in 12ms.
- R-481 (2026-09-19, done) built the tabbed workspace, the SEVENTH AND FINAL task of the approved
  7-task roadmap: restructured `/studio`'s main pane into four real tabs - Preview, Files, Code,
  Problems - with chat persisting alongside, assembling R-474/R-477/R-479/R-480 into one shell.
  Files and Code stay separate (founder's choice), sharing one lifted `selectedFile`. New
  `code-highlight.ts` hand-rolled tokenizer (no new dependency, confirmed live against real
  generated TSX). Problems tab is on-demand per R-480's design. `task verify` 3,625 OK; console
  `typecheck`/`lint`/`build` clean (19 routes, 1 new). Live: full loop confirmed (build ->
  Preview/Files/Code -> edit -> refresh confirmed -> Problems check). A real, pre-existing codegen
  bug was found live (a dynamic-route slug collision from the edit path, unrelated to this task) -
  correctly surfaced as an honest Preview error and independently caught by a real Problems check,
  cross-confirming both features' error-surfacing design. **THIS COMPLETES THE APPROVED 7-TASK
  PHASE D ROADMAP.**
- R-482 (2026-09-19, done) built the Model Provider settings UI, the first follow-up task after the
  roadmap, per the founder's "complete one by one all" direction: continue through every named
  follow-up, one Tracker ID at a time, full discipline. A real, live Dyad-style provider status
  page - `platform_overview()` already existed but only ever generated a static snapshot for
  `/fabric`; new: calling `resolve_generation_provider_from_env()` safely reports which provider
  would actually run the next build, never surfaced anywhere before. New agent-engine
  `GET /api/providers`, new control-plane `GET /jobs/providers` (no debit), new authenticated
  `/settings` page. **A real bug was found and fixed during this task's own live smoke test**
  (introduced by this task's own first draft): a dotenv-load-ordering bug that made the providers
  list's "active" flags read stale in a fresh process - fixed by reordering, verified with `env -i`.
  `task verify` 3,629 OK; control-plane `go test` all green (48 tests, 3 new); console
  `typecheck`/`lint`/`build` clean (20 routes, 2 new). Live: cross-verified `activeNow` against a
  real build whose own log confirmed the exact same provider was used.
- R-483 (2026-09-19, done) fixed the dynamic-route slug-collision + duplicate FK identifier bug
  found live during R-481 (edit-delta path could generate colliding Next.js route slugs, e.g.
  "counterId" vs "counter_id", plus a duplicate lib/types.ts identifier). Root cause verified by
  direct source read: the full-build and edit-delta prompts had an unreconciled casing mismatch for
  API {param}s, and _entity_interface() never checked for an already-declared field before
  synthesizing a relation's FK column. Fixed at the structural root - ApiEndpoint.__post_init__ now
  canonicalizes every {param} to camelCase unconditionally; _entity_interface() now skips the
  synthesized FK when an explicit same-named field exists. `task verify` 3,635 OK (6 new tests).
  Live: reproduced the exact original scenario end to end - built the same counter app, sent the
  same edit, started the preview successfully (no crash, confirmed via the real log), one
  consistent dynamic route folder on disk, a real tsc check showing 0 duplicate-identifier errors.
- R-484 (2026-09-19, done) built real-time build streaming (SSE) - the founder's first named
  post-roadmap priority ("streaming first, then scope isolation properly"), chosen after three
  parallel research passes (competitor streaming architecture, per-user isolation scoping,
  deploy/stack breadth). Backend only - console UI is R-485. `ModelProvider.stream()` already
  existed at the model_gateway layer but nothing above it called it; added purely additive
  streaming twins (generate_ir_stream, build_app_from_prompt_stream, _build_stream, all
  plain-prompt-only per _edit()'s own scope precedent), new `POST /api/build/stream` (agent-engine
  SSE) and `POST /jobs/build/stream` (Go relay via http.Flusher + a trailing credits event once
  the real cost is known). **Two real bugs found and fixed, not glossed over**: (1) the SSE route
  sent `Connection: keep-alive`, which hung every real client since there's no
  Content-Length/chunked framing to signal the body's end - fixed to `Connection: close`. (2)
  RecordingProvider (every production build's real usage-tracking wrapper) had no `.stream()`
  method - invisible to every mocked test, only caught by the task's own required live `curl -N`
  smoke test - fixed with 4 new tests. `task verify` 3,658 OK (27 new tests); control-plane
  `go build`/`vet`/`test` all green (7 new tests, 55 total). Live: a real curl -N session through
  the real Go control-plane showed genuine token-by-token deltas over ~9 real seconds, a real done
  frame (177 files, real commit sha), and a real trailing credits frame; all three unsupported
  build kinds (pack_id/ecosystem_id/hybrid_ui) confirmed cleanly rejected with a 400 before any
  SSE framing.
- R-485 (2026-09-19, done) built the console streaming UI - fast-follow to R-484, closing the loop
  it opened. `/studio`'s chat now consumes POST /jobs/build/stream for its create-path: new
  streamBuildApp() (returns the raw upstream Response, unlike every other client function) feeds a
  new proxy route (app/api/jobs/build/stream/route.ts) that pipes the body straight through
  unbuffered; studio-chat.tsx gains sendBuildStream() (fetch() + manual response.body.getReader()
  SSE-frame parsing, not EventSource, since a POST body is required), replacing the static
  "Building..." wait with a live "Generating your app... (N characters so far)" indicator - the raw
  streaming JSON text itself is never shown (would render as visibly broken partial JSON); the
  full result renders unchanged once "done" arrives. Edit stays non-streaming (R-484's own scope
  boundary). No browser-automation tool was available this session - verified via `next start` +
  curl through a real cookie-based login session, the same request path a real browser takes.
  `pnpm run typecheck`/`lint`/`build` clean (21 routes, 1 new); repo gates all pass (agent-engine
  untouched, 3,658 tests unaffected). Live: a real streamed build through the full console-proxy ->
  Go control-plane -> agent-engine path showed genuine incremental frames over ~9 real seconds, a
  real done frame (174 files, real commit sha), and a real trailing credits frame; a real follow-up
  edit on the same build confirmed the edit path is completely unchanged.
- R-486 (2026-09-19, done) is the first of a five-task sequence (R-486..R-490) toward the
  founder's "Full isolation: per-user processes/sandboxes" direction. Dedicated research (codebase
  audit + competitor platforms + sandbox technology tradeoffs) confirmed every serious 2025-2026 AI
  app-builder running real server-side code uses a managed microVM/gVisor sandbox provider -
  self-hosting Firecracker/K8s from scratch is a multi-quarter effort this project doesn't have
  headcount for. Presented as a hard-gate (new paid cloud dependency) via AskUserQuestion; the
  founder's answer: build real, pluggable drivers for multiple providers (E2B, Vercel Sandbox,
  Daytona) switchable later by cost/speed/smoothness, plus one free browser-only option
  (WebContainers). This task proves the pattern with E2B: confirmed the existing
  RuntimeProvider/PreviewPlan abstraction is a pure planner (describes local commands + a URL, not
  a real orchestrator) and stays untouched; added additive SandboxHandle/SandboxLifecycleProvider
  (create/status/kill), a new stdlib-only sandbox_http.py safety wrapper, and E2BSandboxProvider,
  verified against E2B's real documented REST API (fetched directly from docs.e2b.dev, not
  assumed). No real E2B_API_KEY exists in this environment - every gate is offline via an injected
  fake HTTP transport; live-cloud verification is honestly deferred to a real key from the founder.
  `task verify` 3,680 OK (22 new tests); repo gates all pass.
- R-487 (2026-09-19, done) is the second of the five-task sequence: a real Vercel Sandbox driver,
  proving R-486's SandboxLifecycleProvider pattern is genuinely pluggable against a second,
  differently-shaped API, reusing sandbox_http.py completely unchanged. Verified against Vercel's
  real REST API (fetched directly): POST/GET/DELETE /v2/sandboxes[/{name}], Bearer auth, a
  routes[] array giving each port's real URL directly (no pattern-guessing, unlike E2B). A real,
  documented limitation surfaced honestly: Vercel Sandbox's runtime enum has no Go - backend-go is
  rejected with a specific UnsupportedSandboxRuntimeError. Two real bugs found and fixed: (1) an
  error-classification ordering bug - the first draft checked provider-runtime-support before
  validating the target existed at all, misclassifying an unknown target's error; fixed by
  validating the target first via the shared _port_for_target() helper. (2) adding a
  RUNTIME_SPECS entry broke a pre-existing test expecting a matching drivers.py _SANDBOX_URLS
  placeholder - fixed with one line, drivers.py added to allowed_paths mid-task. No real
  VERCEL_TOKEN/VERCEL_PROJECT_ID exist in this environment - live-cloud verification honestly
  deferred. `task verify` 3,694 OK (14 new tests); repo gates all pass.
- R-488 (2026-09-19, done) is the third of the five-task sequence: a real Daytona driver, whose
  API is shaped a third distinct way - the create response carries no URL at all, so create()
  makes a second real call, GET /sandbox/{id}/ports/{port}/preview-url, to get one. A real
  base-URL ambiguity across Daytona's own docs was found and resolved the same way E2B's was.
  create() always requests "public": true since SandboxHandle.url has no room for a companion
  preview-access-token header. A real, honest tradeoff surfaced, not hidden: Daytona's documented
  default isolation is plain Docker containers, weaker than E2B/Vercel's Firecracker microVMs - not
  worked around, called out for R-490. No real DAYTONA_API_KEY exists in this environment -
  live-cloud verification honestly deferred. `task verify` 3,707 OK (13 new tests); repo gates all
  pass; unlike R-487, no providers.py/drivers.py change was needed this time.
  **All three sandbox providers the founder asked for (E2B, Vercel Sandbox, Daytona) now have
  real, tested, pluggable drivers behind one shared contract.**
- R-489 (2026-09-19, done) is the fourth of the five-task sequence - and it replaces the
  originally planned WebContainers option after real research found WebContainers requires a paid
  commercial license for any non-prototype use, and only runs Node.js anyway (no Python/Go).
  After comparing every candidate's real licensing (Vercel Sandbox/Fly/CodeSandbox: paid-only; raw
  Firecracker: free but a multi-quarter build-your-own-orchestrator project; E2B/Daytona: open
  source but self-hosting means running their full orchestrator; gVisor: genuinely free, open
  source, small lift), the founder approved gVisor, then asked two real follow-ups before
  continuing: real resource cost (light - ~50MB binary, ~15-30MB RAM/sandbox, layers onto the
  Docker daemon already running for Postgres/control-plane) and why not use this in production
  instead of paying (answered honestly: a self-hosted loopback URL only works for a same-machine
  viewer; the managed providers' real value beyond isolation is a global public routing/proxy/
  scale layer this task doesn't build) - positioned explicitly as the free/dev tier, not a
  production replacement, confirmed by the founder. New docker_socket.py (a genuinely different
  transport - Docker's Unix socket, since urllib has no Unix-socket support) and gvisor.py's
  GVisorSandboxProvider. A real, necessary contract correction found and fixed: SandboxHandle's
  https-only URL validation (from R-486) was too narrow once a local provider existed; relaxed to
  match PreviewPlan's own loopback-or-https pattern. active is a live local capability check (is
  runsc registered?), not an env-var check - the only driver with no credential at all. Docker's
  own image ecosystem covers Go, unlike Vercel Sandbox. No live gVisor/Docker daemon exists in
  this environment - live verification honestly deferred. `task verify` 3,729 OK (22 new tests);
  repo gates all pass.
- R-490 (2026-09-19, done) is the fifth and final task in the sequence: a real
  provider-selection surface. New sandbox_selection.py: build_sandbox_from_env(selection=None, *,
  providers=None) -> SandboxSetup, mirroring bootstrap.py's own established
  build_runtime_from_env() shape, plus a new SandboxSelectionError. Defaults to sandboxing
  disabled (selected=None) - zero behavior change until an operator opts in via
  OMNISTACKAI_SANDBOX_PROVIDER. The explicit selection parameter is the concrete "switch per user
  base" mechanism the founder asked about - a caller can pass a per-user choice without touching
  global state, proven by a dedicated test. Kept deliberately separate from the older, still-
  untouched tier.py/bootstrap.py planning system; not wired into Studio/console/control-plane,
  matching every prior task's own boundary (per-user plan data lives in the Go control-plane and
  is a separate future integration). A real test-design risk was caught and avoided: an early
  draft test would have made a real local Docker socket connection attempt via
  GVisorSandboxProvider.active just to test registry wiring - replaced with a zero-I/O
  class-identity check instead. `task verify` 3,738 OK (9 new tests); repo gates all pass.
  **This completes the five-task sandbox-provider sequence (R-486..R-490)**: E2B, Vercel Sandbox,
  Daytona, and a free self-hosted gVisor option are all real, independently-tested, and now
  genuinely pluggable/switchable via configuration - exactly the founder's original ask.
- R-491 (2026-09-19, done) is the first of the six-task Console UI overhaul (R-491..R-496),
  approved after the founder asked why the UI is "just simple and very ugly" (honest diagnosis:
  zero UI dependencies, hand-rolled CSS, an enforced R-470 gate blocking component libraries,
  every prior task backend-first). The founder chose "Full UI overhaul now" (reference bar:
  Emergent/Lovable/Dyad; screenshots to be shared) - that decision retired the R-470 gate
  formally. The console now runs on Tailwind v4 (@tailwindcss/postcss, per Next 16's own bundled
  guide) + shadcn/ui on Radix with the Nova preset (= Lucide/Geist) + next-themes (dark-first) +
  Geist/Geist Mono via next/font, with a tinted OKLCH token system and one amber brand accent;
  legacy CSS names are re-pointed so every old class still renders. Real tooling drift (shadcn
  CLI v4.21: --base library + named presets, Base UI default; `timeout` absent on macOS) and a
  real init bug (it clobbered legacy --muted/--accent) were worked through. 23 routes build;
  every route live-smoked; 3,738 tests unaffected. IMPORTANT: shadcn CLI is v4.x - always read
  `pnpm dlx shadcn@latest <cmd> --help` before assuming flags. No browser tool exists in these
  sessions - the founder eyeballs http://localhost:4321.
- R-492 (2026-09-19, done) shipped the first visible screens of the overhaul: split-screen
  sign-in / create-account with real inline validation (mirroring the server's limits,
  aria-invalid/aria-describedby, role="alert" server banner, loading state, show/hide password;
  signed-in visitors bounce to /), a shared components/app-shell.tsx (skip link to #main, sticky
  header, AppNav with aria-current, UserMenu on a real Radix DropdownMenu with sign-out -
  app/logout-button.tsx deleted), app/not-found.tsx, and a real dashboard on / with live
  provider status via getProviderStatus(). IMPORTANT structural fact: screens were NOT moved into
  route groups because eight earlier scripts/test.sh blocks assert the literal current paths
  (app/login/page.tsx, app/studio/layout.tsx containing getCurrentUser, app/settings/layout.tsx,
  studio-icons.tsx) - keep that layout, or update those blocks deliberately. AppShell's <main>
  keeps the legacy .studio-main geometry on purpose until R-493 rebuilds the Studio grid. Two
  SSR facts learned while smoking: React 19 emits noValidate/autoComplete/maxLength camelCase
  in HTML, and inserts <!-- --> between adjacent text nodes - dump raw tags before believing a
  grep. The console is running detached on 4321 (log in the session scratchpad).
- R-493 (2026-09-19, done) rebuilt the Studio core: AppShell layout="full" (header container
  follows the prop), .studio-grid = chat rail LEFT minmax(340px,400px) + workspace RIGHT at
  calc(100dvh - 3.5rem) each scrolling internally; role="log" thread, working bubble with the
  live character count + shimmer skeletons, skeleton hydration, "What do you want to build?"
  empty state with three real example prompts (proven runnable by a real 9s streamed build, 173
  files), composer with field-sizing-content auto-grow, New app action, workspace progress bar,
  designed empty workspace, compact project header (StudioWorkspace now takes {snapshot,
  buildId}) above the untouched StudioTabs. studio-icons.tsx is a thin Lucide shim because R-475
  pins the file and studio-tabs/preview still import it - R-494 should switch those to Lucide
  directly and retire the shim + the R-475 assertion deliberately. Chat logic in studio-chat.tsx
  is byte-for-byte the R-485 version (hydration, three-shape SSE parser, edit, 404 recovery) -
  do not "clean it up" casually. Known R-477 degradation still open: after ?build= rehydration
  the Files/Code tabs are empty until the next edit (no snapshot) - R-494 could fetch
  /api/jobs/build/{id}/files on hydration. LESSON: scripts/verify.sh runs scripts/test.sh
  first, so a failing contract block makes `task verify` run ZERO tests - always confirm the
  "Ran N tests" line, never an empty tail.
- R-494 (2026-09-19, done) rebuilt the four Studio tabs on the vendored shadcn Tabs + Lucide:
  Files = collapsible tree (file-tree-model.ts pure buildFileTree/ancestorsOf/countFiles +
  file-tree.tsx FileTree; expansion derived from top-level + selected-file ancestors with user
  toggles as overrides), Code = tree pane + viewer (sticky header, unchanged tokenizeCodeLine on
  .code-tok-* colors), Problems = Check button + per-file cards + parseDiagnostic for tsc
  "L12:5 TS2339: msg" lines (verbatim fallback), Preview = unchanged state machine + toolbar
  (StatusPill, URL, Open in new tab, WIDTH_PRESETS Desktop/Tablet/Phone, Restart/Stop). The file
  list is now fetched on ?build= hydration (fetchBuildFiles, module scope). studio-icons.tsx is
  GONE - the R-475 and R-493 test.sh assertions were edited to match; every Studio file imports
  Lucide directly. Remaining legacy CSS to sweep in R-496: .spinner/.pill/.pill--accent (pinned by
  the R-475 assertion), the .wrap/.masthead/.panel/.grid/.stat/.badge/.button family (used by
  /settings and /fabric until R-495), .settings-active-now, .studio-intro. In build-only mode the
  preview route returns 404 (tab shows the disabled state) and the problems POST returns 409
  "tsc is not installed" - both honest; run `task agent-engine:studio:preview` to see them live.
- R-495 (2026-09-19, done) rebuilt /settings (sticky section nav; Account facts; Appearance
  with components/theme-switcher.tsx - System/Light/Dark on next-themes, hydration-safe via
  useSyncExternalStore, NOT a useEffect mounted flag: the react-hooks/set-state-in-effect ESLint
  rule IS enabled in this repo and fails the build on setState inside an effect; Model providers
  as cards with ProviderInfo.keyEnv "Set X_API_KEY in .env" hints) and /fabric (snapshot badge,
  captioned Tailwind tables, DiffBlock) and swept 266 lines of legacy CSS. globals.css is now
  ~367 lines: tokens, base, .grain (absolute, scoped), the R-475-pinned .pill/.pill--accent/
  .spinner + @keyframes spin, .studio-grid/.studio-progress, .code-tok-* colors. LESSON: never
  write "*/" inside a CSS comment (e.g. "--radius-*/"); it terminates the comment and breaks the
  Turbopack build with a CssSyntaxError. R-496 retires the pinned selectors by editing the R-475
  scripts/test.sh block deliberately.
- R-496 (2026-09-19, done) finished the overhaul: app/studio/loading.tsx + app/settings/
  loading.tsx (under their gated layouts), streamed provider cards inside <Suspense> on / and
  /settings, app/error.tsx (Next 16 `retry()` prop) + app/global-error.tsx, metadataBase from
  the optional OMNISTACKAI_CONSOLE_PUBLIC_URL (.env.example) with a dev fallback, openGraph/
  twitter metadata + app/opengraph-image.tsx (ImageResponse from next/og; twitter-image.tsx
  re-exports it), the .reveal utility + lib/motion.ts revealStyle(), tinted shadows via
  --shadow-tint, and every legacy selector/alias gone (globals.css 330 lines; the R-475 test.sh
  block now asserts only --radius-sm/md/lg). HARD-WON RULE: never add a root app/loading.tsx -
  a Suspense boundary ABOVE a redirect() turns it into a streamed 200 + client-side refresh
  (signed-out / and /studio answered 200 until it was removed); scripts/test.sh now fails if the
  file exists. Put loading.tsx only under gated layouts, and stream slow pieces inside pages
  with <Suspense> below the gate. Also: rg -qF patterns that start with "--" need a "--" before
  them. THE SIX-TASK UI OVERHAUL (R-491..R-496) IS COMPLETE - the founder should eyeball the whole
  product at http://localhost:4321 and share the Emergent/Lovable/Dyad screenshots if a further
  visual pass is wanted.
- R-497 (2026-09-19, done): the founder's 96 reference screenshots live at
  ~/Desktop/AI_Platform_Screenshots (folders `Dyad`, `Emergent ` (trailing space), `Lovable
  Screenshots`); LOVABLE is the chosen primary reference (also in the memory notes). Shipped:
  components/home-composer.tsx (home hero composer -> /studio?prompt=), studio-chat.tsx reads
  ?prompt= (never with ?build=), initializes the composer from it and auto-starts ONE build via
  formRef.current.requestSubmit() in a ref-guarded effect (DOM call, not setState - the
  set-state-in-effect rule would fail otherwise), prose assistant rows, FOLLOW_UP_PROMPTS chips,
  FileFilter in studio-tabs.tsx, "Read only" viewer label. Never add facade UI for Lovable
  features without a backend (Cloud DB, Publish, Payments). A project switcher needs a per-user
  build list endpoint first.
- R-498 (2026-09-19, done) is the plan for everything that comes next. **Start here:**
  `R_&_D/OmniStackAI_Platform_Buildout_v1.md` (decisions for every feature, the GitHub App
  mechanism, the Skills design, the dependency graph) and `R_&_D/specs/F-01…G-05` (15 specs, each
  with UI + SQL migration + API + flow + acceptance). **Run the platform with one command:**
  `./scripts/omnistack.sh up` (preview mode by default; `--no-preview` is the safe build-only
  mode), plus `status`, `logs <svc> [-f]`, `down`, `doctor`, `build`, `verify`; `task up`/`down`/
  `status`/`logs` alias it. Facts proven in R-498: the preview engine works (30 s build, 5 s
  preview, the running app served) — "preview not working" was build-only mode; generated apps
  bind to `127.0.0.1` so previews are loopback-only (F-02 adds a same-origin proxy); **the build
  history and editable IR are in memory, so all projects are lost on restart** (F-01 fixes it);
  `/jobs/build/{id}/files` has no per-user ownership check (F-01 closes it); preview already
  creates a real per-app Postgres (F-09 can be honest); every build is already a git repo (F-03
  only needs a remote + token + UI). SHELL LESSONS baked into `omnistack.sh`: never end a loop
  body with `cond && cmd` under `set -e`, and `lsof` exits 1 on a free port, which trips
  `pipefail`.
- NEXT: **F-01 → R-499, projects persisted per user** (read `R_&_D/specs/F-01-projects.md`).
  Gated on the founder: G-01 hosting model, G-03 connectors + OAuth apps, G-04 payment test
  accounts. After the UI overhaul
  (not yet scoped): real multi-target Publish/deploy (Netlify one-click primary, Vercel/Cloudflare/
  self-host/GitHub-export as secondary options), Node.js backend codegen alongside Python/Go, and
  mobile (React Native near-term). Full per-user process/tenant isolation as a wholesale architecture
  (beyond just which sandbox technology runs one preview - session-to-instance routing, per-user
  DB/port allocation, state-store externalization) remains a separate, materially larger
  architecture decision needing its own explicit founder sign-off before any implementation, per
  the standing "stop and ask for hard-gate architecture decisions" rule.
  Keep `task verify` model/Docker/DB-free at its core (the console's own build/lint/typecheck gates need
  no live control-plane; any live/model path stays opt-in); preserve single-session ownership and
  explicit trusted-local mode.
- PROVEN THIS SESSION: a generated app runs live locally on the Mac (Next.js :3000 + FastAPI :8000 +
  seeded PostgreSQL). Run the Next binary directly (`./node_modules/.bin/next dev`), not `pnpm dev`
  (pnpm 11's pre-run check exits 1 on the sharp ignored-build). Backend needs a venv (pyenv hides pip).
- Needs a network/cloud environment (defer until the local product is ready): Tier-2 cloud preview +
  deploy (OMNISTACKAI_TIER=2 + E2B/Vercel keys) and cloud-model live-verify. Governance-deferred: native
  mobile (R-010 etc.) until web/backend stability.

Begin by reading the files above and `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, run the start
protocol, then continue at R-472 (Phase C: bridge the control-plane's Job API to the agent-engine so
credits actually get debited) and write its Standard AI Task Contract before writing code.
```

