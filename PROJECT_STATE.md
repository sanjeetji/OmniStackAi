# Project State — OmniStackAI
Last updated: 2026-09-19

## Current Phase
Stage 0 (Founder Build Sequence, Brief Section 91) — BASIC/MVP

> **R-489 (2026-09-19): Runtime — free, self-hosted gVisor sandbox driver.** Fourth of the
> five-task sequence (R-486..R-490) — **replaces the originally planned WebContainers option**:
> real research found WebContainers requires a paid commercial license for any non-prototype
> commercial use, contradicting the "free, no cost" ask. After comparing every candidate's real
> licensing (Vercel Sandbox/Fly/CodeSandbox: paid-only; raw Firecracker: free but a multi-quarter
> build-your-own-orchestrator project; E2B/Daytona: open source but self-hosting means running
> their full orchestrator; gVisor: genuinely free, open source, small lift), the founder approved
> gVisor, then asked two real follow-ups before continuing — resource cost and "why not use this
> in production instead of paying" — both answered directly: gVisor is lightweight (~50MB binary,
> ~15-30MB RAM/sandbox), but a self-hosted loopback URL only works for a same-machine viewer; the
> managed providers' real value beyond isolation is a global public routing/proxy/scale layer this
> task doesn't build. Positioned explicitly as the free/dev tier, not a production replacement.
> A genuinely different transport (Docker's Unix socket, not a cloud HTTPS API) — new
> `docker_socket.py`. A real, necessary contract correction found and fixed:
> `SandboxHandle`'s https-only URL validation was too narrow once a local provider existed;
> relaxed to match `PreviewPlan`'s own loopback-or-https pattern. `active` is a live local
> capability check (is `runsc` registered?), not an env-var check — the only driver in this
> sequence with no credential at all. Docker's own image ecosystem covers Go, unlike Vercel
> Sandbox. No live gVisor/Docker daemon exists in this environment — live verification honestly
> deferred. `task verify` **3,729 OK** (22 new tests); repo gates all pass.
> NEXT: R-490 (provider-selection surface: free gVisor vs. paid E2B/Vercel/Daytona, switchable per
> user/config) — the last task in this sequence.

> **R-488 (2026-09-19): Runtime — real Daytona driver.** Third of the five-task sequence
> (R-486..R-490). E2B and Vercel Sandbox each proved `SandboxLifecycleProvider`/`sandbox_http.py`
> generalize; this task adds Daytona, whose real API is shaped a third distinct way: the create
> response carries **no URL at all** — a second real call,
> `GET /sandbox/{id}/ports/{port}/preview-url`, is required, verified by a dedicated test asserting
> both requests' exact shapes and ordering. `create()` always requests `"public": true` since
> `SandboxHandle.url` has no room for a companion preview-access-token header, which a non-public
> sandbox's link would otherwise need. **A real base-URL ambiguity across Daytona's own docs** was
> found and resolved the same way R-486's E2B v1/v2 ambiguity was — preferring the more specific,
> structured, directly-fetched source. **A real, honest isolation-strength tradeoff surfaced, not
> hidden**: Daytona's documented default isolation is plain Docker containers, weaker than E2B/
> Vercel's Firecracker microVMs — this driver does not attempt to select its opt-in stronger modes
> (undocumented in the fetched pages), called out explicitly for whenever R-490's
> provider-selection surface exists. No real `DAYTONA_API_KEY` exists in this environment —
> live-cloud verification honestly deferred. `task verify` **3,707 OK** (13 new tests); repo
> `task verify`/`lint`/`security:quick`/`env:check` all pass. Unlike R-487, no `providers.py`/
> `drivers.py` edit was needed at all — `RUNTIME_SPECS["daytona"]` already existed.
> **All three sandbox providers the founder asked for (E2B, Vercel Sandbox, Daytona) now have
> real, tested, pluggable drivers behind one shared contract.**
> NEXT: R-489 (free WebContainers browser option), R-490 (provider-selection surface).

> **R-487 (2026-09-19): Runtime — real Vercel Sandbox driver.** Second of the five-task sequence
> (R-486..R-490). Proves the `SandboxLifecycleProvider` pattern (introduced in R-486 for E2B) is
> genuinely pluggable against a second, differently-shaped API, reusing R-486's `sandbox_http.py`
> completely unchanged. Verified against Vercel's real REST API (fetched directly): `POST/GET/
> DELETE /v2/sandboxes[/{name}]`, `Bearer` auth, a `routes[]` array giving each port's real public
> URL directly (no pattern-guessing, unlike E2B). **A real, documented product limitation, not
> glossed over**: Vercel Sandbox's runtime enum has no Go — `backend-go` is rejected with a
> specific `UnsupportedSandboxRuntimeError`, distinct from an entirely-unknown-target error. **Two
> real bugs found and fixed**: (1) the first draft checked provider-runtime-support before
> validating the target existed at all, misclassifying an unknown target's error; fixed by
> validating the target first. (2) adding a `RUNTIME_SPECS` entry broke a pre-existing test that
> enumerates the registry expecting a matching planning-stub placeholder in `drivers.py` — fixed
> with one added line, `drivers.py` added to `allowed_paths` mid-task. No real `VERCEL_TOKEN`/
> `VERCEL_PROJECT_ID` exist in this environment — live-cloud verification honestly deferred.
> `task verify` **3,694 OK** (14 new tests); repo `task verify`/`lint`/`security:quick`/
> `env:check` all pass.
> NEXT: R-488 (Daytona driver), R-489 (free WebContainers browser option), R-490
> (provider-selection surface).

> **R-486 (2026-09-19): Runtime — real sandbox lifecycle contract + E2B driver.** First of a
> five-task sequence (R-486..R-490) toward the founder's "Full isolation: per-user processes/
> sandboxes" direction. Research (three-way: codebase state, competitor platforms, sandbox
> technologies) confirmed every serious 2025-2026 AI app-builder running real server-side code
> uses a managed microVM/gVisor sandbox provider — self-hosting Firecracker/K8s from scratch is a
> multi-quarter effort this project doesn't have headcount for. The founder's direction: build
> real, pluggable drivers for multiple providers (E2B, Vercel Sandbox, Daytona) so they can be
> switched later by cost/speed/smoothness, plus a free local-browser option — this task proves the
> pattern with the first provider. Confirmed by direct read: the existing `RuntimeProvider`/
> `PreviewPlan` abstraction is a pure *planner* (describes local commands + a URL), not a real
> orchestrator — `CloudSandboxProvider` was a stub reusing a hardcoded placeholder URL, never
> calling any real API. New, additive `SandboxHandle`/`SandboxLifecycleProvider` contract
> (create/status/kill — a genuine remote-resource lifecycle) alongside the untouched planner. New
> `runtime/sandbox_http.py` (a small, safe, stdlib-only JSON HTTP helper) and `runtime/e2b.py`'s
> `E2BSandboxProvider`, verified against E2B's actual documented REST API (fetched directly from
> `docs.e2b.dev`, not assumed): `POST/DELETE https://api.e2b.app/sandboxes[/{id}]`, `X-API-Key`
> auth, public URL pattern `https://{port}-{sandboxID}.e2b.app`. No real `E2B_API_KEY` exists in
> this environment — every gate is offline via an injected fake HTTP transport; live-cloud
> verification is honestly deferred to whenever the founder provides a real key, not faked.
> `task verify` **3,680 OK** (22 new tests); repo `task verify`/`lint`/`security:quick`/
> `env:check` all pass.
> NEXT: R-487 (Vercel Sandbox driver), R-488 (Daytona driver), R-489 (free WebContainers browser
> option), R-490 (provider-selection surface).

> **R-485 (2026-09-19): Console — streaming build UI.** Fast-follow to R-484, closing the loop it
> opened: `/studio`'s own chat now consumes `POST /jobs/build/stream` for its create-path,
> replacing the static "Building…" wait with a real, live-updating "Generating your app… (N
> characters so far)" indicator. New `streamBuildApp()` (`lib/control-plane.ts`) returns the raw
> upstream `Response` (unlike every other client function, which awaits parsed JSON) so a new
> proxy route (`app/api/jobs/build/stream/route.ts`) can pipe it straight through unbuffered — one
> pipe-through correctly handles both real shapes the control-plane can return (a streamed SSE
> success body, and a plain buffered JSON pre-stream rejection). `studio-chat.tsx` gains
> `sendBuildStream()`, replacing `sendBuild()`: `fetch()` + manual `response.body.getReader()`
> framing (not `EventSource`, which cannot send a POST body), handling three real frame shapes
> verified against R-484's own live output — `generating_ir` deltas (only their length drives the
> character count; raw partial JSON is never shown, since it would render as visibly broken text),
> `"done"` (the final result, unchanged rendering from before), and a bare no-`phase` credits frame
> (the Go relay's trailing event). Edit stays non-streaming, per R-484's own scope boundary.
> **No browser-automation tool was available this session** — verified instead via `next start` +
> `curl` through a real cookie-based login session, the same request path a real browser takes.
> `pnpm run typecheck`/`lint`/`build` all clean (21 routes, 1 new); repo `task verify`/`lint`/
> `security:quick`/`env:check` all pass (3,658 agent-engine tests unaffected — no backend file
> touched). Live: a real streamed build through the full console-proxy → Go control-plane →
> agent-engine path showed genuine incremental frames over ~9 real seconds, a real `done` frame
> (174 files, real commit sha), and a real trailing `credits` frame; a real follow-up edit on the
> same build confirmed the edit path is completely unchanged.
> NEXT: per "streaming first, then scope isolation properly," properly SCOPE (not yet build) full
> per-user process/sandbox isolation as its own multi-task project.

> **R-484 (2026-09-19): Backend — real-time build streaming (SSE).** First of the founder's
> post-roadmap priorities ("streaming first, then scope isolation properly"), chosen after three
> parallel research passes (competitor streaming architecture, per-user isolation scoping, deploy/
> stack breadth). Replaces the one-shot "Building…" blocking wait with genuine incremental progress
> — backend only (console UI is R-485, a fast-follow). New additive streaming twins
> (`generate_ir_stream`, `build_app_from_prompt_stream`, `_build_stream`) reuse the
> `ModelProvider.stream()` capability that already existed at the `model_gateway` layer but was
> never called above it. New `POST /api/build/stream` (agent-engine, SSE) and
> `POST /jobs/build/stream` (Go control-plane, verbatim relay via `http.Flusher` + a trailing
> `credits` event once the real cost is known). Plain-prompt builds only — Solution Pack/Ecosystem/
> `hybrid_ui` cleanly rejected with a `400` before any SSE framing begins.
> **Two real bugs found and fixed, not glossed over**: (1) the SSE route sent
> `Connection: keep-alive`, which `BaseHTTPRequestHandler` interprets as "never close this socket" —
> since there's no `Content-Length`/chunked framing, that hung every real client; fixed to
> `Connection: close`, caught by the first HTTP-level test. (2) `RecordingProvider` (the real
> usage-tracking wrapper every production build call goes through) had no `.stream()` method —
> every automated test mocked around it, so only the required live `curl -N` smoke test caught it
> (`'RecordingProvider' object has no attribute 'stream'`); fixed with 4 new tests mirroring
> `generate()`'s own success/failure ledger-recording shape.
> agent-engine `task verify` **3,658 OK** (27 new tests, 0 model/network calls); control-plane
> `go build`/`vet`/`test` all green (7 new tests in `handler_test.go`, 55 total). Live: a real
> `curl -N` session through the real Go control-plane showed genuine token-by-token deltas over
> ~9 real seconds (timestamped, not buffered), a real `done` frame (177 files, real git commit
> sha), and a real trailing `credits` frame (`credits_spent: 0` — this environment's configured
> cloud model has no price-book entry, a pre-existing unrelated fact); all three unsupported build
> kinds confirmed rejected with a clean `400` before any SSE framing.
> NEXT: R-485 (console: streaming build UI, consuming this endpoint in `studio-chat.tsx`), then
> properly scope (not yet build) full per-user process/sandbox isolation.

> **R-483 (2026-09-19): Fix — dynamic-route slug collision & duplicate FK identifier.** Second
> follow-up after the 7-task Phase D roadmap, per "complete one by one all." Fixes the exact real
> bug found live during R-481's own smoke test: a Next.js dev-server crash (`'counterId' !==
> 'counter_id'`) and a duplicate `lib/types.ts` identifier. Root cause verified by direct source
> read: an unreconciled casing mismatch between the full-build and edit-delta prompts for API
> `{param}`s, and `_entity_interface()` never checking for an already-declared field before
> synthesizing a relation's FK column. Fixed at the structural root — `ApiEndpoint.__post_init__`
> now canonicalizes every `{param}` to camelCase unconditionally; `_entity_interface()` now skips
> the synthesized FK when an explicit same-named field exists. `task verify` **3,635 OK** (6 new
> tests). Live: reproduced the exact original scenario end to end — built the same counter app,
> sent the same edit, started the preview successfully (no crash, confirmed via the real log), one
> consistent dynamic route folder on disk, a real `tsc` check showing 0 duplicate-identifier
> errors, `lib/types.ts` inspected directly with no duplicate line.
> NEXT: R-484 (real-time streaming), per-user multi-tenancy, and Publish/deploy each need an
> explicit founder architecture decision before implementation.

> **R-482 (2026-09-19): Model Provider settings UI.** First follow-up after the 7-task Phase D
> roadmap shipped, per the founder's "complete one by one all" direction. A real, live Dyad-style
> provider status page — `platform_overview()` already existed but only ever generated a static
> snapshot for `/fabric`; new: calling `resolve_generation_provider_from_env()` safely reports which
> provider would actually run the next build, never surfaced anywhere before. New agent-engine
> `GET /api/providers`, new control-plane `GET /jobs/providers` (no debit), new authenticated
> `/settings` page. **A real bug was found and fixed during this task's own live smoke test**
> (introduced by this task's own first draft): a dotenv-load-ordering bug that made the providers
> list's "active" flags read stale in a fresh process — fixed by reordering, verified with `env -i`.
> `task verify` **3,629 OK**; control-plane `go test` all green (48 tests, 3 new); console
> `typecheck`/`lint`/`build` clean (20 routes, 2 new). Live: cross-verified `activeNow` against a
> real build whose own log confirmed the exact same provider was used.
> NEXT: scope and fix the dynamic-route slug-collision codegen bug found live during R-481.

> **R-481 (2026-09-19): Tabbed workspace — the SEVENTH AND FINAL task of the founder-approved
> 7-task Phase D roadmap (R-475–R-481).** Restructured `/studio`'s main pane into four real tabs —
> Preview, Files, Code, Problems — with chat persisting alongside, assembling R-474/R-477/R-479/
> R-480 into one shell. Files and Code stay separate (founder's choice), sharing one lifted
> `selectedFile`. New `code-highlight.ts` hand-rolled tokenizer (no new dependency, confirmed live
> against real generated TSX). Problems tab is on-demand per R-480's design. `task verify`
> **3,625 OK**; console `typecheck`/`lint`/`build` clean (19 routes, 1 new). Live: full loop
> confirmed (build → Preview/Files/Code → edit → refresh confirmed → Problems check). A real,
> pre-existing codegen bug was found live (a dynamic-route slug collision from the edit path,
> unrelated to this task) — correctly surfaced as an honest Preview error and independently caught
> by a real Problems check, cross-confirming both features' error-surfacing design.
> **THIS COMPLETES THE APPROVED 7-TASK PHASE D ROADMAP.**
> NEXT: no pre-approved task remains queued — needs explicit founder direction on priority among
> R-482 (Model Provider settings UI), R-483 (streaming), per-user multi-tenancy, Publish/deploy,
> and the newly-found codegen bug.

> **R-480 (2026-09-19): Backend — Problems/compile-report support.** Sixth of the founder-approved
> 7-task plan (R-475–R-481). Real compile-error reporting for the first time in this codebase — the
> founder's explicit choice over a placeholder. New `studio/problems.py` mirrors `files.py`'s
> shape: resolves `apps/web`, raises `NoWebTargetError` if no web app, remaps `verify/compile.py`'s
> real `compile_web_project()`'s `VerifyError` into a clear `ToolchainNotInstalledError`. On-demand,
> not automatic. New control-plane routes `POST`/`GET /jobs/build/{id}/problems`, no credit debit, a
> new `defaultProblemsTimeout` (90s), a new 409 status for "toolchain not installed." `task verify`
> **3,625 OK** (21 new tests); control-plane `go test` all green (45 tests, 7 new). Live: build-only
> mode with no toolchain produced real 409/404, no crash; preview mode with a real installed
> toolchain surfaced **10 genuine TypeScript errors** via a real `tsc` run in an LLM-synthesized
> page; a repeated GET returned the byte-identical cached report in 12ms.
> NEXT: R-481 (tabbed workspace) — the final task of the approved 7-task roadmap.

> **R-479 (2026-09-19): Console — live preview UI.** Fifth of the founder-approved 7-task plan
> (R-475–R-481). An iframe rendering the real running generated app, wired to R-478's four routes.
> Preview start is synchronous, so polling's job is crash detection (5s interval while
> `status: "ready"`), not progress-watching. New `studio-preview.tsx` triggers a re-preview whenever
> `buildId` becomes real or a `previewVersion` counter (bumped after every edit) changes; a 404
> renders an honest disabled message; manual Restart/Stop reuse icons that existed unused since
> R-475. Every `PreviewStatus` shape verified by reading `preview.py` directly. `task verify`
> **3,604 OK**; console `typecheck`/`lint`/`build` clean (18 routes, 4 new). Live: real control-plane
> + real agent-engine Studio server in preview mode proved build → real iframe-ready preview → edit
> → real re-preview on a new port → the real preview OS process was killed directly to simulate an
> external crash, and the next poll correctly reported "stopped" → manual Restart/Stop both worked
> → build-only mode produced the uniform honest 404 disabled state.
> NEXT: R-480 (backend: Problems/compile-report support), then R-481 per the approved plan.

> **R-478 (2026-09-19): Backend — live preview proxy (local-only).** Fourth of the founder-approved
> 7-task plan (R-475–R-481). Four new control-plane routes proxying the agent-engine's existing
> trusted-local preview control surface verbatim: `GET /jobs/preview`, `POST /jobs/preview/stop`,
> `POST /jobs/preview/restart` (the singleton surface) plus `POST /jobs/build/{id}/preview` (the
> build-scoped one, server-constructing its own `{"id": id}` body rather than trusting the
> caller's). All auth-required, no credit debit, zero agent-engine changes. Verified, not assumed:
> an unknown build's build-scoped preview route returns a real 200 `{"status":"error"}`, not a 404
> — the proxy forwards it unchanged. New `defaultPreviewTimeout` (60s) applied to both
> `handleBuildPreview` and `handlePreviewRestart` (both can trigger a real cold start). `task
> verify` **3,604 OK**; control-plane `go test` all green (38 tests, 13 new). Live: real control-plane
> rebuilt + real agent-engine Studio server in preview mode proved a real build auto-starting a real
> preview, real status/stop/restart/build-preview proxying, the 200-with-error shape confirmed live
> for an unknown build, unchanged credit balance across all four calls, and uniform 404s against
> build-only mode.
> NEXT: R-479 (console: live preview UI), then R-480–R-481 per the approved plan.

> **R-477 (2026-09-19): Console — chat UI.** Third of the founder-approved 7-task plan
> (R-475–R-481). Replaced `/studio`'s one-shot prompt form with a persistent, multi-turn chat thread
> on R-475's shell, wired to R-476's new routes. `buildId` (`null` vs. set) decides whether the
> composer calls `/jobs/build` or `/jobs/build/{id}/edit`. New `studio-chat.tsx` +
> `studio-workspace.tsx` (the latter holding the `BuildResult`/`FileBrowser` pieces moved out of the
> retired `studio-form.tsx`, generalized to a `WorkspaceSnapshot`). `buildId` persists in the URL so
> a refresh hydrates chat text history from `/turns` — the workspace panel does not rehydrate, an
> honest, named simplification. A real finding, verified by source read before implementation: `GET
> /turns` does not 404 for an unknown build (`{"turns": []}` instead) — only `_edit()`'s
> `BuildNotFoundError` is a real 404, so the "session no longer available" recovery is wired there.
> `task verify` **3,604 OK**; console `typecheck`/`lint`/`build` clean (14 routes, 2 new). Live: real
> control-plane + real agent-engine Studio server + fresh `next start` proved build → turns hydration
> → follow-up edit with a refreshed file list, then the agent-engine Studio server was killed and
> restarted mid-test to simulate a real stale session — the edit-triggered 404 recovery and the
> turns-hydration honest-empty-thread finding both confirmed live, then a fresh build proved the
> full recovery loop.
> NEXT: R-478 (backend: live preview proxy), then R-479–R-481 per the approved plan.

> **R-476 (2026-09-19): Backend — multi-turn edit bridge.** Second of the founder-approved 7-task
> plan (R-475–R-481). New control-plane routes `POST /jobs/build/{id}/edit` and
> `GET /jobs/build/{id}/turns`, mirroring `POST /jobs/build`'s exact proxy+debit shape (R-472), plus
> two real, verified fixes to the Python edit path found during this roadmap's planning research
> (confirmed by direct source reads): `_edit()` had no `usage_ledger` at all, so every edit debited
> 0 credits regardless of real cost; `_build()` never recorded its own chat turn, so a future chat
> hydrating history from `/turns` after a refresh would silently lose the first message. Both fixed
> by mirroring `_build()`'s own existing patterns. Go side: `handleBuildEdit`/`handleBuildTurns`
> added, with the shared "forward, decode, debit, inject" logic extracted out of `handleBuild` into
> a `proxyAndDebit` helper both handlers reuse. A no-op edit still charges real credits — locked in
> by a dedicated test. Python side: `_edit()` now threads a real `UsageLedger`, adding a real
> `"usage"` key to its response; `_build()` now records its own chat turn. `task verify` **3,604
> OK**; control-plane `go test` all green (25 tests, 10 new). Live (real control-plane + a freshly
> restarted real agent-engine Studio server — Python doesn't hot-reload, and the first attempt
> against the stale process usefully reproduced the exact bug this task fixes): a real build's own
> turn now appears in `/turns` before any edit; a real edit produced a genuine second git commit and
> a real `"usage"` key on the edit response, both honestly `credits_spent: 0` since this
> environment's real configured cloud model has no price-book entry — the "debits a nonzero charge"
> behavior is proven by the new unit tests instead.
> NEXT: R-477 (console: chat UI), then R-478–R-481 per the approved plan.

> **R-475 (2026-09-19): Studio visual foundation.** First of a founder-approved, fully-researched
> 7-task plan (R-475–R-481, saved at `/Users/sanjeet_kumar/.claude/plans/hi-fancy-shannon.md`,
> mirrored in the kickoff doc) to take the Studio from functionally-real-but-plain toward a
> genuinely rich, chat-driven, multi-pane workspace closer to Lovable/Dyad/Emergent. Planning used
> full plan-mode discipline: two Explore agents researched the real frontend/backend code, a Plan
> agent designed the sequence, and the most consequential claims (e.g. `_edit()` has no
> `usage_ledger` today, so every edit currently debits 0 credits; the live-preview API's
> build-scoped route returns an unusual `200`-with-error-status for an unknown build; no
> compile-error endpoint exists anywhere yet) were independently verified by reading the real
> source. Two founder decisions honored: Problems (compile errors) gets built for real via its own
> task (R-480) rather than a placeholder, taking the roadmap from six tasks to seven; Files and
> Code stay as two separate tabs, not one. This task: new `app/studio/layout.tsx` takes over the
> `/studio` auth gate and persistent top-bar chrome; `globals.css` gained additive design tokens
> (`--radius-*`, `--surface-2`, `.spinner`, `.pill--accent`); new hand-rolled `studio-icons.tsx`
> rather than a new npm dependency. `studio-form.tsx` restyled only, zero logic change, no backend
> changes. `task verify` **3,603 OK**; console `typecheck`/`lint`/`build` clean; live: real
> control-plane + real agent-engine Studio server + a fresh `next start` proved the auth gate,
> shell, and unaffected sibling pages all work correctly.
> NEXT: R-476 (backend: multi-turn edit bridge), then R-477–R-481 per the approved plan.

> **R-474 (2026-09-18): file browser in the console Studio — see what a build actually produced.**
> Continues Phase D. R-473's build result panel listed filenames as inert text; each filename is
> now a button showing real generated file content in a read-only viewer, bridged through two new
> authenticated control-plane proxy routes (`GET /jobs/build/{id}/files`,
> `GET /jobs/build/{id}/file?path=...`) to the agent-engine's existing R-467 file-serving endpoints
> — no agent-engine changes, no credit debit. Honest, named limitation carried over unchanged from
> R-467: the Studio server has no per-user build scoping. `task verify` **3,603 OK**; control-plane
> `go test` all green (15 in `internal/jobs`); console `typecheck`/`lint`/`build` clean (13 routes).
> Live, against the founder's own already-running demo stack (only the control-plane and console
> restarted to pick up the code, Postgres and the Studio server's build history left untouched):
> built a real 158-file app via real Groq cloud, then proved the file browser end to end, including
> an unknown-build 404 and a path-traversal 400, both proxied through from the agent-engine unchanged.
> NEXT: continue Phase D (live preview, chat/multi-turn edit, or Solution Pack/Ecosystem selection).
> Phase E still needs its own explicit founder sign-off before starting.

> **R-473 (2026-09-18): Studio v1 in the console — build an app from the product, not curl.**
> Phase D of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, first slice: a logged-in user
> can open `apps/console-web`'s new `/studio` page, type a plain-English app description, click
> Build, and get a real app built through R-472's real Job API, with the console showing the real
> post-debit credit balance. Deliberately scoped small — no file browser, live preview, or chat yet
> — matching how the agent-engine's own hybrid-UI engine shipped across four separate gated Tracker
> IDs (R-465–R-468) rather than one large task; those capabilities are named follow-ups. New
> `app/studio/page.tsx` (auth-gated) + `app/studio/studio-form.tsx` (prompt, Build, result panel,
> error banner) + `app/api/jobs/build/route.ts` (server-side proxy, session-cookie-gated, bearer
> token never exposed to client JS). No control-plane or agent-engine changes. `task verify`
> **3,603 OK**; console `typecheck`/`lint`/`build` clean; live: a real Docker control-plane + a real
> agent-engine Studio server on local Ollama + a real `next start` console proved `/studio`'s auth
> gate, a genuine (unforced) local-model failure rendering as a real error banner, and a genuine
> successful 157-file build with every field matching the UI's expectations.
> NEXT: continue Phase D (file browser/live preview/chat, or Solution Pack/Ecosystem selection in
> the Studio UI). Phase E still needs its own explicit founder sign-off before starting.

> **R-472 (2026-09-18): bridge the control-plane's Job API to the agent-engine — real credit
> debiting.** Phase C of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`: the control-plane's
> new `POST /jobs/build` authenticates the caller, forwards the request body verbatim to the
> agent-engine's real plain-prompt build path, and debits real credits from the actual dollar cost
> the agent-engine now reports. Correction found while researching: that build path returned a raw
> `ModelProvider`, bypassing the gateway's own real-but-previously-demo-only `UsageLedger` entirely
> — closed with a new, additive `model_gateway.RecordingProvider` decorator (zero changes to any
> existing provider or call site). A real bug was caught by the new tests before any commit
> (`RecordingProvider` initially recorded the wrong provider/model identity); a real infrastructure
> bug was found only by the live smoke test (the control-plane's global 15s `WriteTimeout` was
> killing the connection before a real multi-minute build finished, fixed with a per-request
> `http.ResponseController.SetWriteDeadline`). New Go pieces: `auth.RequireUser`,
> `users.Store.DebitCredits` (row-locked, clamped so balance never goes negative — v1 policy is
> never block a build), and the new `internal/jobs` package. `task verify` **3,603 OK** (agent-engine)
> + full control-plane `go test` green; live: a real Docker Postgres+control-plane, a real local
> Ollama build produced a real 161-file repo with correctly-zero cost/credits (local usage is
> credit-exempt by price); `DebitCredits`'s real Postgres path (row lock + clamp) was proven
> separately since a free local build had nothing to debit.
> NEXT R-473 (Phase D): rebuild the real Studio/builder UX inside `apps/console-web` so a logged-in
> user can actually call `/jobs/build` from the product itself.

> **R-471 (2026-09-17): fixed a real dev-mode hydration bug found by the founder's own first live
> try of the console, and added a full name field to registration.** Opening
> `http://127.0.0.1:4321/register` and submitting the form silently did nothing — Next.js 16 blocks
> cross-origin access to its own dev/HMR resources by default and treats `127.0.0.1`/`localhost` as
> different origins, so client JS never hydrated and the browser fell back to a native form
> submission (fields serialized into the URL, no visible error). Fixed with `allowedDevOrigins` in
> `next.config.ts` — verified as far as possible without literally driving a browser (fetched the
> exact client JS chunk the page references with the real origin header: 200, and the warning that
> appeared before the fix no longer does). Also added a required **Name** field to registration
> (new migration `000003_users_full_name`) — explicitly **not** Gender or Age, which serve no
> function in this product and would be unnecessary PII, a deliberate decision recorded in
> `.ai/tasks/R-471.md`. Renumbered the kickoff doc's Phase C from R-471 to R-472. `task verify`
> **3,593 OK**; live: control-plane rebuilt/restarted, migration applied cleanly on the existing
> volume, register-without-name → 400, register-with-name → 201, home page shows "Welcome back,
> {name}", confirmed both through the console and directly against the control-plane.
> NEXT R-472 (Phase C): bridge the control-plane's Job API to the agent-engine so credits get
> debited on a real generation call.

> **R-470 (2026-09-17): real Next.js console-web, wired to R-469's auth API.**
> Phase B of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`: the static, dependency-free
> `apps/console-web` is now a real Next.js (App Router, TypeScript) app. `/login`/`/register`
> pages, an authenticated `/` home page (profile + credit balance), and `/fabric` (the old
> model/cost overview carried forward on the same `data/overview.json` contract). Session handling
> is a server-side cookie proxy (`app/api/auth/*` Route Handlers set/clear an `httpOnly` cookie) —
> the raw token never reaches client-side JS, no CORS needed. No new UI dependency beyond
> React/Next.js itself. Found and fixed five real ecosystem-compatibility issues while
> implementing, most notably a `Secure`-cookie-over-HTTP bug that would have silently broken login
> in a real browser (curl's leniency masked it in the first smoke test) — full detail in
> `.ai/tasks/R-470.md`. `task verify` **3,593 OK**; a real Docker Compose control-plane + a real
> `next start` server proved the full register → home → fabric → logout → login round trip live,
> twice (the second run after the cookie fix).
> NEXT R-471 (Phase C): bridge the control-plane's Job API to the unmodified agent-engine so a real
> generation call debits credits.

> **R-469 (2026-09-17): control-plane foundation — users, auth, plans, credits.**
> Phase A of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` (the founder-approved
> commercial platform kickoff): the existing `services/control-plane` Go skeleton
> (health-check-only before this task) now has real users, authentication, and a plan/credit
> model. Two roles only (`super_admin`, `user` — a user's access is gated entirely by `plan`,
> reusing the Brief Section 22 tier names `free`/`developer`/`pro`/`agency`/`enterprise`, `byok`
> as an add-on flag); every signup gets `free` plus a starting credit grant recorded in an
> append-only `credit_ledger`. New migration `000002_users_auth_billing` applied via a new
> self-healing embedded migration runner (`migrations` package, replays every idempotent
> migration file on every boot — necessary because `docker-entrypoint-initdb.d` only runs against
> a brand-new volume). Password hashing is PBKDF2-HMAC-SHA256 on Go stdlib only — **zero new
> `go.mod` dependency**. Four new endpoints (`/auth/register`, `/auth/login`, `/auth/logout`,
> `/auth/me`); login failure is a generic 401 with no email-enumeration timing leak, proven both
> in unit tests and against a real running container. `go test` all green; `task verify` **3,593
> OK**, 0 model/network calls; a real Docker Compose + PostgreSQL smoke test proved the full
> register → login → me → logout → me-after-logout round trip end to end. `studio/page.py`
> untouched — still the agent-engine's own local proof harness, not the product UI.
> NEXT R-470 (Phase B): replace `apps/console-web` with a real Next.js app wired to these
> endpoints. See `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, `.ai/tasks/R-469.md`.

> **R-468 (2026-09-17): the Studio supports multi-turn "continue editing this app".**
> - `intake/app_delta.py` (new): a generic, non-pack-coupled sibling of `solution_packs/ai_delta.py` — a
>   follow-up prompt proposes a bounded, validated delta (new entities/apis/screens only, never a
>   restatement of the app), merged onto the tracked IR by tuple concatenation (mirrors
>   `solution_packs/application.py`'s merge exactly, backstopped by `ApplicationIR`'s own validation), with
>   a bounded validate→feedback→retry loop (mirrors R-465's `_synthesize_file`). **Zero changes to `edit/`,
>   `git_service/`, or `application_ir/`** — `plan_edit`/`commit_edit` (already proven end-to-end) turn the
>   delta into a real second git commit on the same owned repo, unmodified.
> - `studio/session.py` (new): a small, bounded, in-memory, server-only `StudioSessionStore` tracking each
>   editable build's current IR + turn history. New `POST /api/build/{id}/edit` /
>   `GET /api/build/{id}/turns` routes, wired unconditionally; `page.py` gets a small chat box.
> - v1 scope: additive-only; Solution Pack and "all surfaces" Ecosystem builds get an honest
>   `EditNotSupportedError` rather than a silent no-op.
> - Found and fixed while implementing: neither this module nor `ai_delta.py` validated a screen's `role`
>   against the base IR's real declared roles — fixed at both the parse and merge layers.
> - Gates: `task verify` **3,593** OK (63.8s, no slowdown); demos clean. End-to-end tests
>   (`test_studio_edit.py`) prove real second/third git commits with the new entity's files actually on
>   disk, a rejected collision making zero commits, and both excluded build kinds honestly rejected.
>   NEXT R-469: wire R-466's `compile_and_repair` into the edit flow; an undo/revert UI over the real git
>   history every edited build now has.

> **R-467 (2026-09-17): the HYBRID engine reaches the product UI — a file browser and a hybrid-UI toggle in the Studio.**
> - `studio/files.py` (new): `list_build_files`/`read_build_file`, path safety mirroring `edit/apply.py`'s
>   `_safe_destination`; excludes `.git`/`node_modules`/`__pycache__`/`.next`/`.venv` and real `.env*` files.
>   New `GET /api/build/{id}/files` + `GET /api/build/{id}/file?path=...` routes in `server.py`, resolved
>   against `StudioBuildHistory`'s recorded `target_dir` in `live_serve.py`, wired in build-only mode too.
> - `/api/build` gains `hybrid_ui: bool`, threading `synthesize_screens=True` + a `ui_outcomes` sink into the
>   plain-prompt and Ecosystem Pack build paths (`hybrid_ui_active` reported honestly when a provider didn't
>   resolve); the Solution Pack path (no such parameter exists there) reports `hybrid_ui_active: false`.
>   `intake/build_app.py`'s `app_build_result_to_dict` gained an additive `ui_outcomes` param (unchanged
>   when omitted); `StudioBuildHistory.record` captures the new fields (bounded).
> - `page.py`: the flat, non-clickable file list is now a two-pane browser (list + read-only viewer); a
>   "Hybrid UI (experimental)" checkbox on the build form; a summary line + 🤖 badge for model-written files.
>   Zero external assets preserved.
> - **Live discovery while implementing:** real Groq credentials now sit in the repo's gitignored `.env`
>   (from the R-465/R-466 live proofs) — running the *pre-existing* Studio test suite unmodified made real
>   outbound calls to Groq (one unmocked test cost 23.5s of real traffic). 4 pre-existing test call sites
>   (2 already suspected, 2 more found here) never mocked `resolve_generation_provider_from_env`; all 4 now
>   do — closing a live, active violation of the "0 model/network calls under `task verify`" constraint.
> - Tests: 4 new test files/additions (`test_studio_files` new, 18); `task verify` **3,529** OK (full local
>   suite 3,529 + 42 subtests in 68.80s, materially faster post-fix); demos clean. Manual smoke against a real
>   running server confirmed the file browser end-to-end. NEXT R-468: multi-turn chat in the Studio.

> **R-466 (2026-09-17): the HYBRID engine compiles what the model wrote, paces rate limits, and shrinks too-large requests.**
> - `verify/compile.py`: capturing `tsc --noEmit --pretty false` executor → `CompileReport` of per-file `CompileError`s
>   (+ `ensure_web_dependencies`: reuse / symlink / `pnpm install`). `codegen/hybrid_repair.py`: `llm_file_specs`
>   (the exact R-465 prompts, template fallbacks, compact prompts), `repair_compiled_files` (compiler errors through
>   `_repair_message`; validator-gated; template fallback; outcome per file; deterministic files never rewritten),
>   `build_repair_diff` + `compile_and_repair(_sync)` (compile → repair → apply → recompile; revert on the last round).
> - `model_gateway`: `ProviderHTTPError(status_code, retry_after_seconds)`, `ProviderRateLimitedError` (429),
>   `parse_retry_after`; the cloud adapter waits the provider's own hint and re-sends the same request, bounded by
>   `OMNISTACKAI_RATE_LIMIT_RETRIES` / `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS` (documented in `.env.example`), logged.
> - `codegen/llm_ui.py`: `_Transcript` shrinks on a "request too large" rejection (drop the echo, then
>   `compact_grounding(ir)`); `last_reason` carries the HTTP status (`ProviderHTTPError(413)`), never the body.
> - CLI `task agent-engine:ui:synthesize` Step 3/3 type-checks, repairs, reverts and commits. Tests: 48 new
>   (`test_cloud_rate_limit`, `test_compile_report`, `test_hybrid_repair`, `test_llm_ui_compact`); `task verify`
>   **3,490** OK; `web-typecheck` PASSED ×2. Live (Groq free tier): the 3-step CLI ran end-to-end (fallback repo at 0
>   errors); pacing verified live (`Retry-After: 112` honoured, above the cap); limiter = tokens per day (daily budget
>   spent). NEXT R-467: product-UI shell v1.

> **R-465 (2026-09-17): the HYBRID UI engine is grounded — the LLM writes the UI over the deterministic data layer.**
> - `codegen/nextjs.py`: `summarize_data_layer` (real `lib/types.ts`/`lib/hooks.ts`/`lib/api.ts` surface parsed from
>   the same generators — cannot drift), `_component_files` + `summarize_components` (real ~110 component files and
>   export names; auth-provider only when `needs_auth`), `summarize_design_tokens` (real token names).
> - `codegen/llm_ui.py`: one `_synthesize_file` core with a bounded validation→feedback→retry loop (≤3; retry only on
>   validator rejection, never on exceptions) and a deterministic template fallback; JSON-safe, secret-free
>   `UiSynthesisOutcome` per file; hardened import whitelist (multi-line, exact `react`/`react-dom`, no
>   `react-*`/`require`/dynamic `import`).
> - Explicit `synthesize_screens` + `ui_outcomes` threaded `generate → assemble_project → build_app_from_ir/prompt`
>   (default off; default output byte-identical; the never-set env gate removed). Opt-in CLI
>   `task agent-engine:ui:synthesize` (`intake/ui_synthesize_run.py`). Docs: `docs/HYBRID_UI.md`.
> - Tests: `test_llm_ui_grounding.py` (15) + honest updates to the R-462/platform tests; `task verify` **3,442** OK;
>   `web-typecheck` PASSED ×2. Live proof with the founder's Groq key (free tier, 8k TPM, one model): validator
>   rejection → repair engaged → rate-limited → graceful fallback with a truthful outcome; a full LLM-page proof needs
>   >8k TPM (Gemini key or Groq Dev tier). NEXT R-466 (compile-level repair + 429 pacing), R-467 (product-UI shell).

> **The differentiating SPINE now supports Full-Stack Production Authentication Engine (R-461).**
> - Database schema (`schema_sql.py`): Emits PostgreSQL `users` table with UUID primary key, `VARCHAR UNIQUE NOT NULL` email, `VARCHAR NOT NULL` password_hash, optional full_name, `VARCHAR NOT NULL DEFAULT 'user'` role, and `TIMESTAMPTZ` created_at, plus development admin seed row (`admin@example.local` / `changeme`).
> - FastAPI auth router (`auth_guard.py`): Exported `python_auth_router_file(ir)` with `/register`, `/login`, `/me`, `/logout` endpoints, using `hashlib.pbkdf2_hmac` (SHA-256, 100k iterations) with zero external dependencies, JWT signing/verification, and wired into `main.py` via `backend_python.py`.
> - Next.js Web (`nextjs.py`): Synthesizes `components/auth-provider.tsx` with `useAuth()` hook exposing `user`, `token`, `login()`, `register()`, and `logout()`; responsive `app/login/page.tsx` and `app/register/page.tsx` with error alerts, client validation, and redirection; navbar user state toggle showing user greeting / logout button when logged in and Sign In link when logged out.
> - API Client (`lib/api.ts`): Automatically attaches the Bearer token from localStorage (`auth_token`) with explicit override support.
> - Tested via `test_full_stack_auth.py` (42/42) and full offline `task verify` (3,386 tests total).

## Task Compilation Audit — 2026-09-16

**Updated on 2026-09-16 to achieve 100% synchronization across all task-tracking documentation.**

### Current Metrics
1. **Execution Tracker Workbook** (`R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx`):
   - Row inserted into `Phase_Roadmap` for task R-461. Covers **461 tasks total** with R-461.
   - Status breakdown: **250 Done, 1 Deferred (R-252), 210 Not Started**.
   - MVP completion: **250 / 356 = 70.2%**. Overall: **250 / 461 = 54.2%**.
2. **Changelog** (`CHANGELOG.md`):
   - All 251 completed tasks now have changelog entries. 0 missing.
3. **Documentation Updates**:
   - `docs/PROGRESS.md`: Updated headline counts to 3,386 tests, 250 Done, 461 total tasks.
   - `docs/RESUME_PROMPT.md`: Updated task count and next action to R-462.
   - `PROJECT_STATE.md` (this file): Added R-461 completion details.
   - `.ai/PROJECT_STATE.yaml`, `.ai/WORK_LOG.md`, `.ai/HANDOFF.md`: Updated state and handoff notes.

## Last Completed Task
Tracker ID: R-464 — Full-Stack Platform Feature Completeness (4 Phases) — DONE.
Implemented full-stack platform feature completeness across 4 phases:
- **Phase 1 (Frontend Search, Pagination & Filter UI Controls)**: Verified collection screen controls and updated LLM UI prompt synthesis (`codegen/llm_ui.py`) with complete hook signatures (`page`, `pageSize`, `totalPages`, `params`, `setSearch`, `setPage`, `setPageSize`, `setSort`, `setFilter`, `clearFilters`, `refetch`).
- **Phase 2 (Audit Timestamps on All Entity Tables)**: Added `"created_at"` and `"updated_at"` `TIMESTAMPTZ` with automatic `set_updated_at()` trigger across all entity tables in `schema_sql.py`; added `CreatedAt`/`UpdatedAt` to Go (`backend_go.py`) and Python (`backend_python.py`) models; added `created_at?: string;` and `updated_at?: string;` to TypeScript interfaces and rendered metadata footer in `_detail_screen_page` (`nextjs.py`).
- **Phase 3 (RBAC / Row Ownership `created_by`)**: Conditional on `needs_auth(ir)`: added `"created_by" UUID REFERENCES "users"("id") ON DELETE SET NULL` to entity tables; added `require_owner` (Python) and `RequireOwner` (Go) in `auth_guard.py`; added `created_by?: string | null;` to TypeScript types and `ownerOnly?: boolean` to list hooks in `nextjs.py`.
- **Phase 4 (S3-Compatible File Uploads)**: Added `FieldType.ATTACHMENT = "attachment"` and string aliases to `application_ir/ir.py`; mapped to `TEXT` in SQL, `string` in TypeScript/Go, `str` in Python; added storage environment variables (`STORAGE_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`) to `.env.example`.
- Tested via `test_platform_feature_completeness.py` (14 tests) and full offline test suite (3,427 tests passing). Total completed tasks in tracker: **252 Done / 464 Total**.

Immediately preceded by R-461 — Full-Stack Production Authentication Engine — DONE.
Implemented Full-Stack Production Authentication Engine:
- PostgreSQL `users` table with UUID primary key, `VARCHAR UNIQUE NOT NULL` email, `VARCHAR NOT NULL` password_hash, optional full_name, `VARCHAR NOT NULL DEFAULT 'user'` role, and `TIMESTAMPTZ` created_at, plus development admin seed row (`admin@example.local` / `changeme`).
- FastAPI auth router (`/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`) in `auth_guard.py` using `hashlib.pbkdf2_hmac` (SHA-256, 100k iterations) with zero external dependencies, JWT signing/verification, and wired into `main.py` via `backend_python.py`.
- Next.js AuthProvider (`components/auth-provider.tsx`) exposing `useAuth()` hook with `user`, `token`, `login()`, `register()`, and `logout()`.
- Responsive `app/login/page.tsx` and `app/register/page.tsx` pages with error states, validation, and auto-redirect.
- Navbar user state toggle (signed in greeting & logout button vs. sign-in link).
- API client (`lib/api.ts`) auto-attaching Bearer token with localStorage fallback.
- `test_full_stack_auth.py` (42/42) and full offline `task verify` (3,386 tests passing); zero external dependencies, zero network requests.

Immediately preceded by R-460 — Next.js Codegen End-to-End Route Handler Synthesis and Interactive CRUD Form Submission — DONE.
Implemented Next.js Codegen End-to-End Route Handler Synthesis & Interactive CRUD Form Submission:
- `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`: Replaced scaffolded HTTP 501 `not_implemented` route stubs in generated Next.js web apps (`apps/web/app/<api_path>/route.ts`) with functional route handlers that forward requests directly to the FastAPI backend (`BACKEND_INTERNAL_URL` / `NEXT_PUBLIC_API_URL` / `http://127.0.0.1:8000`), preserving methods, auth headers, query params, and JSON payloads with structured 503 fallback handling; scoped `X-Frame-Options: DENY` to production only in `next.config.mjs` to enable Web Studio iframe preview.
- `scratch/apps/create-a-worker-attendance-management-sy/apps/web/`: Updated active generated app's `next.config.mjs` and `route.ts` files for immediate end-to-end functionality.
- `services/agent-engine/tests/test_nextjs_routes_crud.py`: Added 3 focused tests verifying zero 501 stubs, backend proxy resolution, and parameter forwarding.
- `task verify`: 3,340 tests pass offline; lint, security, and environment checks clean.

Immediately preceded by R-459 — Solution Pack Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts — DONE.
- `studio/page.py`: Enhanced Web UI with sky-blue/amber-themed `#preview-docs-info` container displaying pages, runbooks, and API endpoints count badges, and "Export Docs" / "Refresh" buttons, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `docs` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, `--search`, and `--export` options; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Twenty new focused tests in `test_ecosystem_docs.py`; `task verify` **3,333 passed** offline (+23 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-458 — Solution Pack Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts — DONE.

Immediately preceded by R-456 — Solution Pack Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies — DONE.
Implemented Solution Pack Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies:
- `solution_packs/ecosystem_alerting.py`: Implemented canonical `AlertRule`, `RunbookStep`, `IncidentRunbook`, `EscalationTier`, `EscalationPolicy`, `EcosystemAlertingContract`; implemented deterministic Python 3.13 stdlib-only contract synthesis (`synthesize_ecosystem_alerting`) for all ecosystem surfaces; implemented thread-safe in-process `EcosystemAlertingEngine` evaluating metrics against rules, dry-running runbooks, and executing operational incident simulations across scenarios (`api_error_spike`, `high_latency_degradation`, `db_connection_exhaustion`, `finops_budget_breach`, `healthy_baseline`).
- `solution_packs/ecosystem_pack.py` & `solution_packs/ecosystem_registry.py`: Extended `EcosystemPackPackage` and `EcosystemPack` with `alerting_contract`, validating with whole-package SHA-256 checksums; added `get_alerting_contract` accessor on `EcosystemPackRegistry`; exported all alerting symbols in `solution_packs/__init__.py`.
- `studio/preview.py`, `studio/server.py`, `studio/live_serve.py`: Preview manager tracks alerting contracts and simulation engines, injects `has_alerting`, `alert_rule_count`, `runbook_count`, `escalation_policy_count`, and `alert_status` into preview status/payloads, and exposes `get_ecosystem_alerting()` and `simulate_ecosystem_alerting()`; Studio HTTP server exposes `GET /api/ecosystem/alerting` and `POST /api/ecosystem/alerting/simulate`.
- `studio/page.py`: Enhanced Web UI with rose/crimson-themed `#preview-alerting-info` container displaying alert rules, runbooks, escalation policies, and "Simulate Incident" / "Refresh" buttons, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `alerting` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, `--simulate`, and `--scenario` options; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Twenty-three new focused tests in `test_ecosystem_alerting.py`; `task verify` **3,265 passed** offline (+23 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-455 — Solution Pack Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting — DONE.

Immediately preceded by R-454 — Solution Pack Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration — DONE.
Implemented Solution Pack Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration:
- `solution_packs/ecosystem_recovery.py`: Implemented canonical `BackupTarget`, `SnapshotManifest`, `RecoveryStep`, `RollbackTrigger`, `EcosystemDisasterRecoveryContract`; implemented deterministic Python 3.13 stdlib-only contract synthesis (`synthesize_ecosystem_recovery`) for all ecosystem surfaces; implemented thread-safe in-process `EcosystemRecoveryEngine` executing dry-run simulation for snapshots, recovery steps, rollback triggers, and full DR exercises returning structured PASS/FAIL summaries.
- `solution_packs/ecosystem_pack.py` & `solution_packs/ecosystem_registry.py`: Extended `EcosystemPackPackage` and `EcosystemPack` with `recovery_contract`, validating with whole-package SHA-256 checksums; added `get_recovery_contract` accessor on `EcosystemPackRegistry`; exported all recovery symbols in `solution_packs/__init__.py`.
- `studio/preview.py`, `studio/server.py`, `studio/live_serve.py`: Preview manager tracks recovery contracts and simulation engines, injects `has_recovery`, `backup_target_count`, `recovery_step_count`, `rollback_trigger_count`, and `dr_status` into preview status/payloads, and exposes `get_ecosystem_recovery()` and `simulate_ecosystem_recovery()`; Studio HTTP server exposes `GET /api/ecosystem/recovery` and `POST /api/ecosystem/recovery/simulate`.
- `studio/page.py`: Enhanced Web UI with amber-themed `#preview-recovery-info` container displaying backup targets, recovery steps, rollback triggers, and "Simulate DR" / "Refresh" buttons, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `recovery` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--json`, and `--simulate` modes; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Twenty-one new focused tests in `test_ecosystem_recovery.py`; `task verify` **3,223 passed** offline (+21 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-452 — Solution Pack Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration — DONE.
Implemented Solution Pack Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration:
- `solution_packs/ecosystem_cicd.py`: Implemented canonical `CIJobStep`, `CIJob`, `CIWorkflow`, `EcosystemCICDContract`; implemented deterministic Python 3.13 stdlib-only GitHub Actions YAML workflow generation (`generate_github_actions_workflow` and `to_workflow_yaml`) with zero external dependencies (no PyYAML); implemented in-process DAG dependency validation (Kahn's algorithm cycle detection) and deterministic dry-run pipeline simulation (`EcosystemCICDEngine`); implemented deterministic `synthesize_ecosystem_cicd(ecosystem_id, surfaces)` deriving surface verification jobs (Node.js/pnpm for web/admin surfaces, Python/pip + PostgreSQL service for FastAPI APIs, Go + PostgreSQL service for Go backends) and overarching `ecosystem-integration` verification gate.
- `solution_packs/ecosystem_pack.py` & `solution_packs/ecosystem_registry.py`: Extended `EcosystemPackPackage` and `EcosystemPack` with `cicd_contract`, validating with whole-package SHA-256 checksums; added `get_cicd_contract` accessor on `EcosystemPackRegistry`; exported all CI/CD types and helper functions in `solution_packs/__init__.py`.
- `studio/preview.py`, `studio/server.py`, `studio/live_serve.py`: Preview manager tracks CI/CD contracts and simulation engines, injects `has_cicd`, `cicd_workflow_count`, `cicd_job_count`, and `cicd_status` into preview status/payloads, and exposes `get_ecosystem_cicd()`, `to_workflow_yaml()`, and `simulate_cicd_run()`; Studio HTTP server exposes `GET /api/ecosystem/cicd`, `GET /api/ecosystem/cicd/yaml`, and `POST /api/ecosystem/cicd/simulate`.
- `studio/page.py`: Enhanced Web UI with `#preview-cicd-info` container displaying workflow triggers, job chips, and 1-click "Copy GitHub Actions YAML", "Simulate Pipeline", and "Refresh CI/CD" buttons, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `cicd` subcommand supporting both file paths and registered ecosystem IDs with formatted text summary, `--yaml`, `--json`, and `--simulate` modes; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Fifteen new focused tests in `test_ecosystem_cicd.py`; `task verify` **3,173 passed** offline (+15 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-451 — Solution Pack Ecosystem Cross-Surface Data Sync, Conflict Resolution, and Offline-First Sync Protocol — DONE.
Implemented Solution Pack Ecosystem Multi-Surface Export, Deployment Manifest, and Live Gateway Orchestration:
- `solution_packs/ecosystem_deployment.py`: Implemented canonical `GatewayRoute`, `SurfaceDeploymentSpec`, `EcosystemDeploymentManifest`; implemented deterministic Python 3.13 stdlib-only Docker Compose YAML generator (`generate_docker_compose`, `to_compose_yaml()`) for all surfaces and PostgreSQL with 0 external dependencies; implemented in-process `EcosystemLiveGateway` HTTP reverse proxy routing requests via longest-prefix matching with hop-by-hop header strip and forwarding headers injection; implemented deterministic deployment synthesis (`synthesize_ecosystem_deployment(ecosystem_id, surfaces)`) deriving non-colliding host ports, routes, and environment bindings across surfaces and PostgreSQL.
- `solution_packs/ecosystem_pack.py` & `solution_packs/ecosystem_registry.py`: Extended `EcosystemPackPackage` and `EcosystemPack` with `deployment_manifest`, validating with SHA-256 package checksums; added `get_deployment_manifest` accessor on `EcosystemPackRegistry`; exported symbols in `solution_packs/__init__.py`.
- `studio/preview.py`, `studio/server.py`, `studio/live_serve.py`: Preview manager tracks deployment manifest and live gateway, injects `has_deployment`, `deployment_surface_count`, `gateway_routes`, `gateway_port`, and `gateway_url` into preview status/payloads, and exposes `get_ecosystem_deployment()` and `to_compose_yaml()`; Studio HTTP server exposes `GET /api/ecosystem/deployment` and `GET /api/ecosystem/deployment/compose`.
- `studio/page.py`: Enhanced Web UI with `#preview-deployment-info` container displaying surface counts, route chips, and 1-click "Copy Compose YAML" / "Refresh Deployment" buttons, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `deploy` subcommand supporting both file paths and registered ecosystem IDs with human-readable, `--json`, and `--compose` outputs; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Thirteen new focused tests in `test_ecosystem_deployment.py`; `task verify` **3,144 passed** offline (+13 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-449 — Solution Pack Ecosystem Cross-Surface Telemetry, Audit Trails, and Distributed Tracing — DONE.
Implemented Solution Pack Ecosystem Cross-Surface Webhook and Event Bridge:
- `solution_packs/ecosystem_events.py`: Implemented canonical `WebhookRetryPolicy`, `EcosystemWebhookSubscription`, `EcosystemEventPayload`, `WebhookDeliveryRecord`, and `EcosystemEventBridgeContract`; implemented Python 3.13 stdlib-only HMAC-SHA256 signature generator (`sign_webhook_payload`) and verifier (`verify_webhook_signature`) with constant-time equality check (`hmac.compare_digest`) and zero external dependencies; implemented in-process `EcosystemEventBridge` with subscription management, cross-surface webhook routing, dispatching, and bounded delivery logging (max 100 entries); implemented deterministic `synthesize_ecosystem_events(ecosystem_id, surfaces)` deriving cross-surface subscriptions from entity writers to readers with lowercase slug formatting.
- `solution_packs/ecosystem_pack.py` & `solution_packs/ecosystem_registry.py`: Extended `EcosystemPackPackage` and `EcosystemPack` with `event_bridge`, validating with SHA-256 package checksums; added `get_event_bridge` accessor on `EcosystemPackRegistry`.
- `studio/preview.py`, `studio/server.py`, `studio/live_serve.py`: Preview manager tracks event bridge contracts, injects `has_events`, `event_count`, and `subscription_count` into preview status/payloads, and exposes `get_ecosystem_events()` and `dispatch_ecosystem_event()`; Studio HTTP server exposes `GET /api/ecosystem/events` and `POST /api/ecosystem/events/dispatch`.
- `studio/page.py`: Enhanced Web UI with `#preview-events-info` container displaying subscription count badges, an event simulation panel ("Simulate Event"), and live delivery log table, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `events` subcommand supporting both file paths and registered ecosystem IDs with human-readable and `--json` outputs; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Fifteen new focused tests in `test_ecosystem_event_bridge.py`; `task verify` **3,098 passed** offline (+15 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-447 — Solution Pack Ecosystem Multi-Surface Cross-App Auth and Unified State Binding — DONE.
Implemented Solution Pack Ecosystem Multi-Surface Cross-App Auth and Unified State Binding:
- `solution_packs/ecosystem_auth.py`: Implemented canonical `EcosystemRoleBinding`, `EcosystemAuthContract`, and `CrossAppAuthMatrix`; implemented Python 3.13 stdlib-only HS256 JWT token minter (`mint_ecosystem_token`) and verifier (`verify_ecosystem_token`) with 0 external dependencies; implemented `generate_surface_tokens` and deterministic `synthesize_ecosystem_auth(ecosystem_id, surfaces)`.
- `solution_packs/ecosystem_state.py`: Implemented canonical `SharedEntityBinding`, `StateTransition`, `EntityStateFlow` with role-gated `can_transition`, `CrossAppEndpointBinding`, `SurfaceEnvBinding`, `EcosystemStateBinding`, and `synthesize_ecosystem_state(ecosystem_id, surfaces)`.
- `solution_packs/ecosystem_pack.py` & `solution_packs/ecosystem_registry.py`: Extended `EcosystemPackPackage` and `EcosystemPack` with auth contracts and state bindings, validating with SHA-256 package checksums; added `get_auth_contract` and `get_state_binding` accessors on `EcosystemPackRegistry`.
- `studio/preview.py`, `studio/server.py`, `studio/live_serve.py`: Preview manager generates demo tokens, injects `active_role`, `active_token`, `has_auth`, `has_state` into preview status/payloads, and exposes `get_ecosystem_auth()` and `get_ecosystem_state()`; Studio HTTP server exposes `GET /api/ecosystem/auth` and `GET /api/ecosystem/state`.
- `studio/page.py`: Enhanced Web UI with `#preview-auth-info` container displaying active role badge and "Copy Demo JWT" button, strictly maintaining 0 external network requests.
- `solution_packs/ecosystem_cli.py`: Added `auth` and `state` subcommands supporting both file paths and registered ecosystem IDs with human-readable and `--json` outputs; updated `Taskfile.yml` and `scripts/agent-engine.sh`.
- Sixteen new focused tests in `test_ecosystem_auth_and_state.py`; `task verify` **3,083 passed** offline (+16 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-446 — Solution Pack Ecosystem Studio Live Multi-Surface Preview and Process Orchestration — DONE.
Implemented Solution Pack ecosystem pack registry integration, catalog discovery, and Studio multi-surface selection:
- `ecosystem_registry.py`: Defined `EcosystemPack` descriptor, `EcosystemPackRecommendation`, and immutable `EcosystemPackRegistry`; pre-registered built-in baselines (`minimal-blog-ecosystem`, `rideshare-favourites-ecosystem`) accessible via `DEFAULT_ECOSYSTEM_PACK_REGISTRY`; added `load_surface_ir()` to load clean, valid `ApplicationIR` per surface; used lazy registry loading to avoid circular imports.
- `ecosystem_pack.py` & `ecosystem_cli.py`: Extended `synthesize_ecosystem_pack` to accept `pack_id` string directly; added `catalog` subcommand to CLI for text/json discovery (`task agent-engine:solution-pack:ecosystem -- catalog`).
- `studio/server.py` & `studio/live_serve.py`: Added discovery/recommendation endpoints (`GET /api/ecosystem-packs`, `POST /api/ecosystem-packs/recommend`); extended `POST /api/build` to support `ecosystem_id`, `ecosystem_version`, and `surface_slug`; wired `live_serve.py` to compile a single surface or the entire multi-surface ecosystem with 0 model calls.
- `studio/page.py` & `studio/history.py`: Enhanced UI with tabs, ecosystem dropdown, surface selector, surface cards, and live recommendation banner (0 external network assets); extended `StudioBuildHistory` to record ecosystem and surface metadata.
- Fourteen new focused tests in `test_ecosystem_pack_registry.py` and `test_studio_ecosystem.py`; `task verify` **3,055 passed** offline (+14 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-444 — Solution Pack Multi-Surface Ecosystem Pack Synthesis — DONE.
Implemented Solution Pack multi-surface ecosystem pack synthesis, packaging, CLI, and planner integration:
- `ecosystem_pack.py`: Defined `EcosystemPackPackage` bundle with `schema_version` (`"1.0"`), `ecosystem_id`, `version`, `display_name`, `description`, `domain`, `base_pack_id`, `surfaces`, and whole-ecosystem `package_sha256` checksum (`compute_ecosystem_checksum`); implemented `parse_ecosystem_pack_package` (strict validation, embedded `validate_ir` for all surfaces, digest verification, package integrity check, failing closed on corruption) and `verify_ecosystem_pack`.
- `ecosystem.py`: Implemented `_primary_entity_names_for_pack`, `_writable_entity_names_for_pack`, and `synthesize_surface_ir` to derive surface-scoped Application IRs sharing the pack's authoritative data model; updated `SurfaceApp` with `is_synthesized: bool = False`; enhanced `plan_ecosystem` to synthesize secondary surfaces when `pack_result` is provided.
- `ecosystem_cli.py`: Implemented CLI with `synthesize` (pack -> ecosystem pack JSON), `verify` (integrity & validity check), `inspect` (pretty metadata & surfaces printer), and `build` (materialize all surfaces into separate owned Git repos) subcommands; wired into `scripts/agent-engine.sh` and `Taskfile.yml` (`task agent-engine:solution-pack:ecosystem`).
- Eighteen new focused tests in `test_solution_pack_ecosystem.py`; `task verify` **3,041 passed** offline (+18 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-443 — Solution Pack Packaging, Verification, and Export CLI — DONE.
Implemented Solution Pack packaging, verification, CLI, and dynamic registry ingestion:
- `package.py`: Defined `SolutionPackPackage` bundle with `schema_version` (`"1.0"`), metadata, canonical IR digest, canonical `ir_dict`, verify plans, and whole-package SHA-256 checksum (`compute_package_checksum`); implemented `parse_solution_pack_package` (strict validation, embedded `validate_ir`, digest verification, package integrity check, failing closed on corruption) and `verify_package`.
- `registry.py`: Extended `SolutionPack` with `.package` reference and `from_package` constructor; extended `SolutionPackRegistry` with dynamic `register_package` capability ensuring no duplicate IDs, valid semver, and digest/target integrity.
- `package_cli.py`: Implemented CLI with `export` (stdout or file), `verify` (integrity & validity check), and `inspect` (pretty metadata printer) subcommands; wired into `scripts/agent-engine.sh` and `Taskfile.yml` (`task agent-engine:solution-pack:package`).
- Sixteen new focused tests in `test_solution_pack_package.py`; `task verify` **3,023 passed** offline (+16 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-442 — Studio AI-Delta Feature Modification Controls Above Solution Packs — DONE.
Implemented AI-delta feature modification controls in Studio across `server.py`, `live_serve.py`, `page.py`, and `history.py`:
- `server.py`: Extended `POST /api/build` to accept `ai_features` and `ai_delta_prompt` and pass them to the build pipeline.
- `live_serve.py`: Formulates typed `ai-delta` `SolutionPackChange` intents targeting capability areas; calls `generate_ai_delta_proposal` via the `ModelProvider` boundary (with async/sync compatibility) when AI features are requested; bypasses the model provider completely (0 model calls) when no AI features are requested; applies the proposal safely via `apply_solution_pack_manifest`; and records full provenance including `applied_ai_delta_change_ids`.
- `history.py`: Tracks `applied_ai_delta_change_ids` in `StudioBuildHistory`.
- `page.py`: Enhanced Studio UI with AI Feature Modifications input (`#ai-features`), full-width styling, synthesis status messaging, AI delta badge chips in history items (`.ai-delta-chip`), and applied AI delta provenance rendering; strictly 0 external resources in HTML.
- Four new focused tests; focused studio regressions **53 passed**; `task verify` **3,007 passed** offline (+4 net-new tests); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls in test execution.

Immediately preceded by R-441 — Live Studio Integration and UI Controls for Solution Pack Selection and Modification — DONE.
Implemented Studio integration across `server.py`, `live_serve.py`, `page.py`, and `history.py`:
- `server.py`: Added `GET /api/solution-packs` and `POST /api/solution-packs/recommend` endpoints; extended `POST /api/build` with `pack_id`, `pack_version`, `custom_name`, `custom_description`, and `configuration_changes` options.
- `live_serve.py`: Deterministically builds Solution Pack projects with 0 model calls via `create_solution_pack_manifest`, `apply_solution_pack_manifest`, and `build_solution_pack_project`, recording full provenance (pack id/version, base/derived digests, applied change IDs, verify targets).
- `history.py`: Tracks `pack_id` and `pack_version` in `StudioBuildHistory`.
- `page.py`: Enhanced Studio UI with pack select dropdown, real-time recommendation banner, customization inputs, verified pack chip, and provenance box; strictly 0 external resources in HTML.
- Eight new comprehensive tests; focused studio regressions **63 passed**; `task verify` **3,003 passed** offline (+8); lint, security, env, and both builder demos (152 / 149) pass; 0 model calls.

Immediately preceded by R-440 — Wire Derived Solution Pack Application IRs into Verified Multi-Repo Builder Pipelines and Project Generation — DONE.
Implemented `solution_packs/builder.py` and `solution_packs/build_cli.py`:
- `build_solution_pack_project()`: Assembles a Solution Pack derived `ApplicationIR` into an owned Git repository on disk using `assemble_project()` and `create_repository()`. Computes deterministic verification plans via `verify_plans_for_ir()`, and produces a frozen, byte-stable `SolutionPackBuildResult` tracking complete pack and repository provenance.
- `plan_ecosystem()` and `build_ecosystem()`: Extended with optional `pack_result` or `pack_manifest` (+ `pack_proposal`) arguments. Validates pack compatibility against ecosystem domain (raising `SolutionPackError` on mismatch), transparently substitutes the customer web surface with the pack-derived IR, and serializes pack provenance in the ecosystem plan.
- Standalone CLI & Taskfile: Added `build_cli.py` with full command-line options and `task agent-engine:solution-pack:build` integration.
- Eight new comprehensive tests; focused regressions **74 passed**; `task verify` **2,992 passed** offline; lint, security, env, both demos (152 / 149), and build CLI pass; 0 model calls.

Immediately preceded by R-438 — Bounded Typed Solution Pack AI-Delta Proposal Schema & Local ModelProvider Boundary — DONE.
Defined `solution_packs/ai_delta.py` with frozen `AIDeltaProposal` (`pack_id`, `pack_version`, `base_ir_sha256`,
`addressed_change_ids`, bounded `entities`, `apis`, `screens`, `capabilities`, `rationale`). Manifests with
zero AI deltas bypass the model provider completely (0 calls) and return an empty proposal. For pending AI
deltas, `build_ai_delta_messages` formulates system/user instructions embedding the base pack context and
pending change intents; `parse_ai_delta_proposal` strictly validates untrusted JSON, rejecting credential-bearing
fields (`password`, `secret`, `token`, `jwt`, `api_key`), entity name / API / screen collisions with base IR,
unknown/missing keys, controls, malformed types, and unmapped change IDs; `generate_ai_delta_proposal` issues
a single bounded `GenerateRequest` to `provider.generate()`. The proposal is data only and does not apply the
delta, mutate base IR, generate source, build repos, or invoke cloud models. Fifteen new tests; focused regressions
**52 passed**; `task verify` **2,970 passed** offline; lint, security, env, both demos (152 / 149), and
deterministic zero-call/mock inspection pass; 0 model calls.

Immediately preceded by R-437 — Deterministic Solution Pack configuration application — DONE.
Manifest schema 1.1 adds explicit bounded `desired_text` only for project-name/description updates while
legacy R-436 schema 1.0 remains losslessly readable. Application revalidates the exact pin, preflights all
configuration/duplicate targets, loads a fresh baseline, applies only those two allowlisted fields immutably,
and requires a valid derived IR. Unsupported configuration fails closed; AI-delta IDs stay pending. Frozen
canonical provenance includes base/derived digests, applied/pending IDs, and the derived IR. Repeated results
are byte-stable and registered baselines stay unchanged. Ten new tests; focused regressions **37 passed**;
`task verify` **2,955 passed** offline; lint, security, env, both demos (152 / 149), and deterministic proof
pass; 0 model calls.

Immediately preceded by R-436 — Pinned declarative Solution Pack customization manifests — DONE.
Selected exact recommendations become immutable, canonical, digest-pinned manifests of bounded intent.

Immediately preceded by R-435 — Exact-compatible Solution Pack recommendations in ecosystem planning — DONE.
Every ecosystem plan reports an exact pack id/version/digest/targets recommendation or explicit no-match.

Immediately preceded by R-434 — Versioned baseline Solution Pack registry — DONE.
The verified `minimal-blog` and `rideshare-favourites` IR examples are immutable, digest/target-pinned packs.

Immediately preceded by R-433 — Surface-specific ecosystem data and capability scoping — DONE.
Each ecosystem surface receives bounded entities, read/write capabilities, one actor role, relation-safe
dependencies, and role-gated mutations instead of a cloned full model.

Immediately preceded by R-432 — Opt-in model refinement for tailored ecosystems outside curated domains — DONE.
Known domains bypass the provider; unknown domains can explicitly use local Ollama through `ModelProvider`
for a strictly parsed proposal + typed entity model before the deterministic planner runs.

Immediately preceded by R-431 — Scope → Application IRs: materialize a multi-app ecosystem from one prompt — DONE.
New stdlib-only `intake/ecosystem.py` maps each proposed surface to a valid IR from curated domain entities
and repository-wired deterministic CRUD, then materializes the chosen scope as multiple owned Git repos.

Immediately preceded by R-430 — Ecosystem Scope Compiler: deterministic domain classification + multi-app
scope proposal — DONE. New stdlib-only `intake/scope_compiler.py` turns a business prompt into a framework-neutral
`ScopeProposal` (domain + confidence + matched keywords, actors, multi-surface ecosystem, Complete/
Customer-only/Custom options, ≤3 questions) via a curated 10-domain `DOMAIN_LIBRARY`, weighted-keyword
`classify_domain()`, and `propose_ecosystem()` (with a `custom-application` fallback). Pure/deterministic
(0 model/network), exported from `intake/__init__.py`. Deterministic CLI `intake/scope_propose.py` →
`task agent-engine:scope:propose -- "<prompt>"`: "Create a food delivery app …" → food-delivery (confidence
1.0) → Customer Ordering App + Merchant Portal + Courier Dispatch App + Super-Admin Dashboard + options +
2 questions. `tests/test_scope_compiler.py` (11 tests). `task verify` **2,888 tests** pass (offline; +11);
lint/security/env and both demos (152 / 149) pass; 0 model calls. NOT yet wired into IR/repo generation
(next brick). This is the first brick of the differentiating spine.

Immediately preceded by R-429 — Generated web app passes strict `tsc --noEmit`: component-library type cleanup — DONE.
Fixed **8** type-error classes at `codegen/nextjs.py` + the generated tsconfig so a generated `minimal-blog`
(was 84 errors: 4 `node_modules/next` from a missing `skipLibCheck` + 80 in our code across 19 files) AND
`rideshare-favourites` compile with **0** errors: G0 tsconfig `skipLibCheck: true`; G1 context-menu no longer
double-exports; G2 `displayName` allowed on sub-component aliases (`typeof XInner & { displayName?: string }`);
G3 typed compound for color-picker/pin-input (`…Base` cast to `typeof …Base & { Sub: … }`); G4 `Omit` the
conflicting inherited DOM attribute in Banner/Carousel/Checkbox/CodeBlock(+CopyButton)Props; G5 element ref
annotations `React.RefObject<T>` (was `<T | null>`); G6 terminal `variant` default `"default"`→`"minimal"`
(byte-identical render); G7 `SplitDiffRow.isUnchanged`; G8 the `api` object gains the `…WithCount` methods and
hooks forward a fresh `requestParams` with `...options` first (options no longer override params/abort signal).
Extended `task agent-engine:web-typecheck` to assert a clean `tsc` exit → **PASSED** for both examples. Added 4
regression guards to `test_generated_tsx_compile.py` and updated 7 hook/component test files' exact assertions.
`task verify` **2,877 tests** pass (offline); lint/security/env and both demos (152 / 149) pass; 0 model calls.

Immediately preceded by R-428 — Generated web app compiles: opt-in tsc typecheck gate + fix the bugs it
reveals — DONE. Added `task agent-engine:web-typecheck` (generate + pnpm install + `tsc --noEmit`; opt-in/live,
never in verify) and fixed the RUN-BLOCKING generated-code bugs it revealed (over-braced event handlers, a
`pdf-viewer.tsx` literal `\n`, and nested screen import depth via the `@/` alias at 24 sites). `task verify`
**2,873 tests** pass; both demos (152 / 149) pass; 0 model calls.

Immediately preceded by R-427 — Fix malformed single-brace inline styles in generated Next.js screens — DONE. Found via the
Studio live preview: the generated backend ran fine (`/posts` 200) but the Next.js web app returned HTTP 500
with an SWC syntax error (`Expected '</', got ':'`) on a single-brace JSX inline style. Root cause: 14 f-string
templates in `codegen/nextjs.py` (screen header role badges, `<h1>`/`<h2>` titles, detail `<dt>`/`<dd>` lists)
wrote `style={{ ... }}`, which Python collapses to single-brace `style={ ... }` in the emitted TSX; the fix
rewrites them to quadruple braces `style={{{{ ... }}}}` (→ valid `style={{ ... }}`). Only f-string lines were
changed (regular/raw component templates left untouched); no component template, screen layout, styling value,
or logic changed. Added a deterministic regression test (`test_generated_screen_styles.py`) that forbids any
single-brace object-literal inline style in generated `.tsx` — RED before, GREEN after — so it cannot recur.
`task verify` never caught it because it checks generated code as strings and never compiles the TSX. 3 focused
tests and `task verify`'s **2,870 tests** pass; lint, security, environment, and both demos (152 / 149 files)
pass; diff-invariance/snapshots unaffected; 0 local/cloud model calls.

Immediately preceded by R-426 — Remove a build from the Studio history — DONE. `StudioBuildHistory.remove(build_id) -> bool`
(thread-safe; drops the entry by id, returns whether it was present; unknown id is a safe no-op) plus a new
`POST /api/history/delete {id}` route (injected `delete_build_fn`, reusing the generic `_run_id_control` body
reader; unset -> 404, missing id -> 400). Because removing an entry only edits the bounded in-memory list (it
never runs generated code, touches the database, or deletes anything on disk), the delete handler is wired in
both Studio modes and returns the refreshed, bounded, secret-free history (`{removed, builds}`) so the page
re-renders in one call. The Studio page adds a per-build "Remove" action, DOM-only. Everything else — build,
preview, re-preview, open-folder, live status, status/stop/restart, collision-free ports, single-session
cleanup, PostgreSQL, `studio:serve`/`studio:preview` — is unchanged. 70 focused tests (6 net-new) and
`task verify`'s **2,867 tests** pass; lint, security, environment, and both demos (152 / 149 files) pass; a
deterministic remove/delete inspection confirmed True/False removal and a bounded secret-free payload;
0 local/cloud model calls.

Immediately preceded by R-425 — Per-build repo actions (copy path + open folder) — DONE. The Studio's Recent builds list
now has, per build, a purely client-side "Copy path" (clipboard write of the recorded repo `target_dir`, works
in both modes) and an "Open folder" action that opens the recorded repo directory in the OS file browser via a
new trusted-local route `POST /api/history/open {id}` (injected `open_dir_fn` + a generic `_run_id_control`
body reader shared with re-preview; wired only in trusted-local preview mode, build-only 404s). `live_serve`'s
`_open_path` launches the platform opener (darwin `open` / Windows `os.startfile` / else `xdg-open`,
best-effort, never raises or echoes a command); an unknown build id returns a bounded, secret-free error. The
opener is an opt-in/live path, injected/stubbed in tests. Build/preview/history/status/stop/restart,
collision-free ports, single-session cleanup, and PostgreSQL unchanged. 64 focused tests (4 net-new) and
`task verify`'s **2,861 tests** pass; lint, security, environment, and both demos (152 / 149 files) pass; a
deterministic open-route inspection (opener stubbed) confirmed bounded, secret-free opened/error/unknown
payloads; 0 local/cloud model calls.

Immediately preceded by R-424 — Live preview status (liveness-aware status + Studio polling) — DONE. `LocalAppSession.is_alive()`
reports whether a session is still running (not stopped and every owned background process alive), and
`StudioPreviewManager.status()` is now liveness-aware: under its lock it stops/forgets a dead active session
exactly once and reports a bounded, secret-free "stopped" state instead of a stale "ready". The Studio page
polls the existing R-422 `GET /api/preview` route every 5s while a preview is running and re-renders on change,
stopping the poll when not running and never reloading the embedded iframe when the URL is unchanged (no
flicker). No new routes, server signature change, or `live_serve` wiring change. Collision-free ports,
status/stop/restart + history controls, `studio:serve`/`studio:preview` semantics, single-session cleanup, and
PostgreSQL unchanged. 60 focused tests (7 net-new) and `task verify`'s **2,857 tests** pass; lint, security,
environment, and both demos (152 / 149 files) pass; a deterministic liveness/status inspection confirmed the
ready→stopped transition and secret-free payloads; 0 local/cloud model calls.

Immediately preceded by R-423 — Studio build history + re-preview a recent build — DONE. New dependency-free, thread-safe
`StudioBuildHistory` (stdlib only; in-memory ring capped at 10) records each successful build as a bounded,
secret-free entry (id, truncated prompt, name, entities, file_count, target_dir, commit_sha, created_at). The
stdlib Studio server gained `GET /api/history` (recent builds newest-first) and `POST /api/history/preview {id}`
(re-previews a recorded build's already-materialized repo through the R-422 `StudioPreviewManager`), wired via
optional injected handlers (unset → 404, missing/unknown id → bounded error). `live_serve` records every
successful build (both modes) and wires re-preview only in trusted-local mode. The Studio page adds a "Recent
builds" list that loads on start, refreshes after each build, and re-previews on click with `textContent` only.
Collision-free ports, status/stop/restart, `studio:serve`/`studio:preview` semantics, single-session cleanup,
and PostgreSQL unchanged. 53 focused tests (12 net-new) and `task verify`'s **2,850 tests** pass; lint,
security, environment, and both demos (152 / 149 files) pass; a deterministic history-payload inspection
confirmed bounded, newest-first, secret-free entries; 0 local/cloud model calls.

Immediately preceded by R-422 — Collision-free Studio preview ports + status/stop/restart controls — DONE. Each trusted-
local preview now allocates two distinct, currently-free loopback ports (`allocate_preview_ports` holds both
sockets open while reading their OS-assigned ports) and threads them through the R-419 run plan (and the
generated web app's `NEXT_PUBLIC_API_URL`) via a new `start_preview_app` boundary that delegates to the strict
`start_app`, so a preview never fails on, or clobbers, an existing `task app:run` app on 3000/8000 or a prior
preview. `StudioPreviewManager` (default `start_fn` now `start_preview_app`) gained bounded, JSON-safe,
secret-free `status()`/`stop()`/`restart()` (single remembered repo; restart re-previews it, idle no-op before
any build; stop is idempotent). The stdlib Studio server gained optional injected `status_fn`/`stop_fn`/
`restart_fn` → `GET /api/preview`, `POST /api/preview/stop`, `POST /api/preview/restart`, wired only in
trusted-local preview mode (build-only returns 404). The Studio page adds Stop/Restart controls + a live status
line without HTML injection. `studio:serve` stays build-only, `studio:preview` stays trusted-local,
single-session cleanup and PostgreSQL unchanged. 53 focused tests (15 net-new) and `task verify`'s **2,838
tests** pass; lint, security, environment, and both demos (152 / 149 files) pass; a deterministic payload/port
inspection confirmed distinct free ports and secret-free control payloads; 0 local/cloud model calls.

Immediately preceded by R-421 — Managed live generated-app preview inside the local Studio — DONE. New explicit
`task agent-engine:studio:preview` starts PostgreSQL, builds the owned repo, starts it through the R-419
run-plan boundary, waits for API/web readiness, and embeds the actual loopback Next.js URL in a sandboxed
iframe. `studio:serve` remains build-only. `LocalAppSession` owns cleanup; `StudioPreviewManager` serializes
replacement and returns bounded secret-free preview states without losing a successful build. Occupied
ports and exited children are rejected before they can create false readiness. All 38 focused tests and
`task verify`'s **2,823 tests** pass; lint, security, environment, and both demos pass. No model/generated
code ran in verification; 0 local/cloud model calls. The earlier user app on ports 3000/8000 was preserved.

Immediately preceded by R-420 — SQL-safe generated PostgreSQL identifiers and FK dependency ordering — DONE.
Generated DDL, fixture INSERTs, Python repositories, and Go stores now use the same defensively quoted
PostgreSQL identifiers without changing logical code or API names. Entity tables and fixture groups use
a stable FK topological order; independent entities keep source order, self-references work, and non-self
cycles fail with a deterministic `ValueError`. Seven focused safety tests and 186 related regressions pass;
`task verify` passes **2,808 tests**; lint, security, environment, and both builder demos pass. Representative
Python and Go output was syntax/formatted checked, and a reserved-name User/Order migration ran successfully
against local PostgreSQL inside a rollback-only transaction. No dependency, infrastructure, database-engine,
IR, or top-level-layout change; 0 local/cloud model calls.

Immediately preceded by R-419 — Turnkey local run (`omnistackai_agent_engine/localrun/`) — DONE, `task verify` (2,801
tests, 12 new focused R-419 tests) passing. Brick 4 of the front door: `build_run_plan(repo_dir, ...)`
inspects a generated repo and composes a deterministic, JSON-safe run plan (recreate a per-app Postgres DB,
apply migrations, start backend with `DATABASE_URL`/`JWT_SECRET`, start web with `next dev` directly +
`NEXT_PUBLIC_API_URL`); the opt-in executor `task agent-engine:app:run -- <dir>` (Task deps `db:up`) runs
setup, launches both servers, polls `/healthz`, prints URLs, cleans up on Ctrl+C. Verified END-TO-END on the
Mac: one command booted `~/omnistackai-blog-run` — Postgres up, DB recreated, both migrations applied,
uvicorn on :8000 (`/healthz` 200, `/posts` seeded), Next.js on :3000 (200). Fixed a real bug (`pnpm install`
→ `pnpm install --ignore-scripts`), and surfaced two pre-existing schema-generator bugs (unquoted
reserved-word identifiers; FK/table ordering) that only executing real migrations reveals → R-420. All
local, no paid cloud. Immediately preceded by R-418 — Chat studio web UI
(`omnistackai_agent_engine/studio/`) — DONE, `task verify` (2,789
tests, 11 new focused R-418 tests) passing. Brick 3 of the "chat → create an app" front door: a
dependency-free local web studio (Python 3.13 stdlib `http.server` only — no npm/pnpm). `page.py` serves a
self-contained HTML page (prompt box + Build button + results panel, inline CSS/JS); `server.py`'s
`create_studio_server(build_fn, ...)` handles `GET /` (page) and `POST /api/build` (`{prompt}` → injected
`build_fn` → JSON), with the build function injected so `task verify` tests the HTTP layer against an
ephemeral localhost server + in-memory stub (0 model calls); `live_serve.py` wires the real local-Ollama
build path (`task agent-engine:studio:serve`, default 127.0.0.1:4173). Added `app_build_result_to_dict` to
`intake/build_app.py`. Verified live on the Mac: studio served the page and `POST /api/build` with a
bookstore description → local Ollama → IR "Bookstore" (Book/Order) → a 154-file owned Git repo. All local,
no paid cloud. Immediately preceded by R-417 — Prompt → generated app repo
(`omnistackai_agent_engine/intake/build_app.py`) — DONE,
`task verify` (2,778 tests, 7 new focused R-417 tests) passing. Brick 2 of the "chat → create an app" front
door: `build_app_from_ir(ir, target_dir, ...)` composes `assemble_project` + `create_repository` into an
`AppBuildResult`, and `async build_app_from_prompt(prompt, provider, target_dir, ...)` chains the R-416
intake agent so a plain-English sentence → validated IR → assembled monorepo → real owned Git repo (depends
only on the vendor-neutral `ModelProvider` protocol; verify runs it against an in-memory stub into a temp dir,
0 model calls). Shared local-Ollama construction refactored into `intake/_ollama.py`; opt-in live builder
`task agent-engine:app:build -- "<description>"`. Verified live on the Mac: a "recipe box" description →
local Ollama (`qwen2.5-coder:14b`) → IR "Recipe Box" (Ingredient/Recipe) → a 154-file owned Git repo with
recipe-specific routes/screens. All local, no paid cloud. Immediately preceded by R-416 — Prompt →
Application IR intake agent (`omnistackai_agent_engine/intake/`) — DONE,
`task verify` (2,771 tests, 18 new focused R-416 tests) passing. The first brick of the user-facing "chat →
create an app" front door: `build_intake_messages` (schema-by-example system prompt + explicit allowed field
types), `parse_ir_response` (raw model text → validated, normalized `ApplicationIR`; tolerates ```json fences
+ prose), and `async generate_ir(prompt, provider, ...)` (single I/O step via the vendor-neutral
`ModelProvider` protocol → offline-testable with an in-memory stub, 0 model calls in verify). Ships
`IntakeResult`, `IntakeError`/`IntakeResponseError`, and an opt-in live runner
(`task agent-engine:intake:run -- "<description>"`). Verified live on the Mac: local Ollama
(`qwen2.5-coder:14b`) turned a plain-English task-tracker description into a valid Application IR that feeds
the existing code generators. All local, no paid cloud. Immediately preceded by R-415 — Generated Accessible
Futuristic Reusable Phone Number Input Suite (components/phone-input.tsx) — DONE,
`task verify` (2,753 agent-engine tests, 18 new focused R-415 tests) passing. A genuinely functional international phone field — a country
selector (ISO2 + dial code from a curated 20-entry `DEFAULT_COUNTRIES` table, overridable via a `countries` prop) paired with a national-number
input that strips non-digits (`replace(/[^0-9]/g, '')`), groups them loosely for display, assembles an E.164 string (`dial + digits`), and
validates by digit length (6..14); computes a meta object (`{country, dial, national, e164, valid}`); controlled + uncontrolled national value,
`defaultCountry`, `onChange(e164, meta)`, and WAI-ARIA (labeled country `<select>` + `<input type="tel" inputMode="tel">`, `aria-label`,
`aria-invalid` on invalid, `aria-required`); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`PhoneInputHandle`:
getValue/getE164/setValue/getCountry/clear/focus), alias exports (`PhoneInput`, `PhoneNumberInput`, `TelInput`, `PhoneField`, default) with
explicit `displayName`; 100% diff-invariance across `ir.description`, ASCII-only source (ISO codes + dial codes, no flag emoji), 0 external
runtime dependencies. Immediately preceded by R-414 — Generated Accessible Futuristic Reusable Duration Input Suite (components/duration-input.tsx)
— DONE, `task verify` (2,735 agent-engine tests, 18 new focused R-414 tests) passing. A genuinely functional duration field — segmented
days/hours/minutes/seconds inputs (configurable `units` via a `UNIT_SECONDS` table) converting to/from a single total-seconds value
(`toSegments`/`fromSegments`), with `min`/`max` clamping (normalizing on clamp), a `formatDuration` helper + live summary, controlled +
uncontrolled value (seconds), `onChange(totalSeconds)`, and WAI-ARIA (`role="group"` + per-segment `aria-label` + `inputMode="numeric"`); 4
variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`DurationInputHandle`: getValue/setValue/getFormatted/clear/focus), alias exports
(`DurationInput`, `DurationField`, `TimeSpanInput`, `IntervalInput`, default) with explicit `displayName`; 100% diff-invariance across
`ir.description`, ASCII-only source, 0 external runtime dependencies. Immediately preceded by R-413 — Generated Accessible Futuristic Reusable
Copy-to-Clipboard Button Suite (components/copy-button.tsx) — `task verify` (2,717 agent-engine tests, 18 new focused R-413 tests) passing. A genuinely functional copy button — copies a given value via
`navigator.clipboard.writeText` with a `document.execCommand('copy')` textarea fallback, shows a transient "Copied" state (configurable
`timeout`) with a swapped inline SVG icon (copy -> check) and an `aria-live` announcement, disables when there is nothing to copy, and exposes
`onCopy`/`onError`; WAI-ARIA (button `aria-label` + visually-hidden `aria-live` status); 4 variants, 3 sizes, `forwardRef` +
`useImperativeHandle` (`CopyButtonHandle`: copy/isCopied/reset/focus), alias exports (`CopyButton`, `CopyToClipboard`, `ClipboardButton`,
`CopyIconButton`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, ASCII-only source, 0 external runtime
dependencies. Immediately preceded by R-412 — Generated Accessible Futuristic Reusable Character & Word Counter Textarea Suite
(components/character-counter.tsx) — `task verify` (2,699 agent-engine tests, 18 new focused R-412 tests) passing. A genuinely functional counting textarea — live Unicode-safe
character counting (`Array.from` code points) and word counting (trim + whitespace split), configurable `maxLength`/`maxWords` with a computed
stats object (`{characters, words, remaining, overLimit}`), an optional hard limit that blocks input past maxLength, a warn threshold that
recolors near the limit, an optional progress bar, controlled + uncontrolled value, `onChange(value, stats)`, and WAI-ARIA (labeled textarea,
`aria-describedby` → a `role="status"` `aria-live` counter region); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle`
(`CharacterCounterHandle`: getValue/setValue/getStats/clear/focus), alias exports (`CharacterCounter`, `CharCounter`, `WordCounter`,
`TextCounter`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0 external runtime dependencies. Immediately
preceded by R-411 — Generated Accessible Futuristic Reusable Slug / URL Input Suite (components/slug-input.tsx) — `task verify` (2,681 agent-engine tests, 18 new focused R-411 tests) passing. A genuinely functional slug field — a `slugify()` helper
converts arbitrary text to a URL-safe slug in real time (Unicode NFKD normalization + `charCodeAt` filter stripping combining diacritics
`0x300`-`0x36f`, lowercase, non-alphanumeric runs collapsed to a configurable separator, leading/trailing separators trimmed); auto-sync from
an optional `source` prop until the user manually edits; an optional `prefix`/base URL with a computed full URL; copy-to-clipboard with copied
feedback; controlled + uncontrolled `value`; `maxLength`; `onChange(slug)` + `onCopy(fullUrl)`; WAI-ARIA (labeled input, `aria-label`,
`aria-live` copied announcement); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`SlugInputHandle`:
getValue/getFullUrl/setValue/slugify/clear/focus), alias exports (`SlugInput`, `Slugify`, `UrlSlugInput`, `PermalinkInput`, default) with
explicit `displayName`; 100% diff-invariance across `ir.description`, ASCII-only generated source, 0 external runtime dependencies. Immediately
preceded by R-410 — Generated Accessible Futuristic Reusable Password Generator Suite (components/password-generator.tsx) — `task verify` (2,663 agent-engine tests, 18 new focused R-410 tests) passing. A genuinely functional secure password generator — builds a
password from configurable character sets (uppercase/lowercase/numbers/symbols, optional exclude-ambiguous) using `crypto.getRandomValues`
(Uint32Array, `Math.random` fallback), guaranteeing one char per enabled set and shuffling with Fisher-Yates; a length slider, set toggles, a
strength meter, a read-only output, copy-to-clipboard (`navigator.clipboard.writeText` + `execCommand` fallback) with copied feedback, and a
regenerate action; SSR-safe (auto-generates on mount); `onGenerate`/`onCopy`; WAI-ARIA (`role="group"`, labeled controls, `aria-live` copied
announcement); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`PasswordGeneratorHandle`: generate/getValue/copy/setLength), alias
exports (`PasswordGenerator`, `PasswordCreator`, `SecurePasswordGenerator`, `PasswordMaker`, default) with explicit `displayName`; 100%
diff-invariance across `ir.description`, 0 external runtime dependencies. Immediately preceded by R-409 — Generated Accessible Futuristic
Reusable Currency / Money Input Suite (components/currency-input.tsx) — `task verify` (2,645 agent-engine tests, 17 new focused R-409 tests) passing. A genuinely functional money field — sanitizes typed input to
a clean numeric string, parses it (`parseFloat`), clamps to `min`/`max` on blur, and formats the value as locale-aware currency via the
built-in `Intl.NumberFormat` (`style: 'currency'`) when unfocused (plain numeric while focused for easy editing); configurable
`currency`/`locale` (default USD / en-US), `min`/`max`/`step`, `allowNegative`; controlled + uncontrolled value; `onChange(value|null,
formatted)` + `onBlur`; WAI-ARIA (labeled input, `aria-invalid`, `aria-required`, `inputMode="decimal"`); 4 variants, 3 sizes, `forwardRef`
+ `useImperativeHandle` (`CurrencyInputHandle`: getValue/getFormatted/setValue/clear/focus), alias exports (`CurrencyInput`, `MoneyInput`,
`CurrencyField`, `PriceInput`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0 external runtime
dependencies. Immediately preceded by R-408 — Generated Accessible Futuristic Reusable Color Contrast Checker Suite
(components/color-contrast.tsx) — `task verify` (2,628 agent-engine tests, 18 new focused R-408 tests) passing. A genuinely functional WCAG contrast tool — parses
foreground/background hex (`#rgb`/`#rrggbb`), computes WCAG 2.x relative luminance (`0.2126`/`0.7152`/`0.0722` + `Math.pow` gamma) and the
contrast ratio (`(lighter+0.05)/(darker+0.05)`), and evaluates AA/AAA pass-fail for normal text (>=4.5 / >=7), large text (>=3 / >=4.5), and
UI components (>=3); a computed `ContrastResult`; native color + hex inputs, a swap action, a live preview swatch, and pass/fail badges;
controlled + uncontrolled colors; `onChange`; WAI-ARIA (labeled inputs, `role="status"` `aria-live` results); 4 variants, 3 sizes,
`forwardRef` + `useImperativeHandle` (`ColorContrastHandle`: getRatio/getResult/setColors/swap), alias exports (`ColorContrast`,
`ContrastChecker`, `WcagContrast`, `ContrastRatio`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0
external runtime dependencies. Immediately preceded by R-407 — Generated Accessible Futuristic Reusable Credit Card Payment Field Suite
(components/credit-card.tsx) — `task verify` (2,610 agent-engine tests, 18 new focused R-407 tests) passing. A genuinely functional payment field — card-number, expiry
(MM/YY), CVC, and optional cardholder-name inputs with real-time formatting, IIN-prefix brand detection (visa/mastercard/amex/discover/
unknown), Luhn checksum validation, expiry validity (valid month + not past), and brand-aware CVC length; a computed meta
(`{brand, numberValid, expiryValid, cvcValid, complete}`); an optional live gradient card preview; controlled + uncontrolled value
(Partial); `onChange(value, meta)` + `onComplete`; WAI-ARIA (labeled inputs, `aria-invalid`, `inputMode="numeric"`, autoComplete cc-* hints);
4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`CreditCardHandle`: getValue/getMeta/clear/focus), alias exports (`CreditCard`,
`CreditCardField`, `PaymentCardField`, `CardInput`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0
external runtime dependencies. Immediately preceded by R-406 — Generated Accessible Futuristic Reusable Marquee / Ticker Suite
(components/marquee.tsx) — `task verify` (2,592 agent-engine tests, 18 new focused R-406 tests) passing. A seamless continuous scroller for arbitrary children
(news tickers, logo walls, announcement bars) that duplicates its content once for a seamless `-50%` loop, driven by CSS `@keyframes`
injected via an inline `<style>` (`omni-marquee-x`/`omni-marquee-y` with `animationDirection` for left/right/up/down); configurable
`durationSeconds`/`gap`/edge gradient fade (CSS `maskImage`); pause-on-hover plus a controlled `paused` prop and an imperative
pause/resume/toggle handle (`animationPlayState`); a CSS `prefers-reduced-motion` guard that stops the animation; accessibility (duplicated
copy `aria-hidden`, container `role="group"` + `aria-label`); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`MarqueeHandle`:
pause/resume/toggle/isPaused), alias exports (`Marquee`, `MarqueeTicker`, `ScrollingBanner`, `NewsTicker`, default) with explicit
`displayName`; 100% diff-invariance across `ir.description`, 0 external runtime dependencies. Immediately preceded by R-405 — Generated
Accessible Futuristic Reusable Mention / @-Autocomplete Textarea Suite (components/mention.tsx) — `task verify` (2,574 agent-engine tests, 18 new focused R-405 tests) passing. A genuinely functional textarea that detects a configurable
trigger char (default `@`) at the caret via a `detectTrigger()` helper, opens a filtered suggestion listbox from an `items` prop, supports
keyboard navigation (ArrowDown/ArrowUp/Enter/Tab to insert, Escape to close) plus mouse, inserts the chosen mention token and repositions the
caret (`requestAnimationFrame` + `setSelectionRange`), extracts the set of mentioned ids from the text, supports controlled + uncontrolled
`value`, and fires `onChange(value, mentions)` + `onMention` callbacks; ARIA combobox/listbox pattern (`aria-expanded`/`aria-controls`/
`aria-activedescendant`/`aria-autocomplete`; `role="listbox"`/`role="option"`/`aria-selected`); 4 variants, 3 sizes, `forwardRef` +
`useImperativeHandle` (`MentionHandle`: getValue/setValue/getMentions/focus/clear), alias exports (`Mention`, `MentionInput`,
`MentionTextarea`, `AtMention`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0 external runtime
dependencies. Immediately preceded by R-404 — Generated Accessible Futuristic Reusable Masked / Pattern Input Suite
(components/masked-input.tsx) — `task verify` (2,556 agent-engine tests, 18 new focused R-404 tests) passing. A genuinely functional token-based masked text input
(`9`=digit, `A`=letter, `*`=alphanumeric, other chars = literals) formatting in real time, with built-in presets
(phone/date/card/time/ssn via `PRESET_MASKS`) and custom masks; an `applyMask()` producing both the formatted display value and the raw
(unmasked) value plus a completeness flag; the caret kept at end after reformatting (`requestAnimationFrame` + `setSelectionRange`);
controlled + uncontrolled `value`; `onChange`/`onComplete` callbacks; `inputMode` pass-through; WAI-ARIA (`aria-label`, `aria-required`); 4
variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`MaskedInputHandle`: getValue/getRawValue/setValue/clear/focus), alias exports
(`MaskedInput`, `InputMask`, `PatternInput`, `FormattedInput`, default) with explicit `displayName`; 100% diff-invariance across
`ir.description`, 0 external runtime dependencies. Immediately preceded by R-403 — Generated Accessible Futuristic Reusable Password
Strength Meter & Requirements Suite (components/password-strength.tsx) — `task verify` (2,538 agent-engine tests, 18 new focused R-403 tests) passing. A genuinely functional password field with live rule-based
strength evaluation (empty/weak/fair/good/strong levels from the passed-rule ratio), a 4-segment strength bar, a live requirements checklist
(default rules: min length, uppercase, lowercase, number, symbol — overridable via a `rules` prop of `{id,label,test}`), a show/hide password
toggle (`aria-pressed`), controlled + uncontrolled `value`, `onChange`/`onStrengthChange` callbacks, SSR-safe rendering with a JS
`prefers-reduced-motion` guard on the bar transition, and WAI-ARIA semantics (`role="status"` + `aria-live` strength text, `aria-describedby`
wiring the input to the strength + requirements via `useId`); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle`
(`PasswordStrengthHandle`: getValue/setValue/getStrength/clear/focus), alias exports (`PasswordStrength`, `PasswordStrengthMeter`,
`PasswordInput`, `PasswordField`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0 external runtime
dependencies. Immediately preceded by R-402 — Generated Accessible Futuristic Reusable Cookie Consent & Preferences Manager Suite
(components/cookie-consent.tsx) — `task verify` (2,520 agent-engine tests, 18 new focused R-402 tests) passing. A genuinely functional (non-cosmetic) consent banner with a
compact view (Accept all / Reject all / Customize) and an expandable per-category preferences view using `role="switch"` toggles (required
categories forced on and disabled); `localStorage` persistence (`getItem`/`setItem` under a configurable `storageKey`, try/catch-wrapped) so
returning visitors are not re-prompted; SSR-safe (renders null until a `mounted` flag flips, stored consent read only after mount to avoid
hydration mismatch); configurable categories, title/description, optional privacy-policy link, and button labels; `forceShow` override;
`onAccept`/`onReject`/`onChange` callbacks; WAI-ARIA semantics (`role="region"` + `aria-label`, `role="switch"` + `aria-checked`); 5
placements; 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`CookieConsentHandle`: open/close/accept/reject/getConsent/reset),
alias exports (`CookieConsent`, `ConsentBanner`, `CookieBanner`, `ConsentManager`, default) with explicit `displayName`; 100% diff-invariance
across `ir.description`, 0 external runtime dependencies. Immediately preceded by R-401 — Generated Accessible Futuristic Reusable Countdown
Timer, Stopwatch & Live Clock Suite (components/countdown.tsx) — `task verify` (2,502 agent-engine tests, 18 new focused R-401 tests) passing. Three modes — countdown (to a `targetDate` or fixed
`duration`), stopwatch, and live clock (12h/24h) — driven by a real `setInterval` tick reading `Date.now()`, with SSR-safe mounting (a
`mounted` flag gives deterministic "--" first paint; real time only after mount to avoid hydration mismatch); day/hour/minute/second
segments with optional labels and configurable separator, `autoStart`, controlled + uncontrolled `paused`, `onComplete`/`onTick`
callbacks, a JS `prefers-reduced-motion` guard, WAI-ARIA semantics (`role="timer"`, `aria-atomic`, a visually-hidden `aria-live`
completion announcement); 4 variants, 3 sizes, `forwardRef` + `useImperativeHandle` (`CountdownHandle`:
start/pause/reset/restart/getTime/isRunning), alias exports (`Countdown`, `CountdownTimer`, `Stopwatch`, `LiveClock`, default) with
explicit `displayName`; 100% diff-invariance across `ir.description`, 0 external runtime dependencies. Immediately preceded by
R-400 — Generated Accessible Futuristic Reusable Before/After Image Comparison Slider Suite (components/image-comparison.tsx) —
`task verify` (2,484 agent-engine tests, 18 new focused R-400 tests) passing. A genuinely interactive (non-cosmetic) before/after
image revealer: an "after" base layer with a "before" layer clipped via CSS `clip-path`, a draggable divider with pointer capture,
click/tap-to-position, and a `role="slider"` handle with full keyboard control (Arrow keys by step, Home/End → 0/100, PageUp/PageDown by 10);
horizontal + vertical orientations; controlled + uncontrolled `position` with `onChange`; optional before/after labels; gradient placeholder
layers when no src; `disabled` state; WAI-ARIA 1.2 semantics (`role="group"` container, `role="slider"` handle with
`aria-valuemin`/`aria-valuemax`/`aria-valuenow`/`aria-valuetext`/`aria-orientation`); 4 variants, 3 sizes, `forwardRef` +
`useImperativeHandle` (`ImageComparisonHandle`: setPosition/getPosition/reset), alias exports (`ImageComparison`, `BeforeAfterSlider`,
`CompareSlider`, `ImageReveal`, default) with explicit `displayName`; 100% diff-invariance across `ir.description`, 0 external runtime
dependencies. Immediately preceded by R-399 — Generated Accessible Futuristic Reusable Particle Network & Interactive Constellation Canvas Suite (components/particle-network.tsx) —
`task verify` (2,466 agent-engine tests, 18 new focused R-399 tests) passing. Enabled an accessible, futuristic, zero-dependency
desktop-and-mobile-grade ambient particle/constellation canvas background across generated Next.js web applications (distinct from the
data-driven network-graph — no required data props): added a standalone, reusable Particle Network compound component suite
(`components/particle-network.tsx`) with internally-seeded particles (count derived from `count`/`density`, clamped 12–200) animated on an
HTML5 Canvas 2D `requestAnimationFrame` loop with edge-bounce motion, proximity link lines with distance-proportional `globalAlpha`,
pointer reactivity (gentle cursor attraction + accent-colored cursor links within `interactionRadius`), device-pixel-ratio-aware sizing,
a JS `prefers-reduced-motion` guard (single static frame, no rAF, live change listener — a net-new pattern since CSS reduced-motion cannot
stop a canvas loop), imperative `ParticleNetworkHandle` (`pause`, `resume`, `toggle`, `restart`, `isPaused`, `getCanvas`) via
`useImperativeHandle`, WAI-ARIA decorative semantics (wrapper `role="img"` + `aria-label`, `aria-hidden="true"` canvas, no focus trap),
4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyan glow),
3 size scales ("sm", "md", "lg"), React ref forwarding (`forwardRef`),
canonical TypeScript types (`ParticleNetworkVariant`, `ParticleNetworkSize`, `ParticleNetworkHandle`, `ParticleNetworkProps`),
compound and semantic alias exports (`ParticleNetwork`, `ConstellationCanvas`, `ParticleField`, `StarfieldBackground`, default export) with explicit `displayName`,
100% diff-invariance across `ir.description`, and 0 external runtime dependencies.
Preceded by R-398 (audio visualizer), R-397 (mind map), R-396 (log viewer), R-395 (network graph), R-394 (image gallery), R-393 (json viewer), R-392 (merge editor), R-391 (whiteboard), R-390 (video player), R-389 (audio player), R-388 (pdf viewer), R-387 (geo map), R-386 (file explorer), R-385 (audio recorder), R-384 (chat & real-time messaging suite), R-383 (spreadsheet & inline data sheet suite), R-382 (qr code & barcode suite), R-381 (terminal), R-380 (flow canvas), R-379 (gantt chart), R-378 (image cropper), R-377 (pivot table), R-376 (media player), R-375 (heatmap), R-374 (org chart), R-373 (diff viewer), R-372 (signature pad), R-371 (time picker), R-370 (chart), R-369 (filter builder), R-368 (virtual list), R-367 (kanban), R-366 (calendar), R-365 (markdown editor), R-364 (transfer), R-363 (tour), R-362 (sidebar), R-361 (notification center), R-360 (number input), R-359 (bottom nav), R-358 (combobox), R-357 (banner), R-356 (checkbox), R-355 (radio group), R-354 (kbd), R-353 (separator), R-352 (aspect ratio), R-351 (collapsible), R-350 (scroll area), R-349 (hover card), R-348 (context menu), R-347 (speed dial), R-346 (pin input), R-345 (color picker), R-344 (resizable), R-343 (carousel), R-342 (segmented control), R-341 (radial gauge), R-340 (code block), R-339 (tag input), R-338 (tree view),
R-337 (stat card), R-336 (timeline), R-335 (file upload), R-334 (stepper), R-333 (rating), R-332 (progress), R-331 (slider),
R-330 (command palette), R-329 (data grid), R-328 (date picker), R-327 (form controls), R-326 (dialog), R-325 (theme toggle),
R-324 (theming tokens), R-323 (popover), R-322 (dropdown menu), R-321 (accordion), R-320 (toggle), R-319 (avatar), R-318 (drawer),
R-317 (skeleton), R-316 (alert), R-315 (card), R-314 (tooltip), R-313 (column visibility), R-312 (badge), R-311 (table density),
R-310 (tabs), R-309 (pagination), and R-308 (JSON export).

**Notes:** R-437 is complete with 2,955 tests passing. The next proposed task is R-438: define a strict typed
AI-delta proposal schema plus an explicit opt-in local `ModelProvider` path that returns validated proposal
data only—no application, source generation, build, or cloud fallback—and its contract must be recorded first.









## Workflow note
Founder consolidated all work onto `main` (per-task branches deleted; `main` is the default). Continue
committing directly to `main` with the Tracker-ID discipline (contract -> tests -> gates -> tracker ->
commit tagged [R-###]).

## Milestone: first end-to-end builder slice complete + multi-target
`Application IR (R-225) -> framework adapter contract (R-226) -> Next.js code adapter (R-227) -> Git
service (R-228)` now turns a structured app spec into a real Next.js app inside a customer-owned Git
repo, fully offline and tested. Remaining slice steps — sandbox run, instant browser preview, deploy —
need a cloud/network-capable environment.

## In Progress (if any)
Tracker ID: none
Files touched so far: none
Blocker: none (R-224 Next.js upgrade remains deferred — env-blocked)

## Product direction
The model fabric (R-005..R-223) is the engine. The actual product (Emergent-class app builder) starts
with the vertical slice: **Application IR (R-225)** → framework adapter contract → Next.js code adapter
→ Git service → preview/sandbox (the last needs a cloud/network-capable environment).

## ID note
The workbook backlog already assigns R-010..R-219 (R-010 = Native iOS Agent, deferred until web/backend
stability). Founder-requested work uses unique IDs after R-219: R-220 = cloud streaming (done);
R-221 = cross-provider fallback (done); R-222 = platform console slice (done); R-223 = env-driven
fallback wiring (done); R-224 = Next.js console upgrade (deferred — environment-blocked).

## Next Up (queued, in order)
1. R-293 candidate — extend loading skeletons to the two remaining "Loading..." spots (form edit-mode
   initial load, detail record-selector "recent records" list), or another generated-app UX/robustness
   increment (skeletons now cover the collection table, subcollection lists, and detail main — R-292)
2. Live-verify the model fabric with the available Groq key (Balanced gateway → groq; real cloud
   inference + cost accounting) — set `GROQ_API_KEY` in the gitignored `.env`; may need a network machine
3. R-224 Next.js console upgrade and R-010 native iOS remain deferred under their existing gates
(The full offline builder AND the Tier 0-3 runtime/deploy wiring are complete: one IR ->
web+backend monorepo -> owned Git repo, plus a local preview provider and key-activated cloud
sandbox/deploy providers.)

## Decisions Made This Session
- Applied the normative V6 precedence rules and Section 91 Phase 0 sequence.
- Kept R-001 to repository/bootstrap metadata; no service, database, cloud, model, or mobile implementation was added.
- Added the V6-required `.ai/`, `.github/`, and `.cursor/` roots with explicit founder approval.
- Reconstructed only R-001 in the tracker with explicit founder approval; R-002 through R-009 remain unresolved.
- Installed the free Go Task CLI locally to exercise the canonical repository command contract.
- Reconstructed R-002 from the kickoff kit's explicit example with founder approval to continue.
- Bounded R-002 to local PostgreSQL+pgvector and migration tooling; Redis and all services remain out of scope.
- Pinned `pgvector/pgvector:0.8.6-pg18-trixie` and used PostgreSQL 18's major-version-aware data mount.
- Kept credentials in ignored `.env`; only placeholders are tracked.
- Reconstructed R-003 as the Stage 0 local Ollama foundation because it is required before cloud
  escalation and costs nothing beyond the existing laptop.
- Selected the already-pulled `qwen2.5-coder:14b` through configuration, not product hardcoding.
- Enforced loopback-only Ollama configuration and verified one real local inference with zero cloud calls.
- Reconstructed R-004 as the minimal Go control-plane foundation; Redis remains deferred until an
  implemented feature proves a cache, lease, rate-limit, or ephemeral coordination need.
- Used local `qwen2.5-coder:14b` for a bounded design review; no cloud model was called.
- Added only the control-plane as the second Compose service, with typed configuration, structured
  logs, bounded HTTP and database timeouts, graceful shutdown, and loopback-only host publishing.
- Verified stable liveness and PostgreSQL-backed readiness from the running container, plus unit and
  race-enabled tests; the container runs as the non-root `omnistackai` user.
- Reconstructed R-005 from the brief's explicit provider-registry handoff example and provider
  boundary rules; provider adapters and routing remain deferred to later Tracker IDs.
- Classified R-005 as L2. Two bounded local `qwen2.5-coder:14b` review attempts produced no
  capturable review text, so deterministic brief/repository evidence defines the task; cloud calls remain zero.
- Added immutable validated provider/model/capability/request/response/usage/health/stream records,
  a runtime-checkable async `ModelProvider` protocol, and a deterministic provider registry.
- Used only Python 3.13 standard-library functionality and added no adapter, provider SDK, runtime
  process, database change, Compose service, or infrastructure.
- Reconstructed R-006 as the smallest early Ollama provider required by the V6 MVP sequence.
- Bounded R-006 to a loopback-only native HTTP adapter, conservative model profiles, conformance
  tests, and an explicit live verifier; routing, cloud adapters, and orchestration remain deferred.
- Classified R-006 as L2. One bounded local `qwen3.5:9b` review call returned no capturable output;
  deterministic brief/repository evidence and official Ollama API documentation define the task.
- Added a standard-library-only `OllamaProvider` for native version health, allowlisted discovery,
  non-stream chat, and NDJSON streaming behind the accepted provider contract.
- Enforced Stage 0 loopback endpoints, proxy/redirect rejection, stable errors, finite timeouts,
  bounded bodies and concurrency, cancellation cleanup, output ceilings, and exact-digest evidence
  before a capability can be marked verified.
- Proved the adapter with 28 offline tests and two live `qwen2.5-coder:14b` calls: generation and
  streaming each produced 4 output tokens; no cloud provider was called.
- Reconstructed R-007 as the Balanced Model Gateway router, the third foundational model-boundary
  piece after the R-005 registry and R-006 adapter and the smallest next Stage 0/MVP dependency.
- Founder confirmed intent to support both API-key cloud providers and local Ollama, added one
  Tracker ID at a time; R-007 delivers the routing seam and defers the first cloud adapter to R-008.
- Router refuses L0 deterministic work, routes sub-L3 to local Ollama, returns escalation-required
  for L3/L4 (cloud unconfigured), guards a conservative context budget, and never silently falls
  back to a cloud model when the local provider is unavailable. Routing is deterministic; zero model
  calls were made to build or test it.
- Restored the declared `pnpm` (via corepack) and `ripgrep` toolchains that had regressed from the
  environment; no repository dependency was added. `task doctor` and `task verify` pass again.
- On founder instruction, added an opt-in live gateway runner (`task agent-engine:gateway:run`) and
  ran the platform locally through the Balanced gateway on both `qwen2.5-coder:14b` and `qwen3.5:9b`;
  added cloud API-key placeholders (names only) to `.env.example` for the R-008 provider decision.
- R-008: founder chose to configure every cloud provider (not just one), activated by API key, while
  running locally on Ollama until keys are added. Added standard-library HTTPS adapters (no vendor
  SDK) for Anthropic, OpenAI, Google Gemini, OpenRouter, and Groq behind the ModelProvider boundary,
  plus an env bootstrap that registers local Ollama always and each key-present cloud provider.
- Each cloud provider is key-activated with an overridable default model; keys are read only from the
  environment and never logged, stored, or shown. With no key, the platform stays local at zero cloud
  cost; `OMNISTACKAI_CLOUD_PROVIDER` selects the L3/L4 tier when a key is present.
- Evolved a stale R-005-era guard in `scripts/test.sh` (it forbade any provider adapter) to enforce
  the durable invariants instead — no vendor SDK import, gateway/cloud/bootstrap files exist, and
  cloud providers are opt-in defaulting to none — since cloud adapters are the sanctioned R-008 work.
- R-009: founder selected best-in-class usage & cost accounting. Added deterministic, privacy-safe
  accounting — immutable metadata-only usage records (no content/secret), a configurable Decimal
  price book (local Ollama zero, unknown unpriced), and an aggregating ledger (per-provider/model
  breakdowns, p50/p95 latency, cost per successful call). Gateway records one record per dispatch
  without altering results; the live runner prints a cost summary. Zero model calls to verify.
- R-220: founder asked to complete both true streaming and a second required item, one by one. Added
  true incremental Server-Sent-Events streaming for the cloud adapters (OpenAI-compatible, Anthropic,
  Gemini), reusing the HTTP-safety bounds; ordered delta events plus a final event with measured
  usage. Discovered the workbook backlog already owns R-010..R-219 (R-010 = Native iOS Agent), so new
  model-fabric tasks take unique IDs after R-219 (R-220 here) rather than overwriting a backlog row.

## Environment / Secrets Status
- Local Ollama: server 0.33.3 healthy on loopback; `qwen2.5-coder:14b` adapter health, discovery,
  generation, and streaming live-verified; `qwen3.5:9b` remains pulled but is not implicitly eligible
- Cloud keys configured: not inspected; no cloud provider API authorized or required for R-006
- Database: local container healthy via Colima; pgvector 0.8.6 and migration version 1 verified; no cloud database is authorized
- Control plane: local container healthy on `127.0.0.1:8080`; liveness `ok`, readiness `ready`
