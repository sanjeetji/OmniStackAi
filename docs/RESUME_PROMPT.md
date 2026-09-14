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

WHAT IS ALREADY BUILT (platform generators are Python 3.13 stdlib-only, offline, in services/agent-engine; 2,984 tests pass)
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
Do NOT overwrite backlog rows; continue from R-359.
NOTE: the execution tracker's planned universe ends at R-358 (358 tasks: 147 Done, 1 Deferred, 210 Not
Started; MVP 147/253 = 58.1%). Work past R-358 now covers 80 completed tasks: 57 reusable UI-component
suites (R-359 -> R-415), four front-door bricks (R-416 -> R-419), generated-SQL hardening (R-420),
managed embedded trusted-local Studio preview (R-421), collision-free preview ports + status/stop/
restart controls (R-422), build history + re-preview (R-423), live preview status (R-424), per-build
repo actions - copy path + open folder (R-425), remove-from-history (R-426), a generated-JSX
inline-style fix (R-427), generated-app compile fixes + an opt-in tsc gate (R-428), strict generated-app
type cleanup (R-429), and the first ten differentiating-spine bricks (R-430 -> R-439).
The generated component library is 110 components. Its UI-COMPONENT SERIES IS PAUSED at R-415
(resumable under a future free ID; each component is independent/additive, nothing decays). Git, state files
(.ai/), CHANGELOG, and docs/PROGRESS.md remain the executable/detail sources of truth. Current through
R-439; `task verify` = 2,984 tests. R-416 added prompt-to-IR intake, R-417 materialized a generated
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
in codegen/nextjs.py for FK-editor / multi-subcollection / filterable-child shapes). No tracker workbook row
exists past R-358. R-432 added the third spine brick: an explicit local-model refinement layer for prompts
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
- R-430 through R-439 are DONE — the DIFFERENTIATING SPINE now proposes a curated multi-app ecosystem,
  materializes it as multiple owned repos, and can explicitly refine an unknown domain through local Ollama
  before using the same deterministic planner. R-433 then gives each surface a bounded read/write entity
  policy, relation-safe dependencies, one actor role, and role-gated mutations. R-434 registers immutable,
  versioned, digest-pinned verified baselines; R-435 exposes exact target-aware recommendations or no-match
  in ecosystem planning; R-436 captures bounded configuration/AI-delta intent in a strict pinned manifest;
  R-437 applies explicit allowlisted project metadata to a fresh validated IR with provenance and leaves
  AI-delta intent pending; R-438 converts pending manifest AI-delta intents into strict validated proposal
  data via an opt-in local ModelProvider boundary (0 calls when no AI-delta changes exist); R-439 safely
  applies validated AI-delta proposals to Application IR with pin/collision/relation revalidation, immutable
  merging, semantic validation, and byte-stable provenance tracking.
- NEXT R-440: wire derived Solution Pack Application IRs into verified multi-repo builder pipelines and
  project generation.
  Keep `task verify` model/Docker/DB/install/network-free (any live/model path stays opt-in); preserve
  single-session ownership and explicit trusted-local mode.
- The UI-component series remains paused at R-415 and can be resumed later under a future free ID.
- PROVEN THIS SESSION: a generated app runs live locally on the Mac (Next.js :3000 + FastAPI :8000 +
  seeded PostgreSQL). Run the Next binary directly (`./node_modules/.bin/next dev`), not `pnpm dev`
  (pnpm 11's pre-run check exits 1 on the sharp ignored-build). Backend needs a venv (pyenv hides pip).
- Needs a network/cloud environment (defer until the local product is ready): Tier-2 cloud preview +
  deploy (OMNISTACKAI_TIER=2 + E2B/Vercel keys) and cloud-model live-verify. Governance-deferred: native
  mobile (R-010 etc.) until web/backend stability.

Begin by reading the files above and running the start protocol, then continue the spine at R-439
and write its Standard AI Task Contract before writing code.

```

