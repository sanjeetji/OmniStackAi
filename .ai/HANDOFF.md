# Current Handoff

Task ID: R-485
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main`

> **R-485 Completed (2026-09-19): Console — streaming build UI.**
> - Fast-follow to R-484, closing the loop it opened. `/studio`'s own chat now consumes
>   `POST /jobs/build/stream` for its create-path, replacing the static "Building…" wait with a
>   real, live-updating "Generating your app… (N characters so far)" indicator.
> - New `streamBuildApp()` (`lib/control-plane.ts`) returns the raw upstream `Response` (unlike
>   every other client function, which awaits parsed JSON) so a new proxy route
>   (`app/api/jobs/build/stream/route.ts`) can pipe it straight through unbuffered — one
>   pipe-through correctly handles both real shapes the control-plane can return (streamed SSE
>   success, or a plain buffered JSON pre-stream rejection).
> - `studio-chat.tsx` gains `sendBuildStream()`, replacing `sendBuild()`: `fetch()` + manual
>   `response.body.getReader()` framing (not `EventSource`, which cannot send a POST body),
>   handling three real frame shapes verified against R-484's own live output — `generating_ir`
>   deltas (only their length drives the character count; raw partial JSON is never shown, since
>   it would render as visibly broken text to a non-technical user), `"done"` (unchanged final
>   rendering), and a bare no-`phase` credits frame (the Go relay's trailing event). Edit stays
>   non-streaming, per R-484's own scope boundary.
> - **No browser-automation tool was available this session** (checked via `ToolSearch`) —
>   verified instead via `next start` (the real production build) plus `curl` driven through a
>   real, cookie-based login session — the exact same request path a real browser takes, exercising
>   the identical code path end to end.
> - Gates: `pnpm run typecheck`/`lint`/`build` all clean (21 routes, 1 new); repo `task
>   verify`/`lint`/`security:quick`/`env:check` all pass (3,658 agent-engine tests unaffected — no
>   backend file touched). **Live**: a real streamed build through the full console-proxy → Go
>   control-plane → agent-engine path showed genuine incremental frames over ~9 real seconds, a
>   real `done` frame (174 files, real commit sha), and a real trailing `credits` frame; a real
>   401/400 confirmed the auth/validation gates; a real follow-up edit on the same build confirmed
>   the edit path is completely unchanged.
> - **NEXT** (per "streaming first, then scope isolation properly"): properly SCOPE (not yet build)
>   full per-user process/sandbox isolation as its own multi-task project — a materially different
>   architecture decision needing explicit founder sign-off; the agent-engine has zero
>   containerization today and `scripts/test.sh` actively blocks adding it as a Compose service.
>   Publish/deploy and backend/mobile stack breadth remain named and directionally approved but not
>   yet scoped. See `.ai/tasks/R-485.md`.

> **R-484 Completed (2026-09-19): Backend — real-time build streaming (SSE).**
> - First of the founder's post-roadmap priorities ("streaming first, then scope isolation
>   properly"), chosen after three parallel research passes (competitor streaming architecture,
>   per-user isolation scoping, deploy/stack breadth). Backend only — console UI is R-485.
> - `ModelProvider.stream()` already existed at the `model_gateway` layer but `_build()`'s whole
>   call chain never called it. Added purely additive streaming twins: `generate_ir_stream()`
>   (`intake/nl_to_ir.py`), `build_app_from_prompt_stream()` (`intake/build_app.py`),
>   `_build_stream()` (`studio/live_serve.py`, plain-prompt-only — Solution Pack/Ecosystem/
>   `hybrid_ui` explicitly rejected via `StreamingBuildNotSupportedError`, matching `_edit()`'s own
>   scope precedent). New `POST /api/build/stream` (agent-engine SSE) and
>   `POST /jobs/build/stream` (Go relay via `http.Flusher`, appending a trailing `credits` event
>   once the upstream `done` event's usage is known — crediting can't happen mid-stream).
> - **Two real bugs found and fixed, not glossed over**: (1) the SSE route sent
>   `Connection: keep-alive`, which `BaseHTTPRequestHandler` treats as "never close this socket" —
>   with no `Content-Length`/chunked framing, that hung every real client; caught by the first
>   HTTP-level test, fixed to `Connection: close`. (2) `RecordingProvider` (every production
>   build's real usage-tracking wrapper) had no `.stream()` method — invisible to every mocked
>   test, only caught by the required live `curl -N` smoke test
>   (`'RecordingProvider' object has no attribute 'stream'`); fixed with 4 new tests mirroring
>   `generate()`'s own success/failure ledger-recording shape.
> - Gates: agent-engine `task verify` **3,658 OK** (27 new); control-plane `go build`/`vet`/`test`
>   all green (7 new, 55 total); repo `task verify`/`lint`/`security:quick`/`env:check` all pass;
>   new `scripts/test.sh` contract block. **Live**: a real `curl -N` session through the real Go
>   control-plane showed genuine token-by-token deltas over ~9 real seconds (timestamped, not
>   buffered), a real `done` frame (177 files, real git commit sha, real `usage`), and a real
>   trailing `credits` frame (`credits_spent: 0` — this environment's configured cloud model has no
>   price-book entry, a pre-existing unrelated fact); all three unsupported build kinds
>   (`pack_id`/`ecosystem_id`/`hybrid_ui`) confirmed cleanly rejected with a `400` before any SSE
>   framing began.
> - **NEXT** (per "streaming first, then scope isolation properly"): R-485 (console: streaming
>   build UI). Then properly SCOPE (not build) full per-user process/sandbox isolation — a
>   materially different architecture decision needing explicit founder sign-off; the agent-engine
>   has zero containerization today and `scripts/test.sh` actively blocks adding it as a Compose
>   service, which full isolation will need to explicitly revise. See `.ai/tasks/R-484.md`.

> **R-483 Completed (2026-09-19): Fix — dynamic-route slug collision & duplicate FK identifier.**
> - Second follow-up after the 7-task Phase D roadmap, per "complete one by one all." Fixes the
>   exact real bug found live during R-481's own smoke test: a Next.js dev-server crash
>   (`'counterId' !== 'counter_id'`) and a duplicate `lib/types.ts` identifier.
> - Root cause verified by direct source read: (1) the full-build prompt has no path-param casing
>   rule while the edit-delta prompt demanded snake_case, with nothing reconciling a new endpoint's
>   param against an existing one for the same resource; (2) `_entity_interface()` unconditionally
>   synthesized a `<relation>_id` FK field with no check against already-declared explicit fields.
> - Fixed at the structural root: `ApiEndpoint.__post_init__` now canonicalizes every `{param}` to
>   camelCase unconditionally (every construction path, not just the two known ones);
>   `_entity_interface()` now skips the synthesized FK when an explicit same-named field exists.
> - A pre-existing test's assertion (matching an old, inconsistent snake_case spelling) was updated
>   to the new correct camelCase expectation, confirmed not a functional regression — the generated
>   reader code already defensively checked the camelCase spelling as its own fallback.
> - Gates: agent-engine `task verify` **3,635 OK** (6 new); repo `task verify`/`lint`/
>   `security:quick`/`env:check` all pass. **Live**: reproduced the exact original scenario — built
>   the same counter app, sent the same edit, started the preview → real `ready`, no crash (grepped
>   the real log, error absent); one consistent dynamic route folder on disk; a real `tsc` check via
>   Problems → 0 duplicate-identifier errors; `lib/types.ts` inspected directly, no duplicate line.
> - **NEXT** (per "complete one by one all"): R-484 (real-time streaming, renumbered), per-user
>   multi-tenancy, and Publish/deploy each need an explicit founder architecture decision first.
>   See `.ai/tasks/R-483.md`.

> **R-482 Completed (2026-09-19): Model Provider settings UI.**
> - First follow-up after the 7-task Phase D roadmap shipped, per the founder's "complete one by
>   one all" direction. A real, live Dyad-style provider status page. `platform_overview()` already
>   existed (real, tested) but only ever generated a static snapshot for `/fabric` — no live
>   endpoint existed anywhere. New: calling `resolve_generation_provider_from_env()` safely reports
>   which provider would actually run the *next* build, never surfaced anywhere before.
> - New agent-engine `GET /api/providers` (build-only mode included); new control-plane
>   `GET /jobs/providers` (no debit); new authenticated `/settings` page (live "Ready" callout +
>   provider table, linked from the Studio topbar and home page).
> - **A real bug found AND FIXED during this task's own live smoke test** (introduced by this
>   task's own first draft): calling `platform_overview()` before `resolve_generation_provider_
>   from_env()` read the providers list's `active` flags *before* `.env` had been lazily loaded —
>   in a fresh process, every cloud provider showed "Needs key" even with a real key configured,
>   while `activeNow` (computed after the dotenv load) was correct. Fixed by reordering; verified
>   with `env -i` both reproducing and confirming the fix.
> - Gates: agent-engine `task verify` **3,629 OK** (4 new); control-plane `go test` all green (48
>   tests, 3 new); console `typecheck`/`lint`/`build` clean (20 routes, 2 new); repo
>   `task verify`/`lint`/`security:quick`/`env:check` all pass. **Live**: real `/api/providers` +
>   `/settings` both correct; **cross-verified `activeNow` against a real build** — the
>   agent-engine's own log showed real Groq rate-limit retries, confirming the real call matched
>   `activeNow`'s report exactly.
> - **NEXT** (per "complete one by one all"): scope and fix the dynamic-route slug-collision
>   codegen bug found live during R-481. See `.ai/tasks/R-482.md`.

> **R-481 Completed (2026-09-19): Tabbed workspace — the SEVENTH AND FINAL task of the
> founder-approved 7-task Phase D roadmap (R-475–R-481).**
> - Restructured `/studio`'s main pane into four real tabs — Preview, Files, Code, Problems — with
>   chat persisting alongside, assembling R-474 (files), R-477 (chat), R-479 (preview), and R-480
>   (problems) into one shell. Files and Code stay separate real tabs (founder's explicit choice),
>   sharing one lifted `selectedFile`. New `code-highlight.ts`: a hand-rolled tokenizer porting the
>   approach of `codegen/nextjs.py`'s own generated `tokenizeCodeLine` — no new dependency, confirmed
>   live it renders real generated TSX cleanly. Problems tab is an explicit on-demand button, per
>   R-480's own design.
> - Gates: console `typecheck`/`lint`/`build` clean (19 routes, 1 new); `task verify` **3,625 OK**
>   (unchanged); `task lint`/`security:quick`/`env:check` all pass. **Live** (Colima had stopped
>   again, restarted; real control-plane + real agent-engine Studio server in preview mode + fresh
>   `next start`): full loop confirmed — build → real Preview/Files/Code → real edit → confirmed
>   Files/Preview refresh → real Problems check.
> - **A real, pre-existing codegen bug found live** (unrelated to this task, not fixed): a Next.js
>   dynamic-route slug-name collision (`counterId` vs `counter_id`) from the edit-delta path —
>   correctly surfaced as an honest Preview error *and* independently caught by a real Problems
>   check (18 genuine TypeScript errors), cross-confirming R-479's and R-480's error-surfacing design
>   both work under real failure conditions.
> - **THIS COMPLETES THE APPROVED 7-TASK PHASE D ROADMAP.** The Studio is now a real chat-driven,
>   multi-pane workspace closer to Lovable/Dyad/Emergent parity.
> - **NEXT:** no pre-approved task remains queued. Named follow-ups: R-482 (Model Provider settings
>   UI), R-483 (real-time streaming — its prerequisite now exists), per-user backend
>   multi-tenancy, Publish/deploy, and the newly-found route-slug codegen bug. **Needs explicit
>   founder direction on priority before picking the next Tracker ID.** See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-481.md`, and the plan file.

> **R-480 Completed (2026-09-19): Backend — Problems/compile-report support.**
> - **Sixth of the founder-approved 7-task plan** (R-475–R-481). Real compile-error reporting for
>   the first time in this codebase — the founder's explicit choice over a placeholder. New
>   `studio/problems.py` mirrors `files.py`'s shape: resolves `apps/web`, raises `NoWebTargetError`
>   if there's no web app, remaps `verify/compile.py`'s real `compile_web_project()`'s `VerifyError`
>   into a clear `ToolchainNotInstalledError` — never silently installs dependencies. On-demand, not
>   automatic (`node_modules`/`tsc` only exist after a preview install). `StudioProblemsStore` is a
>   bounded per-build-id LRU cache mirroring `StudioSessionStore`.
> - New control-plane routes `POST`/`GET /jobs/build/{id}/problems`, no credit debit, a new
>   `defaultProblemsTimeout` (90s). Error mapping includes a new 409 for "toolchain not installed."
> - Gates: agent-engine `task verify` **3,625 OK** (21 new tests, no real toolchain needed —
>   injected fake `tsc` runner, mirroring `verify/compile.py`'s own test style); control-plane
>   `go test` all green (45 tests, 7 new); repo `task verify`/`lint`/`security:quick`/`env:check`
>   all pass. **Live**: build-only mode with no toolchain → real 409/404, no crash. Hit two real,
>   pre-existing environment issues unrelated to this task (a generated-migration collision, a
>   500ing preview page) worked through honestly. Preview mode with a real installed toolchain → a
>   real `tsc` run surfaced **10 genuine TypeScript errors** in an LLM-synthesized page — real,
>   substantial compiler output, explaining why that same preview page was 500ing. A repeated GET
>   returned the byte-identical cached report in 12ms.
> - **NEXT:** R-481 (tabbed workspace) — the final task of the approved 7-task roadmap. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-480.md`, and the plan file.

> **R-479 Completed (2026-09-19): Console — live preview UI.**
> - **Fifth of the founder-approved 7-task plan** (R-475–R-481). An iframe rendering the real
>   running generated app, wired to R-478's four routes.
> - Preview start is synchronous (confirmed live during R-478), so polling's job is crash
>   detection (5s interval while `status: "ready"`), not progress-watching. New `studio-preview.tsx`
>   triggers a re-preview whenever `buildId` becomes real or a `previewVersion` counter (bumped by
>   `studio-chat.tsx` after every edit) changes. A 404 renders an honest disabled message. Manual
>   Restart/Stop reuse the `RefreshIcon`/`StopIcon` that existed unused since R-475.
> - Every `PreviewStatus` shape verified by reading `preview.py` directly before implementation.
> - Gates: console `typecheck`/`lint`/`build` clean (18 routes, 4 new); `task verify` **3,604 OK**
>   (unchanged); `task lint`/`security:quick`/`env:check` all pass. **Live** (real control-plane +
>   real agent-engine Studio server in preview mode + fresh `next start`): build → real iframe-ready
>   preview (fetched `web_url` directly, got real HTML) → edit → real re-preview on a new port →
>   **killed the real preview OS process directly** to simulate an external crash — the next poll
>   correctly reported "stopped" → manual Restart/Stop both worked → build-only mode produced the
>   uniform honest 404 disabled state.
> - **NEXT:** R-480 (backend: Problems/compile-report support) per the approved plan. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-479.md`, and the plan file.

> **R-478 Completed (2026-09-19): Backend — live preview proxy (local-only).**
> - **Fourth of the founder-approved 7-task plan** (R-475–R-481). Four new control-plane routes
>   proxying the agent-engine's existing trusted-local preview control surface verbatim: the
>   singleton surface (`GET /jobs/preview`, `POST /jobs/preview/stop`, `POST /jobs/preview/restart`)
>   plus the build-scoped one (`POST /jobs/build/{id}/preview`) a chat-per-build UI actually needs.
>   All auth-required, no credit debit. Zero agent-engine changes.
> - **Verified, not assumed**: an unknown/evicted build's build-scoped preview route does not 404 —
>   it returns a real 200 `{"status":"error","message":"..."}`. Confirmed by source read before
>   writing the tests, then confirmed live too. The proxy forwards this shape unchanged.
> - Generalized `proxyGet` into `proxyUpstream(method, body)`. `handleBuildPreview` always
>   constructs its own `{"id": "<path id>"}` body server-side, never trusting the caller's. New
>   `defaultPreviewTimeout` (60s) applied to both `handleBuildPreview` and `handlePreviewRestart` —
>   the latter added during implementation once it was clear restart can itself cold-start.
> - Gates: control-plane `go test` all green (38 tests, 13 new); repo `task verify` **3,604 OK**
>   (unchanged, no agent-engine/console touched); `task lint`/`security:quick`/`env:check` all pass.
>   **Live** (real control-plane rebuilt + real agent-engine Studio server in preview mode): a real
>   build auto-started a real preview (real `pnpm install` + Next.js dev server + FastAPI backend,
>   including a real Groq rate-limit retry along the way); real status/stop/restart/build-preview all
>   proxied correctly; the 200-with-error shape confirmed live for an unknown build; credit balance
>   unchanged across all four calls; switching to build-only mode made all four routes return the
>   identical uniform 404.
> - **NEXT:** R-479 (console: live preview UI) per the approved plan. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-478.md`, and the plan file.

> **R-477 Completed (2026-09-19): Console — chat UI.**
> - **Third of the founder-approved 7-task plan** (R-475–R-481). Replaced `/studio`'s one-shot
>   prompt form with a persistent, multi-turn chat thread on R-475's shell, wired to R-476's new
>   `POST /jobs/build/{id}/edit` / `GET /jobs/build/{id}/turns` routes. `buildId` (`null` vs. set) is
>   the single piece of state deciding whether the composer calls `/jobs/build` or
>   `/jobs/build/{id}/edit` — same composer, same input box.
> - New `studio-chat.tsx` owns `messages`/`buildId`/`workspace` state; new `studio-workspace.tsx`
>   holds the `BuildResult`/`FileBrowser` pieces moved out of the retired `studio-form.tsx`,
>   generalized to a `WorkspaceSnapshot` an edit's narrower response can patch (re-fetching the file
>   list separately, since `_edit()`'s response has no `files` key). `buildId` persists in the URL
>   so a refresh hydrates chat *text* history from `/turns` — the workspace panel does not
>   rehydrate, an honest, named simplification.
> - **A real finding, verified by reading the actual source before writing the failure-mode handling
>   (not assumed from the plan sketch)**: `GET /turns` does not 404 for an unknown/evicted build —
>   it returns `{"turns": []}`, not an error. Only `_edit()`'s own `BuildNotFoundError` is a real,
>   reachable 404, so the "session no longer available" recovery is wired to a failed edit response,
>   not to turns-hydration.
> - Gates: console `typecheck`/`lint`/`build` clean (14 routes, 2 new); `task verify` **3,604 OK**
>   (unchanged, no backend touched); `task lint`/`security:quick`/`env:check` all pass. **Live** (real
>   control-plane + real agent-engine Studio server + a fresh `next start`): build → turns hydration
>   → follow-up edit with a refreshed file list → **the agent-engine Studio server was killed and
>   restarted mid-test to simulate a real stale session** — an edit against the now-stale `buildId`
>   returned a real 404, exactly what the recovery code checks for, while `/turns` against the same
>   stale id returned `200 {"turns": []}`, confirming the finding above live; a fresh build afterward
>   proved the full recovery loop.
> - **NEXT:** R-478 (backend: live preview proxy) per the approved plan. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-477.md`, and the plan file.

> **R-476 Completed (2026-09-19): Backend — multi-turn edit bridge.**
> - **Second of the founder-approved 7-task plan** (R-475–R-481). New control-plane routes
>   `POST /jobs/build/{id}/edit` and `GET /jobs/build/{id}/turns`, mirroring `POST /jobs/build`'s
>   exact proxy+debit shape (R-472), plus two real, verified fixes to the Python edit path found
>   during this roadmap's planning research (not assumed — confirmed by direct source reads):
>   `_edit()` had no `usage_ledger` at all, so every edit debited 0 credits regardless of real cost;
>   `_build()` never recorded its own chat turn, so a future chat hydrating history from `/turns`
>   after a refresh would silently lose the first message. Both fixed by mirroring `_build()`'s own
>   existing patterns exactly.
> - **Go side**: `handleBuildEdit`/`handleBuildTurns` added to `internal/jobs/handler.go`; the
>   shared "forward, decode, debit, inject" logic extracted out of `handleBuild` into a
>   `proxyAndDebit` helper both handlers now call — mirrors the `writeAuthError` extraction
>   precedent R-474 set. A no-op edit still charges real credits (the model call happened even if
>   the diff was empty) — locked in by a dedicated test, since it's non-obvious and easy to regress.
> - **Python side** (`studio/live_serve.py`): `_edit()` now threads a real `UsageLedger` through
>   `resolve_generation_provider_from_env`, adding a real `"usage"` key to both its response
>   branches; `_build()` now calls `session_store.record_turn` for its own user/assistant turn.
> - Gates: control-plane `go build/vet/test` all green (25 tests in `internal/jobs`, 10 new);
>   agent-engine `task verify` **3,604 OK** (0 model/network calls — stub-provider-mocked, matching
>   every prior task); repo `task verify`/`lint`/`security:quick`/`env:check` all pass. **Live**
>   (real Docker control-plane + a freshly restarted real agent-engine Studio server — Python
>   doesn't hot-reload; the first attempt against the still-running old process usefully reproduced
>   the exact bug this task fixes before the restart, confirming the fix is real): a real build's
>   own turn now appears in `/turns` before any edit; a real edit produced a genuine second git
>   commit and, for the first time, a real `"usage"` key on the edit response. Both came back
>   `credits_spent: 0` honestly — this environment's real configured cloud model has no price-book
>   entry, a pre-existing fact unrelated to this task; the "debits a nonzero charge" behavior is
>   proven by the new unit tests instead, not misrepresented as something the live run itself showed.
> - **NEXT:** R-477 (console: chat UI) per the approved plan. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-476.md`, and the plan file.

> **R-475 Completed (2026-09-19): Studio visual foundation.**
> - **First of a founder-approved, fully-researched 7-task plan** (R-475–R-481, saved at
>   `/Users/sanjeet_kumar/.claude/plans/hi-fancy-shannon.md` and mirrored in the kickoff doc's
>   "Remaining Phase D roadmap") to take the Studio from functionally-real-but-plain toward a
>   genuinely rich, chat-driven, multi-pane workspace. Planning went through full plan-mode
>   discipline this session: two Explore agents researched the real frontend/backend code, a Plan
>   agent designed the task sequence, and the most consequential claims were independently verified
>   by reading the actual source (see the plan file's "Findings from research" for the full list —
>   e.g. `_edit()` has no `usage_ledger` today, so every edit currently debits 0 credits regardless
>   of real cost; the agent-engine's live-preview API has an unusual 200-with-error-status shape for
>   an unknown build; no compile-error endpoint exists anywhere in the Studio path today). Two
>   direct founder decisions are folded in: Problems (compile errors) gets built for real, given its
>   own task (R-480) rather than a placeholder — this is what took the roadmap from six tasks to
>   seven; Files and Code stay as two separate real tabs, not collapsed into one.
> - **This task**: new `app/studio/layout.tsx` takes over `/studio`'s auth gate and renders
>   persistent top-bar chrome (brand, back link, sign-out) that later chat/tab tasks build on top
>   of. `globals.css` gained additive design tokens (`--radius-sm/md/lg` replacing inconsistent
>   inline values, `--surface-2`, an accent chip background, a CSS-only `.spinner`, `.pill--accent`)
>   mirrored into the existing dark-mode media query. New hand-rolled `studio-icons.tsx` rather than
>   a new npm dependency — the fixed, small icon surface doesn't clear the bar for one.
>   `studio-form.tsx` restyled only, zero logic change. No backend changes.
> - Gates: console `typecheck`/`lint`/`build` clean (13 routes unchanged); `task verify` **3,603
>   OK**; `task lint`/`security:quick`/`env:check` all pass. **Live** (Colima had stopped since the
>   prior session, restarted; real control-plane + real agent-engine Studio server + a fresh `next
>   start`): `/studio`'s auth gate now correctly lives in `layout.tsx` (307 signed out), the new
>   shell renders correctly signed in with a real credit pill, and `/`, `/fabric`, `/login`,
>   `/register` all remain structurally unaffected. Confirmed no new npm dependency was added.
> - **NEXT:** R-476 (backend: multi-turn edit bridge) per the approved plan. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-475.md`, and the plan file.

> **R-474 Completed (2026-09-18): File browser in the console Studio — see what a build actually produced.**
> - The founder asked to see the platform running before continuing Phase D — brought up the real
>   Docker control-plane + real agent-engine Studio server + real `next start` console for a live
>   look, then, per "Left it as running and continue," kept building on that same running stack.
> - R-473's build result panel listed filenames as inert text; each filename is now a button that
>   fetches and shows real generated file content in a read-only viewer.
> - **No agent-engine changes**: bridges the agent-engine's existing, real, path-safe read-only file
>   endpoints (`studio/files.py`, R-467) through two new authenticated control-plane proxy routes —
>   `GET /jobs/build/{id}/files` / `GET /jobs/build/{id}/file?path=...` — the same "generic proxy"
>   shape R-472 established. No credit debit (browsing isn't a billable model call).
> - New `listBuildFiles()`/`readBuildFile()` clients in `lib/control-plane.ts`, two new dynamic
>   Route Handlers, and a `FileBrowser` component in `studio-form.tsx` (binary-file guard included).
>   A shared `writeAuthError` helper replaces three copies of the same auth-error mapping.
> - **Honest, named limitation, not fixed here**: the agent-engine's Studio server has no per-user
>   build scoping (unchanged from R-467) — any authenticated caller who knows a build id can browse
>   its files. Real per-user isolation needs the Studio server itself to become multi-tenant-aware.
> - Gates: control-plane `go test` all green (15 in `internal/jobs`, 6 new); console
>   `typecheck`/`lint`/`build` clean (13 routes); `task verify` **3,603 OK**;
>   `task lint`/`security:quick`/`env:check` all pass. **Live** (against the founder's own
>   already-running stack, only the control-plane and console restarted to pick up the code —
>   Postgres and the Studio server's build history left completely untouched): built a real 158-file
>   "Simple Notes App" via real Groq cloud, then proved the file browser end to end — real
>   `README.md` content read from the real repo on disk, an unknown build id proxied as the
>   agent-engine's own 404, a path-traversal attempt proxied as the agent-engine's own 400.
> - **NEXT:** continue Phase D — live preview (executes generated code, a materially different
>   trust posture needing its own scoped decision), chat/multi-turn edit (porting R-468), or
>   Solution Pack/Ecosystem build selection in the Studio UI. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-474.md`.

> **R-473 Completed (2026-09-18): Studio v1 in the console — build an app from the product, not curl.**
> - **Phase D of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` (first slice)** — a
>   logged-in user can open `apps/console-web`'s new `/studio` page, type a plain-English app
>   description, click Build, and get a real app built through R-472's real Job API, with the
>   console showing the real post-debit credit balance.
> - **Deliberately scoped small, not the full Phase D vision** (persistent chat, top tabs
>   Preview/Files/Code/Problems/Publish/More): matches how the agent-engine's own hybrid-UI engine
>   shipped across four separate gated Tracker IDs (R-465–R-468) rather than one large task. File
>   browser, live preview, and chat/multi-turn edit are named follow-ups, not silently dropped.
> - New `app/studio/page.tsx` (auth-gated, mirrors `app/page.tsx` exactly) +
>   `app/studio/studio-form.tsx` (prompt textarea, Build button, a real pending state — builds take
>   real time, 3s–3+min observed live — result panel, error banner) +
>   `app/api/jobs/build/route.ts` (server-side proxy: reads the session cookie, 401s locally with
>   no upstream call if absent, forwards to the control-plane with the bearer token attached, never
>   exposed to client JS). `lib/control-plane.ts` gained `BuildJobResponse`/`buildApp()` following
>   the existing `login`/`registerAccount` pattern exactly.
> - **No control-plane or agent-engine changes** — R-472 already built the real backend this task's
>   UI calls.
> - Gates: console `typecheck`/`lint`/`build` all clean (11 routes); `task verify` **3,603 OK**;
>   `task lint`/`security:quick`/`env:check` all pass. **Live:** real Docker Postgres+control-plane,
>   a real agent-engine Studio server on local Ollama, a real `next start` console — `/studio`
>   redirects when signed out (307), renders correctly signed in (200, real credit balance); a real
>   build attempt hit a genuine local-model IR-validation failure, honestly proxied as a `502` (a
>   real, unforced proof of the error-banner path); a retry succeeded for real — a genuine 157-file
>   "Recipe Box" repo with every field (`entities`/`commit_sha`/`files`/`usage`/`credits_spent`/
>   `credit_balance`) matching exactly what the new UI renders.
> - **NEXT:** continue Phase D — port the agent-engine's own `studio/page.py` capabilities (file
>   browser + live preview from R-467, multi-turn chat/edit from R-468) into the console, and/or add
>   Solution Pack/Ecosystem build selection to the Studio UI. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-473.md`.

> **R-472 Completed (2026-09-18): Bridge the control-plane's Job API to the agent-engine — real credit debiting.**
> - **Phase C of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`** — the control-plane's new
>   `POST /jobs/build` authenticates the caller, proxies verbatim to the agent-engine's real
>   plain-prompt build path, and debits real credits from the actual cost the agent-engine reports.
> - **Correction found while researching:** the Studio's real build path returned a raw
>   `ModelProvider`, bypassing the gateway's own (real, tested, but previously demo-only)
>   `UsageLedger` entirely. Closed with a new, additive `model_gateway.RecordingProvider` decorator
>   — zero changes to any existing provider or call site.
> - **Real bug caught by the new tests, before any commit:** `RecordingProvider` originally sourced
>   `provider_id`/`model_id` from the response's own echoed `.model` field instead of
>   `self._inner.provider_id`/`request.model.model_id` (the pattern `ModelGateway._record` actually
>   uses) — the local-Ollama test caught the mismatch immediately.
> - **Go side:** new exported `auth.RequireUser` (factored out of `handleMe`); new
>   `users.Store.DebitCredits` (row-locked `SELECT ... FOR UPDATE`, clamped via a pure, unit-tested
>   `clampCharge` so `credit_balance` never goes negative — v1 policy: never block a build, only
>   clamp); new `internal/jobs` package (`POST /jobs/build`, generic proxy, converts
>   `cost_micros_usd` to credits via `OMNISTACKAI_CREDITS_PER_USD`, round-to-nearest).
> - **Real infra bug found only by the live smoke test:** the control-plane's global 15s
>   `http.Server.WriteTimeout` was killing `/jobs/build`'s connection before a real multi-minute
>   build finished. Fixed with `http.NewResponseController(w).SetWriteDeadline(...)` scoped to just
>   this handler, leaving the server-wide timeout intact everywhere else.
> - **Compose networking:** added `OMNISTACKAI_AGENT_ENGINE_URL` (default
>   `http://host.docker.internal:4173`) + `extra_hosts: host-gateway` so the containerized
>   control-plane can reach the host-run agent-engine Studio server (Compose is still hard-blocked
>   from adding it as a service).
> - Gates: agent-engine `task verify` — 3,603 tests OK, 0 model/network calls. Control-plane
>   `go test ./...` all green (7 new `internal/jobs` cases, `creditsForUsage` + `clampCharge` table
>   tests). Repo-wide `task verify` — Stage 0 verification passed. **Live:** real Docker
>   Postgres+control-plane, a real local Ollama build via `POST /jobs/build` produced a real
>   161-file "Task Tracker" repo with `usage.cost_micros_usd: 0`/`credits_spent: 0` (correct — local
>   is credit-exempt by price); `DebitCredits`'s row-locked/clamped SQL path proven separately
>   against the same live Postgres (a free local build has nothing to debit) with a throwaway,
>   never-committed `go run` program: `100 → 63 → 0` (clamped, never negative), independently
>   confirmed via a real `GET /auth/me`.
> - **NEXT R-473 (Phase D):** rebuild the real Studio/builder UX inside `apps/console-web` so a
>   logged-in user can actually call the now-real `/jobs/build` from the product itself. See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-472.md`.

> **R-471 Completed (2026-09-17): Fix dev-mode hydration bug + add full name to registration.**
> - **Real bug the founder hit, found via the dev server's own log:** Next.js 16 blocks
>   cross-origin access to its dev/HMR resources by default and treats `127.0.0.1`/`localhost` as
>   different origins — the founder was pointed at `127.0.0.1`, so client JS never hydrated and the
>   register form fell back to a native GET submission (fields in the URL, doing nothing, no
>   visible error). Fixed with `allowedDevOrigins` in `next.config.ts`; verified as far as possible
>   without a real browser (fetched the actual client JS chunk with the real origin header — 200,
>   warning gone).
> - **Registration now collects a Name** (`full_name`, new migration `000003`, threaded through
>   `internal/auth`/`internal/users` and the console). Explicitly **did not** add Gender or Age —
>   no function in this product's roadmap, unnecessary PII/privacy liability for no benefit; a
>   deliberate decision recorded in `.ai/tasks/R-471.md`, not a silent omission.
> - Renumbered the kickoff doc's Phase C from R-471 to **R-472** since this task took the R-471 slot.
> - Gates: control-plane `go test` all green (15/2/3/8/4 across packages); console
>   `typecheck`/`lint`/`build` clean; `task verify` **3,593 OK**. Live: control-plane
>   rebuilt/restarted (migration `000003` applied cleanly on the existing volume); register without
>   a name → 400; with a name → 201; home page shows "Welcome back, Saurabh Chopra"; confirmed
>   directly against the control-plane too, bypassing the console.
> - **NEXT R-472 (Phase C):** bridge the control-plane's Job API to the unmodified agent-engine so a
>   real generation call debits credits. See `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`,
>   `.ai/tasks/R-471.md`.

> **R-470 Completed (2026-09-17): Real Next.js console-web, wired to R-469's auth API.**
> - **Phase B of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`** — replaced the static
>   `apps/console-web` (plain HTML/CSS/JS) with a real Next.js (App Router, TypeScript) app.
> - **Session handling:** server-side cookie proxy (`app/api/auth/{register,login,logout}`), not a
>   browser-held bearer token — no CORS, raw token never reaches client-side JS. `lib/session.ts`
>   reads the cookie server-side for `getCurrentUser()`.
> - **Pages:** `/login`, `/register`, `/` (authenticated home — profile + credit balance, redirects
>   to `/login` otherwise), `/fabric` (the old model/cost overview carried forward on the same
>   `data/overview.json` contract, now a Server Component).
> - **No new UI dependency** beyond React/Next.js — existing CSS design tokens carried into
>   `app/globals.css`. A real design system is Phase D's job.
> - **Five real ecosystem-compatibility issues found and fixed** (see `.ai/tasks/R-470.md` "Live
>   discovery" for full detail): pnpm's fetch timeout too short for this network (`.npmrc` added);
>   `typescript@7.0.2` (npm's actual latest) unsupported by `typescript-eslint` yet (pinned to
>   `6.0.3`); the documented `FlatCompat` ESLint pattern crashed on a circular-reference bug (fixed
>   by importing `eslint-config-next`'s native flat-config export directly); pnpm 11.19 moved
>   `onlyBuiltDependencies`/`allowBuilds` from `package.json` to `pnpm-workspace.yaml`; and, most
>   importantly, **the session cookie's `Secure` flag was wired from `NODE_ENV` instead of the
>   actual request protocol** — would have silently broken login in a real browser over local HTTP
>   (curl doesn't enforce `Secure` the way browsers do, so the first smoke test's 200s masked it).
>   Fixed with a per-request `isSecureRequest()` check; re-verified live afterward.
> - Gates: console `typecheck`/`lint`/`build` all clean; `task verify` **3,593 OK** (63.6s, `next
>   build` succeeds with no control-plane running). **Live smoke, twice** (real `next start` + the
>   real R-469 Docker Compose control-plane): the second run (post-fix) proved register(201, no
>   leaked token) → duplicate(409) → home-authenticated(200, real email) → fabric(200) →
>   home-no-cookie(307) → logout(204) → home-after-logout(307, real invalidation) → login(200, new
>   cookie) end to end.
> - **NEXT R-471 (Phase C):** bridge the control-plane's Job API to the unmodified agent-engine so a
>   real generation call debits credits (local Ollama stays credit-exempt). See
>   `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-470.md`.

> **R-469 Completed (2026-09-17): Control-plane foundation — users, auth, plans, credits.**
> - **Phase A of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`** — the founder's decision
>   (2026-09-17) to advance from the Stage-0 static console/stdlib Studio prototype toward the real
>   commercial platform (Next.js console over a Go control-plane, Implementation Brief Section 33).
>   No frontend, no agent-engine bridge, no payment processor here — those are Phases B/C/E,
>   separate Tracker IDs, already sequenced in the kickoff doc.
> - **Role/plan/credit model:** two roles only (`super_admin` full access; `user` gated entirely by
>   `plan`, never a second role tier). Plans reuse the Brief Section 22 tier names
>   (`free`/`developer`/`pro`/`agency`/`enterprise`, `byok` an add-on flag). Every signup gets
>   `free` + a starting credit grant (`OMNISTACKAI_SIGNUP_CREDIT_GRANT`, default 100) recorded in
>   an append-only `credit_ledger`.
> - **New migration `000002_users_auth_billing`** (`users`/`credit_ledger`/`sessions`) plus a new
>   `migrations` package (`//go:embed *.up.sql`) that replays every migration, in order, inside a
>   Go-managed transaction on every boot — every file is idempotent, so this is safe, and it's
>   necessary because `docker-entrypoint-initdb.d` only runs against a brand-new empty volume.
> - **Password hashing:** PBKDF2-HMAC-SHA256 on `crypto/hmac`+`crypto/sha256`+`crypto/subtle` —
>   zero new `go.mod` dependency (`golang.org/x/crypto/bcrypt` considered and rejected for that
>   reason). Session tokens: opaque `crypto/rand` bearer tokens, only their SHA-256 hash persisted.
> - **New `internal/auth`:** `POST /auth/{register,login,logout}` + `GET /auth/me`, mounted with
>   the existing health routes on one shared `http.ServeMux` (`health.NewHandler` → `Register`).
>   Login failure is a generic 401 regardless of wrong-password vs. unknown-email, including a
>   same-cost dummy-hash check on the "not found" path — no email-enumeration timing leak.
> - **New `internal/users`:** the real PostgreSQL-backed `Store`; `CreateUser` wraps the insert and
>   the signup credit-grant ledger row in one transaction. Deliberately not unit-tested against a
>   live DB in `go test` (keeps `control-plane:test` hermetic, matching `internal/health`'s fake
>   `Pinger`) — proven instead by a real Docker Compose smoke test.
> - **Live discovery (not anticipated):** an initial timing-mitigation design used a package-level
>   mutable global (`SetDefaultHasher`) with real footguns (panic risk, cross-test cache staleness)
>   — replaced with computing the dummy hash once per handler construction from the request's own
>   injected `Hasher`, removing the global entirely.
> - Gates: `go test` all green (migrations 4, password 8, auth 15, health 3, config 2/9 subtests);
>   `task verify` **3,593 OK** (62.4s, 0 model/network calls, no slowdown); `scripts/test.sh`'s new
>   R-469 block passed (including a mechanical check that `go.mod` gained zero new direct
>   dependencies). **Live smoke against a real running Docker container** (Colima + real
>   PostgreSQL): register (201, `credit_balance:100`) → duplicate (409) → login (200, new token) →
>   wrong password (401) → unknown email (401, byte-identical body) → `/auth/me` (200) → no-token
>   (401) → logout (204) → `/auth/me` post-logout (401, real DB deletion) → logout again (204).
> - **NEXT R-470 (Phase B):** replace `apps/console-web` with a real Next.js app wired to these
>   four endpoints — the point where `task bootstrap`/`task doctor` deliberately gain a Node/npm
>   toolchain requirement. See `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`,
>   `.ai/tasks/R-469.md`.

> **R-468 Completed (2026-09-17): Multi-turn chat / "continue editing this app" in the Studio.**
> - **New generic delta:** `intake/app_delta.py` mirrors `solution_packs/ai_delta.py`'s shape (bounded typed
>   proposal, strict JSON-only prompt, collision-checked merge) with no pack coupling — a follow-up prompt
>   proposes only *new* entities/apis/screens, validated (`parse_app_delta_proposal`), merged by tuple
>   concatenation (`apply_app_delta`, mirrors `solution_packs/application.py`'s merge exactly, backstopped by
>   `ApplicationIR`'s own validation), with a bounded validate→feedback→retry loop
>   (`generate_app_delta_proposal`, mirroring R-465's repair idiom).
> - **Zero changes to `edit/`, `git_service/`, or `application_ir/`** — `plan_edit`/`commit_edit` (proven
>   end-to-end already by `test_edit_loop.py`) are reused exactly as-is to turn the delta into a real second
>   git commit on the same owned repo.
> - **New `studio/session.py`:** a small, bounded, in-memory, server-only `StudioSessionStore` tracking each
>   editable build's current `ApplicationIR` + turn history (never sent to the browser).
> - **New routes:** `POST /api/build/{id}/edit`, `GET /api/build/{id}/turns`; wired unconditionally (no
>   toolchain needed). `page.py` gets a small chat box under the file browser.
> - **v1 scope:** additive-only (rename/remove is rejected, never merged); works for plain-prompt and
>   single-surface Ecosystem builds; Solution Pack and "all surfaces" builds get an honest
>   `EditNotSupportedError` (400), not a silent no-op.
> - **Found and fixed:** neither this module nor `ai_delta.py` validated a screen's `role` against the base
>   IR's real roles — caught only as a last resort by `ApplicationIR`, too late for the retry loop. Fixed at
>   both the parse and merge layers.
> - Gates: `task verify` **3,593 OK** (63.8s, no slowdown); lint/security/env green; demos clean. End-to-end
>   tests prove a real second (and third, stacked) git commit with the new entity's files actually on disk.
> - **NEXT R-469:** wire R-466's toolchain-dependent `compile_and_repair` into the edit flow, and/or an
>   undo/revert UI over the real git history every edited build now has. See `docs/CHAT_EDIT.md`,
>   `.ai/tasks/R-468.md`.

> **R-467 Completed (2026-09-17): Studio File Browser + Hybrid UI Toggle — the hybrid engine reaches the product UI.**
> - **File browser:** new `studio/files.py` (path safety mirrors `edit/apply.py`) backs
>   `GET /api/build/{id}/files` + `GET /api/build/{id}/file?path=...`; wired in build-only mode too. `page.py`'s
>   flat inert file list is now a clickable two-pane browser (list + read-only viewer).
> - **Hybrid UI toggle:** `/api/build` accepts `hybrid_ui: bool`, threading R-465's `synthesize_screens`/
>   `ui_outcomes` into the plain-prompt and Ecosystem Pack paths; Solution Pack builds honestly report
>   `hybrid_ui_active: false` (no such parameter exists there). Surfaced in the response, `StudioBuildHistory`,
>   and the page (summary line + 🤖 badge).
> - **Live discovery (not anticipated):** the founder's real Groq credentials now sit in `.env` — running the
>   *pre-existing, unmodified* Studio suite made real outbound Groq calls (one unmocked test cost 23.5s of
>   real R-466-paced traffic). Found 2 more unmocked `resolve_generation_provider_from_env` call sites beyond
>   the 2 already suspected (`test_studio_server.py`'s solution-pack/ai-delta tests); all 4 now mocked — this
>   closed a live, active violation of the "0 model/network calls under `task verify`" constraint.
> - Also fixed a missing `ApplicationIR` import (latent `NameError`) in `live_serve.py`'s ecosystem branch.
> - Gates: `task verify` **3,529 OK** (full local suite 3,529 passed + 42 subtests in 68.80s — materially
>   faster post-fix); lint/security/env green; demos clean. Manual smoke against a real running server
>   (build-only mode): build → file tree → file content → 404/400 error mapping, all correct.
> - **NEXT R-468:** multi-turn chat / "continue editing this app" — no session concept exists at all today;
>   likely built on `edit/diff.py`'s `plan_edit`/`ProjectDiff`/`apply_diff`. Then wire R-466's
>   `compile_and_repair` into `studio:preview`. See `docs/HYBRID_UI.md`, `.ai/tasks/R-467.md`.

> **R-466 Completed (2026-09-17): Compile-Level Repair for LLM-Written UI + Rate-Limit-Aware Pacing — second brick of the hybrid engine.**
> - **Compiler has the last word:** `verify/compile.py` captures `tsc --noEmit --pretty false` into per-file
>   `CompileError`s; `codegen/hybrid_repair.py` feeds each LLM-written file's errors back through R-465's
>   corrective channel (validator-gated, template fallback, outcome record), applies a `ProjectDiff` via
>   `edit/apply_diff`, recompiles, reverts what still fails; deterministic files are never rewritten.
> - **Pacing:** typed `ProviderRateLimitedError(429)` with parsed `Retry-After`; the adapter waits and re-sends
>   the same request, bounded by `OMNISTACKAI_RATE_LIMIT_RETRIES` / `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS`
>   (`.env.example`), every wait logged. **Shrink on 413:** drop the echo, then a compact grounding that fits 8k
>   tokens. Outcomes carry the HTTP status, never the body.
> - CLI `task agent-engine:ui:synthesize` Step 3/3: link/install `node_modules`, compile, repair, commit.
> - Gates: `task verify` **3,490 OK**; lint/security/env green; demos clean; `web-typecheck` PASSED ×2.
> - Live (Groq free tier, honest): the 3-step CLI ran end-to-end (fallback repo compiled at 0 errors); pacing
>   verified live (`Retry-After: 112` honoured, above the 60 s cap); the limiter was **tokens per day** (200k,
>   191k used) — daily budget spent. **Founder action:** after the reset run with
>   `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS=180`, or add `GOOGLE_API_KEY` (Gemini) to `.env`.
> - **NEXT R-467:** product-UI shell v1 (multi-turn chat, live preview, real file tree/viewer via
>   `GET /api/build/{id}/files` + `/file?path=`, "hybrid UI" toggle, `ui_outcomes` + `CompileRepairReport` in
>   the build payload). See `docs/HYBRID_UI.md`, `.ai/tasks/R-466.md`.

> **R-465 Completed (2026-09-17): Grounded Hybrid UI Synthesis — first brick of the founder-approved HYBRID engine.**
> - The LLM writes the modern Next.js UI **grounded in the real generated data layer** (`summarize_data_layer` parses
>   `lib/types.ts`/`lib/hooks.ts`/`lib/api.ts` from the same generators — no more hallucinated `refresh()`/`page`
>   params), the real component files/exports (`summarize_components`), and the real design tokens
>   (`summarize_design_tokens`; hardcoded hex is gone).
> - `codegen/llm_ui.py` rewritten around one `_synthesize_file` core: validator rejection → reason fed back →
>   retry (≤3; never on exceptions) → deterministic template fallback; JSON-safe secret-free `UiSynthesisOutcome`
>   per file; import whitelist hardened (multi-line, exact react/react-dom, no react-*/require/dynamic import).
> - Explicit `synthesize_screens` flag threaded `generate → assemble_project → build_app_from_ir/prompt` (default
>   off; default output byte-identical); the never-set env gate is gone. Opt-in CLI `task agent-engine:ui:synthesize`.
> - Gates: `task verify` **3,442 OK**; lint/security/env green; demos 157/153; `web-typecheck` PASSED ×2.
> - Live proof (Groq, free tier 8k TPM, one model): model answered → validator rejected a truncated file with an
>   exact reason → repair engaged → repair call rate-limited → graceful fallback (truthful outcome). A full
>   LLM-page-compiles proof needs >8k TPM: **founder action — add `GOOGLE_API_KEY` (Gemini) to `.env` or upgrade Groq.**
> - **NEXT R-466:** compile-level repair (capturing `tsc` executor → per-file errors through `_repair_message`) +
>   HTTP-429 pacing in the gateway. **Then R-467:** the product-UI shell (chat + live preview + file tree).
> - See `docs/HYBRID_UI.md`, `.ai/tasks/R-465.md`.

> **R-464 Completed (2026-09-16): Full-Stack Platform Feature Completeness — 4-Phase Plan.**
> - **Phase 1 (Frontend Search, Pagination & Filter UI Controls)**:
>   - Verified collection screen pagination, search, and segmented filter controls.
>   - Updated `llm_ui.py` (`build_ui_synthesis_prompt`) to document complete hook signatures (`page`, `pageSize`, `totalPages`, `params`, `setSearch`, `setPage`, `setPageSize`, `setSort`, `setFilter`, `clearFilters`, `refetch`).
> - **Phase 2 (Audit Timestamps on All Entity Tables)**:
>   - Added `"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()` and `"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()` to all entity tables in `schema_sql.py`.
>   - Added PostgreSQL `set_updated_at()` trigger function and `BEFORE UPDATE ON "<table>"` triggers for all entities.
>   - Excluded `created_at` and `updated_at` from `_insert_columns` in `data_access.py`.
>   - Added `CreatedAt` and `UpdatedAt` (`time.Time`) to Go model structs in `backend_go.py`.
>   - Added `created_at` and `updated_at` (`Optional[datetime] = None`) to Python models in `backend_python.py`.
>   - Added `created_at?: string;` and `updated_at?: string;` to TypeScript entity interfaces in `nextjs.py`.
>   - Rendered record creation & last-updated metadata footer in `_detail_screen_page` in `nextjs.py`.
> - **Phase 3 (RBAC / Row Ownership `created_by`)**:
>   - Conditional on `needs_auth(ir)`: added `"created_by" UUID REFERENCES "users"("id") ON DELETE SET NULL` to entity tables in `schema_sql.py`.
>   - Added `created_by: str | None = None` support to `create_*` in `data_access.py`.
>   - Added `require_owner` helper in `python_auth_file` and `RequireOwner` in `go_auth_file` in `auth_guard.py`.
>   - Added `created_by?: string | null;` to TypeScript interfaces and `ownerOnly?: boolean` param to `useList*` hooks in `nextjs.py`.
> - **Phase 4 (S3-Compatible File Uploads)**:
>   - Added `FieldType.ATTACHMENT = "attachment"` and string aliases (`attachment`, `file`, `upload`, `media`) in `application_ir/ir.py`.
>   - Mapped `FieldType.ATTACHMENT` to `TEXT` in `schema_sql.py`, `string` in TypeScript (`nextjs.py`), `str` in Python (`backend_python.py`), and `string` in Go (`backend_go.py`).
>   - Added storage environment variables (`STORAGE_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`) to `.env.example` in Next.js, Python FastAPI, and Go Gin adapters.
> - Verified:
>   - `python3 -m unittest test_platform_feature_completeness.py`: 14 tests passed.
>   - `bash scripts/agent-engine.sh lint`: Passed.
>   - `bash scripts/agent-engine.sh test`: **3,427 tests passing (100% OK)**.


> **R-463 Completed (2026-09-16): Auth Lifecycle Hardening, Webpack Syntax Fix & Forgot Password Workflow.**
> - Diagnosed and fixed the Next.js Webpack syntax crash (`Unterminated regexp literal ./app/register/page.tsx:68:1`) caused by single-closing braces in f-string branding icon JSX (`f'          }}>{brand_initial}</div>\n'`), which rendered `}>C</div>`. Fixed by using 4 curly braces `}}}}` yielding valid JSX `}}>C</div>`.
> - Fixed `AttributeError: 'ApplicationIR' object has no attribute 'title'` in `_forgot_password_page` by standardizing on `ir.name`.
> - Added full Forgot Password workflow:
>   - Frontend screen `app/forgot-password/page.tsx` with email, new password, confirmation password validation, and auto-redirect.
>   - Added "Forgot password?" link on `app/login/page.tsx`.
>   - Added backend endpoints in `auth_guard.py` (`ResetPasswordRequest`, `POST /auth/forgot-password`, `POST /auth/reset-password`).
> - Synchronized active project `scratch/apps/build-a-clinic-management-app`: validated with `npx tsc --noEmit` and `next build` (24/24 static & dynamic pages compiled successfully).
> - All 3,413 tests pass in `scripts/agent-engine.sh test`.

> **R-462 Completed (2026-09-16): Hybrid Generative LLM-Powered UI Synthesis Engine, Universal Domain Archetype Expansion & Groq Cloud Resolution.**
> - Implemented bespoke UI synthesizer (`codegen/llm_ui.py`) leveraging the 57 built-in components and data hooks for overview and screen-level pages (`app/[screen]/page.tsx`).
> - Strict JSX AST/syntax validation (`clean_and_validate_jsx`) checking `'use client'`, import whitelisting, balanced delimiters, and preventing unapproved npm imports.
> - Bulletproof silent fallback to deterministic templates (`_overview_page` and `_fallback_screen_page`) on offline, timeouts, or invalid model output.
> - Universal Domain Archetype Expansion & 1:1 Full-Stack Triad Mapping in `intake/nl_to_ir.py`: short prompts and multi-feature requests expand into complete 4–8 entity architectures with PostgreSQL migrations, FastAPI REST endpoints, and interactive Next.js screens.
> - Dynamic Multi-Provider Resolution (`intake/provider_resolution.py`): seamlessly resolves Groq (`openai/gpt-oss-120b`) from `.env` while preserving local container execution (`OMNISTACKAI_TIER=0`).
> - All 3,411 tests pass offline in `task verify`. Total completed tasks in tracker: **251 Done / 462 Total**.

> **R-461 Completed (2026-09-16): Full-Stack Production Authentication Engine.**
> - Implemented complete production-ready authentication across the full generated stack:
>   - PostgreSQL `users` table with UUID primary key, `VARCHAR UNIQUE NOT NULL` email, `VARCHAR NOT NULL` password_hash, optional full_name, `VARCHAR NOT NULL DEFAULT 'user'` role, and `TIMESTAMPTZ` created_at, plus development admin seed row (`admin@example.local` / `changeme`).
>   - FastAPI auth router (`/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`) in `auth_guard.py` using `hashlib.pbkdf2_hmac` (SHA-256, 100k iterations) with zero external dependencies, JWT signing/verification, and wired into `main.py` via `backend_python.py`.
>   - Next.js AuthProvider (`components/auth-provider.tsx`) exposing `useAuth()` hook with `user`, `token`, `login()`, `register()`, and `logout()`.
>   - Responsive `app/login/page.tsx` and `app/register/page.tsx` pages with error states, validation, and auto-redirect.
>   - Navbar user state toggle (signed in greeting & logout button vs. sign-in link).
>   - API client (`lib/api.ts`) auto-attaching Bearer token with localStorage fallback.
> - All 3,386 tests pass offline in `task verify`. Total completed tasks in tracker: **250 Done / 461 Total**.

> **The differentiating SPINE now supports Solution Pack Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts.**
> R-430 proposes the ecosystem, R-431 materializes it, R-432 refines unknown domains, R-433 scopes surfaces, R-434 registers
> packs, R-435 recommends one, R-436 records bounded intent, R-437 applies safe configuration deterministically,
> R-438 converts pending manifest AI-delta intents into strictly typed, bounded AIDeltaProposal objects via an
> explicit opt-in local ModelProvider boundary, R-439 safely applies validated AI-delta proposals to
> derived Application IRs, R-440 wires derived Solution Pack Application IRs into verified multi-repo
> builder pipelines, R-441 wires Solution Pack selection into the Studio, R-442 wires natural-language
> AI-delta feature modifications on top of Solution Packs into the Studio, R-443 introduces portable
> SolutionPackPackage bundles and export CLI, R-444 enables synthesizing a complete, coordinated
> multi-surface ecosystem from a Solution Pack's unified data model, R-445 provides the immutable EcosystemPackRegistry,
> R-446 provides multi-surface process coordination in StudioPreviewManager, collision-free loopback port allocation,
> POST /api/preview/switch, and Studio Web UI surface navigation tabs, R-447 provides canonical
> EcosystemAuthContract, CrossAppAuthMatrix, stdlib-only deterministic HS256 JWT minting/verifying,
> EcosystemStateBinding with entity lifecycle state flows and role-gated transitions, Studio preview auth/state
> injection and endpoints, and CLI auth/state inspection subcommands, R-448 provides canonical
> WebhookRetryPolicy, EcosystemWebhookSubscription, EcosystemEventPayload, WebhookDeliveryRecord,
> EcosystemEventBridgeContract, stdlib-only deterministic HMAC-SHA256 signature generation and verification,
> R-449 provides canonical TelemetrySpan, AuditTrailEntry, DistributedTrace, TelemetrySamplingPolicy,
> TracedSurface, EcosystemTelemetryContract, stdlib-only deterministic trace ID and span ID generation,
> in-process EcosystemTelemetryCollector, Studio preview telemetry injection and GET /api/ecosystem/telemetry,
> R-450 provides canonical GatewayRoute, SurfaceDeploymentSpec, EcosystemDeploymentManifest,
> deterministic Docker Compose YAML generation, thread-safe in-process HTTP reverse-proxy EcosystemLiveGateway,
> R-451 provides canonical SyncEntitySpec, SyncMutation, SyncConflict, SyncCheckpoint, EcosystemSyncContract,
> deterministic Python 3.13 stdlib-only conflict resolution algorithms (last_write_wins, source_of_truth, field_merge),
> R-452 provides canonical CIJobStep, CIJob, CIWorkflow, EcosystemCICDContract, deterministic Python 3.13 stdlib-only
> GitHub Actions YAML workflow generation (generate_github_actions_workflow, to_workflow_yaml), in-process DAG dependency
> validation (Kahn's algorithm cycle detection) and dry-run pipeline simulation (EcosystemCICDEngine),
> R-453 provides canonical HealthCheckProbe, SmokeTestStep, SmokeTestSpec, CanaryVerificationRule,
> EcosystemVerificationContract, deterministic Python 3.13 stdlib-only verification contract synthesis,
> R-454 provides canonical BackupTarget, SnapshotManifest, RecoveryStep, RollbackTrigger, EcosystemDisasterRecoveryContract,
> R-455 provides canonical ResourceQuota, SurfaceCapacitySpec, UnitEconomicsCostModel, EcosystemCapacityContract,
> R-456 provides canonical AlertRule, RunbookStep, IncidentRunbook, EscalationTier, EscalationPolicy, EcosystemAlertingContract,
> R-457 provides canonical ServiceLevelIndicator, ServiceLevelObjective, ErrorBudget, ServiceLevelAgreement, EcosystemSLAContract,
> R-458 provides canonical ComplianceStandard, CompliancePolicy, DataClassification, AuditEvidenceItem, EcosystemGovernanceContract,
> and **R-459 provides canonical DocPage, RunbookStep, ArchitectureRunbook, OpenAPIRoute, OpenAPIAggregationEntry,
> AggregatedAPISpec, EcosystemDocsContract, deterministic Python 3.13 stdlib-only contract synthesis (synthesize_ecosystem_docs)
> for all ecosystem surfaces, in-process thread-safe EcosystemDocsEngine for unified Markdown bundle rendering,
> keyword/tag search, OpenAPI 3.1 route aggregation with collision detection, and documentation export simulations,
> whole-package SHA-256 integrity, Studio preview docs status injection, endpoints GET /api/ecosystem/docs and POST /api/ecosystem/docs/export,
> Studio UI sky-blue/amber-themed #preview-docs-info panel, and CLI docs subcommand**.
> UI-component series PAUSED at R-415. **NEXT:** R-460 Solution Pack Ecosystem Multi-Surface Unified Developer CLI and Operational Control Plane Contracts.

## Repo/workflow state

- **R-459 (Solution Pack Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts — thirtieth spine brick)** shipped:
  `solution_packs/ecosystem_docs.py` implements `DocPage`, `RunbookStep`, `ArchitectureRunbook`, `OpenAPIRoute`, `OpenAPIAggregationEntry`, `AggregatedAPISpec`, `EcosystemDocsContract`;
  implements deterministic Python 3.13 stdlib-only contract synthesis (`synthesize_ecosystem_docs`) for all ecosystem surfaces;
  implements thread-safe in-process `EcosystemDocsEngine` rendering unified Markdown documentation bundles, searching docs with relevance scoring, aggregating OpenAPI 3.1 specs with collision detection, and simulating multi-format exports;
  `solution_packs/ecosystem_pack.py` bundles and validates docs contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `docs_contract` and `get_docs_contract()`; exports all docs symbols in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_docs`, `page_count`, `runbook_count`, `api_endpoint_count`, and `docs_status` to preview status/payloads, and
  exposes `get_ecosystem_docs()` and `export_ecosystem_docs()`;
  `studio/server.py` and `studio/live_serve.py` expose `GET /api/ecosystem/docs` and `POST /api/ecosystem/docs/export`;
  `studio/page.py` renders sky-blue/amber-themed `#preview-docs-info` container with pages, runbooks, and API endpoints badges, and 1-click "Export Docs" / "Refresh" buttons (0 external network requests);
  `solution_packs/ecosystem_cli.py` adds `docs` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, `--search`, and `--export` options;
  `tests/test_ecosystem_docs.py` adds 20 new focused unit tests. `task verify` **3,333 passed** offline (+23 net-new);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-458 (Solution Pack Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts — twenty-ninth spine brick)** shipped:
  `solution_packs/ecosystem_governance.py` implements `ComplianceStandard`, `CompliancePolicy`, `DataClassification`, `AuditEvidenceItem`, `EcosystemGovernanceContract`;
  implements deterministic Python 3.13 stdlib-only contract synthesis (`synthesize_ecosystem_governance`) for all ecosystem surfaces;
  implements thread-safe in-process `EcosystemGovernanceEngine` evaluating surface configuration rules, verifying cryptographic audit evidence hashes, and simulating full compliance audits across operational scenarios;
  `solution_packs/ecosystem_pack.py` bundles and validates governance contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `governance_contract` and `get_governance_contract()`; exports all governance symbols in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_governance`, `standard_count`, `policy_count`, `evidence_count`, and `governance_status` to preview status/payloads, and
  exposes `get_ecosystem_governance()` and `simulate_ecosystem_governance()`;
  `studio/server.py` and `studio/live_serve.py` expose `GET /api/ecosystem/governance` and `POST /api/ecosystem/governance/simulate`;
  `studio/page.py` renders indigo/violet-themed `#preview-governance-info` container with standards, policies, audit evidence items, and 1-click "Simulate Audit" / "Refresh" buttons (0 external network requests);
  `solution_packs/ecosystem_cli.py` adds `governance` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, `--simulate`, and `--scenario` options;
  `tests/test_ecosystem_governance.py` adds 22 new focused unit tests. `task verify` **3,310 passed** offline (+22);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-457 (Solution Pack Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts — twenty-eighth spine brick)** shipped:
  `solution_packs/ecosystem_sla.py` implements `ServiceLevelIndicator`, `ServiceLevelObjective`, `ErrorBudget`, `ServiceLevelAgreement`, `EcosystemSLAContract`;
  implements deterministic Python 3.13 stdlib-only contract synthesis (`synthesize_ecosystem_sla`) for all ecosystem surfaces;
  implements thread-safe in-process `EcosystemSLAEngine` evaluating metrics against SLO targets, calculating multi-window error budget burn rates (1h, 6h, 24h), and executing SLA compliance simulations across operational scenarios;
  `solution_packs/ecosystem_pack.py` bundles and validates SLA contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `sla_contract` and `get_sla_contract()`; exports all SLA symbols in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_sla`, `sli_count`, `slo_count`, `sla_count`, and `sla_status` to preview status/payloads, and
  exposes `get_ecosystem_sla()` and `simulate_ecosystem_sla()`;
  `studio/server.py` and `studio/live_serve.py` expose `GET /api/ecosystem/sla` and `POST /api/ecosystem/sla/simulate`;
  `studio/page.py` renders emerald/teal-themed `#preview-sla-info` container with SLIs, SLO targets, error budget burn rates, SLA tiers, and 1-click "Simulate SLA" / "Refresh" buttons (0 external network requests);
  `solution_packs/ecosystem_cli.py` adds `sla` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, `--simulate`, and `--scenario` options;
  `tests/test_ecosystem_sla.py` adds 23 new focused unit tests. `task verify` **3,288 passed** offline (+23);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.
  `solution_packs/ecosystem_alerting.py` implements `AlertRule`, `RunbookStep`, `IncidentRunbook`, `EscalationTier`, `EscalationPolicy`, `EcosystemAlertingContract`;
  implements deterministic Python 3.13 stdlib-only contract synthesis (`synthesize_ecosystem_alerting`) for all ecosystem surfaces;
  implements thread-safe in-process `EcosystemAlertingEngine` evaluating metrics against rules, dry-running runbooks, and executing incident simulations across operational scenarios;
  `solution_packs/ecosystem_pack.py` bundles and validates alerting contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `alerting_contract` and `get_alerting_contract()`; exports all alerting symbols in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_alerting`, `alert_rule_count`, `runbook_count`, `escalation_policy_count`, and `alert_status` to preview status/payloads, and
  exposes `get_ecosystem_alerting()` and `simulate_ecosystem_alerting()`;
  `studio/server.py` and `studio/live_serve.py` expose `GET /api/ecosystem/alerting` and `POST /api/ecosystem/alerting/simulate`;
  `studio/page.py` renders rose/crimson-themed `#preview-alerting-info` container with alert rules, runbooks, escalation policies, and 1-click "Simulate Incident" / "Refresh" buttons (0 external network requests);
  `solution_packs/ecosystem_cli.py` adds `alerting` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, `--simulate`, and `--scenario` options;
  `tests/test_ecosystem_alerting.py` adds 23 new focused unit tests. `task verify` **3,265 passed** offline (+23);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-455 (Solution Pack Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting — twenty-sixth spine brick)** shipped:
  `solution_packs/ecosystem_capacity.py` implements `ResourceQuota`, `SurfaceCapacitySpec`, `UnitEconomicsCostModel`, `EcosystemCapacityContract`;
  implements deterministic Python 3.13 stdlib-only capacity planning contract synthesis (`synthesize_ecosystem_capacity`) for all ecosystem surfaces;
  implements thread-safe in-process `EcosystemCapacityEngine` executing workload tier simulation (base, peak, stress with quota breach detection), quota evaluation, and MAU unit economics projections;
  `solution_packs/ecosystem_pack.py` bundles and validates capacity contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `capacity_contract` and `get_capacity_contract()`; exports all capacity symbols in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_capacity`, `capacity_spec_count`, `quota_count`, `cost_model_count`, `monthly_budget_usd`, and `capacity_status` to preview status/payloads, and
  exposes `get_ecosystem_capacity()` and `simulate_ecosystem_capacity()`; `studio/server.py` exposes
  `GET /api/ecosystem/recovery` and `POST /api/ecosystem/recovery/simulate`;
  `studio/page.py` renders `#preview-recovery-info` with backup targets, recovery steps, rollback triggers, and "Simulate DR" / "Refresh" buttons (0 external requests);
  `solution_packs/ecosystem_cli.py` adds `recovery` subcommand.
  21 new tests in `test_ecosystem_recovery.py`; `task verify` **3,223 passed** offline (+21);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-452 (Solution Pack Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration — twenty-third spine brick)** shipped:
  `solution_packs/ecosystem_cicd.py` implements `CIJobStep`, `CIJob`, `CIWorkflow`, `EcosystemCICDContract`;
  implements deterministic Python 3.13 stdlib-only GitHub Actions YAML workflow generation (`generate_github_actions_workflow`, `to_workflow_yaml`) with 0 external dependencies (no PyYAML);
  implements in-process DAG dependency validation (Kahn's algorithm cycle detection) and deterministic dry-run pipeline simulation (`EcosystemCICDEngine`);
  implements deterministic `synthesize_ecosystem_cicd(ecosystem_id, surfaces)` deriving surface verification jobs and overarching `ecosystem-integration` verification gate;
  `solution_packs/ecosystem_pack.py` bundles and validates CI/CD contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `cicd_contract` and `get_cicd_contract()`; exports all CI/CD types in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_cicd`, `cicd_workflow_count`, `cicd_job_count`, and `cicd_status` to preview status/payloads, and exposes `get_ecosystem_cicd()`, `to_workflow_yaml()`, and `simulate_cicd_run()`;
  `studio/server.py` exposes `GET /api/ecosystem/cicd`, `GET /api/ecosystem/cicd/yaml`, and `POST /api/ecosystem/cicd/simulate`;
  `studio/page.py` renders `#preview-cicd-info` with workflow triggers, job chips, and copy YAML and simulate buttons (0 external requests);
  `solution_packs/ecosystem_cli.py` adds `cicd` subcommand.
  15 new tests in `test_ecosystem_cicd.py`; `task verify` **3,173 passed** offline (+15);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-451 (Solution Pack Ecosystem Cross-Surface Data Sync, Conflict Resolution, and Offline-First Sync Protocol — twenty-second spine brick)** shipped:
  `solution_packs/ecosystem_sync.py` implements `SyncEntitySpec`, `SyncMutation`, `SyncConflict`, `SyncCheckpoint`, `EcosystemSyncContract`;
  implements deterministic Python 3.13 stdlib-only conflict resolution algorithms (`resolve_sync_conflict` supporting `last_write_wins`,
  `source_of_truth`, and `field_merge` strategies) with 0 external dependencies; implements thread-safe in-process `EcosystemSyncEngine` with
  mutation log, state store, conflict log (bounded 500), push/pull checkpoints, and mutation base-version validation; implements deterministic
  `synthesize_ecosystem_sync` deriving sync entities, authority mappings, and conflict strategies across ecosystem surfaces;
  `solution_packs/ecosystem_pack.py` bundles and validates sync contracts with whole-package SHA-256 checksums;
  `solution_packs/ecosystem_registry.py` exposes `sync_contract` and `get_sync_contract()`; exports all symbols in `solution_packs/__init__.py`;
  `studio/preview.py` attaches `has_sync`, `sync_entity_count`, `sync_conflict_count`, and `sync_version` to preview status/payloads, and
  exposes `get_ecosystem_sync()`, `push_sync_mutations()`, `pull_sync_changes()`, and `simulate_sync_conflict()`; `studio/server.py` exposes
  `GET /api/ecosystem/sync`, `POST /api/ecosystem/sync/push`, `GET /api/ecosystem/sync/pull`, and `POST /api/ecosystem/sync/simulate`;
  `studio/page.py` renders `#preview-sync-info` with entity chips, conflict/version badges, and 1-click "Simulate Conflict" and "Refresh Sync"
  buttons (0 external requests); `solution_packs/ecosystem_cli.py` adds `sync` subcommand.
  14 new tests in `test_ecosystem_sync.py`; `task verify` **3,158 passed** offline (+14);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-450 (Solution Pack Ecosystem Multi-Surface Export, Deployment Manifest, and Live Gateway Orchestration — twenty-first spine brick)** shipped:
  `solution_packs/ecosystem_deployment.py` implements `GatewayRoute`, `SurfaceDeploymentSpec`, `EcosystemDeploymentManifest`;
  implements deterministic Python 3.13 stdlib-only Docker Compose YAML generator (`generate_docker_compose`, `to_compose_yaml()`) for
  all surfaces and PostgreSQL with 0 external dependencies; implements in-process `EcosystemLiveGateway` HTTP reverse proxy routing
  requests via longest-prefix matching with hop-by-hop header strip and forwarding headers injection; implements deterministic deployment
  synthesis (`synthesize_ecosystem_deployment`) deriving non-colliding host ports, routes, and environment bindings across surfaces
  and PostgreSQL; `solution_packs/ecosystem_pack.py` bundles and validates deployment manifests with package checksums;
  `solution_packs/ecosystem_registry.py` exposes `deployment_manifest` and `get_deployment_manifest()`; exports all symbols in
  `solution_packs/__init__.py`; `studio/preview.py` attaches `has_deployment`, `deployment_surface_count`, `gateway_routes`, `gateway_port`,
  and `gateway_url` to preview status/payloads, and exposes `get_ecosystem_deployment()` and `to_compose_yaml()`; `studio/server.py`
  exposes `GET /api/ecosystem/deployment` and `GET /api/ecosystem/deployment/compose`; `studio/page.py` renders `#preview-deployment-info`
  with surface counts, route chips, and 1-click "Copy Compose YAML" / "Refresh Deployment" buttons (0 external requests);
  `solution_packs/ecosystem_cli.py` adds `deploy` subcommand.
  13 new tests in `test_ecosystem_deployment.py`; `task verify` **3,144 passed** offline (+13);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-448 (Solution Pack Ecosystem Cross-Surface Webhook and Event Bridge — nineteenth spine brick)** shipped:
  `solution_packs/ecosystem_events.py` implements `WebhookRetryPolicy`, `EcosystemWebhookSubscription`, `EcosystemEventPayload`,
  `WebhookDeliveryRecord`, `EcosystemEventBridgeContract`, stdlib-only deterministic HMAC-SHA256 signing and verification
  (`sign_webhook_payload`, `verify_webhook_signature`) with `hmac.compare_digest`, in-process `EcosystemEventBridge` with
  subscription management and bounded delivery logging (max 100 records), and deterministic contract synthesis (`synthesize_ecosystem_events`)
  deriving subscriptions from entity writers to readers; `solution_packs/ecosystem_pack.py` bundles and validates event bridge contracts
  with package checksums; `solution_packs/ecosystem_registry.py` exposes `event_bridge` and `get_event_bridge`; `studio/preview.py`
  attaches `has_events`, `event_count`, and `subscription_count` to preview payloads and exposes `get_ecosystem_events` and
  `dispatch_ecosystem_event`; `studio/server.py` exposes `GET /api/ecosystem/events` and `POST /api/ecosystem/events/dispatch`;
  `studio/page.py` renders `#preview-events-info` with subscription count, "Simulate Event" panel, and live delivery log table (0 external requests);
  `solution_packs/ecosystem_cli.py` adds `events` subcommand.
  15 new tests in `test_ecosystem_event_bridge.py`; `task verify` **3,098 passed** offline (+15);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-447 (Solution Pack Ecosystem Multi-Surface Cross-App Auth and Unified State Binding — eighteenth spine brick)** shipped:
  `solution_packs/ecosystem_auth.py` implements `EcosystemRoleBinding`, `EcosystemAuthContract`, `CrossAppAuthMatrix`,
  stdlib-only HS256 JWT minting/verifying (`mint_ecosystem_token`, `verify_ecosystem_token`), demo token generation, and
  `synthesize_ecosystem_auth`; `solution_packs/ecosystem_state.py` implements `SharedEntityBinding`, `StateTransition`,
  `EntityStateFlow` with role-gated `can_transition`, `CrossAppEndpointBinding`, `SurfaceEnvBinding`, `EcosystemStateBinding`, and
  `synthesize_ecosystem_state`; `solution_packs/ecosystem_pack.py` bundles and validates auth and state bindings with checksums;
  `solution_packs/ecosystem_registry.py` exposes `get_auth_contract` and `get_state_binding`; `studio/preview.py` attaches
  `active_role` and `active_token` to preview payloads and exposes `get_ecosystem_auth` and `get_ecosystem_state`; `studio/server.py`
  exposes `GET /api/ecosystem/auth` and `GET /api/ecosystem/state`; `studio/page.py` renders `#preview-auth-info` with role badge
  and "Copy Demo JWT" button (0 external requests); `solution_packs/ecosystem_cli.py` adds `auth` and `state` subcommands.
  16 new tests in `test_ecosystem_auth_and_state.py`; `task verify` **3,083 passed** offline (+16);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-446 (Solution Pack Ecosystem Studio Live Multi-Surface Preview and Process Orchestration — seventeenth spine brick)** shipped:
  `studio/preview.py` enhanced `StudioPreviewManager` with `replace_ecosystem`, `switch_surface`, per-surface/global `stop` & `restart`,
  multi-session tracking (`_sessions: dict[str, LocalAppSession]`), collision-free loopback port allocation per surface, and
  liveness-aware multi-surface status tracking, using `threading.RLock` to eliminate reentrant deadlocks; `studio/server.py` added
  `switch_surface_fn`, implementing `POST /api/preview/switch` and surface-scoping for stop, restart, and history preview;
  `studio/live_serve.py` and `studio/history.py` wired automatic multi-surface preview on ecosystem compilation and history persistence;
  `studio/page.py` added `#preview-surface-tabs` surface switcher bar with live status indicators and 0 external network requests.
  12 new tests in `test_studio_ecosystem_preview.py`; `task verify` **3,067 passed** offline (+12);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-445 (Solution Pack Ecosystem Pack Registry Integration, Catalog Discovery, and Studio Multi-Surface Selection — sixteenth spine brick)** shipped:
  `solution_packs/ecosystem_registry.py` defines `EcosystemPack`, `EcosystemPackRecommendation`, and `EcosystemPackRegistry`
  with immutable operations (`list_packs()`, `get()`, `select()`, `recommend()`, `register_package()`, and `load_surface_ir()`);
  pre-registers built-in ecosystem baselines (`minimal-blog-ecosystem`, `rideshare-favourites-ecosystem`) via `DEFAULT_ECOSYSTEM_PACK_REGISTRY`;
  Studio server (`studio/server.py`) exposes discovery and recommendation endpoints (`GET /api/ecosystem-packs`, `POST /api/ecosystem-packs/recommend`);
  Studio `POST /api/build` in `server.py` and `live_serve.py` accepts `ecosystem_id`, `ecosystem_version`, and `surface_slug`
  to build an individual surface or complete multi-surface platform with 0 model calls; `studio/history.py` tracks `ecosystem_id`,
  `ecosystem_version`, `surface_slug`, `surface_kind`, and `is_ecosystem`; `studio/page.py` adds tab selector (`#tab-single` vs `#tab-ecosystem`),
  ecosystem dropdown (`#eco-select`), surface selector (`#surface-select`), surface cards (`#surface-cards`), real-time recommendations,
  and history badges with strictly 0 external assets; `solution_packs/ecosystem_cli.py` adds `catalog` subcommand (`task agent-engine:solution-pack:ecosystem -- catalog`).
  14 new tests across `test_ecosystem_pack_registry.py` and `test_studio_ecosystem.py`; `task verify` **3,055 passed** offline (+14);
  lint/security/env + demos (152/149) green; 0 model calls in test execution.


- **R-444 (Solution Pack Multi-Surface Ecosystem Pack Synthesis — fifteenth spine brick)** shipped:
  `intake/ecosystem.py` and `solution_packs/ecosystem_pack.py` add `synthesize_surface_ir` and `synthesize_ecosystem_pack`,
  scoping entity visibility, mutation authority, actor roles, APIs, and screens per surface while preserving the pack's
  unified data model and project strategy; `EcosystemPackPackage` and `EcosystemSurfacePackage` bundle all surfaces
  with canonical IR digests, verify targets, and whole-ecosystem package checksum; `parse_ecosystem_pack_package` strictly
  validates all surface IRs (`validate_ir`), digests, and checksums; `plan_ecosystem` synthesizes secondary surfaces
  from pack_result data models (marking `is_synthesized=True`); and `ecosystem_cli.py` provides `synthesize`, `verify`,
  `inspect`, and `build` subcommands (`task agent-engine:solution-pack:ecosystem`). 18 new tests in `test_solution_pack_ecosystem.py`;
  `task verify` **3,041 passed** offline (+18); lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-443 (Solution Pack Packaging, Verification, and Export CLI — fourteenth spine brick)** shipped:
  `solution_packs/package.py` defines `SolutionPackPackage` bundles pinning schema version (`"1.0"`), metadata,
  `ir_sha256`, canonical `ir_dict`, `verify_plans`, and `package_sha256` checksum; `parse_solution_pack_package`
  strictly validates JSON/dict payloads, verifies embedded Application IR with `validate_ir`, confirms `ir_sha256`
  digest matching, verifies whole-package SHA-256 integrity, and fails closed with `SolutionPackError` on corruption
  or drift; `SolutionPackRegistry` supports dynamic package registration via `register_package` and `SolutionPack.from_package`;
  `package_cli.py` provides `export`, `verify`, and `inspect` subcommands; and Taskfile + `scripts/agent-engine.sh`
  expose `task agent-engine:solution-pack:package`. 16 new tests in `test_solution_pack_package.py`;
  `task verify` **3,023 passed** offline (+16); lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-442 (Studio AI-delta feature modification controls above Solution Packs — thirteenth spine brick)** shipped:
  `server.py` extends `POST /api/build` to accept `ai_features` and `ai_delta_prompt`; `live_serve.py` generates
  bounded `AIDeltaProposal` via `generate_ai_delta_proposal` when AI features are requested (and bypasses the model
  with 0 calls when none requested), applying the proposal safely via `apply_solution_pack_manifest` and recording
  full provenance in `applied_ai_delta_change_ids`; `history.py` tracks `applied_ai_delta_change_ids` in `StudioBuildHistory`;
  and `page.py` adds `#ai-features` input, AI synthesis status messaging, and AI delta badge chips in history items
  and build provenance, strictly preserving 0 external resources. 4 new tests; focused studio suite: 53 passed;
  `task verify` **3,007 passed** offline (+4); lint/security/env + demos (152/149) green; 0 model calls in test execution.

- **R-441 (live Studio integration and UI controls for Solution Pack selection and modification — twelfth spine brick)** shipped:
  `server.py` adds `GET /api/solution-packs` and `POST /api/solution-packs/recommend` endpoints; `POST /api/build` accepts
  `pack_id`, `pack_version`, `custom_name`, `custom_description`, and `configuration_changes`; `live_serve.py` compiles
  Solution Pack projects deterministically with 0 model calls using `create_solution_pack_manifest`, `apply_solution_pack_manifest`,
  and `build_solution_pack_project`; `history.py` tracks `pack_id` and `pack_version`; `page.py` includes Solution Pack
  selection dropdown, real-time recommendation banner, customization inputs, verified badges, and full SHA-256 / change
  provenance rendering with zero external resources in HTML. 8 new tests; focused studio suite: 63 passed; `task verify`
  **3,003 passed** offline (+8); lint/security/env + demos (152/149) green; 0 model calls. Workbook unchanged past R-358.


- **R-440 (wire derived Solution Pack Application IRs into verified builder pipelines — eleventh spine brick)** shipped:
  `solution_packs/builder.py` and `solution_packs/build_cli.py` add `build_solution_pack_project`, which assembles
  an owned Git repository for a `SolutionPackApplicationResult` or `SolutionPackManifest` (+ optional `AIDeltaProposal`),
  validates verification gate plans against the derived Application IR, and returns a frozen byte-stable `SolutionPackBuildResult`.
  `plan_ecosystem` and `build_ecosystem` now accept optional `pack_result` or `pack_manifest` (+ `pack_proposal`),
  revalidating domain compatibility, transparently substituting the customer surface with the pack-derived IR while
  preserving other surfaces, and recording complete pack provenance in `EcosystemAppBuild`.
  New CLI `task agent-engine:solution-pack:build`. 11 new tests; focused 86 passed; `task verify` **2,995 passed**
  offline (+11); lint/security/env + demos (152/149) green; 0 model calls. Workbook unchanged past R-358.

- **R-439 (safely apply validated AI-delta proposals to Application IR — tenth spine brick)** shipped:
  `apply_solution_pack_manifest(manifest, *, proposal=None, registry=...)` now accepts an optional validated
  `AIDeltaProposal`. When `proposal is None`, application is backward-compatible with R-437 (configuration applied,
  AI deltas unapplied). When `proposal` is provided: pins (`pack_id`, `pack_version`, `base_ir_sha256`) are revalidated;
  `addressed_change_ids` are mapped to `manifest.changes`; collisions on entity names, API endpoints (method + path),
  and screen IDs are rejected; relation targets are verified against base and proposed entities; entities, APIs,
  and screens are immutably merged; and the derived IR is verified to be `validate_ir`-clean. `SolutionPackApplicationResult`
  tracks `applied_ai_delta_change_ids` and remaining `unapplied_ai_delta_change_ids` in deterministic JSON provenance.
  14 new tests; focused 66 passed; `task verify` **2,984 passed** offline (+14); lint/security/env + demos (152/149) green;
  deterministic serialization inspection green; 0 model calls. Workbook unchanged past R-358.

- **R-438 (bounded typed AI-delta proposal schema & local ModelProvider boundary — ninth spine brick)** shipped:
  new stdlib-only `solution_packs/ai_delta.py` defines frozen `AIDeltaProposal` (`pack_id`, `pack_version`,
  `base_ir_sha256`, `addressed_change_ids`, bounded `entities`, `apis`, `screens`, `capabilities`, `rationale`).
  Manifests with zero pending `ai-delta` changes bypass the model provider completely (0 calls) and return an empty
  proposal. For pending AI deltas, `build_ai_delta_messages` formulates system and user instructions embedding the
  base pack context and pending change intents; `parse_ai_delta_proposal` strictly validates untrusted JSON, rejecting
  credential-bearing fields (`password`, `secret`, `token`, `jwt`, `api_key`), entity name / API / screen collisions
  with base IR, unknown/missing keys, controls, malformed types, and unmapped change IDs; `generate_ai_delta_proposal`
  issues a single bounded `GenerateRequest` to `provider.generate()`. The proposal is data only and does not apply the
  delta, mutate base IR, generate source, build repos, or invoke cloud models. 15 new tests; focused 52 passed;
  `task verify` **2,970 passed** offline (+15); lint/security/env + demos (152/149) green; deterministic zero-call/mock
  inspection green; 0 model calls. Workbook unchanged past R-358.
- **R-437 (deterministic pack configuration application — eighth spine brick)** shipped: manifest schema 1.1
  adds bounded `desired_text` only for explicit configuration/update of `project:name` or
  `project:description`; summaries are never interpreted and legacy R-436 schema 1.0 JSON round-trips
  losslessly. New `application.py` revalidates the exact registry pin, preflights all config/duplicate targets,
  loads a fresh pack IR, applies only those two metadata targets immutably, and requires validate_ir-clean
  output. Unsupported config fails closed; AI-delta IDs are reported unapplied. Frozen canonical result records
  base/derived digests, applied/pending IDs, and the derived IR. Repeated apply is byte-stable; empty/AI-only
  retains the base digest; baseline unchanged. 10 new tests; focused 37 passed; `task verify` **2,955 passed**
  offline; lint/security/env + demos (152/149) green; deterministic inspection green; 0 model calls. Workbook
  unchanged past R-358.
- **R-436 (pinned declarative customization manifests — seventh spine brick)** shipped: new stdlib-only
  `solution_packs/manifest.py` defines frozen, factory-created manifests above selected R-435 recommendations.
  Pack id/version/canonical IR SHA-256 plus the exact domain/capability/target query are pinned and revalidated
  against the registry. At most 32 canonical changes use typed configuration/AI-delta source, add/update/remove
  operation, six semantic areas, area-compatible target refs, bounded summary, and 1–8 acceptance criteria.
  Strict parsing rejects unknown/missing keys, malformed/unbounded values, duplicates, controls, noncanonical
  order, and registry/query/version/digest drift. Canonical JSON is byte-stable. The schema cannot carry file
  paths, patches, source blobs, commands, raw model output, or secret values and has no application/build/model
  behavior. 11 new tests; focused 27 passed; `task verify` **2,945 passed** offline; lint/security/env + demos
  (152/149) green; canonical round-trip green; 0 model calls. Workbook unchanged past R-358.
- **R-435 (exact-compatible pack recommendations — sixth spine brick)** shipped: registry selection now
  accepts required targets as well as exact domain/capabilities. Frozen `SolutionPackRecommendation` stores
  a canonical query and minimal id/version/digest/targets selection metadata or `no-exact-match`. Every
  `EcosystemPlan` derives targets from its already-planned surface IR project plans and exposes one
  recommendation in JSON/CLI without applying a pack. Blog-cms Next.js/Python selects
  `minimal-blog@1.0.0`; current rideshare Next.js/Python correctly does not select its Go-backed baseline.
  Existing IRs/build output unchanged. 8 new tests; focused 25 passed; `task verify` **2,934 passed** offline;
  lint/security/env + demos (152/149) green; 0 model calls. Workbook unchanged past R-358.
- **R-434 (versioned baseline Solution Pack registry — fifth spine brick)** shipped: new stdlib-only
  `solution_packs` package registers `minimal-blog@1.0.0` and `rideshare-favourites@1.0.0` by reference to
  their existing Application IR examples. Frozen descriptors pin domains/capabilities, canonical IR SHA-256,
  and exact targets; registry construction revalidates IRs, targets, and verify plans and rejects malformed,
  duplicate, missing, or drifted entries. Selection is exact-domain + capability-subset, deterministic,
  newest-version-first, and returns no match rather than guessing. Fresh pack loads are validate_ir-clean.
  `task agent-engine:solution-packs` lists/selects JSON without build/model/network/live execution. 8 new
  tests; `task verify` **2,926 passed** offline; lint/security/env + demos (152/149) green; 0 model calls.
  Workbook unchanged because its planned universe ends at R-358.
- **R-433 (surface-specific data/capability scoping — fourth spine brick)** shipped: `intake/ecosystem.py`
  now applies complete read/write mappings for every surface in all ten curated domains and conservative
  entity-name matching to R-432 refined domains, with a complete-model fallback when intent is ambiguous.
  Recursive relation closure retains targets as read dependencies. Each IR declares only the normalized
  surface actor role with entity-qualified permissions; selected readable data gets list screens, only the
  writable subset gets editors + POST/PUT/DELETE, and every mutation requires that role. Public GET behavior
  is preserved for current previews. Food delivery now plans Customer (catalog read, Order write), Merchant,
  Courier (Order + Restaurant dependency, Order-only write; 8 APIs/2 screens), and Admin (Order+Restaurant;
  11 APIs/4 screens) as distinct IRs. Plan JSON exposes roles/permissions/writable entities. 7 new tests;
  focused R-431/R-432/R-433 suite 30 passed; `task verify` **2,918 passed** offline; lint/security/env + demos
  (152/149) green; 0 model calls. Workbook unchanged because its planned universe ends at R-358.
- **R-432 (opt-in unknown-domain refinement — third spine brick)** shipped: new stdlib-only
  `intake/scope_refinement.py` runs R-430 first, bypasses the provider for curated domains, and permits one
  explicit `ModelProvider` request only for `custom-application`. Exact bounded parsing produces a
  `ScopeProposal` + typed entities and rejects invalid keys/types/actors/relations, >3 questions, credential
  fields, relation-derived FK collisions, and unsupported validation rules. `plan_refined_ecosystem` reuses
  R-431's deterministic repository-wired CRUD/IR path. New local-only CLI
  `task agent-engine:ecosystem:refine`; it prints parsed data, not raw model output, and never uses cloud.
  Live apiary proof: Beekeeper Dashboard + Admin Panel, 4 entities, 23 APIs, 8 screens per app. 14 focused
  tests; `task verify` **2,911 passed** offline with 0 model calls; lint/security/env + demos (152/149) green.
  Five explicit local calls outside verify hardened/proved the boundary; 0 cloud calls.
- **R-431 (Scope → Application IRs — second spine brick)** shipped: new stdlib-only `intake/ecosystem.py` maps each proposed `AppSurface` to a `validate_ir`-clean `ApplicationIR` from a curated `DOMAIN_ENTITIES` model (10 domains + fallback) + a deterministic CRUD API/screen deriver that WIRES to real repositories (no 501 stubs). `plan_ecosystem`/`plan_ecosystem_from_prompt` build an `EcosystemPlan` (respecting the build-scope option); `build_ecosystem` materializes each app as its own owned repo via `build_app_from_ir`. CLIs `task agent-engine:ecosystem:plan` (deterministic) / `:build` (opt-in). A food-delivery prompt → 4 apps → 4 owned repos (164 files each). **Verified all four compile clean (`tsc --noEmit` → 0 errors)**, which exposed + fixed **4 generator bugs** in `codegen/nextjs.py` (over-braced FK `<select>` onChange; single-brace bool-badge style; multi-subcollection two-root → fragment; entity interface missing the scalar `<relation>_id` FK field). `tests/test_ecosystem.py` (9 tests). `task verify` **2,897** pass; lint/security/env + demos (152/149) green; R-429 examples still pass `web-typecheck`; 0 model calls. Single commit authored `sanjeetji <sk698166@gmail.com>`.
- **R-430 (Ecosystem Scope Compiler — first spine brick)** shipped: new stdlib-only `intake/scope_compiler.py` turns a prompt into a framework-neutral `ScopeProposal` (domain + confidence + matched keywords, actors, multi-surface ecosystem, Complete/Customer-only/Custom options, ≤3 questions) via a deterministic 10-domain `DOMAIN_LIBRARY` + weighted keyword `classify_domain()` + `propose_ecosystem()` (with a `custom-application` fallback). Deterministic CLI `task agent-engine:scope:propose`. `tests/test_scope_compiler.py` (11 tests). `task verify` **2,888** pass; 0 model calls. Single commit authored `sanjeetji <sk698166@gmail.com>`.
- **R-429 (generated web app passes strict `tsc --noEmit`)** shipped: fixed **8** type-error classes at `codegen/nextjs.py` + the generated tsconfig so a generated `minimal-blog` (was 84 errors) and `rideshare-favourites` compile with **0** errors — G0 `skipLibCheck`, G1 duplicate exports (context-menu), G2 `displayName` on sub-component aliases, G3 typed compound (color-picker/pin-input), G4 `HTMLAttributes` `Omit` (banner/carousel/checkbox/code-block), G5 `React.RefObject<T>` (was `<T | null>`), G6 terminal `variant` default `"default"`→`"minimal"`, G7 `SplitDiffRow.isUnchanged`, G8 `api` object gains the `…WithCount` methods + hooks forward a fresh `requestParams` with `...options` first. `task agent-engine:web-typecheck` reports PASSED for both examples. `task verify` **2,877** pass; 0 model calls. Single commit authored `sanjeetji <sk698166@gmail.com>`.
- **R-428 (generated-app compile fixes + opt-in tsc gate)** shipped: added `task agent-engine:web-typecheck` (generate + pnpm install + `tsc --noEmit`, opt-in/live). Fixed the run-blocking generator bugs it revealed — over-braced event handlers (`=> {{`), a `pdf-viewer.tsx` literal `\n`, and screen import depth (switched `../components/`/`../lib/` → the `@/` alias at 24 sites). Verified: generated `minimal-blog` compiles under `next dev`, `/`,`/post_list`,`/post_editor` → 200. Added `test_generated_tsx_compile.py` + updated 9 screen-test files (`../` → `@/`). `task verify` **2,873** pass; lint/security/env + demos green; 0 model calls. Single commit authored `sanjeetji <sk698166@gmail.com>`.
- **R-427 (generated JSX inline-style fix)** shipped: 14 f-string `style={{ … }}` → `{{{{ … }}}}` (single-brace JSX styles were causing HTTP 500) + a regression test.
- **R-426 (remove from history)** shipped: `StudioBuildHistory.remove(id)` + `POST /api/history/delete {id}` (in-memory, both modes) + a per-build "Remove" button.
- **R-425 (per-build repo actions)** shipped: Recent builds items have Copy path (client clipboard, both modes) and Open folder (`POST /api/history/open {id}`, trusted-local) via injected `open_dir_fn` + generic `_run_id_control`.
- **R-424 (live preview status)** shipped: `LocalAppSession.is_alive()` + liveness-aware `StudioPreviewManager.status()` + page polling of `GET /api/preview` (no iframe reload on unchanged URL).
- **R-423 (build history + re-preview)** shipped: `studio/history.py` `StudioBuildHistory` + `GET /api/history` and `POST /api/history/preview {id}`, a "Recent builds" list, and history recording in `live_serve`.
- **R-422 (collision-free preview ports + controls)** shipped: each preview allocates two distinct free loopback ports (`allocate_preview_ports`) via `start_preview_app`; `StudioPreviewManager` gained bounded, secret-free `status()`/`stop()`/`restart()` at `GET /api/preview` + `POST /api/preview/stop|restart` (trusted-local only; build-only 404s).
- **R-421 (managed embedded local preview)** shipped: `studio:serve` remains build-only; explicit
  `studio:preview` (depends `db:up`) executes one generated app through exported LocalAppSession/start_app,
  waits for API/web readiness, and embeds its loopback URL in a sandboxed iframe. StudioPreviewManager
  serializes replacement and cleanup, with secret-free failure states that preserve the repo. Port
  preflight/exited-child checks prevent stale apps from being reported ready. 38 focused tests and
  `task verify` **2,823** pass; lint/security/env and both demos green; 0 model calls.
- **R-420 (generated SQL hardening)** shipped: one PostgreSQL identifier encoder is used across schema,
  seed, Python repository, and Go store SQL. Stable FK topological ordering puts parents before dependants,
  preserves independent source order, supports self-references, and rejects non-self cycles clearly.
  Seven focused tests + 186 related regressions pass; `task verify` **2,808** passing; lint/security/env and
  both demos green. Generated Python/Go syntax checks passed. A reserved-name User/Order migration passed
  a rollback-only live PostgreSQL proof. 0 model calls. No workbook row exists past R-358.
- **R-419 (turnkey local run)** shipped: new `localrun/` package (`plan.py` `build_run_plan`, `run.py` executor) + opt-in `task agent-engine:app:run` (Task deps `db:up`). 12 focused tests, `task verify` **2,801** passing (0 model calls), lint/security/env green, demo unchanged. Live proof: one command booted the blog app (uvicorn :8000 `/healthz` 200 + `/posts` seeded; Next.js :3000 200). Fixed `pnpm install` → `pnpm install --ignore-scripts`. Surfaced 2 codegen SQL bugs → R-420. Single commit authored `sanjeetji <sk698166@gmail.com>`, pushed.
- **R-418 (chat studio web UI)** shipped (brick 3): `studio/` package + opt-in `task agent-engine:studio:serve`.
- **R-417 (Prompt → generated app repo)** shipped (brick 2): `intake/build_app.py` + opt-in `task agent-engine:app:build`.
- **R-416 (Prompt → Application IR intake agent)** shipped (brick 1): `intake/` package + opt-in `task agent-engine:intake:run`.
- **R-415 (Phone Number Input Suite)** was the last UI-component-series task (110 components; paused/resumable).
- **R-421 code and required documentation are verified for the checkpoint commit on `main`**. Preserve
  and exclude the unrelated untracked `.claude/` directory.
- Tracker and state files kept fully consistent and verified.
- Completed:
  1. **R-363**: Tour & Onboarding Spotlight Guide Suite (`components/tour.tsx`)
  2. **R-364**: Transfer / Dual Listbox Picker Primitive (`components/transfer.tsx`)
  3. **R-365**: Markdown & Rich Content Editor Suite (`components/markdown-editor.tsx`)
  4. **R-366**: Calendar & Event Scheduler Suite (`components/calendar.tsx`)
  5. **R-367**: Kanban Board & Task Flow Matrix Suite (`components/kanban.tsx`)
  6. **R-368**: Infinite Virtual List & Windowed Scroller Suite (`components/virtual-list.tsx`)
  7. **R-369**: Query Filter Builder & Dynamic Rule Bar Suite (`components/filter-builder.tsx`)
  8. **R-370**: Data Visualization & SVG Chart Suite (`components/chart.tsx`)
  9. **R-371**: Time Picker & Time Range Suite (`components/time-picker.tsx`)
  10. **R-372**: Digital Signature Pad & Drawing Canvas Primitive (`components/signature-pad.tsx`)
  11. **R-373**: Diff Viewer & Code/Text Comparison Suite (`components/diff-viewer.tsx`)
  12. **R-374**: Org Chart & Hierarchy Flow Diagram Suite (`components/org-chart.tsx`)
  13. **R-375**: Heatmap & Activity Contribution Matrix Suite (`components/heatmap.tsx`)
  14. **R-376**: Media Player Suite (`components/media-player.tsx`)
  15. **R-377**: Pivot Table & Cross-Tabulation Matrix Suite (`components/pivot-table.tsx`)
  16. **R-378**: Image Cropper & Canvas Mask Suite (`components/image-cropper.tsx`)
  17. **R-379**: Gantt Chart & Project Roadmap Suite (`components/gantt-chart.tsx`)
  18:   18. **R-380**: Flowchart & Node-Based Workflow Canvas Suite (`components/flow-canvas.tsx`)
  19. **R-381**: Terminal & Command Console Suite (`components/terminal.tsx`)
  20. **R-382**: QR Code & Barcode Suite (`components/qr-code.tsx`)
  21. **R-383**: Spreadsheet & Inline Data Sheet Suite (`components/spreadsheet.tsx`)
  22. **R-384**: Chat & Real-Time Messaging Suite (`components/chat.tsx`)
  23. **R-385**: Audio & Voice Recorder Suite (`components/audio-recorder.tsx`)
  24. **R-386**: File Explorer & Storage Browser Suite (`components/file-explorer.tsx`)
  25. **R-387**: Interactive Geo Map & Location Pinpoint Suite (`components/geo-map.tsx`)
  26. **R-388**: PDF & Document Viewer Suite (`components/pdf-viewer.tsx`)
  27. **R-389**: Audio Player & Frequency Equalizer Suite (`components/audio-player.tsx`)
  28. **R-390**: Video Player & Streaming Theater Suite (`components/video-player.tsx`)
  29. **R-391**: Whiteboard & Collaborative Canvas Suite (`components/whiteboard.tsx`)
  30. **R-392**: Code Diff Editor & 3-Way Merge Conflict Resolver Suite (`components/merge-editor.tsx`)
  31. **R-393**: Interactive JSON Viewer & Schema Tree Inspector Suite (`components/json-viewer.tsx`)
  32. **R-394**: Image Gallery & Masonry Lightbox Suite (`components/image-gallery.tsx`)
  33. **R-395**: Network Graph & Topology Map Suite (`components/network-graph.tsx`)
  34. **R-396**: Live Log Viewer & Event Stream Inspector Suite (`components/log-viewer.tsx`)
  35. **R-397**: Mind Map & Concept Tree Suite (`components/mind-map.tsx`)
  36. **R-398**: Audio Waveform & Spectrum Visualizer Suite (`components/audio-visualizer.tsx`)
  37. **R-399**: Particle Network & Interactive Constellation Canvas Suite (`components/particle-network.tsx`)
  38. **R-400**: Before/After Image Comparison Slider Suite (`components/image-comparison.tsx`)
  39. **R-401**: Countdown Timer, Stopwatch & Live Clock Suite (`components/countdown.tsx`)
  40. **R-402**: Cookie Consent & Preferences Manager Suite (`components/cookie-consent.tsx`)
  41. **R-403**: Password Strength Meter & Requirements Suite (`components/password-strength.tsx`)
  42. **R-404**: Masked / Pattern Input Suite (`components/masked-input.tsx`)
  43. **R-405**: Mention / @-Autocomplete Textarea Suite (`components/mention.tsx`)
  44. **R-406**: Marquee / Ticker Suite (`components/marquee.tsx`)
  45. **R-407**: Credit Card Payment Field Suite (`components/credit-card.tsx`)
  46. **R-408**: Color Contrast Checker Suite (`components/color-contrast.tsx`)
  47. **R-409**: Currency / Money Input Suite (`components/currency-input.tsx`)
  48. **R-410**: Password Generator Suite (`components/password-generator.tsx`)
  49. **R-411**: Slug / URL Input Suite (`components/slug-input.tsx`)
  50. **R-412**: Character & Word Counter Textarea Suite (`components/character-counter.tsx`)
  51. **R-413**: Copy-to-Clipboard Button Suite (`components/copy-button.tsx`)
  52. **R-414**: Duration Input Suite (`components/duration-input.tsx`)
- R-437 is complete; the next coding action is gated on recording the R-438 contract. Still stop-and-ask
  only for paid cloud / DB engine / new infra / native-mobile / a materially different architecture decision.

## Completed

### R-414 — Generated Accessible Futuristic Reusable Duration Input Suite (components/duration-input.tsx)

Enabled a genuinely functional duration input across generated Next.js web applications:
- **Standalone Duration Input Suite (`apps/web/components/duration-input.tsx`)**:
  - Implemented `DurationInputVariant`, `DurationInputSize`, `DurationUnit`, `DurationInputHandle`, `DurationInputProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps, `UNIT_SECONDS`/`UNIT_LABEL`/`UNIT_SUFFIX` tables, and `toSegments`/`fromSegments`/`formatDuration` helpers.
  - Compound and semantic alias exports: `DurationInput`, `DurationField`, `TimeSpanInput`, `IntervalInput`, default export.
  - Segmented days/hours/minutes/seconds inputs converting to/from total seconds; min/max clamp with normalization; live formatted summary; controlled + uncontrolled `value`.
  - `onChange(totalSeconds)`; WAI-ARIA `role="group"` + per-segment `aria-label` + `inputMode="numeric"`.
  - React ref forwarding (`forwardRef`), imperative handle (`DurationInputHandle`: `getValue`/`setValue`/`getFormatted`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_duration_input_component` in `omnistackai_agent_engine.codegen` and registered `components/duration-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; ASCII-only; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_duration_input_component.py` (all passing).
  - `task verify` passing: 2,735 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 151 files (includes `apps/web/components/duration-input.tsx`).

### R-413 — Generated Accessible Futuristic Reusable Copy-to-Clipboard Button Suite (components/copy-button.tsx)

Enabled a genuinely functional copy-to-clipboard button across generated Next.js web applications:
- **Standalone Copy Button Suite (`apps/web/components/copy-button.tsx`)**:
  - Implemented `CopyButtonVariant`, `CopyButtonSize`, `CopyButtonHandle`, `CopyButtonProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps, `writeClipboard` helper, and inline `CopyGlyph`/`CheckGlyph` SVG icons.
  - Compound and semantic alias exports: `CopyButton`, `CopyToClipboard`, `ClipboardButton`, `CopyIconButton`, default export.
  - `navigator.clipboard.writeText` with `execCommand` fallback; transient "Copied" state (timeout) with icon swap + `aria-live`; disabled when nothing to copy; `onCopy`/`onError`.
  - ASCII-only source (inline SVG); WAI-ARIA button `aria-label` + visually-hidden `aria-live` status.
  - React ref forwarding (`forwardRef`), imperative handle (`CopyButtonHandle`: `copy`/`isCopied`/`reset`/`focus`), explicit `displayName` across all exports.
  - Exported `render_copy_button_component` in `omnistackai_agent_engine.codegen` and registered `components/copy-button.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_copy_button_component.py` (all passing).
  - `task verify` passing: 2,717 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 150 files (includes `apps/web/components/copy-button.tsx`).

### R-412 — Generated Accessible Futuristic Reusable Character & Word Counter Textarea Suite (components/character-counter.tsx)

Enabled a genuinely functional character/word counting textarea across generated Next.js web applications:
- **Standalone Character Counter Suite (`apps/web/components/character-counter.tsx`)**:
  - Implemented `CharacterCounterVariant`, `CharacterCounterSize`, `CharacterCounterStats`, `CharacterCounterHandle`, `CharacterCounterProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps and `countCharacters`/`countWordsIn`/`computeStats` helpers.
  - Compound and semantic alias exports: `CharacterCounter`, `CharCounter`, `WordCounter`, `TextCounter`, default export.
  - Unicode-safe char counting (`Array.from`), word counting (trim + whitespace split), maxLength/maxWords, computed stats, hard limit, warn threshold, optional progress bar.
  - Controlled + uncontrolled `value`; `onChange(value, stats)`; WAI-ARIA labeled textarea + `aria-describedby` → `role="status"` `aria-live` counter.
  - React ref forwarding (`forwardRef`), imperative handle (`CharacterCounterHandle`: `getValue`/`setValue`/`getStats`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_character_counter_component` in `omnistackai_agent_engine.codegen` and registered `components/character-counter.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_character_counter_component.py` (all passing).
  - `task verify` passing: 2,699 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 149 files (includes `apps/web/components/character-counter.tsx`).

### R-411 — Generated Accessible Futuristic Reusable Slug / URL Input Suite (components/slug-input.tsx)

Enabled a genuinely functional URL-slug field across generated Next.js web applications:
- **Standalone Slug Input Suite (`apps/web/components/slug-input.tsx`)**:
  - Implemented `SlugInputVariant`, `SlugInputSize`, `SlugInputHandle`, `SlugInputProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps and a `slugify()` helper.
  - Compound and semantic alias exports: `SlugInput`, `Slugify`, `UrlSlugInput`, `PermalinkInput`, default export.
  - Real-time slugify (NFKD + charCodeAt diacritic strip, lowercase, non-alphanumeric→separator, trim/collapse); auto-sync from `source` until manually edited; prefix + full URL; copy-to-clipboard.
  - Controlled + uncontrolled `value`; `maxLength`; `onChange`/`onCopy`; WAI-ARIA labeled input + `aria-live` copied announcement; ASCII-only generated source.
  - React ref forwarding (`forwardRef`), imperative handle (`SlugInputHandle`: `getValue`/`getFullUrl`/`setValue`/`slugify`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_slug_input_component` in `omnistackai_agent_engine.codegen` and registered `components/slug-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_slug_input_component.py` (all passing).
  - `task verify` passing: 2,681 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 148 files (includes `apps/web/components/slug-input.tsx`).

### R-410 — Generated Accessible Futuristic Reusable Password Generator Suite (components/password-generator.tsx)

Enabled a genuinely functional secure password generator across generated Next.js web applications:
- **Standalone Password Generator Suite (`apps/web/components/password-generator.tsx`)**:
  - Implemented `PasswordGeneratorVariant`, `PasswordGeneratorSize`, `PasswordGeneratorOptions`, `PasswordGeneratorHandle`, `PasswordGeneratorProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps and `secureRandomInt`/`buildSets`/`generatePassword`/`strengthOf`/`writeClipboard` helpers.
  - Compound and semantic alias exports: `PasswordGenerator`, `PasswordCreator`, `SecurePasswordGenerator`, `PasswordMaker`, default export.
  - `crypto.getRandomValues` secure RNG (Math.random fallback); guaranteed per-set coverage + Fisher-Yates shuffle; charset toggles; exclude-ambiguous; length slider; strength meter; copy-to-clipboard + regenerate.
  - SSR-safe (auto-generate on mount); `onGenerate`/`onCopy`; WAI-ARIA `role="group"`, labeled controls, `aria-live` copied announcement.
  - React ref forwarding (`forwardRef`), imperative handle (`PasswordGeneratorHandle`: `generate`/`getValue`/`copy`/`setLength`), explicit `displayName` across all exports.
  - Exported `render_password_generator_component` in `omnistackai_agent_engine.codegen` and registered `components/password-generator.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_password_generator_component.py` (all passing).
  - `task verify` passing: 2,663 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 147 files (includes `apps/web/components/password-generator.tsx`).

### R-409 — Generated Accessible Futuristic Reusable Currency / Money Input Suite (components/currency-input.tsx)

Enabled a genuinely functional locale-aware currency input across generated Next.js web applications:
- **Standalone Currency Input Suite (`apps/web/components/currency-input.tsx`)**:
  - Implemented `CurrencyInputVariant`, `CurrencyInputSize`, `CurrencyInputHandle`, `CurrencyInputProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps and `sanitizeNumeric`/`toNumber`/`formatCurrency` helpers.
  - Compound and semantic alias exports: `CurrencyInput`, `MoneyInput`, `CurrencyField`, `PriceInput`, default export.
  - `Intl.NumberFormat` currency formatting on blur, plain numeric on focus; `parseFloat` parsing; min/max clamp; step/allowNegative/currency/locale props.
  - Controlled + uncontrolled `value`; `onChange(value|null, formatted)`/`onBlur`; WAI-ARIA labeled input, `aria-invalid`, `inputMode="decimal"`.
  - React ref forwarding (`forwardRef`), imperative handle (`CurrencyInputHandle`: `getValue`/`getFormatted`/`setValue`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_currency_input_component` in `omnistackai_agent_engine.codegen` and registered `components/currency-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_currency_input_component.py` (all passing).
  - `task verify` passing: 2,645 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 146 files (includes `apps/web/components/currency-input.tsx`).

### R-408 — Generated Accessible Futuristic Reusable Color Contrast Checker Suite (components/color-contrast.tsx)

Enabled a genuinely functional WCAG color-contrast checker across generated Next.js web applications:
- **Standalone Color Contrast Suite (`apps/web/components/color-contrast.tsx`)**:
  - Implemented `ColorContrastVariant`, `ColorContrastSize`, `ContrastResult`, `ColorContrastHandle`, `ColorContrastProps`, plus `VARIANT_STYLES`/`SIZE_STYLES` maps and `parseHex`/`channelLuminance`/`relativeLuminance`/`contrastRatio`/`evaluateContrast` helpers.
  - Compound and semantic alias exports: `ColorContrast`, `ContrastChecker`, `WcagContrast`, `ContrastRatio`, default export.
  - WCAG 2.x relative luminance + contrast ratio; AA/AAA pass-fail for normal/large text and UI components; computed `ContrastResult`; live preview swatch; native color + hex inputs; swap action; pass/fail badges.
  - Controlled + uncontrolled colors; `onChange(result, colors)`; WAI-ARIA labeled inputs + `role="status"` `aria-live` result region.
  - React ref forwarding (`forwardRef`), imperative handle (`ColorContrastHandle`: `getRatio`/`getResult`/`setColors`/`swap`), explicit `displayName` across all exports.
  - Exported `render_color_contrast_component` in `omnistackai_agent_engine.codegen` and registered `components/color-contrast.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_color_contrast_component.py` (all passing).
  - `task verify` passing: 2,628 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 145 files (includes `apps/web/components/color-contrast.tsx`).

### R-407 — Generated Accessible Futuristic Reusable Credit Card Payment Field Suite (components/credit-card.tsx)

Enabled a genuinely functional credit-card payment field across generated Next.js web applications:
- **Standalone Credit Card Suite (`apps/web/components/credit-card.tsx`)**:
  - Implemented `CreditCardVariant`, `CreditCardSize`, `CardBrand`, `CreditCardValue`, `CreditCardMeta`, `CreditCardHandle`, `CreditCardProps`, plus `VARIANT_STYLES`/`SIZE_STYLES`/`BRAND_META` maps and `onlyDigits`/`detectBrand`/`formatNumber`/`formatExpiry`/`luhnValid`/`expiryValid` helpers.
  - Compound and semantic alias exports: `CreditCard`, `CreditCardField`, `PaymentCardField`, `CardInput`, default export.
  - Real-time number formatting + IIN brand detection + Luhn validation; expiry MM/YY validity; brand-aware CVC length; optional cardholder name; computed meta; optional live gradient preview.
  - Controlled + uncontrolled `value`; `onChange(value, meta)`/`onComplete`; WAI-ARIA labeled inputs with `aria-invalid`, `inputMode="numeric"`, `autoComplete` cc-* hints.
  - React ref forwarding (`forwardRef`), imperative handle (`CreditCardHandle`: `getValue`/`getMeta`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_credit_card_component` in `omnistackai_agent_engine.codegen` and registered `components/credit-card.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies; only placeholder card numbers in source.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_credit_card_component.py` (all passing).
  - `task verify` passing: 2,610 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 144 files (includes `apps/web/components/credit-card.tsx`).

### R-406 — Generated Accessible Futuristic Reusable Marquee / Ticker Suite (components/marquee.tsx)

Enabled a genuinely functional continuous ticker/marquee across generated Next.js web applications:
- **Standalone Marquee Suite (`apps/web/components/marquee.tsx`)**:
  - Implemented `MarqueeVariant`, `MarqueeSize`, `MarqueeDirection`, `MarqueeHandle`, `MarqueeProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` maps and a `MARQUEE_CSS` keyframes string.
  - Compound and semantic alias exports: `Marquee`, `MarqueeTicker`, `ScrollingBanner`, `NewsTicker`, default export.
  - Seamless `-50%` loop via a duplicated (aria-hidden) content copy; CSS `@keyframes` (`omni-marquee-x`/`omni-marquee-y`) injected in an inline `<style>`; `animationDirection` handles left/right/up/down.
  - Configurable `durationSeconds`/`gap`/`gradientEdges` (CSS `maskImage`); `pauseOnHover` + controlled `paused` + imperative pause/resume/toggle (`animationPlayState`); CSS `prefers-reduced-motion` guard stops the scroll.
  - React ref forwarding (`forwardRef`), imperative handle (`MarqueeHandle`: `pause`/`resume`/`toggle`/`isPaused`), explicit `displayName` across all exports.
  - Exported `render_marquee_component` in `omnistackai_agent_engine.codegen` and registered `components/marquee.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_marquee_component.py` (all passing).
  - `task verify` passing: 2,592 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 143 files (includes `apps/web/components/marquee.tsx`).

### R-405 — Generated Accessible Futuristic Reusable Mention / @-Autocomplete Textarea Suite (components/mention.tsx)

Enabled a genuinely functional @-mention autocomplete textarea across generated Next.js web applications:
- **Standalone Mention Suite (`apps/web/components/mention.tsx`)**:
  - Implemented `MentionVariant`, `MentionSize`, `MentionItem`, `MentionHandle`, `MentionProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` maps and `detectTrigger()`/`defaultFilter()`/`extractMentions()` helpers.
  - Compound and semantic alias exports: `Mention`, `MentionInput`, `MentionTextarea`, `AtMention`, default export.
  - Caret-aware trigger detection (configurable `trigger`, default `@`); filtered suggestion listbox from `items`; keyboard nav (ArrowDown/ArrowUp/Enter/Tab/Escape) + mouse; token insertion with caret repositioning; mention-id extraction.
  - Controlled + uncontrolled `value`; `onChange(value, mentions)` / `onMention`; ARIA combobox/listbox (`aria-expanded`/`aria-controls`/`aria-activedescendant`/`aria-autocomplete`; `role="listbox"`/`role="option"`/`aria-selected`).
  - React ref forwarding (`forwardRef`), imperative handle (`MentionHandle`: `getValue`/`setValue`/`getMentions`/`focus`/`clear`), explicit `displayName` across all exports.
  - Exported `render_mention_component` in `omnistackai_agent_engine.codegen` and registered `components/mention.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_mention_component.py` (all passing).
  - `task verify` passing: 2,574 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 142 files (includes `apps/web/components/mention.tsx`).

### R-404 — Generated Accessible Futuristic Reusable Masked / Pattern Input Suite (components/masked-input.tsx)

Enabled a genuinely functional masked/pattern text input across generated Next.js web applications:
- **Standalone Masked Input Suite (`apps/web/components/masked-input.tsx`)**:
  - Implemented `MaskedInputVariant`, `MaskedInputSize`, `MaskedInputPreset`, `MaskedInputResult`, `MaskedInputHandle`, `MaskedInputProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` maps, `PRESET_MASKS`, `TOKENS`, and the `applyMask()` helper.
  - Compound and semantic alias exports: `MaskedInput`, `InputMask`, `PatternInput`, `FormattedInput`, default export.
  - Token-based masking (`9`/`A`/`*` + literals) formatting in real time; returns `{formatted, raw, complete}`; presets (phone/date/card/time/ssn) + custom masks.
  - Caret kept at end via `requestAnimationFrame` + `setSelectionRange`; controlled + uncontrolled `value`; `onChange`/`onComplete`; `inputMode` pass-through; WAI-ARIA `aria-label`/`aria-required`.
  - React ref forwarding (`forwardRef`), imperative handle (`MaskedInputHandle`: `getValue`/`getRawValue`/`setValue`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_masked_input_component` in `omnistackai_agent_engine.codegen` and registered `components/masked-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_masked_input_component.py` (all passing).
  - `task verify` passing: 2,556 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 141 files (includes `apps/web/components/masked-input.tsx`).

### R-403 — Generated Accessible Futuristic Reusable Password Strength Meter & Requirements Suite (components/password-strength.tsx)

Enabled a genuinely functional password strength meter across generated Next.js web applications:
- **Standalone Password Strength Suite (`apps/web/components/password-strength.tsx`)**:
  - Implemented `PasswordStrengthVariant`, `PasswordStrengthSize`, `PasswordStrengthLevel`, `PasswordRule`, `PasswordStrengthResult`, `PasswordStrengthHandle`, `PasswordStrengthProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES`/`LEVEL_META` maps and `defaultRules(minLength)`/`evaluate()` helpers.
  - Compound and semantic alias exports: `PasswordStrength`, `PasswordStrengthMeter`, `PasswordInput`, `PasswordField`, default export.
  - Live rule-based scoring → `empty`/`weak`/`fair`/`good`/`strong`; 4-segment strength bar; live requirements checklist (default: min length, uppercase, lowercase, number, symbol; overridable via `rules`).
  - Show/hide toggle (`aria-pressed`), controlled + uncontrolled `value`, `onChange`/`onStrengthChange` callbacks.
  - Accessibility: `role="status"` + `aria-live` strength text, `aria-describedby` via `useId`; SSR-safe; JS `prefers-reduced-motion` guard on the bar transition.
  - React ref forwarding (`forwardRef`), imperative handle (`PasswordStrengthHandle`: `getValue`/`setValue`/`getStrength`/`clear`/`focus`), explicit `displayName` across all exports.
  - Exported `render_password_strength_component` in `omnistackai_agent_engine.codegen` and registered `components/password-strength.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_password_strength_component.py` (all passing).
  - `task verify` passing: 2,538 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 140 files (includes `apps/web/components/password-strength.tsx`).

### R-402 — Generated Accessible Futuristic Reusable Cookie Consent & Preferences Manager Suite (components/cookie-consent.tsx)

Enabled a genuinely functional cookie-consent / preferences manager across generated Next.js web applications:
- **Standalone Cookie Consent Suite (`apps/web/components/cookie-consent.tsx`)**:
  - Implemented `CookieConsentVariant`, `CookieConsentSize`, `CookieConsentPosition`, `ConsentCategory`, `ConsentState`, `CookieConsentHandle`, `CookieConsentProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` maps and `DEFAULT_CATEGORIES`.
  - Compound and semantic alias exports: `CookieConsent`, `ConsentBanner`, `CookieBanner`, `ConsentManager`, default export.
  - Compact banner (Accept all / Reject all / Customize) + expandable per-category `role="switch"` preferences (required categories forced on & disabled).
  - `localStorage` persistence (`getItem`/`setItem` under `storageKey`, try/catch-wrapped); SSR-safe `mounted` flag (renders null until mounted; stored consent read only after mount).
  - Configurable categories, title/description, optional privacy-policy link, button labels, `forceShow`; `onAccept`/`onReject`/`onChange` callbacks; 5 placements; WAI-ARIA `role="region"` + `role="switch"`/`aria-checked`.
  - React ref forwarding (`forwardRef`), imperative handle (`CookieConsentHandle`: `open`/`close`/`accept`/`reject`/`getConsent`/`reset`), explicit `displayName` across all exports.
  - Exported `render_cookie_consent_component` in `omnistackai_agent_engine.codegen` and registered `components/cookie-consent.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_cookie_consent_component.py` (all passing).
  - `task verify` passing: 2,520 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 139 files (includes `apps/web/components/cookie-consent.tsx`).

### R-401 — Generated Accessible Futuristic Reusable Countdown Timer, Stopwatch & Live Clock Suite (components/countdown.tsx)

Enabled a genuinely functional countdown/stopwatch/live-clock timer across generated Next.js web applications:
- **Standalone Countdown Suite (`apps/web/components/countdown.tsx`)**:
  - Implemented `CountdownVariant`, `CountdownSize`, `CountdownMode`, `CountdownHandle`, `CountdownProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` hard-coded hex maps.
  - Compound and semantic alias exports: `Countdown`, `CountdownTimer`, `Stopwatch`, `LiveClock`, default export.
  - Three modes — `countdown` (to `targetDate` or fixed `duration`), `stopwatch`, `clock` (12h/24h) — driven by a real `window.setInterval` tick reading `Date.now()`.
  - SSR-safe `mounted` flag (deterministic "--" first paint, real time only after mount) to avoid hydration mismatch.
  - Day/hour/minute/second segments with optional labels + configurable `separator`, `autoStart`, controlled + uncontrolled `paused`, `onComplete`/`onTick` callbacks, JS `prefers-reduced-motion` guard, WAI-ARIA (`role="timer"`, `aria-atomic`, visually-hidden `aria-live` completion announcement).
  - React ref forwarding (`forwardRef`), imperative handle (`CountdownHandle`: `start`/`pause`/`reset`/`restart`/`getTime`/`isRunning`), explicit `displayName` across all exports.
  - Exported `render_countdown_component` in `omnistackai_agent_engine.codegen` and registered `components/countdown.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_countdown_component.py` (all passing).
  - `task verify` passing: 2,502 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 138 files (includes `apps/web/components/countdown.tsx`).

### R-400 — Generated Accessible Futuristic Reusable Before/After Image Comparison Slider Suite (components/image-comparison.tsx)

Enabled a genuinely interactive (non-cosmetic) before/after image comparison revealer across generated Next.js web applications:
- **Standalone Image Comparison Suite (`apps/web/components/image-comparison.tsx`)**:
  - Implemented `ImageComparisonVariant`, `ImageComparisonSize`, `ImageComparisonOrientation`, `ImageComparisonHandle`, `ImageComparisonProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` hard-coded hex maps.
  - Compound and semantic alias exports: `ImageComparison`, `BeforeAfterSlider`, `CompareSlider`, `ImageReveal`, default export.
  - Two layered images ("after" base + "before" clipped via CSS `clip-path`), with gradient placeholder layers when no `beforeSrc`/`afterSrc` is supplied.
  - Draggable divider with `setPointerCapture` pointer drag, click/tap-to-position on the track, and a `role="slider"` handle with full keyboard control (Arrow keys by `step`, Home/End → 0/100, PageUp/PageDown by 10).
  - Horizontal and vertical orientations; controlled + uncontrolled `position` with `onChange`; optional before/after labels; `disabled` state.
  - WAI-ARIA 1.2 semantics: `role="group"` container, `role="slider"` handle with `aria-valuemin`/`aria-valuemax`/`aria-valuenow`/`aria-valuetext`/`aria-orientation`; `aria-hidden` divider; alt text on image layers.
  - React ref forwarding (`forwardRef`), imperative handle (`ImageComparisonHandle`: `setPosition`/`getPosition`/`reset`), and explicit `displayName` across all exports.
  - Exported `render_image_comparison_component` in `omnistackai_agent_engine.codegen` and registered `components/image-comparison.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_image_comparison_component.py` (all passing).
  - `task verify` passing: 2,484 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 137 files (includes `apps/web/components/image-comparison.tsx`).

### R-399 — Generated Accessible Futuristic Reusable Particle Network & Interactive Constellation Canvas Suite (components/particle-network.tsx)

Enabled an accessible, desktop-and-mobile-grade, futuristic ambient particle/constellation canvas background across generated Next.js web applications (distinct from the data-driven `network-graph` — no required data props):
- **Standalone Particle Network Suite (`apps/web/components/particle-network.tsx`)**:
  - Implemented `ParticleNetworkVariant`, `ParticleNetworkSize`, `ParticleNetworkHandle`, `ParticleNetworkProps`, plus internal `VARIANT_STYLES`/`SIZE_STYLES` hard-coded hex maps.
  - Implemented compound and semantic alias exports: `ParticleNetwork`, `ConstellationCanvas`, `ParticleField`, `StarfieldBackground`, default export.
  - Implemented an HTML5 Canvas 2D `requestAnimationFrame` loop: internally-seeded particles (count derived from `count`/`density`, clamped 12–200), edge-bounce motion, proximity link lines with distance-proportional `globalAlpha`, and neon-variant glow.
  - Implemented pointer reactivity: gentle attraction toward the cursor and accent-colored cursor links within `interactionRadius` (pointer tracked in a ref — no re-render).
  - Implemented device-pixel-ratio-aware sizing (`ctx.setTransform` reset + `ctx.scale(dpr, dpr)`) with `window` resize handling.
  - Implemented a JS `prefers-reduced-motion` guard (net-new pattern): `matchMedia('(prefers-reduced-motion: reduce)')` renders a single static frame and schedules no rAF when reduced, with a live `change` listener (and `addListener` fallback).
  - Implemented imperative `ParticleNetworkHandle` (`pause`, `resume`, `toggle`, `restart`, `isPaused`, `getCanvas`) via `useImperativeHandle`, plus a controlled `paused` prop.
  - Implemented WAI-ARIA decorative semantics: wrapper `role="img"` + `aria-label`, `aria-hidden="true"` canvas, no focus trap, not keyboard-interactive.
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyan glow) and 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_particle_network_component` in `omnistackai_agent_engine.codegen` and registered `components/particle-network.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`; 0 external runtime dependencies.
- **Verification**:
  - 18 unit tests in `services/agent-engine/tests/test_particle_network_component.py` (all passing).
  - `task verify` passing: 2,466 tests passed.
  - `task lint`, `task security:quick`, `task env:check` — pass. `task builder:demo -- minimal-blog` — 136 files (includes `apps/web/components/particle-network.tsx`).

### R-398 — Generated Accessible Futuristic Reusable Audio Waveform & Spectrum Visualizer Suite (components/audio-visualizer.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Audio Waveform & Spectrum Visualizer compound components across generated Next.js web applications:
- **Standalone Audio Visualizer Suite (`apps/web/components/audio-visualizer.tsx`)**:
  - Implemented `AudioVisualizerVariant`, `AudioVisualizerSize`, `AudioVisualizerMode`, `AudioVisualizerHandle`, `AudioVisualizerControlsProps`, `AudioVisualizerCanvasProps`, `AudioVisualizerProps`.
  - Implemented compound and semantic alias exports: `AudioVisualizer`, `WaveformVisualizer`, `SpectrumAnalyzer`, `Oscilloscope`, `AudioVisualizerControls`, `AudioVisualizerCanvas`, default export.
  - Implemented 4 dynamic visualization modes on HTML5 `<canvas>`: vertical frequency bars with peak hold indicators, continuous oscilloscope waveform line, area frequency spectrum with gradient fill, and 360-degree radial circular spectrum with pulsating bass core.
  - Implemented simulated harmonic audio oscillation loop alongside optional real `HTMLMediaElement` / Web Audio API connection.
  - Implemented interactive timeline scrubber slider with current/total time display (`MM:SS`) and keyboard seek controls.
  - Implemented play/pause toggling, volume slider, mute/unmute toggle, and playback speed selector (0.5x, 1x, 1.5x, 2x).
  - Implemented accessible keyboard shortcuts (Space to play/pause, M to mute, Left/Right arrow keys to seek ±5s).
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Audio Visualizer"`, `role="toolbar"`, `role="slider"`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan/magenta glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`AudioVisualizerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_audio_visualizer_component` in `omnistackai_agent_engine.codegen` and registered `components/audio-visualizer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_audio_visualizer_component.py` (all passing).
  - `task verify` passing: 2,448 tests passed in 2.020s.
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passing (135 files generated).

### R-397 — Generated Accessible Futuristic Reusable Mind Map & Concept Tree Suite (components/mind-map.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Mind Map & Concept Tree compound components across generated Next.js web applications:
- **Standalone Mind Map Suite (`apps/web/components/mind-map.tsx`)**:
  - Implemented `MindMapVariant`, `MindMapSize`, `MindMapLayout`, `MindMapNode`, `MindMapHandle`, `MindMapControlsProps`, `NodeInspectorProps`, `MindMapProps`.
  - Implemented compound and semantic alias exports: `MindMap`, `ConceptTree`, `BrainstormMap`, `IdeaGraph`, `MindMapControls`, `NodeInspector`, default export.
  - Implemented hierarchical multi-layout algorithms: radial layout (center-out balanced distribution), tree-horizontal (left-to-right hierarchy), and tree-vertical (top-to-bottom hierarchy).
  - Implemented smooth SVG cubic bezier curved branches connecting parent and child concept nodes.
  - Implemented pan/zoom viewport (0.3x to 3x) with mouse drag panning and wheel zooming.
  - Implemented collapsible subtrees with interactive expand/collapse toggling and child progress indicators.
  - Implemented node selection with slide-over Node Inspector editing panel (label, notes/description, theme color palette picker, completion progress slider, add child node, delete branch).
  - Implemented dynamic node addition and recursive subtree deletion.
  - Implemented search input by label and notes with glowing match highlighting.
  - Implemented export to PNG, vector SVG, and JSON formats.
  - Implemented WAI-ARIA 1.2 application & tree semantics (`role="application"`, `role="tree"`, `role="treeitem"`, `role="toolbar"`, `role="complementary"`, `aria-label="Mind Map Canvas"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`MindMapHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_mind_map_component` in `omnistackai_agent_engine.codegen` and registered `components/mind-map.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_mind_map_component.py` (all passing).
  - `task verify` passing: 2,431 tests passed in 2.014s.
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passing (134 files generated).

### R-396 — Generated Accessible Futuristic Reusable Live Log Viewer & Event Stream Inspector Suite (components/log-viewer.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Live Log Viewer and Event Stream Inspector compound components across generated Next.js web applications:
- **Standalone Log Viewer Suite (`apps/web/components/log-viewer.tsx`)**:
  - Implemented `LogViewerVariant`, `LogViewerSize`, `LogLevel`, `LogEntry`, `LogViewerHandle`, `LogToolbarProps`, `LogEntryRowProps`, `LogViewerProps`.
  - Implemented compound and semantic alias exports: `LogViewer`, `LogStream`, `EventViewer`, `ConsoleLogs`, `LogToolbar`, `LogEntryRow`, default export.
  - Implemented real-time tail streaming with auto-scroll lock toggle, user scroll-up pause detection, and floating resume badge with unread counts.
  - Implemented severity level filter chips (`ALL`, `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`) with event counters and color badges.
  - Implemented real-time search/filter input with match counter badge and highlighted text substrings (`<mark>`).
  - Implemented service/source filtering dropdown and available sources discovery.
  - Implemented expandable structured JSON metadata drawer with tag badges and syntax formatting.
  - Implemented line wrap toggle (`wrapLines`), line numbers gutter, copy log line / JSON to clipboard with checkmark feedback.
  - Implemented export / download logs to `.txt` and `.json` files, alongside clear logs action.
  - Implemented WAI-ARIA 1.2 log semantics (`role="log"`, `aria-live="polite"`, `role="region"`, `role="toolbar"`, `aria-label="Log stream viewer"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with color-coded luminous level badges).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`LogViewerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_log_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/log-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_log_viewer_component.py` (all passing).
  - `task verify` passing: 2,414 tests passed in 2.049s.
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passing.

### R-395 — Generated Accessible Futuristic Reusable Network Graph & Topology Map Suite (components/network-graph.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Network Graph & Topology Map compound components across generated Next.js web applications:
- **Standalone Network Graph Suite (`apps/web/components/network-graph.tsx`)**:
  - Implemented `NetworkGraphVariant`, `NetworkGraphSize`, `GraphNodeType`, `GraphNodeStatus`, `GraphNodeMetrics`, `GraphNode`, `GraphEdge`, `NetworkGraphHandle`, `GraphControlsProps`, `NodeDetailsPanelProps`, `NetworkGraphProps`.
  - Implemented compound and semantic alias exports: `NetworkGraph`, `TopologyMap`, `ForceGraph`, `GraphVisualizer`, `GraphControls`, `NodeDetailsPanel`, default export.
  - Implemented force-directed organic physics layout with Coulomb repulsion, Hooke spring attraction along edges, center gravity, and velocity damping.
  - Implemented interactive SVG viewport with pan dragging, zoom in/out (0.3x to 3x), zoom reset, and node drag-and-drop repositioning with physics reheating.
  - Implemented node selection with slide-over inspection drawer displaying node metadata, status pill, live metrics (CPU, memory, latency, throughput, uptime), and interactive connected nodes list.
  - Implemented search input by label, ID, and tags, alongside multiselect type filtering pills.
  - Implemented export topology to PNG capability via SVG serialization and canvas rasterization.
  - Implemented WAI-ARIA 1.2 application semantics (`role="application"`, `aria-label="Network Topology Graph"`, `role="toolbar"`, `role="complementary"`, `role="button"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`NetworkGraphHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_network_graph_component` in `omnistackai_agent_engine.codegen` and registered `components/network-graph.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_network_graph_component.py` (all passing).
  - `task verify` passing: 2,397 tests passed in 1.881s.
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passing.

### R-394 — Generated Accessible Futuristic Reusable Image Gallery & Masonry Lightbox Suite (components/image-gallery.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Image Gallery & Masonry Lightbox compound components across generated Next.js web applications:
- **Standalone Image Gallery Suite (`apps/web/components/image-gallery.tsx`)**:
  - Implemented `ImageGalleryVariant`, `ImageGallerySize`, `GalleryLayout`, `GalleryItem`, `ImageGalleryHandle`, `ImageGalleryToolbarProps`, `LightboxModalProps`, `ImageGalleryProps`.
  - Implemented compound and semantic alias exports: `ImageGallery`, `PhotoGallery`, `MediaGallery`, `MasonryGallery`, `Lightbox`, `ImageGalleryToolbar`, default export.
  - Implemented responsive multi-column grid and masonry layouts with dynamic aspect ratios and responsive columns.
  - Implemented full-screen interactive Lightbox modal with zoom in/out, zoom reset, 90-degree image rotation, previous/next navigation, and backdrop click-to-dismiss.
  - Implemented auto-advancing slideshow presentation mode with play/pause toggling and configurable timer intervals.
  - Implemented category filter tabs ("All", "Architecture", "Sci-Fi", "Abstract", "Nature") and real-time search filtering across titles, descriptions, and tags.
  - Implemented bottom thumbnail strip navigation inside the lightbox with active thumbnail indicator and click-to-jump.
  - Implemented image download action and interactive like/favorite toggle with heart counters.
  - Implemented WAI-ARIA 1.2 dialog and grid semantics (`role="region"`, `role="grid"`, `role="gridcell"`, `role="dialog"`, `aria-modal="true"`, `role="toolbar"`, keyboard navigation).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`ImageGalleryHandle`), and explicit `displayName` across all compound exports.
  - Registered `components/image-gallery.tsx` in `NextjsWebAdapter.generate()` and exported `render_image_gallery_component` in `codegen`.
  - 100% diff-invariance across `ir.description` and 0 external runtime dependencies.
- **Verification**:
  - 17 comprehensive unit tests in `services/agent-engine/tests/test_image_gallery_component.py`.
  - `task verify` passed (2,380 tests).
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passed.

### R-393 — Generated Accessible Futuristic Reusable Interactive JSON Viewer & Schema Tree Inspector Suite (components/json-viewer.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Interactive JSON Viewer & Schema Tree Inspector compound components across generated Next.js web applications:
- **Standalone JSON Viewer Suite (`apps/web/components/json-viewer.tsx`)**:
  - Implemented `JsonViewerVariant`, `JsonViewerSize`, `JsonViewMode`, `JsonValueType`, `JsonViewerHandle`, `JsonViewerToolbarProps`, `JsonTreeNodeProps`, `JsonViewerProps`.
  - Implemented compound and semantic alias exports: `JsonViewer`, `JsonTree`, `ObjectInspector`, `SchemaViewer`, `JsonViewerToolbar`, default export.
  - Implemented collapsible & expandable tree nodes (`JsonTreeNode`) with item count badges, indentation guide rails, and expand/collapse chevrons.
  - Implemented color-coded type badges (`TYPE_COLORS`) and value syntax highlighting.
  - Implemented copy path (JSONPath / dot-notation, e.g. `$.users[0].name`) and copy value to clipboard with animated feedback.
  - Implemented real-time key/value search filtering with match counter badge and highlighted text substrings (`<mark>`).
  - Implemented depth expansion controls: Expand All, Collapse All, and default expansion depth (`defaultDepth`).
  - Implemented dual view modes: Interactive Tree view (`tree`) vs Raw Formatted JSON view (`raw`).
  - Implemented inline primitive value editing with live validation, type parsing (`parseInputPrimitive`), and immutable tree updater (`updateAtPath`).
  - Implemented download/export formatted JSON file and copy entire JSON root to clipboard.
  - Implemented WAI-ARIA 1.2 tree semantics (`role="tree"`, `role="treeitem"`, `role="group"`, `aria-expanded`, `aria-level`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`JsonViewerHandle`), and explicit `displayName` across all compound exports.
  - Registered `components/json-viewer.tsx` in `NextjsWebAdapter.generate()` and exported `render_json_viewer_component` in `codegen`.
  - 100% diff-invariance across `ir.description` and 0 external runtime dependencies.
- **Verification**:
  - 17 comprehensive unit tests in `services/agent-engine/tests/test_json_viewer_component.py`.
  - `task verify` passed (2,363 tests).
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passed.

### R-392 — Generated Accessible Futuristic Reusable Code Diff Editor & 3-Way Merge Conflict Resolver Suite (components/merge-editor.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Code Diff Editor & 3-Way Merge Conflict Resolver compound components across generated Next.js web applications:
- **Standalone Merge Editor Suite (`apps/web/components/merge-editor.tsx`)**:
  - Implemented `MergeEditorVariant`, `MergeEditorSize`, `ConflictStatus`, `MergeConflict`, `MergeEditorHandle`, `MergeEditorToolbarProps`, `MergeEditorProps`.
  - Implemented compound and semantic alias exports: `MergeEditor`, `ConflictResolver`, `ThreeWayMerge`, `DiffEditor`, `MergeEditorToolbar`, default export.
  - Implemented 3-pane synchronized layout: Left ("Current Change / Ours", emerald accent), Center ("Result / Merged View", violet accent), Right ("Incoming Change / Theirs", sky blue accent).
  - Implemented interactive conflict block resolution actions ("Accept Current", "Accept Incoming", "Accept Both").
  - Implemented raw git conflict marker parser (`parseRawConflicts`) parsing `<<<<<<< HEAD`, `=======`, `>>>>>>> incoming`.
  - Implemented batch resolution actions: "All Current", "All Incoming", "Reset All".
  - Implemented conflict navigation jumper bar (Next/Prev conflict jumper, conflict counter, remaining unresolved badge).
  - Implemented direct editable merged result buffer with change tracking, copy to clipboard, and file download actions.
  - Implemented WAI-ARIA 1.2 semantics (`role="region"`, `aria-label="3-Way Merge Editor"`, `role="toolbar"`, `role="status"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`MergeEditorHandle`), and explicit `displayName` across all compound exports.
  - Registered `components/merge-editor.tsx` in `NextjsWebAdapter.generate()` and exported `render_merge_editor_component` in `codegen`.
  - 100% diff-invariance across `ir.description` and 0 external runtime dependencies.
- **Verification**:
  - 17 comprehensive unit tests in `services/agent-engine/tests/test_merge_editor_component.py`.
  - `task verify` passed (2,346 tests).
  - `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` all passed.

### R-391 — Generated Accessible Futuristic Reusable Whiteboard & Collaborative Canvas Suite (components/whiteboard.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Whiteboard & Collaborative Canvas compound components across generated Next.js web applications:
- **Standalone Whiteboard Suite (`apps/web/components/whiteboard.tsx`)**:
  - Implemented `WhiteboardVariant`, `WhiteboardSize`, `WhiteboardTool`, `WhiteboardPoint`, `WhiteboardElement`, `WhiteboardHandle`, `WhiteboardToolbarProps`, `WhiteboardProps`.
  - Implemented compound and semantic alias exports: `Whiteboard`, `DrawingCanvas`, `SketchBoard`, `CollaborativeCanvas`, `WhiteboardToolbar`, default export.
  - Implemented vector shape drawing (rectangle, ellipse/circle, arrow, line, freehand pencil with quadratic smoothing, text sticky notes, eraser).
  - Implemented color palette presets (`PRESET_COLORS`) and stroke width selector (`STROKE_WIDTHS`: 2px to 14px).
  - Implemented infinite canvas pan & zoom transform with mouse wheel zoom, click-drag panning, and reset zoom button.
  - Implemented multi-level undo/redo history stack (`pushHistory`, `undo`, `redo`).
  - Implemented export to PNG (`canvas.toDataURL`), export to standalone vector SVG XML (`exportSvg`), export and import JSON canvas diagrams (`exportJson`, `loadJson`).
  - Implemented WAI-ARIA 1.2 application semantics (`role="application"`, `aria-label="Whiteboard Canvas"`, `role="toolbar"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`WhiteboardHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_whiteboard_component` in `omnistackai_agent_engine.codegen` and registered `components/whiteboard.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Unit Tests**:
  - Added `services/agent-engine/tests/test_whiteboard_component.py` covering rendering, interfaces, variants, sizes, aliases, forwardRef, displayName, tools, colors, undo/redo, pan/zoom, and diff-invariance (17 tests passing).
- **Verification Gates**:
  - `task verify` passed 2,329 tests (17 new), 0 failures.
  - `task lint` passed with 0 errors.
  - `task security:quick` passed.
  - `task builder:demo -- minimal-blog` passed (generated 128 files).

### R-390 — Generated Accessible Futuristic Reusable Video Player & Streaming Theater Suite (components/video-player.tsx)


Enabled accessible, desktop-and-mobile-grade, futuristic Video Player & Streaming Theater compound components across generated Next.js web applications:
- **Standalone Video Player Suite (`apps/web/components/video-player.tsx`)**:
  - Implemented `VideoPlayerVariant`, `VideoPlayerSize`, `VideoQuality`, `VideoChapter`, `VideoCaption`, `VideoSource`, `VideoPlayerHandle`, `VideoControlsProps`, `VideoPlayerProps`.
  - Implemented compound and semantic alias exports: `VideoPlayer`, `MoviePlayer`, `TheaterPlayer`, `StreamPlayer`, `VideoControls`, default export.
  - Implemented video playback controls (play, pause, 10s skip forward/backward, time formatting helper `formatVideoTime`).
  - Implemented interactive seekable timeline / scrubber with buffered progress bar and visual chapter markers with hover tooltips.
  - Implemented theater mode layout expansion and native Fullscreen API integration.
  - Implemented picture-in-picture (PiP) toggle via HTML5 `requestPictureInPicture`.
  - Implemented closed captions / subtitles overlay with active cue text matching.
  - Implemented playback speed selector (0.5x to 2x) and video quality selector (Auto, 1080p, 720p, 480p, 360p).
  - Implemented volume slider with mute toggle and keyboard shortcuts (Space, K, Arrows, F, T, M, C).
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Video Player"`, `role="toolbar"`, `role="slider"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`VideoPlayerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_video_player_component` in `omnistackai_agent_engine.codegen` and registered `components/video-player.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Unit Tests**:
  - Added `services/agent-engine/tests/test_video_player_component.py` covering rendering, interfaces, variants, sizes, aliases, forwardRef, displayName, scrubber, chapters, theater, and diff-invariance (17 tests passing).
- **Verification Gates**:
  - `task verify` passed 2,312 tests (17 new), 0 failures.
  - `task lint` passed with 0 errors.
  - `task security:quick` passed.
  - `task builder:demo -- minimal-blog` passed (generated 127 files).

### R-389 — Generated Accessible Futuristic Reusable Audio Player & Frequency Equalizer Suite (components/audio-player.tsx)


Enabled accessible, desktop-and-mobile-grade, futuristic Audio Player & Frequency Equalizer compound components across generated Next.js web applications:
- **Standalone Audio Player Suite (`apps/web/components/audio-player.tsx`)**:
  - Implemented `AudioPlayerVariant`, `AudioPlayerSize`, `AudioTrack`, `AudioEqualizerBand`, `AudioEqualizerPreset`, `AudioPlayerHandle`, `AudioPlaylistProps`, `AudioEqualizerProps`, `AudioPlayerProps`.
  - Implemented compound and semantic alias exports: `AudioPlayer`, `MusicPlayer`, `SoundPlayer`, `AudioPlaylist`, `AudioEqualizer`, default export.
  - Implemented audio playback controls (play, pause, previous, next, seek forward/back 10s).
  - Implemented interactive seekable waveform / scrubber with duration and current time indicators (`MM:SS`).
  - Implemented multi-band frequency equalizer (`AudioEqualizer`: 60Hz, 250Hz, 1kHz, 4kHz, 16kHz) with presets ("Flat", "Bass Boost", "Vocal", "Electronic", "Rock") and vertical interactive sliders.
  - Implemented multi-track playlist queue drawer (`AudioPlaylist`) with track selection, active track indicator, and track durations.
  - Implemented playback speed selector (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x).
  - Implemented volume slider with mute toggle, repeat (none, all, one) and shuffle toggles.
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Audio Player"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`AudioPlayerHandle`), and explicit `displayName` across all exports.
  - Exported `render_audio_player_component` in `omnistackai_agent_engine.codegen` and registered `components/audio-player.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Unit Tests**:
  - Added `services/agent-engine/tests/test_audio_player_component.py` covering rendering, interfaces, variants, sizes, aliases, forwardRef, displayName, equalizer, playlist, and diff-invariance (17 tests passing).
- **Verification Gates**:
  - `task verify` passed 2,295 tests (17 new), 0 failures.
  - `task lint` passed with 0 errors.
  - `task security:quick` passed.
  - `task builder:demo -- minimal-blog` passed (generated 126 files).

### R-388 — Generated Accessible Futuristic Reusable PDF & Document Viewer Suite (components/pdf-viewer.tsx)


Enabled accessible, desktop-and-mobile-grade, futuristic PDF & Document Viewer compound components across generated Next.js web applications:
- **Standalone PDF Viewer Suite (`apps/web/components/pdf-viewer.tsx`)**:
  - Implemented `PdfViewerVariant`, `PdfViewerSize`, `PdfViewMode`, `PdfPage`, `PdfViewerHandle`, `PdfThumbnailProps`, `PdfToolbarProps`, `PdfPageCanvasProps`, `PdfViewerProps`.
  - Implemented compound and semantic alias exports: `PdfViewer`, `DocumentViewer`, `FileViewer`, `PdfThumbnails`, `PdfToolbar`, `PdfPageCanvas`, default export.
  - Implemented multi-page document pagination with page number jumper and page counter indicators (`Page X of Y`).
  - Implemented interactive page zooming (50% to 300%) with zoom in/out buttons, zoom presets, and smooth scaling.
  - Implemented page rotation (90° clockwise per trigger).
  - Implemented slide-over thumbnail navigation drawer (`PdfThumbnails`) with clickable miniature page preview cards.
  - Implemented in-document text search with live match counter (`Match X of Y`), previous/next match navigation, and `<mark>` highlighted text styling.
  - Implemented single-page and continuous vertical scroll view modes (`single` vs `continuous`).
  - Implemented action toolbar with print trigger (`window.print`), download action, and fullscreen presentation toggle.
  - Implemented WAI-ARIA 1.2 document and toolbar semantics (`role="region"`, `role="toolbar"`, `role="document"`, `aria-label="Document Viewer"`, keyboard shortcuts).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`PdfViewerHandle`), and explicit `displayName` across all exports.
  - Exported `render_pdf_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/pdf-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Test suite**: `services/agent-engine/tests/test_pdf_viewer_component.py` (17 tests passing).
- **Verification**: `task verify` passed (2,278 tests passing). Linter, secret scans, and demo apps passed cleanly.

### R-387 — Generated Accessible Futuristic Reusable Interactive Geo Map & Location Pinpoint Suite (components/geo-map.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Interactive Geo Map & Location Pinpoint compound components across generated Next.js web applications:
- **Standalone Geo Map Suite (`apps/web/components/geo-map.tsx`)**:
  - Implemented `GeoMapVariant`, `GeoMapSize`, `MarkerStyle`, `MapMarker`, `MapRoute`, `GeoMapHandle`, `MapCalloutProps`, `MapControlsProps`, `GeoMapProps`.
  - Implemented compound and semantic alias exports: `GeoMap`, `InteractiveMap`, `LocationPicker`, `MapPin`, `MapCallout`, `MapControls`, `RouteLine`, default export.
  - Implemented zero-dependency mathematical vector SVG Equirectangular coordinate projection (`lngToX`, `latToY`, `xToLng`, `yToLat`).
  - Implemented stylized world continent paths and latitude/longitude graticule lines.
  - Implemented interactive pan & zoom transform with mouse drag, mouse wheel, keyboard arrows, and reset controls.
  - Implemented location markers with 4 styles (`pin`, `dot`, `pulse`, `beacon`) and pulsating animated radar rings.
  - Implemented interactive marker callout popup card (`MapCallout`) with category badge, description, coordinates, and action triggers.
  - Implemented route polyline visualizer (`RouteLine`) connecting waypoints with glowing animated dataflow.
  - Implemented search bar and category filter pill buttons.
  - Implemented coordinate crosshair dropper mode (`onCoordinateSelect`).
  - Implemented floating HUD controls (`MapControls`) and cursor coordinates badge.
  - Implemented WAI-ARIA 1.2 application semantics (`role="application"`, `aria-label="Interactive Map"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`GeoMapHandle`), and explicit `displayName` across all exports.
  - Exported `render_geo_map_component` in `omnistackai_agent_engine.codegen` and registered `components/geo-map.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Test suite**: `services/agent-engine/tests/test_geo_map_component.py` (17 tests passing).
- **Verification**: `task verify` passed (2,261 tests passing). Linter, secret scans, and demo apps passed cleanly.

### R-386 — Generated Accessible Futuristic Reusable File Explorer & Storage Browser Suite (components/file-explorer.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic File Explorer & Storage Browser compound components across generated Next.js web applications:
- **Standalone File Explorer Suite (`apps/web/components/file-explorer.tsx`)**:
  - Implemented `FileExplorerVariant`, `FileExplorerSize`, `FileExplorerViewMode`, `FileItemType`, `FileItem`, `FileExplorerHandle`, `FileBreadcrumbsProps`, `FileDetailsProps`, `FileExplorerProps`.
  - Implemented compound and semantic alias exports: `FileExplorer`, `FileManager`, `FileBrowser`, `DocumentManager`, `FileGrid`, `FileList`, `FileDetailsPanel`, `FileBreadcrumbs`, default export.
  - Implemented folder navigation with interactive path breadcrumbs bar and click-to-navigate hierarchy.
  - Implemented dual view modes: responsive card grid view with file type icons and tabular sortable list view with Name, Size, Date, Type columns.
  - Implemented single and multi-selection modes with checkboxes and select-all affordance.
  - Implemented slide-over file inspector details panel with formatted file sizes (B, KB, MB, GB), timestamps, and item actions.
  - Implemented action toolbar with upload, download, and delete triggers.
  - Implemented WAI-ARIA 1.2 grid and region semantics (`role="region"`, `aria-label="File Explorer"`, `role="grid"`, `role="row"`, `role="gridcell"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`FileExplorerHandle`), and explicit `displayName` across all exports.
  - Exported `render_file_explorer_component` in `omnistackai_agent_engine.codegen` and registered `components/file-explorer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Test suite**: `services/agent-engine/tests/test_file_explorer_component.py` (17 tests passing).
- **Verification**: `task verify` passed (2,244 tests passing). Linter, secret scans, and demo apps passed cleanly.

### R-385 — Generated Accessible Futuristic Reusable Audio & Voice Recorder Suite (components/audio-recorder.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Audio & Voice Recorder compound components across generated Next.js web applications:
- **Standalone Audio Recorder Suite (`apps/web/components/audio-recorder.tsx`)**:
  - Implemented `AudioRecorderVariant`, `AudioRecorderSize`, `RecordingState`, `WaveformStyle`, `AudioRecording`, `AudioRecorderHandle`, `WaveformVisualizerProps`, `AudioPlayerBarProps`, `AudioRecorderProps`.
  - Implemented compound and semantic alias exports: `AudioRecorder`, `VoiceRecorder`, `SoundRecorder`, `WaveformVisualizer`, `AudioPlayerBar`, default export.
  - Real-time sound recording lifecycle state machine (`idle` -> `recording` <-> `paused` -> `stopped`).
  - Sound waveform canvas visualizer (`WaveformVisualizer`) supporting 3 visual styles: `bars`, `wave`, and `mirror`.
  - Real-time duration timer (`MM:SS`) with animated pulsing live recording indicator.
  - Maximum duration limit guard (`maxDuration`) with automatic stop.
  - Integrated playback bar with seek scrubber slider, play/pause toggle, and elapsed/total time readout.
  - Audio export actions (`Download`, `Delete`/discard).
  - WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Audio Recorder"`, `aria-live="polite"`).
  - 4 styling variants ("default", "card", "glass", "neon") and 3 size scales ("sm", "md", "lg").
  - React ref forwarding (`forwardRef`) and imperative handle (`AudioRecorderHandle`).
  - 100% diff-invariance across `ir.description`, zero runtime npm dependencies.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_audio_recorder_component.py` passing.
  - `task verify` passed (2,227 tests total).
  - `task lint`, `task security:quick`, and `task builder:demo -- minimal-blog` passed.

### R-384 — Generated Accessible Futuristic Reusable Chat & Real-Time Messaging Suite (components/chat.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Chat & Real-Time Messaging compound components across generated Next.js web applications:
- **Standalone Chat Suite (`apps/web/components/chat.tsx`)**:
  - Implemented `ChatVariant`, `ChatSize`, `MessageSender`, `MessageStatus`, `ChatAttachment`, `ChatAction`, `ChatMessage`, `ChatConversation`, `ChatHandle`, `ChatHeaderProps`, `ChatMessageProps`, `ChatInputProps`, `ChatSidebarProps`, `ChatMessageListProps`, `ChatProps`.
  - Implemented compound and semantic alias exports: `Chat`, `ChatWindow`, `Messenger`, `ChatWidget`, `ChatHeader`, `ChatSidebar`, `ChatMessageItem`, `ChatInput`, `ChatMessageList`, default export.
  - Conversational message bubbles with user, agent/bot, and system message styling distinctions.
  - Delivery status ticks (sending, sent, delivered, read) and timestamps.
  - Pulsing animated dots typing indicator.
  - Auto-expanding input bar with Enter-to-send, Shift+Enter newline, and file attachments.
  - Quick action suggestion pills and media attachment previews.
  - Multi-conversation thread sidebar with search filter and unread badge counters.
  - WAI-ARIA 1.2 log semantics (`role="log"`, `aria-live="polite"`, `role="list"`, `role="listitem"`).
  - 4 styling variants ("default", "card", "glass", "neon") and 3 size scales ("sm", "md", "lg").
  - React ref forwarding (`forwardRef`) and imperative handle (`ChatHandle`).
  - 100% diff-invariance across `ir.description`, zero runtime npm dependencies.
- **Verification**:
  - 17 unit tests in `services/agent-engine/tests/test_chat_component.py` passing.
  - `task verify` passed (2,210 tests total).
  - `task lint`, `task security:quick`, and `task builder:demo -- minimal-blog` passed.

### R-383 — Generated Accessible Futuristic Reusable Spreadsheet & Inline-Editable Data Sheet Suite (components/spreadsheet.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Spreadsheet & Inline-Editable Data Sheet compound components across generated Next.js web applications:
- **Standalone Spreadsheet Suite (`apps/web/components/spreadsheet.tsx`)**:
  - Implemented `SpreadsheetVariant`, `SpreadsheetSize`, `CellType`, `CellValue`, `CellCoord`, `CellRange`, `ColumnDef`, `RowData`, `SpreadsheetHandle`, `SpreadsheetProps`, `SpreadsheetToolbarProps`, `SpreadsheetCellProps`.
  - Implemented compound and semantic alias exports: `Spreadsheet`, `DataSheet`, `InlineGrid`, `SpreadsheetToolbar`, `SpreadsheetCell`, default export.
  - Inline cell editing on double-click/F2/Enter with commit/abort handling.
  - Zero-dependency formula engine supporting `=SUM`, `=AVG`, `=COUNT`, `=MIN`, `=MAX`, `=IF`.
  - Arrow key navigation, Tab, Home/End, PgUp/PgDn, Ctrl+Home/End.
  - Multi-cell range selection with Shift+Click/Arrow.
  - Column freeze (`frozen: true`), column resize handles, row numbers gutter.
  - Undo/redo history stack (Ctrl+Z/Ctrl+Y), CSV export/import, clipboard copy/paste (Ctrl+C/Ctrl+V).
  - Context menu (Insert/Delete/Clear row), Ctrl+F find bar, column header sorting.
  - WAI-ARIA 1.2 grid semantics (`role="grid"`, `role="row"`, `role="columnheader"`, `role="gridcell"`, `aria-selected`, `aria-sort`).
  - 4 futuristic visual variants (default, card, glass, neon), 3 size scales (sm, md, lg).
  - React ref forwarding (`forwardRef`), `SpreadsheetHandle`, explicit `displayName`.
  - Exported `render_spreadsheet_component` in `codegen` and registered in `NextjsWebAdapter`.
  - 17 unit tests in `test_spreadsheet_component.py` (2,193 tests total pass).

### R-382 — Generated Accessible Futuristic Reusable QR Code & Barcode Suite (components/qr-code.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic QR Code & Barcode compound components across generated Next.js web applications:
- **Standalone QR Code Suite (`apps/web/components/qr-code.tsx`)**:
  - Implemented `QrErrorCorrectionLevel`, `QrModuleStyle`, `QrEyeStyle`, `QrGradientType`, `BarcodeFormat`, `QrCodeVariant`, `QrCodeSize`, `QrCodeHandle`, `QrCodeProps`, `BarcodeProps`, `QrCardProps`.
  - Implemented compound exports: `QrCode`, `Barcode`, `QrCard`, default export.
  - Zero-dependency mathematical QR encoder with Galois Field GF(2^8) Reed-Solomon polynomial math and error correction levels (L, M, Q, H).
  - Zero-dependency mathematical 1D barcode generator (Code 128 / EAN-13) in SVG.
  - Action toolbar: copy to clipboard, high-res PNG download, vector SVG download, print.
  - Module dot styles (square, rounded, dots, diamonds), customizable eyes styling, center logo slot.
  - WAI-ARIA 1.2 `role="img"`, 4 visual variants (default, card, glass, neon), 3 size scales (sm, md, lg).
  - React ref forwarding, imperative handle `QrCodeHandle`, explicit `displayName`.
  - Exported `render_qr_code_component` in `codegen` and registered in `NextjsWebAdapter`.
  - 17 unit tests in `test_qr_code_component.py`.

### R-381 — Generated Accessible Futuristic Reusable Terminal & Command Console Suite (components/terminal.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Terminal & Command Console compound components across generated Next.js web applications:

- **Standalone Terminal Suite (`apps/web/components/terminal.tsx`)**:
  - Implemented `TerminalVariant` (`"terminal"` | `"neon"` | `"glass"` | `"minimal"`), `TerminalSize` (`"sm"` | `"md"` | `"lg"`), `TerminalLineType` (`"stdout"` | `"stderr"` | `"system"` | `"command"` | `"info"`), `TerminalLine`, `TerminalTab`, `TerminalHandle`, `TerminalProps`, `TerminalHeaderProps`, `TerminalOutputProps`, and `TerminalPromptProps` interfaces.
  - Implemented compound and semantic alias exports: `Terminal`, `TerminalHeader`, `TerminalTabs`, `TerminalOutput`, `TerminalPrompt`, `ConsoleViewer`, `CommandLine`, and default export.
  - Implemented ANSI color code parser (`parseAnsi`) supporting standard 16-color ANSI codes (red, green, yellow, blue, magenta, cyan, white), bold, and underline styles.
  - Implemented interactive CLI command line prompt with user@host:cwd prefix and glowing cursor.
  - Implemented command history stack navigation using ArrowUp and ArrowDown keys.
  - Implemented multi-tab terminal session bar (`TerminalTabs`) with tab switching, close buttons, and add tab affordance.
  - Implemented real-time search filtering across terminal output buffer lines.
  - Implemented toolbar controls: Auto-scroll toggle, Copy all buffer to clipboard with checkmark feedback, Download as log file, Clear buffer.
  - Implemented keyboard shortcuts: `Ctrl+L` (clear buffer), `Ctrl+C` (cancel input).
  - Implemented WAI-ARIA 1.2 log & region accessibility semantics (`role="region"`, `role="log"`, `aria-live="polite"`).
  - Implemented 4 futuristic visual styling variants ("terminal" retro CRT phosphor green, "neon" cyberpunk glowing cyan, "glass" with backdropFilter blur, "minimal" high-contrast dark).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`TerminalHandle`), and explicit `displayName` across all exports.
  - Exported `render_terminal_component` in `omnistackai_agent_engine.codegen` and registered `components/terminal.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.

### R-380 — Generated Accessible Futuristic Reusable Flowchart & Node-Based Workflow Canvas Suite (components/flow-canvas.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Flowchart & Node-Based Workflow Canvas compound components across generated Next.js web applications:

- **Standalone Flow Canvas Suite (`apps/web/components/flow-canvas.tsx`)**:
  - Implemented `FlowVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `FlowSize` (`"sm"` | `"md"` | `"lg"`), `FlowNodeType` (`"default"` | `"input"` | `"output"` | `"action"` | `"condition"`), `FlowNodeStatus` (`"idle"` | `"running"` | `"success"` | `"error"`), `FlowEdgeStyle` (`"bezier"` | `"straight"` | `"step"`), `FlowPortPosition` (`"left"` | `"right"` | `"top"` | `"bottom"`), `FlowPort`, `FlowNode`, `FlowEdge`, `FlowCanvasHandle`, `FlowCanvasProps`, `FlowNodeProps`, `FlowEdgeProps`, `FlowMinimapProps`, and `FlowControlsProps` interfaces.
  - Implemented compound and semantic alias exports: `FlowCanvas`, `WorkflowBuilder`, `NodeGraph`, `FlowNodeItem`, `FlowEdgeLine`, `FlowMinimap`, `FlowControls`, and default export.
  - Implemented 2D interactive canvas pan and zoom transform with mouse wheel zoom, click-drag panning, and reset/fit-view buttons.
  - Implemented draggable nodes with grid snapping (`snapToGrid`, `gridSize`).
  - Implemented SVG cubic bezier curved connection lines with customizable directional arrow markers.
  - Implemented active animated dataflow pulses along edges (`animated: true`).
  - Implemented real-time interactive Minimap (`FlowMinimap`) with viewport indicator box and click-to-pan.
  - Implemented floating canvas toolbar controls (`FlowControls`): Zoom In, Zoom Out, Reset Zoom, Fit to View, Toggle Grid.
  - Implemented WAI-ARIA 1.2 application accessibility semantics (`role="application"`, `aria-label="Workflow Canvas"`), keyboard arrow keys to nudge selected nodes, Delete to remove, Escape to deselect.
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant node halos and luminous bezier edges).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`FlowCanvasHandle`), and explicit `displayName` across all exports.
  - Exported `render_flow_canvas_component` in `omnistackai_agent_engine.codegen` and registered `components/flow-canvas.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.

### R-379 — Generated Accessible Futuristic Reusable Gantt Chart & Project Roadmap Suite (components/gantt-chart.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Gantt Chart & Project Roadmap compound components across generated Next.js web applications:

- **Standalone Gantt Chart Suite (`apps/web/components/gantt-chart.tsx`)**:
  - Implemented `GanttViewMode` (`"day"` | `"week"` | `"month"`), `GanttVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `GanttSize` (`"sm"` | `"md"` | `"lg"`), `GanttTask`, `GanttChartHandle`, and `GanttChartProps` interfaces.
  - Implemented compound and semantic alias exports: `GanttChart`, `ProjectRoadmap`, `TimelineGantt`, `GanttTaskBar`, `GanttTimescale`, `GanttDependencyLine`, and default export.
  - Implemented interactive task duration bars with proportional progress fill.
  - Implemented diamond milestone markers for instantaneous deadlines.
  - Implemented SVG dependency connector lines and bezier arrowheads connecting predecessor tasks to successor tasks.
  - Implemented multi-scale timescale zoom levels ("day", "week", "month").
  - Implemented synchronized task list sidebar with task name and progress.
  - Implemented weekend column shading and vertical "Today" indicator line.
  - Implemented timescale navigation controls (Jump to Today, Zoom In, Zoom Out).
  - Implemented WAI-ARIA 1.2 grid semantics (`role="grid"`, `aria-label="Project Gantt Chart"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant progress bars and luminous dependency lines).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`GanttChartHandle`), and explicit `displayName` across all exports.
  - Exported `render_gantt_chart_component` in `omnistackai_agent_engine.codegen` and registered `components/gantt-chart.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.

### R-378 — Generated Accessible Futuristic Reusable Image Cropper & Canvas Mask Suite (components/image-cropper.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Image Cropper & Canvas Mask compound components across generated Next.js web applications:

- **Standalone Image Cropper Suite (`apps/web/components/image-cropper.tsx`)**:
  - Implemented `CropAspectRatio` (`"free"` | `"1:1"` | `"4:3"` | `"16:9"` | `"circular"`), `ImageCropperVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `ImageCropperSize` (`"sm"` | `"md"` | `"lg"`), `CropArea`, `CropData`, `ImageCropperHandle`, `ImageCropperProps`, `CropToolbarProps`, `CropPreviewProps`, and `AvatarCropperProps` interfaces.
  - Implemented compound and semantic alias exports: `ImageCropper`, `AvatarCropper`, `CropCanvas`, `CropToolbar`, `CropPreview`, and default export.
  - Implemented draggable crop marquee bounding box and 8 tactile resize handles (`nw`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w`) with pointer capture APIs.
  - Implemented aspect ratio constraints: `"free"`, `"1:1"`, `"4:3"`, `"16:9"`, `"circular"` (for avatars and user profiles).
  - Implemented continuous zoom scaling slider (0.5x to 3x).
  - Implemented rotation controls (-180° to +180° slider and ±90° step quick buttons).
  - Implemented horizontal flip and vertical flip transform toggles.
  - Implemented HTML5 `<canvas>` rendering with circular clipping option and data export (`crop()`, `toDataURL()`).
  - Implemented real-time thumbnail preview component (`CropPreview`).
  - Implemented keyboard arrow key nudging (`ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`) with Shift multiplier for precision control.
  - Implemented WAI-ARIA 1.2 accessibility semantics (`role="region"`, `aria-label="Image Cropper"`, `aria-roledescription="image cropping canvas"`, `tabIndex={0}`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with luminous handles).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`ImageCropperHandle`), and explicit `displayName` across all exports.
  - Exported `render_image_cropper_component` in `omnistackai_agent_engine.codegen` and registered `components/image-cropper.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.

### R-377 — Generated Accessible Futuristic Reusable Pivot Table & Cross-Tabulation Matrix Suite (components/pivot-table.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Pivot Table & Cross-Tabulation Matrix compound components across generated Next.js web applications:

- **Standalone Pivot Table Suite (`apps/web/components/pivot-table.tsx`)**:
  - Implemented `PivotAggregator` (`"sum"` | `"avg"` | `"count"` | `"min"` | `"max"`), `PivotVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `PivotSize` (`"sm"` | `"md"` | `"lg"`), `PivotValueField`, `PivotCellCoord`, `PivotTableHandle`, `PivotTableProps`, `PivotCellProps`, and `PivotHeaderProps` interfaces.
  - Implemented compound and semantic alias exports: `PivotTable`, `CrossTab`, `MatrixTable`, `PivotCell`, `PivotHeader`, and default export.
  - Implemented multi-dimensional hierarchical row grouping and multi-level column dimension grouping.
  - Implemented aggregation calculations: `sum`, `avg`, `count`, `min`, `max`.
  - Implemented collapsible and expandable row hierarchies with chevron toggle buttons and indentation depth.
  - Implemented automatic calculation and rendering of row subtotals and global grand totals for rows and columns.
  - Implemented interactive sorting on dimension and metric column headers.
  - Implemented live search filtering input for dimension matching.
  - Implemented cell click selection callback (`onCellClick`, `selectedCell`).
  - Implemented CSV export capability via imperative handle (`exportCsv`) and toolbar trigger.
  - Implemented WAI-ARIA 1.2 table/grid accessibility semantics (`role="table"`, `role="row"`, `role="columnheader"`, `role="rowheader"`, `role="gridcell"`, `aria-expanded`, `aria-sort`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant total rows).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_pivot_table_component` in `omnistackai_agent_engine.codegen` and registered `components/pivot-table.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
  - Unit tests: 17 focused tests in `services/agent-engine/tests/test_pivot_table_component.py` (all passing). Total test count: 2,091 tests.

### R-376 — Generated Accessible Futuristic Reusable Media Player Suite (components/media-player.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Media Player compound components across generated Next.js web applications:

- **Standalone Media Player Suite (`apps/web/components/media-player.tsx`)**:
  - Implemented `MediaType` (`"video"` | `"audio"`), `MediaPlayerVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `MediaPlayerSize` (`"sm"` | `"md"` | `"lg"`), `MediaPlaybackRate` (0.5 | 0.75 | 1 | 1.25 | 1.5 | 2), `MediaTrackSource`, `MediaSubtitle`, `MediaPlayerHandle`, `MediaPlayerProps`, `MediaScrubberProps`, and `VolumeSliderProps` interfaces.
  - Implemented compound and semantic alias exports: `MediaPlayer`, `VideoPlayer`, `AudioPlayer`, `MediaControls`, `MediaScrubber`, `VolumeSlider`, and default export.
  - Implemented dual media modes: Video player with aspect-ratio container, poster image, overlay controls, fullscreen, and Picture-in-Picture; and Audio player with album cover art, track/artist metadata, and animated equalizer bars.
  - Implemented interactive scrubber bar with loaded buffer progress, played progress bar, and hover timestamp preview tooltip.
  - Implemented volume control slider with mute toggle and dynamic volume level icons.
  - Implemented playback rate selector (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x).
  - Implemented skip forward/backward buttons (±10s).
  - Implemented fullscreen and Picture-in-Picture controls with native API fallback.
  - Implemented closed captions / subtitles track support (CC).
  - Implemented comprehensive keyboard navigation shortcuts (`Space`/`K` for play/pause, `ArrowLeft`/`ArrowRight` for seek, `ArrowUp`/`ArrowDown` for volume, `M` for mute, `F` for fullscreen, `P` for PiP).
  - Implemented WAI-ARIA media semantics (`role="region"`, `role="slider"`, `aria-valuenow`, `aria-roledescription`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant scrubber).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_media_player_component` in `omnistackai_agent_engine.codegen` and registered `components/media-player.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
  - Unit tests: 17 focused tests in `services/agent-engine/tests/test_media_player_component.py` (all passing). Total test count: 2,074 tests.

### R-375 — Generated Accessible Futuristic Reusable Heatmap & Activity Contribution Matrix Suite (components/heatmap.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Heatmap & Activity Contribution Matrix compound components across generated Next.js web applications:

- **Standalone Heatmap Suite (`apps/web/components/heatmap.tsx`)**:
  - Implemented `HeatmapMode` (`"calendar"` | `"grid"`), `HeatmapColor` (`"emerald"` | `"cyan"` | `"violet"` | `"amber"` | `"rose"`), `HeatmapVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `HeatmapSize` (`"sm"` | `"md"` | `"lg"`), `HeatmapIntensityLevel` (0 | 1 | 2 | 3 | 4), `HeatmapDatum`, `HeatmapStats`, `HeatmapHandle`, `HeatmapProps`, `HeatmapLegendProps`, and `HeatmapCellProps` interfaces.
  - Implemented compound and semantic alias exports: `Heatmap`, `ActivityCalendar`, `ContributionGraph`, `HeatmapLegend`, `HeatmapCell`, and default export.
  - Implemented dual layout modes: 52-week calendar contribution matrix with month headers and weekday labels, and 24x7 / arbitrary 2D dense coordinate grid with X and Y category labels.
  - Implemented 5 cyberpunk and natural color palettes: emerald, cyan, violet, amber, rose.
  - Implemented dynamic quantile intensity bucketing (levels 0 to 4) with threshold customization.
  - Implemented interactive cell hover/focus floating tooltips with custom formatter support.
  - Implemented keyboard arrow-key navigation and cell selection (`onCellClick`, `selectedCell`).
  - Implemented WAI-ARIA grid accessibility semantics (`role="grid"`, `role="row"`, `role="gridcell"`, `aria-selected`).
  - Implemented integrated legend sub-component (`HeatmapLegend`) with configurable labels and intensity markers.
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant cells).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_heatmap_component` in `omnistackai_agent_engine.codegen` and registered `components/heatmap.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
  - Unit tests: 17 focused tests in `services/agent-engine/tests/test_heatmap_component.py` (all passing). Total test count: 2,057 tests.

### R-374 — Generated Accessible Futuristic Reusable Org Chart & Hierarchy Flow Diagram Suite (components/org-chart.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Organizational Chart & Hierarchy Flow Diagram compound components across generated Next.js web applications:

- **Standalone Org Chart Suite (`apps/web/components/org-chart.tsx`)**:
  - Implemented `OrgChartOrientation` (`"vertical"` | `"horizontal"`), `OrgChartVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `OrgChartSize` (`"sm"` | `"md"` | `"lg"`), `OrgChartNode`, `OrgChartHandle`, `OrgChartProps`, and `OrgNodeCardProps` interfaces.
  - Implemented compound and semantic alias exports: `OrgChart`, `HierarchyTree`, `OrgNode`, and default export.
  - Implemented recursive hierarchical tree layout with SVG/CSS connector stems and crossbars linking parent nodes to child branches without third-party diagramming dependencies.
  - Implemented collapsible and expandable subtree nodes with direct and indirect report count pill badges.
  - Implemented dual layout orientations (`vertical` top-to-bottom and `horizontal` left-to-right).
  - Implemented built-in search filter input matching names, roles, departments, or emails with glowing highlight rings and automatic ancestor expansion.
  - Implemented interactive node selection (`selectedId`, `onNodeClick`) and optional action menus.
  - Implemented full WAI-ARIA 1.2 accessibility tree semantics (`role="tree"`, `role="treeitem"`, `aria-expanded`, `aria-selected`).
  - Implemented 5 built-in zero-dependency vector icons (`SearchIcon`, `ChevronDownIcon`, `ChevronRightIcon`, `UsersIcon`, `MoreVerticalIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with glowing connectors).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_org_chart_component` in `omnistackai_agent_engine.codegen` and registered `components/org-chart.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**: 2,040 tests passing (17 new focused tests in `test_org_chart_component.py`). `task verify`, `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

### R-373 — Generated Accessible Futuristic Reusable Diff Viewer & Code/Text Comparison Suite (components/diff-viewer.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Diff Viewer & Code/Text Comparison compound components across generated Next.js web applications:

- **Standalone Diff Viewer Suite (`apps/web/components/diff-viewer.tsx`)**:
  - Implemented `DiffViewMode` (`"split"` | `"unified"`), `DiffLineType` (`"added"` | `"deleted"` | `"unchanged"`), `DiffViewerVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `DiffViewerSize` (`"sm"` | `"md"` | `"lg"`), `DiffWordPart`, `DiffLine`, `SplitDiffRow`, `DiffViewerHandle`, and `DiffViewerProps` interfaces.
  - Implemented compound and semantic alias exports: `DiffViewer`, `CodeDiff`, `TextDiff`, and default export.
  - Implemented zero-dependency pure mathematical LCS (Longest Common Subsequence) diff algorithm for line addition, deletion, and unchanged resolution.
  - Implemented word-level intraline character diffing highlighting specific within-line modifications.
  - Implemented Split (side-by-side) comparison view mode with synchronized row alignment and gap padding.
  - Implemented Unified (inline) comparison view mode with dual old and new line number gutters.
  - Implemented collapsible unchanged lines folding with configurable threshold (`foldThreshold`), context buffers (`contextLines`), and interactive expand trigger banners.
  - Implemented responsive toolbar with filename badge, addition (`+N`) and deletion (`-N`) counter statistics, view mode toggles, and one-click clipboard copy actions (raw patch, original, modified).
  - Implemented full WAI-ARIA accessibility semantics (`role="region"`, `role="table"`, `role="row"`, `role="cell"`, `aria-label="Code diff viewer"`, `aria-roledescription="diff view"`).
  - Implemented 6 built-in zero-dependency vector icons (`SplitIcon`, `UnifiedIcon`, `CopyIcon`, `CheckIcon`, `FileCodeIcon`, `ChevronDownIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with emerald/rose glowing diff gutters).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all compound exports.
  - Exported `render_diff_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/diff-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**: 2,023 tests passing (17 new focused tests in `test_diff_viewer_component.py`). `task verify`, `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

### R-372 — Generated Accessible Futuristic Reusable Digital Signature Pad & Drawing Canvas Primitive (components/signature-pad.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Digital Signature Pad & Drawing Canvas compound components across generated Next.js web applications:

- **Standalone Digital Signature Pad Suite (`apps/web/components/signature-pad.tsx`)**:
  - Implemented `SignaturePadVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `SignaturePadSize` (`"sm"` | `"md"` | `"lg"`), `SignaturePoint`, `SignatureStroke`, `SignaturePadHandle`, and `SignaturePadProps` interfaces.
  - Implemented compound and semantic alias exports: `SignaturePad`, `SignatureCanvas`, `DrawingPad`, and default export.
  - Implemented zero-dependency HTML5 `<canvas>` rendering with quadratic bezier curve stroke interpolation for silk-smooth lines.
  - Implemented high-DPI Retina `devicePixelRatio` scaling for razor-sharp rendering on all displays.
  - Implemented cross-device pointer events (`pointerdown`, `pointermove`, `pointerup`, `pointerleave`, `pointercancel` with `touch-action: none`) supporting stylus pressure, touch, and mouse input.
  - Implemented multi-level stroke history stack with undo, redo, and clear actions.
  - Implemented raster PNG dataURL export (`toDataURL()`) and vector SVG export (`toSVG()`) generating crisp scalable vector paths.
  - Implemented signing guide line with dashed styling, subtle "✕" mark, and configurable text ("Sign on line above").
  - Implemented pristine placeholder prompt overlay.
  - Implemented responsive toolbar with stroke counter badge and action buttons (Undo, Redo, Clear, Download).
  - Implemented native HTML form hidden input synchronization (`name`).
  - Implemented full WAI-ARIA application semantics (`role="application"`, `aria-label="Signature Pad"`, `aria-roledescription="drawing canvas"`, `aria-label="Signature drawing area"`).
  - Implemented 5 built-in zero-dependency vector icons (`UndoIcon`, `RedoIcon`, `TrashIcon`, `DownloadIcon`, `PenIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_signature_pad_component` in `omnistackai_agent_engine.codegen` and registered `components/signature-pad.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- **Verification**: 2,006 tests passing (17 new focused tests in `test_signature_pad_component.py`). `task verify`, `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

### R-371 — Generated Accessible Futuristic Reusable Time Picker & Time Range Suite (components/time-picker.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic Time Picker and Time Range compound components across generated Next.js web applications:

- **Standalone Time Picker Suite (`apps/web/components/time-picker.tsx`)**:
  - Implemented `TimeFormat` (`"12h"` | `"24h"`), `TimePickerVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `TimePickerSize` (`"sm"` | `"md"` | `"lg"`), `TimePreset`, `TimeRangePreset`, `TimePickerProps`, `TimeRangePickerProps`, and `TimeInputProps` interfaces.
  - Implemented compound and semantic alias exports: `TimePicker`, `TimeRangePicker`, `TimeInput`, `TimeColumn`, `ClockIcon`, and default export.
  - Implemented 12h (with AM/PM period selector) and 24h military/international format modes.
  - Implemented scrollable column listboxes for hours, minutes, and optional seconds with active item auto-scrolling into view.
  - Implemented customizable step increments (`stepMinutes`, `stepSeconds`).
  - Implemented quick-select preset chips ("Now", "09:00 AM", "12:00 PM", "05:00 PM").
  - Implemented dual-input `TimeRangePicker` with start and end time validation.
  - Implemented popover dropdown trigger with outside click and Escape key dismissal, alongside direct inline embedding mode (`inline={true}`).
  - Implemented full WAI-ARIA 1.2 combobox, listbox, and option semantics (`role="combobox"`, `role="listbox"`, `role="option"`, `role="group"`, `aria-haspopup="dialog"`, `aria-selected`).
  - Implemented 5 built-in zero-dependency vector icons (`ClockIcon`, `ChevronUpIcon`, `ChevronDownIcon`, `XIcon`, `CheckIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden inputs (`name`).
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_time_picker_component` in `omnistackai_agent_engine.codegen` and registered `components/time-picker.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.

## Verification

- `task verify` — pass (2,970 agent-engine tests; 15 new focused R-438 tests in `test_solution_pack_ai_delta.py` + 37 regression tests).
- `task lint`, `task security:quick`, `task env:check` — pass.
- `task builder:demo -- minimal-blog` and `task builder:demo -- rideshare-favourites` — pass (152 and 149 files).
- Zero-call fast-path and mock provider generation inspection — pass.

## Blockers and risks

- None for offline Solution Pack AI-delta proposal schema and local model provider integration.
- Deferred R-224 (Next.js console upgrade) remains paused pending network/npm registry access.

## Next action

- R-438 is complete. Before coding, record the R-439 Standard AI Task Contract. Recommended scope: safely apply
  validated AI-delta proposals to Application IR with semantic validation and provenance tracking, extending
  `SolutionPackApplicationResult` to reflect applied AI-delta modifications while rejecting invalid deltas.

## Next command

- `task ai:status`

