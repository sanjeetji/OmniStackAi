# OmniStackAI — implementation progress (as of R-347)

A living summary of what is built, what is pending, and how to see results. Numbers come from the
execution tracker (`R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx`, `Phase_Roadmap`).

## Headline

- **1,535 automated tests pass**, fully offline and network-independent (`task verify`).
- **136 tracker tasks Done, 1 Deferred, 210 Not Started** across 347 tasks (355 total spreadsheet rows).
- The offline builder loop is complete end to end: **describe (IR) → generate (web with typed API client, React hooks, interactive master-detail screen components with field validation, page size selector & contextual empty states, bulk selection & batch deletion, CSV data export & bulk export, deep-linking & entity lifecycle in detail screens, global responsive navigation shell & header navbar with active route detection & quick-create CTA, post-submit contextual CTAs & record navigation with Cancel action in form footer, rich entity-aware dashboard overview page (live count cards, screen nav tiles, quick-create CTAs, diff-stable), record selector dropdown, prev/next record navigation & deep-link sync in detail screens, form screen dirty state tracking, unsaved changes guard & reset confirmation, collection screen boolean & enum field filtering with segmented controls, global notification toast system & action feedback with ToastProvider & useToast, subcollection navigation, child item deletion & mutation feedback, full-stack update/edit actions, foreign-key relation selectors & parent auto-population, App Router resilience quartet, full loading-skeleton coverage, consistent error & retry recovery, enterprise WAI-ARIA accessibility semantics, power-user collection, detail, and form keyboard navigation & shortcuts, form input constraints & live character counters, search clear affordances & form first-field autofocus, collection status badges & detail copy affordances, overview interactive entity links, health badge & metrics chips, accessible modal confirmation dialog replacing window.confirm(), keyboard shortcuts help modal & global discovery affordance, accessible breadcrumb navigation component & screen hierarchy, accessible EmptyState component & screen zero-state integrations, collection screen JSON data export & bulk selection export controls, accessible reusable Pagination component, accessible reusable Tabs component, collection table display density toggle (Compact, Comfortable, Spacious), accessible reusable Badge component, collection table column visibility dropdown & selector controls, accessible reusable Tooltip component, accessible reusable Card compound component, accessible reusable Alert & Notification component, accessible reusable Skeleton loader compound component, accessible reusable Drawer / Sheet compound component, accessible reusable Avatar & AvatarGroup compound component, accessible reusable Toggle Switch component, accessible reusable Accordion compound component, accessible reusable Dropdown Menu compound component, accessible reusable Popover compound component, Design Tokens & CSS Custom Properties Theming Engine (styles/tokens.css), accessible reusable Theme Switcher / Mode Toggle component (components/theme-toggle.tsx), accessible reusable Dialog / Modal component (components/dialog.tsx), accessible reusable Form Controls & Input Primitives suite (components/form-controls.tsx), accessible reusable Date Picker & Calendar component (components/date-picker.tsx), accessible reusable Data Grid / Table component (components/data-grid.tsx), accessible Command Palette / Search Menu component (components/command-palette.tsx), accessible reusable Slider & Range component (components/slider.tsx), accessible reusable Progress & Spinner component (components/progress.tsx), accessible reusable Rating & Review component (components/rating.tsx), accessible reusable Stepper / Multi-step Wizard component (components/stepper.tsx), accessible reusable File Upload / Dropzone component (components/file-upload.tsx), accessible reusable Timeline / Activity Feed component (components/timeline.tsx), accessible futuristic reusable Stat & Metric KPI Card component (components/stat-card.tsx), accessible reusable Hierarchical Tree View component (components/tree-view.tsx), accessible futuristic reusable Tag & Chip Input Tokenizer component (components/tag-input.tsx), accessible futuristic reusable Code Block & Syntax Presentation component (components/code-block.tsx), accessible futuristic reusable Radial Gauge & Activity Rings component (components/radial-gauge.tsx), accessible futuristic reusable Segmented Control & Mode Switcher component (components/segmented-control.tsx), accessible futuristic reusable Carousel & Slider Showcase component (components/carousel.tsx), accessible futuristic reusable Resizable Panels & Splitter component (components/resizable.tsx), accessible futuristic reusable Color Picker & Palette Swatch component (components/color-picker.tsx), accessible futuristic reusable PIN & OTP Code Input component (components/pin-input.tsx), accessible futuristic reusable Speed Dial & Floating Action Button component (components/speed-dial.tsx) + API with
  working CRUD incl. PATCH/PUT update + pagination + sorting + total count header + keyword search + sub-collections + DB schema + data-access + JWT-verified auth
  & per-endpoint roles + field validation + CORS middleware + OpenAPI 3.1 contract)
  → verify → edit → commit to an owned Git repo.**

## Completion by phase

| Phase | Done | Total | % complete |
|-------|------|-------|-----------|
| **MVP** (current milestone) | 136 | 242 | **56.2%** |
| MID | 0 | 47 | 0% |
| ADVANCED | 0 | 29 | 0% |
| PRODUCTION | 0 | 29 | 0% |
| **Overall program** | **136** | **347** | **39.2%** |










> The 210 "Not Started" rows are largely the pre-existing backlog catalogue (R-010..R-219 — many are
> individual specialized agents and later-phase features). Capability-wise the platform is further along
> than the raw ~25% suggests, because the work done so far is the **core engine + builder**, which
> everything else builds on. The MVP figure (~40%) is the truest near-term measure. (The MVP lane has
> grown as founder-requested builder work was split into explicit implementation rows. The previously
> reported "145 MVP tasks at R-251" was one low: direct recount of that workbook is 146. R-252..R-296
> added 45 rows, producing the current 191. Equivalently, current MVP contains 114 rows from R-001..R-219
> and 77 founder-requested rows from R-220..R-296.)

## Capabilities — completed vs pending

| Area | Status | Notes |
|------|--------|-------|
| Repo/monorepo bootstrap, Task runner, Stage-0 verify | ✅ Done | R-001 |
| Local PostgreSQL + pgvector (platform DB) | ✅ Done | R-002 |
| Local Ollama config + lifecycle + live inference | ✅ Done | R-003 |
| Go control-plane (config, health, shutdown) | ✅ Done | R-004 |
| Model provider contract + registry | ✅ Done | R-005 |
| Local Ollama adapter (bounded, streaming) | ✅ Done | R-006 |
| Balanced gateway router (escalation ladder) | ✅ Done | R-007 |
| Cloud provider catalog (11 providers + custom) | ✅ Done | R-008, R-236 |
| SSE streaming, fallback + circuit breaker | ✅ Done | R-220, R-221, R-223 |
| Usage + cost accounting (price book) | ✅ Done | R-009 |
| Platform console (static, model/cost overview) | ✅ Done | R-222 |
| Application IR + validator/normalizer + fixtures | ✅ Done | R-225, R-231 |
| Code adapters: Next.js web, FastAPI, Go | ✅ Done | R-227, R-229, R-230 |
| Project assembler (one IR → monorepo) | ✅ Done | R-232 |
| Git service (materialize → owned repo) | ✅ Done | R-228 |
| Runtime/deploy provider layer + tier switch + drivers | ✅ Done | R-233, R-234 |
| Verifiable-engineering verify plans | ✅ Done | R-235 |
| Edit loop (IR-diff → patch-apply → commit) | ✅ Done | R-237 |
| PostgreSQL schema/migration from the IR | ✅ Done | R-238 |
| Data-access/repository layer (Python + Go) | ✅ Done | R-239 |
| Route wiring — handlers → repositories (real CRUD) | ✅ Done | R-240 |
| Authentication guards (enforce IR `auth` flag) | ✅ Done | R-241 |
| JWT verification (HS256, secret from env) | ✅ Done | R-242 |
| Per-endpoint role enforcement (IR `required_roles` → 403) | ✅ Done | R-243 |
| Sub-collection route wiring (parent-scoped lists) | ✅ Done | R-244 |
| Combined build/verify/preview plan surface | ✅ Done | R-245 (`task plan:show`) |
| Richer edit-loop diff (hunk-level + rename detection) | ✅ Done | R-246 |
| Static-console builder proof (real plan + unified patch) | ✅ Done | R-247 (`task console:serve`) |
| Seed data from explicit IR fixtures (`migrations/0002_seed.sql`) | ✅ Done | R-248 |
| Schema indexes + unique constraints (IR `Field.unique`/`Entity.indexes`) | ✅ Done | R-249 |
| Field validation -> schema + Pydantic (max_length, enum) | ✅ Done | R-250 |
| Field validation -> Go tags + numeric min/max (all 3 targets) | ✅ Done | R-251 |
| Go validation enforcement (validator.Struct → 400 on create+update) | ✅ Done | R-252 |
| **Structured JSON validation error bodies** (per-field field/rule/message) | ✅ Done | R-254 |
| **Query parameter pagination** (`limit` & `offset` on list endpoints) | ✅ Done | R-255 |
| **PUT update handlers** (full-replace CRUD verb wired) | ✅ Done | R-256 |
| **Frontend Typed API client** (`apps/web/lib/api.ts`) + **Backend CORS** | ✅ Done | R-257 |
| **Query parameter sorting** (`sort` & `order` with whitelist protection) | ✅ Done | R-258 |
| **Total count queries & `X-Total-Count` header** (Go, FastAPI, Next.js) | ✅ Done | R-259 |
| **OpenAPI 3.1 specification generation** (`render_openapi`, `contracts/openapi.json`) | ✅ Done | R-260 |
| **Full-text & keyword search filtering** (`q` query param across Go, FastAPI, Next.js, OpenAPI) | ✅ Done | R-261 |
| **React data-fetching & mutation hooks** (`apps/web/lib/hooks.ts` for Next.js web client) | ✅ Done | R-262 |
| **Interactive Screen Component Generator** (live React client components, search, pagination, forms in `apps/web/app/<screen>/page.tsx`) | ✅ Done | R-263 |
| **Field-level validation & error feedback** (per-field errors, accessible borders, client pre-validation) | ✅ Done | R-264 |
| **Subcollection navigation & master-detail views** (nested detail views, total count badges, child lists) | ✅ Done | R-265 |
| **Update/Edit mode in forms & collection screen edit actions** (dual-mode forms, editId prefill, table edit actions) | ✅ Done | R-266 |
| **Foreign-key relation selectors & parent auto-population** (typed dropdowns, parent title display, searchParams prefill) | ✅ Done | R-267 |
| **Subcollection child item deletion & mutation feedback** (child deletion, confirm prompt, error alert, refetch) | ✅ Done | R-268 |
| **Page size selector & contextual empty state CTAs** (configurable page size, Clear search, + Create first, + Add first child) | ✅ Done | R-269 |
| **Bulk selection & batch deletion in collection screens** (multi-row checkboxes, contextual toolbar, batch delete, confirmation prompt, mutation progress & errors) | ✅ Done | R-270 |
| **CSV data export & bulk export in collection screens** (client-side RFC 4180 export, full-page Export CSV button, contextual Bulk Actions Export Selected, Blob URL lifecycle) | ✅ Done | R-271 |
| **Deep-linking & entity lifecycle in detail screens** (query param auto-load, single-record JSON export, edit/delete actions, collection View link, breadcrumbs) | ✅ Done | R-272 |
| **Post-submit contextual CTAs, record navigation & Cancel in form screens** (`lastSavedId`, View →, ← Back, + Create another, Dismiss, Cancel link button) | ✅ Done | R-274 |
| **Rich entity-aware dashboard overview page** (`"use client"`, `useList<Entity>` live count cards, screen nav tiles, Quick Actions CTAs, diff-stable — no `ir.description` in output) | ✅ Done | R-275 |
| **Detail screen record selector, prev/next navigation & deep-link sync** (interactive dropdown, sequential record cycling, `window.history.replaceState` sync, recent records grid) | ✅ Done | R-276 |
| **Form screen dirty state tracking, unsaved changes guard & reset confirmation** (deterministic `isDirty`, header & footer badges, guarded Cancel & Reset, `beforeunload` listener) | ✅ Done | R-277 |
| **Collection screen boolean & enum field filtering with segmented controls** (FieldType.BOOL, enum dropdowns, active filter indicators, dedicated empty filter state) | ✅ Done | R-278 |
| **Global notification toast system & action feedback** (ToastProvider, useToast hook, fixed bottom-right viewport, auto-dismiss, action feedback in collections, details, forms) | ✅ Done | R-279 |
| **Deep-linked collection list state + debounced, race-safe search** (URL sync of sort/order/q/page/pageSize, AbortController refetch, 300ms search debounce) | ✅ Done | R-280 |
| **Subcollection list controls** (search + sort select + pagination footer on master-detail child lists) | ✅ Done | R-281 |
| **Server-side boolean/enum field filters** (`?field=` on LIST endpoints; Go + FastAPI + OpenAPI; whitelisted, parameterized) | ✅ Done | R-282 |
| **Next.js collection controls wired to server filters** (allowlisted hook state → `?field=` request params; pagination reset + URL sync; no page-local filtering) | ✅ Done | R-283 |
| **Server-side boolean/enum filters on FK-scoped subcollections** (FastAPI + Go + OpenAPI LIST_BY; relation/search/filter order preserved; parameterized list/count predicates) | ✅ Done | R-284 |
| **Next.js subcollection controls wired to scoped server filters** (typed allowlisted hook state → LIST_BY query params; both parent views; filtered-empty recovery; no page-local filtering) | ✅ Done | R-285 |
| **Race-safe generated subcollection refetches** (AbortController per LIST_BY hook; stale success/error/loading writes blocked; parent deselection and cleanup cancel in-flight work) | ✅ Done | R-286 |
| **Race-safe generated detail refetches** (AbortController per `use<Entity>` GET hook; internal signal after caller options; stale success/AbortError/loading writes blocked; id-change/unmount cleanup aborts) | ✅ Done | R-287 |
| **Deduplicated in-flight mutation requests** (`useCreate`/`useUpdate`/`useDelete` return the pending promise while in flight; a double-click cannot fire a duplicate write) | ✅ Done | R-288 |
| **Debounced live subcollection search** (subcollection search-as-you-type, 300ms debounce → race-safe LIST_BY hook; parity with top-level search) | ✅ Done | R-289 |
| **Optimistic delete with rollback** (collection rows vanish instantly on single/batch delete; reappear + error toast on failure; reconcile-on-refetch) | ✅ Done | R-290 |
| **Optimistic subcollection child delete** (child rows vanish instantly on delete; reappear + error toast on failure; per-subcollection reconcile) | ✅ Done | R-291 |
| **Loading skeletons** (layout-preserving skeleton placeholders across every generated data-loading state: collection table, subcollection lists, detail-main, form edit-mode initial load, and detail record-selector list) | ✅ Done | R-292, R-293 |
| **App Router resilience** (generated `app/error.tsx` + `app/global-error.tsx` error boundaries with reset(), `app/not-found.tsx` 404, and `app/loading.tsx` route-level Suspense skeleton fallback) | ✅ Done | R-294 |
| **Error + Retry across every fetch state** (collection list, detail main, and both subcollection lists each render a Retry button that calls the relevant `refetch()`) | ✅ Done | R-280, R-295 |
| **Accessible confirmation dialog replacing window.confirm** (ConfirmDialog component, useConfirm hook, focus trapping, Escape dismiss, backdrop dismiss, danger/primary variants) | ✅ Done | R-304 |
| **Keyboard shortcuts help modal & global discovery affordance** (ShortcutsDialog modal component, ? hotkey listener in navbar, Shortcuts (?) trigger button, <kbd> cheatsheet) | ✅ Done | R-305 |
| **Accessible breadcrumb navigation component & screen hierarchy** (Breadcrumbs component, WAI-ARIA 1.2 breadcrumb trail, detail and form screen wayfinding) | ✅ Done | R-306 |
| **Accessible EmptyState component & screen zero-state integrations** (EmptyState component, WAI-ARIA status card, vector SVG illustrations, action dispatch) | ✅ Done | R-307 |
| **Collection screen JSON data export & bulk selection export controls** (RFC-formatted JSON blob export, toolbar Export JSON, bulk action bar export) | ✅ Done | R-308 |
| **Accessible reusable Pagination component** (Pagination component, WAI-ARIA nav, page size selector, dynamic ellipsis, compact mode) | ✅ Done | R-309 |
| **Accessible reusable Tabs component** (Tabs & TabPanel components, WAI-ARIA tablist/tab/tabpanel, roving tabIndex, keyboard navigation, line/pills variants) | ✅ Done | R-310 |
| **Collection table display density toggle** (Compact/Comfortable/Spacious density toggle, dynamic cell padding, fontSize, data-density attribute) | ✅ Done | R-311 |
| **Accessible reusable Badge component** (Badge component, WAI-ARIA status role, 5 semantic variants, dot indicator with pulse, sm/md sizing) | ✅ Done | R-312 |
| **Collection table column visibility dropdown & selector controls** (Columns ▾ dropdown, checkbox toggles, dynamic th/td rendering) | ✅ Done | R-313 |
| **Accessible reusable Tooltip component** (Tooltip component, WAI-ARIA tooltip role, 4 placement directions, Escape dismiss) | ✅ Done | R-314 |
| **Accessible reusable Card compound component** (Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, 4 variants) | ✅ Done | R-315 |
| **Accessible reusable Alert & Notification component** (Alert, AlertTitle, AlertDescription, 4 status variants, dismiss button) | ✅ Done | R-316 |
| **Accessible reusable Skeleton loader compound component** (Skeleton, SkeletonText, SkeletonCard, SkeletonTable, pulse/wave/none animations) | ✅ Done | R-317 |
| **Accessible reusable Drawer / Sheet compound component** (Drawer compound, left/right/top/bottom placements, backdrop blur, scroll lock) | ✅ Done | R-318 |
| **Accessible reusable Avatar & AvatarGroup compound component** (Avatar, AvatarGroup, image/initials/icon cascade, status dots, overflow pill) | ✅ Done | R-319 |
| **Accessible reusable Toggle Switch component** (Toggle component, WAI-ARIA switch role, keyboard Space/Enter, sm/md/lg sizes) | ✅ Done | R-320 |
| **Accessible reusable Accordion compound component** (Accordion compound, single/multiple modes, collapsible, rotating chevron indicator) | ✅ Done | R-321 |
| **Accessible reusable Dropdown Menu compound component** (DropdownMenu compound, WAI-ARIA menu/menuitem, Arrow traversal, shortcut slots) | ✅ Done | R-322 |
| **Accessible reusable Popover compound component** (Popover compound, WAI-ARIA dialog, click-outside and Escape dismiss, orientation arrow) | ✅ Done | R-323 |
| **Design Tokens & CSS Custom Properties Theming Engine** (tokens.css, semantic colors, light/dark themes, spacing/typography scales) | ✅ Done | R-324 |
| **Theme Switcher / Mode Toggle component** (ThemeProvider, useTheme, ThemeToggle button, ThemeSelect segmented control, ThemeScript) | ✅ Done | R-325 |
| **Accessible reusable Dialog / Modal component** (Dialog compound, WAI-ARIA dialog, backdrop overlay, body scroll lock, sm-full sizing) | ✅ Done | R-326 |
| **Accessible reusable Form Controls & Input Primitives suite** (Input, Textarea, Select, Checkbox, RadioGroup, Label, FormField) | ✅ Done | R-327 |
| **Accessible reusable Date Picker & Calendar component** (DatePicker, Calendar, month grid traversal, WAI-ARIA grid/dialog, zero dependencies) | ✅ Done | R-328 |
| **Accessible reusable Data Grid / Table component** (DataGrid, generic ColumnDef<T>, sortable headers, row selection, density presets) | ✅ Done | R-329 |
| **Accessible Command Palette / Search Menu component** (CommandPalette, Cmd+K listener, query filtering, combobox/listbox pattern) | ✅ Done | R-330 |
| **Accessible reusable Slider & Range component** (Slider, single/range modes, pointer dragging, keyboard traversal, WAI-ARIA slider) | ✅ Done | R-331 |
| **Accessible reusable Progress & Spinner component** (ProgressBar, CircularProgress, Spinner, determinate/indeterminate, SVG stroke math, WAI-ARIA progressbar) | ✅ Done | R-332 |
| **Accessible reusable Rating & Review component** (Rating, fractional star fills, hover preview, interactive & read-only modes, WAI-ARIA slider) | ✅ Done | R-333 |
| **Accessible reusable Stepper / Multi-step Wizard component** (Stepper, numbered/pill/dot variants, horizontal/vertical orientations, WAI-ARIA list) | ✅ Done | R-334 |
| **Accessible reusable File Upload / Dropzone component** (FileUpload, drag-and-drop, mime/size validation, file previews, progress simulation) | ✅ Done | R-335 |
| **Accessible reusable Timeline / Activity Feed component** (Timeline, connected track line, custom status icons, compact/detailed modes) | ✅ Done | R-336 |
| **Accessible futuristic Stat & Metric KPI Card component** (StatCard, glass/neon styling, trend delta arrows, pure SVG Catmull-Rom sparklines) | ✅ Done | R-337 |
| **Accessible reusable Hierarchical Tree View component** (TreeView, recursive nodes, connector lines, search filter auto-expansion, WAI-ARIA 1.2) | ✅ Done | R-338 |
| **Accessible futuristic Tag & Chip Input Tokenizer component** (TagInput, autocomplete suggestions, delimiter parsing, chip traversal, WAI-ARIA combobox) | ✅ Done | R-339 |
| **Accessible futuristic Code Block & Syntax Presentation component** (CodeBlock, multi-tab snippets, zero-dep tokenizer, line highlighting, animated copy) | ✅ Done | R-340 |
| **Accessible futuristic Radial Gauge & Activity Rings component** (RadialGauge, ActivityRings, pure SVG arc trigonometry, angle sweeps, threshold colors, WAI-ARIA meter) | ✅ Done | R-341 |
| **Accessible futuristic Segmented Control & Mode Switcher component** (SegmentedControl, sliding pill indicator animation, option badges, 4 visual variants, WAI-ARIA radiogroup) | ✅ Done | R-342 |
| Next.js console upgrade (rich UI) | ⏸ Deferred | R-224 — needs npm registry access |
| Live sandbox preview + real deploy (Tier 2) | ⛔ Pending | needs a network machine + provider keys |
| Native mobile agents | ⛔ Deferred (governance) | until web/backend stability (Brief §25/§91) |
| MID / ADVANCED / PRODUCTION phase work | ⛔ Not started | 105 rows |

## Can I see a result today? Yes — offline, on your Mac

Everything below runs with **no cloud keys** and no internet (except where noted). From the repo root:

1. **See the whole engine is real and green:**
   ```
   task verify            # 998 tests pass
   ```
2. **Generate a real app from a spec and inspect it** (the headline result):
   ```
   task builder:demo -- rideshare-favourites     # or: minimal-blog
   ```
   This turns one Application IR into a **25-file customer monorepo** (Next.js `apps/web` + Go/FastAPI
   `services/api` + a PostgreSQL `migrations/0001_init.sql`) inside a brand-new **Git repo owned by
   you**, and prints the file tree, the generated SQL schema, and the verify plans. The path it prints
   is a normal folder you can open, edit, and `git log`.
3. **See the model fabric / provider catalog / tiers / verify ladders:**
   ```
   task platform:status                      # active tier + which provider keys are present
   task agent-engine:verify-plan -- backend-go
   task console:serve                         # http://127.0.0.1:4321  (builder proof + model fabric)
   ```
4. **Run a real AI generation locally through the gateway** (uses your installed Ollama
   `qwen2.5-coder:14b`, zero cloud cost):
   ```
   task ollama:status
   task agent-engine:gateway:run
   ```

## When can I see the generated app running in a browser?

On **your Mac in a normal terminal** (not this sandbox), right now:

```
task builder:demo -- minimal-blog          # note the printed repo path
cd <that path>/apps/web && pnpm install && pnpm dev      # -> http://127.0.0.1:3000
cd <that path>/services/api && uvicorn app.main:app --reload   # (FastAPI)  -> :8000
#   or, for a Go backend:  cd <that path>/services/api && go run .            -> :8080
```

`pnpm install` needs internet the first time (this AI sandbox blocks the large Next.js binary download,
which is why the platform never runs it during `task verify`). On your own machine it works normally.

**One-click cloud preview and real deploy** (open a public URL without any local toolchain) arrive when
Tier 2 is turned on: add a provider key (e.g. `E2B_API_KEY` for a sandbox or `VERCEL_TOKEN` for a
deploy), set `OMNISTACKAI_TIER=2`, and run the runtime/deploy driver. The plumbing is built (R-233/234);
the live run needs the key + a network machine.

## What's next

Near-term MVP candidate: **R-296** = another generated-app UX/robustness increment — e.g. a reusable
EmptyState/error inline-state component to DRY the screens, an accessibility pass, or optimistic
create/update reflected in the collection list. The generated app now has full loading-skeleton coverage
(R-292 + R-293), the App Router resilience quartet (R-294), and consistent Error + Retry across every
fetch state (R-295). (The founder paused development after R-295; resume from R-296 via
`docs/RESUME_PROMPT.md`.) A Groq API key may be available for a separately chosen live model-fabric
verification (Balanced gateway → Groq, real cloud inference + cost accounting); keep it only in gitignored
`.env`. Then, on a network machine: live Tier-2 preview and deploy. This file is refreshed as tasks land.
