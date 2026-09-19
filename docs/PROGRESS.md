# OmniStackAI — implementation progress (as of R-489)

A living summary of what is built, what is pending, and how to see results. Numbers come from the
execution tracker (`R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx`, `Phase_Roadmap`, 461 tasks as of
R-461 completion) plus the state files (`.ai/`), Git history, and CHANGELOG.

## Headline

- **3,729 automated tests pass** (agent-engine + Go control-plane), fully offline and
  network-independent (`task verify`), plus the console's own `typecheck`/`lint`/`build` gates.
- **R-489 — Runtime: free, self-hosted gVisor sandbox driver (2026-09-19):** fourth of the
  five-task sequence (R-486..R-490) — **replaces the originally planned WebContainers option**
  after real research found it requires a paid commercial license for any non-prototype use and
  only runs Node.js anyway. After comparing every candidate's real licensing (Vercel Sandbox/Fly/
  CodeSandbox: paid-only; raw Firecracker: free but a multi-quarter build-your-own-orchestrator
  project; E2B/Daytona: open source but self-hosting means running their full orchestrator;
  gVisor: genuinely free, open source, small lift), the founder approved gVisor, then asked two
  real follow-ups before continuing — resource cost and "why not use this in production instead
  of paying" — both answered directly: lightweight (~50MB binary, ~15-30MB RAM/sandbox), but a
  self-hosted loopback URL only works for a same-machine viewer; the managed providers' real value
  beyond isolation is a global public routing/proxy/scale layer this task doesn't build.
  Positioned explicitly as the free/dev tier, not a production replacement. A genuinely different
  transport (Docker's Unix socket, new `docker_socket.py`) and a real, necessary contract
  correction (relaxed `SandboxHandle`'s https-only URL validation to match `PreviewPlan`'s own
  loopback-or-https pattern). `active` is a live local capability check (is `runsc` registered?),
  not an env-var check. Docker's own image ecosystem covers Go, unlike Vercel Sandbox. No live
  gVisor/Docker daemon exists in this environment — live verification honestly deferred.
  `task verify` **3,729 OK** (22 new tests); repo gates all pass. See `.ai/tasks/R-489.md` for
  full detail.
- **R-488 — Runtime: real Daytona driver (2026-09-19):** third of the five-task sandbox sequence
  (R-486..R-490) — **all three sandbox providers the founder asked for (E2B, Vercel Sandbox,
  Daytona) now have real, tested, pluggable drivers behind one shared
  `SandboxLifecycleProvider` contract.** Daytona's API is shaped a third, genuinely distinct way:
  the create response carries no URL at all — a second real call,
  `GET /sandbox/{id}/ports/{port}/preview-url`, is required (verified against Daytona's real docs,
  including resolving a real base-URL ambiguity across their own pages). `create()` always
  requests `"public": true` since `SandboxHandle.url` has no room for a companion preview-token
  header. A real, honest tradeoff surfaced, not hidden: Daytona's documented default isolation is
  plain Docker containers, weaker than E2B/Vercel's Firecracker microVMs. No real
  `DAYTONA_API_KEY` exists in this environment — live-cloud verification honestly deferred.
  `task verify` **3,707 OK** (13 new tests); repo gates all pass; unlike R-487, no
  `providers.py`/`drivers.py` change was needed. See `.ai/tasks/R-488.md` for full detail.
- **R-487 — Runtime: real Vercel Sandbox driver (2026-09-19):** second of the five-task sandbox
  sequence (R-486..R-490), proving R-486's `SandboxLifecycleProvider` pattern is genuinely
  pluggable against a second, differently-shaped API, reusing `sandbox_http.py` completely
  unchanged. Verified against Vercel's real REST API (fetched directly): `POST/GET/DELETE
  /v2/sandboxes[/{name}]`, `Bearer` auth, a `routes[]` array giving each port's real URL directly
  (no pattern-guessing). A real, documented limitation surfaced honestly: Vercel Sandbox's runtime
  enum has no Go — `backend-go` is rejected with a specific typed error. Two real bugs found and
  fixed: an error-classification ordering bug (unknown target vs. unsupported-by-this-provider),
  and a registry/planning-stub consistency gap in `drivers.py` (one line fixed it). No real
  `VERCEL_TOKEN`/`VERCEL_PROJECT_ID` exist in this environment — live-cloud verification honestly
  deferred. `task verify` **3,694 OK** (14 new tests); repo gates all pass. See
  `.ai/tasks/R-487.md` for full detail.
- **R-486 — Runtime: real sandbox lifecycle contract + E2B driver (2026-09-19):** first of a
  five-task sequence (R-486..R-490) toward the founder's "Full isolation: per-user processes/
  sandboxes" direction. Research confirmed every serious 2025-2026 AI app-builder running real
  server-side code uses a managed microVM/gVisor sandbox provider — self-hosting Firecracker/K8s
  from scratch is a multi-quarter effort this project doesn't have headcount for. The founder's
  direction: build real, pluggable drivers for multiple providers (E2B, Vercel Sandbox, Daytona)
  switchable by cost/speed/smoothness, plus a free local-browser option. This task proves the
  pattern with E2B: new additive `SandboxHandle`/`SandboxLifecycleProvider` contract (create/
  status/kill — the existing `RuntimeProvider`/`PreviewPlan` is a pure planner and stays
  untouched), a new stdlib-only `sandbox_http.py` safety wrapper, and `E2BSandboxProvider`,
  verified against E2B's real documented REST API (fetched directly, not assumed). No real
  `E2B_API_KEY` exists in this environment — every gate is offline via an injected fake HTTP
  transport, and live-cloud verification is honestly deferred to a real key from the founder, not
  faked. `task verify` **3,680 OK** (22 new tests); repo `task verify`/`lint`/`security:quick`/
  `env:check` all pass. See `.ai/tasks/R-486.md` for full verification detail.
- **R-485 — Console: streaming build UI (2026-09-19):** fast-follow to R-484, closing the loop it
  opened. `/studio`'s own chat now consumes `POST /jobs/build/stream` for its create-path,
  replacing the static "Building…" wait with a real, live-updating "Generating your app… (N
  characters so far)" indicator. New `streamBuildApp()` returns the raw upstream `Response` so a
  new proxy route (`app/api/jobs/build/stream/route.ts`) can pipe it straight through unbuffered;
  `studio-chat.tsx` gains `sendBuildStream()` (fetch + manual SSE-frame parsing, not `EventSource`,
  since a POST body is required), handling three real frame shapes verified against R-484's own
  live output — `generating_ir` deltas (character count only; raw partial JSON is never shown to
  the user), `"done"` (unchanged final rendering), and a bare no-`phase` credits frame. Edit stays
  non-streaming per R-484's own scope boundary. **No browser-automation tool was available this
  session** — verified via `next start` + `curl` through a real cookie-based login session, the
  same request path a real browser takes. `pnpm run typecheck`/`lint`/`build` all clean (21
  routes, 1 new); repo `task verify`/`lint`/`security:quick`/`env:check` all pass (agent-engine
  untouched). Live: a real streamed build through the full console-proxy → Go control-plane →
  agent-engine path showed genuine incremental frames over ~9 real seconds, a real `done` frame
  (174 files, real commit sha), and a real trailing `credits` frame; a real follow-up edit on the
  same build confirmed the edit path is completely unchanged. See `.ai/tasks/R-485.md` for full
  verification detail.
- **R-484 — Backend: real-time build streaming, SSE (2026-09-19):** first of the founder's
  post-roadmap priorities ("streaming first, then scope isolation properly"), chosen after three
  parallel research passes (competitor streaming architecture, per-user isolation scoping,
  deploy/stack breadth). Replaces the one-shot blocking "Building…" wait with genuine incremental
  progress — backend only, console UI is R-485. New additive streaming twins
  (`generate_ir_stream`, `build_app_from_prompt_stream`, `_build_stream`) reuse the
  `ModelProvider.stream()` capability that already existed at the `model_gateway` layer but was
  never called above it; new `POST /api/build/stream` (agent-engine SSE) and
  `POST /jobs/build/stream` (Go control-plane, verbatim relay via `http.Flusher` + a trailing
  `credits` event once the real cost is known). Plain-prompt builds only — Solution Pack/
  Ecosystem/`hybrid_ui` cleanly rejected with a `400` before any SSE framing begins. **Two real
  bugs found and fixed, not glossed over**: (1) the SSE route sent `Connection: keep-alive`, which
  `BaseHTTPRequestHandler` treats as "never close this socket" — since there's no
  `Content-Length`/chunked framing, that hung every real client; fixed to `Connection: close`,
  caught by the first HTTP-level test. (2) `RecordingProvider` (the real usage-tracking wrapper
  every production build call goes through) had no `.stream()` method — every automated test
  mocked around it, so only the required live `curl -N` smoke test caught it; fixed with 4 new
  tests mirroring `generate()`'s own success/failure ledger-recording shape. `task verify`
  **3,658 OK** (27 new tests, 0 model/network calls); control-plane `go build`/`vet`/`test` all
  green (7 new tests, 55 total). Live: a real `curl -N` session through the real Go control-plane
  showed genuine token-by-token deltas over ~9 real seconds (timestamped, not buffered), a real
  `done` frame (177 files, real git commit sha), and a real trailing `credits` frame
  (`credits_spent: 0` — this environment's configured cloud model has no price-book entry, a
  pre-existing unrelated fact); all three unsupported build kinds confirmed rejected with a clean
  `400` before any SSE framing. See `.ai/tasks/R-484.md` for full verification detail.
- **R-483 — Fix: dynamic-route slug collision & duplicate FK identifier (2026-09-19):** second
  follow-up task after the 7-task Phase D roadmap shipped, per the founder's "complete one by one
  all" direction. Fixes a real, reproducible bug found live during R-481's own manual smoke test: a
  Next.js dev-server crash (`'counterId' !== 'counter_id'`) and a duplicate `lib/types.ts`
  identifier. Root cause verified by direct source read: the full-build and edit-delta prompts had
  an unreconciled casing mismatch for API `{param}`s, and `_entity_interface()` never checked for
  an already-declared field before synthesizing a relation's FK column. Fixed at the structural
  root — `ApiEndpoint.__post_init__` now canonicalizes every `{param}` to camelCase unconditionally
  (every construction path, not just the two known ones); `_entity_interface()` now skips the
  synthesized FK when an explicit same-named field exists. A pre-existing test's assertion (an old,
  inconsistent snake_case expectation) was updated, confirmed not a functional regression — the
  generated reader code already defensively checked the camelCase spelling as its own fallback.
  `task verify` **3,635 OK** (6 new tests). Live: reproduced the exact original scenario end to
  end — built the same counter app, sent the same edit, started the preview successfully (no
  crash, confirmed via the real log), one consistent dynamic route folder on disk, a real `tsc`
  check showing 0 duplicate-identifier errors, `lib/types.ts` inspected directly with no duplicate
  line. See `.ai/tasks/R-483.md` for full verification detail.
- **R-482 — Model Provider settings UI (2026-09-19):** first follow-up task after the 7-task Phase D
  roadmap shipped, per the founder's "complete one by one all" direction. A real, live Dyad-style
  provider status page. `platform_overview()` already existed (real, tested) but only ever
  generated a static snapshot for the public `/fabric` page — no live endpoint existed anywhere.
  New, never surfaced before: calling `resolve_generation_provider_from_env()` safely reports which
  provider would actually run the *next* build right now. New agent-engine `GET /api/providers`
  (build-only mode included); new control-plane `GET /jobs/providers` (no debit); new authenticated
  `/settings` page (live "Ready"/"Not ready" callout + provider table, linked from the Studio
  topbar and home page). **A real bug was found and fixed during this task's own live smoke test**
  (introduced by this task's own first draft, not a pre-existing platform issue): calling
  `platform_overview()` before `resolve_generation_provider_from_env()` read the providers list's
  "active" flags before `.env` had been lazily loaded — in a fresh process, every cloud provider
  showed "Needs key" even with a real key configured, while `activeNow` was correct. Fixed by
  reordering; verified with `env -i` (a clean environment) both reproducing and confirming the fix.
  `task verify` **3,629 OK** (4 new tests); control-plane `go test` all green (48 tests, 3 new);
  console `typecheck`/`lint`/`build` clean (20 routes, 2 new). Live: real `/api/providers` +
  `/settings` both correct; cross-verified `activeNow` against a real build whose own log confirmed
  the exact same provider (Groq) was actually used. See `.ai/tasks/R-482.md` for full verification
  detail.
- **R-481 — Tabbed workspace (2026-09-19): THE SEVENTH AND FINAL TASK of the founder-approved
  7-task Phase D roadmap (R-475–R-481) is complete.** Restructured `/studio`'s main pane into four
  real tabs — Preview, Files, Code, Problems — with chat persisting alongside, assembling R-474
  (files), R-477 (chat), R-479 (preview), and R-480 (problems) into one shell. Files and Code stay
  separate real tabs (founder's explicit choice), sharing one lifted `selectedFile`. New
  `code-highlight.ts`: a hand-rolled, dependency-free tokenizer porting the approach of
  `codegen/nextjs.py`'s own generated `tokenizeCodeLine` — no new dependency, confirmed live it
  renders real generated TSX cleanly. Problems tab is an explicit on-demand button per R-480's own
  design. `task verify` **3,625 OK**; console `typecheck`/`lint`/`build` clean (19 routes, 1 new).
  Live: full loop confirmed — build → real Preview/Files/Code → real edit → confirmed Files/Preview
  refresh → real Problems check. A real, pre-existing codegen bug was found live (a dynamic-route
  slug collision from the edit-delta path, unrelated to this task) — correctly surfaced as an
  honest Preview error *and* independently caught by a real Problems check (18 genuine TypeScript
  errors), cross-confirming both R-479's and R-480's error-surfacing design work under real failure
  conditions. **The Studio is now a real chat-driven, multi-pane workspace closer to
  Lovable/Dyad/Emergent parity than at the start of this roadmap.** No pre-approved task remains
  queued — see `.ai/tasks/R-481.md` for full verification detail and named follow-ups.
- **R-480 — Backend: Problems/compile-report support (2026-09-19):** sixth of the seven. Real
  compile-error reporting for the first time in this codebase — the founder's explicit choice over
  a placeholder. New `studio/problems.py` mirrors `files.py`'s shape: resolves `apps/web`, raises
  `NoWebTargetError` if there's no web app, remaps `verify/compile.py`'s real
  `compile_web_project()`'s `VerifyError` into a clear `ToolchainNotInstalledError` — never
  silently installs dependencies. On-demand, not automatic (`node_modules`/`tsc` only exist after a
  preview install). `StudioProblemsStore` is a bounded per-build-id LRU cache mirroring
  `StudioSessionStore`. New control-plane routes `POST`/`GET /jobs/build/{id}/problems`, no credit
  debit, a new `defaultProblemsTimeout` (90s), a new 409 status for "toolchain not installed."
  `task verify` **3,625 OK** (21 new tests, no real toolchain needed); control-plane `go test` all
  green (45 tests, 7 new). Live: build-only mode with no toolchain produced real 409/404, no crash;
  along the way hit two real, pre-existing environment issues unrelated to this task (a
  generated-migration collision, a 500ing preview page) worked through honestly; preview mode with
  a real installed toolchain surfaced **10 genuine TypeScript errors** via a real `tsc` run in an
  LLM-synthesized page — real compiler output that also explained the runtime 500; a repeated GET
  returned the byte-identical cached report in 12ms. See `.ai/tasks/R-480.md` for full verification
  detail.
- **R-479 — Console: live preview UI (2026-09-19):** fifth of the seven. An iframe rendering the
  real running generated app, wired to R-478's four routes. Preview start is synchronous, so
  polling's job is crash detection (5s interval while `status: "ready"`), not progress-watching.
  New `studio-preview.tsx` triggers a re-preview whenever `buildId` becomes real or a
  `previewVersion` counter (bumped after every edit, since `_edit()` never restarts the preview)
  changes; a 404 renders an honest disabled message; manual Restart/Stop reuse icons that existed
  unused since R-475. Every `PreviewStatus` shape verified by reading `preview.py` directly.
  `task verify` **3,604 OK**; console `typecheck`/`lint`/`build` clean (18 routes, 4 new). Live: real
  control-plane + real agent-engine Studio server in preview mode proved build → real iframe-ready
  preview (fetched the real `web_url` directly, got genuine HTML) → edit → real re-preview on a new
  port → the real preview OS process was killed directly to simulate an external crash, and the
  next poll correctly reported "stopped" → manual Restart/Stop both worked → build-only mode
  produced the uniform honest 404 disabled state. See `.ai/tasks/R-479.md` for full verification
  detail.
- **R-478 — Backend: live preview proxy, local-only (2026-09-19):** fourth of the seven. Four new
  control-plane routes proxying the agent-engine's existing trusted-local preview control surface
  verbatim: `GET /jobs/preview`, `POST /jobs/preview/stop`, `POST /jobs/preview/restart` (the
  singleton surface) plus `POST /jobs/build/{id}/preview` (the build-scoped one, server-constructing
  its own `{"id": id}` body rather than trusting the caller's). All auth-required, no credit debit,
  zero agent-engine changes. Verified, not assumed: an unknown build's build-scoped preview route
  returns a real 200 `{"status":"error"}`, not a 404 — the proxy forwards it unchanged. New
  `defaultPreviewTimeout` (60s) applied to both `handleBuildPreview` and `handlePreviewRestart`
  (both can trigger a real cold start). `task verify` **3,604 OK**; control-plane `go test` all
  green (38 tests, 13 new). Live: real control-plane rebuilt + real agent-engine Studio server in
  preview mode proved a real build auto-starting a real preview, real
  status/stop/restart/build-preview proxying, the 200-with-error shape confirmed live for an
  unknown build, unchanged credit balance across all four calls, and uniform 404s against
  build-only mode. See `.ai/tasks/R-478.md` for full verification detail.
- **R-477 — Console: chat UI (2026-09-19):** third of the seven. Replaced `/studio`'s one-shot
  prompt form with a persistent, multi-turn chat thread on R-475's shell, wired to R-476's new
  routes. `buildId` (`null` vs. set) is the single piece of state deciding whether the composer
  calls `/jobs/build` or `/jobs/build/{id}/edit`. New `studio-chat.tsx` + `studio-workspace.tsx`
  (the latter holding the `BuildResult`/`FileBrowser` pieces moved out of the retired
  `studio-form.tsx`, generalized to a `WorkspaceSnapshot`). `buildId` persists in the URL so a
  refresh hydrates chat text history from `/turns` — the workspace panel does not rehydrate, an
  honest, named simplification. A real finding, verified by source read before implementation: `GET
  /turns` does not 404 for an unknown build (`{"turns": []}` instead) — only `_edit()`'s
  `BuildNotFoundError` is a real 404, so the "session no longer available" recovery is wired there.
  `task verify` **3,604 OK**; console `typecheck`/`lint`/`build` clean (14 routes, 2 new). Live: real
  control-plane + real agent-engine Studio server + fresh `next start` proved build → turns hydration
  → follow-up edit with a refreshed file list, then the agent-engine Studio server was killed and
  restarted mid-test to simulate a real stale session — the edit-triggered 404 recovery and the
  turns-hydration honest-empty-thread finding both confirmed live, then a fresh build proved the
  full recovery loop. See `.ai/tasks/R-477.md` for full verification detail.
- **R-476 — Backend: multi-turn edit bridge (2026-09-19):** second of the seven. New control-plane
  routes `POST /jobs/build/{id}/edit` and `GET /jobs/build/{id}/turns`, mirroring
  `POST /jobs/build`'s exact proxy+debit shape (R-472), plus two real, verified fixes to the Python
  edit path found during this roadmap's planning research: `_edit()` had no `usage_ledger` at all
  (every edit debited 0 credits regardless of real cost); `_build()` never recorded its own chat
  turn (only `_edit()` did, so a chat hydrating history from `/turns` after a refresh would lose the
  first message). Both fixed by mirroring `_build()`'s own existing patterns. Go side extracts a
  shared `proxyAndDebit` helper out of `handleBuild`, reused by the new `handleBuildEdit`. A no-op
  edit still charges real credits — locked in by a dedicated test. `task verify` **3,604 OK**;
  control-plane `go test` all green (25 tests, 10 new). Live: a real build's own turn now appears in
  `/turns` before any edit, and a real edit produced a genuine second git commit plus, for the first
  time, a real `"usage"` key on the edit response — both honestly `credits_spent: 0` since this
  environment's real configured cloud model has no price-book entry (a pre-existing, unrelated
  fact); the "debits a nonzero charge" behavior is proven by the new unit tests instead. See
  `.ai/tasks/R-476.md` for full verification detail.
- **R-475 — Studio visual foundation (2026-09-19):** first of a founder-approved, fully-researched
  7-task plan (R-475–R-481, saved at `/Users/sanjeet_kumar/.claude/plans/hi-fancy-shannon.md`,
  mirrored in the kickoff doc's "Remaining Phase D roadmap") to take the Studio from
  functionally-real-but-plain toward a genuinely rich, chat-driven, multi-pane workspace. Planning
  used full plan-mode discipline (two Explore agents, a Plan agent, direct source verification of
  the most consequential claims) and two direct founder decisions: Problems (compile errors) gets
  built for real via its own task rather than a placeholder, and Files/Code stay as two separate
  tabs. This task: a new `app/studio/layout.tsx` takes over the auth gate and persistent top-bar
  chrome later tasks build on; `globals.css` gained additive design tokens; a new hand-rolled
  icon set avoids a new npm dependency. No backend changes. `task verify` **3,603 OK**; live:
  real control-plane + real agent-engine Studio server + a fresh `next start` proved the auth gate,
  new shell, and unaffected sibling pages. See `.ai/tasks/R-475.md` for full verification detail.
- **R-474 — file browser in the console Studio (2026-09-18):** continues Phase D. Each filename in
  a build result panel is now a clickable button showing real generated file content in a
  read-only viewer, bridged through two new authenticated control-plane proxy routes
  (`GET /jobs/build/{id}/files`, `GET /jobs/build/{id}/file?path=...`) to the agent-engine's
  existing R-467 file-serving endpoints — no agent-engine changes, no credit debit for browsing.
  Honest, named limitation carried over unchanged from R-467: the Studio server has no per-user
  build scoping. This session began with the founder asking to see the platform running before
  continuing Phase D; the live demo stack was brought up, shown, and left running per the
  founder's request — this task's own implementation continued and was verified against that same
  stack. See `.ai/tasks/R-474.md` for full live-verification detail.
- **R-473 — Studio v1 in the console, build an app from the product (2026-09-18):** Phase D of
  `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, first slice. A logged-in user can now open
  `apps/console-web`'s new `/studio` page, type a plain-English app description, click Build, and
  get a real app built through R-472's real Job API, with the console showing the real post-debit
  credit balance. Deliberately scoped small — no file browser, live preview, or chat yet — matching
  how the agent-engine's own hybrid-UI engine shipped across four separate gated Tracker IDs
  (R-465–R-468) rather than one large task; those capabilities are named follow-ups, not silently
  dropped. No control-plane or agent-engine changes. Live proof: a real Docker control-plane + a
  real agent-engine Studio server on local Ollama + a real `next start` console proved the auth
  gate, a genuine (unforced) local-model failure rendering as a real error banner, and a genuine
  successful 157-file build with every field matching the UI's expectations. See `.ai/tasks/
  R-473.md` for full live-verification detail.
- **R-472 — bridge the control-plane's Job API to the agent-engine, real credit debiting
  (2026-09-18):** Phase C of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`. The
  control-plane's new `POST /jobs/build` authenticates the caller, proxies verbatim to the
  agent-engine's real plain-prompt build path, and debits real credits from the actual dollar cost
  the agent-engine now reports (a new, additive `model_gateway.RecordingProvider` decorator closes
  a real gap found while researching: that build path bypassed the gateway's own real-but-demo-only
  `UsageLedger` entirely). New Go pieces: `auth.RequireUser`, a row-locked and clamped
  `users.Store.DebitCredits` (v1 policy — never block a build, only clamp the charge), and the new
  `internal/jobs` package. A real bug was caught by the new tests before any commit; a real
  infrastructure bug (the control-plane's global `WriteTimeout` killing a slow build's connection)
  was found only by the live smoke test and fixed with a per-request write-deadline extension. Live
  proof: a real Docker Postgres+control-plane, a real local Ollama build produced a real 161-file
  repo with correctly-zero cost/credits (local usage is credit-exempt by price); the real
  `DebitCredits` row-lock/clamp path was proven separately against the same live Postgres. See
  `.ai/tasks/R-472.md` for full live-verification detail.
- **R-471 — fixed a real dev-mode hydration bug + added Name to registration (2026-09-17):** the
  founder's own first live try of the R-470 console hit a real bug — Next.js 16 blocks
  cross-origin access to its dev/HMR resources by default and treats `127.0.0.1`/`localhost` as
  different origins, so opening the console at `127.0.0.1` (as instructed) meant client JS never
  hydrated and the register form silently fell back to a native GET submission. Fixed with
  `allowedDevOrigins`. Also added a required Name field to registration (a new, additive
  migration) — explicitly declined to add Gender or Age, which serve no function in this
  product's roadmap. See `.ai/tasks/R-471.md` for full live-verification detail.
- **R-470 — real Next.js console-web, wired to R-469's auth API (2026-09-17):** Phase B of
  `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`. The static `apps/console-web` is now a
  real Next.js (App Router, TypeScript) app: `/login`/`/register` pages, an authenticated `/` home
  page (profile + credit balance), and `/fabric` carrying the old model/cost overview forward on
  the same `data/overview.json` contract. Session handling is a server-side cookie proxy
  (`app/api/auth/*` Route Handlers) — the raw token never reaches client-side JS, no CORS needed.
  No new UI dependency beyond React/Next.js itself. Found and fixed five real ecosystem
  compatibility issues while implementing (pnpm fetch timeouts, `typescript@7`/`typescript-eslint`
  incompatibility, an ESLint `FlatCompat` crash, pnpm 11.19 moving build-script allowlisting to
  `pnpm-workspace.yaml`, and — most importantly — a `Secure`-cookie-over-HTTP bug that would have
  silently broken login in a real browser). A real Docker Compose control-plane + a real `next
  start` server proved the full register → home → fabric → logout → login round trip live, twice.
- **R-469 — control-plane foundation: users, auth, plans, credits (2026-09-17):** Phase A of
  `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` — the founder's decision to advance from the
  Stage-0 static console/stdlib Studio prototype toward the real commercial platform (Next.js console
  over a Go control-plane, per Implementation Brief Section 33). The existing `services/control-plane`
  Go skeleton (health-check-only before this task) now has real users, authentication, and a
  plan/credit model: two roles only (`super_admin`, `user` — a user's access is gated entirely by
  `plan`, reusing the Brief Section 22 tier names `free`/`developer`/`pro`/`agency`/`enterprise`,
  `byok` an add-on flag); every signup gets `free` plus a starting credit grant recorded in an
  append-only `credit_ledger`. New migration `000002_users_auth_billing` applied by a new self-healing
  embedded migration runner (replays every idempotent migration file on every boot — necessary because
  `docker-entrypoint-initdb.d` only runs against a brand-new Postgres volume). Password hashing is
  PBKDF2-HMAC-SHA256 on Go stdlib only — zero new `go.mod` dependency. Four new endpoints
  (`/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`); login failure is a generic 401 with
  no email-enumeration timing leak, proven both in unit tests and against a real running Docker
  container (register → login → me → logout → me-after-logout, real PostgreSQL). No frontend, no
  agent-engine bridge, no payment processor yet — those are Phases B/C/E, separate Tracker IDs.
  `studio/page.py` is untouched — still the agent-engine's own local proof harness, not the product UI.
- **R-468 — multi-turn chat / "continue editing this app" (2026-09-17):** a follow-up prompt ("add a
  favorites feature") now lands as a real second commit on the same owned repo. New `intake/app_delta.py`
  is a generic, non-pack-coupled sibling of `solution_packs/ai_delta.py`: a bounded, validated delta (new
  entities/apis/screens only) merged onto the app's tracked IR by tuple concatenation, backstopped by
  `ApplicationIR`'s own validation and a retry loop mirroring R-465's repair idiom. The diff/commit half
  needed zero changes — `edit/diff.py::plan_edit` + `edit/apply.py::commit_edit` (already proven
  end-to-end) turn the delta straight into a git commit. New `studio/session.py`'s bounded, server-only
  `StudioSessionStore` tracks each editable build's current IR; `POST /api/build/{id}/edit` +
  `GET /api/build/{id}/turns` and a small chat box in the Studio page. v1 is additive-only (renaming/
  removing existing structure is rejected, never merged); Solution Pack and multi-surface Ecosystem builds
  get an honest "not supported" error rather than a silent no-op. See `docs/CHAT_EDIT.md`.
- **R-467 — the hybrid engine reaches the product UI (2026-09-17):** the Studio a user actually opens in a
  browser (`task agent-engine:studio:serve`/`:preview`) gets a read-only file browser
  (`GET /api/build/{id}/files` / `.../file?path=...`, a new pure `studio/files.py` with `edit/apply.py`-style
  path safety; the flat file list is now clickable, opening a viewer pane) and a "Hybrid UI (experimental)"
  toggle on `/api/build` that threads R-465's `synthesize_screens`/`ui_outcomes` into the plain-prompt and
  Ecosystem Pack build paths (Solution Pack builds report `hybrid_ui_active: false` honestly — no such
  parameter exists there). While implementing, found and fixed a live, active violation of the "0
  model/network calls under `task verify`" constraint: with real Groq credentials now in the gitignored
  `.env` (from the R-465/R-466 live proofs), four pre-existing Studio test call sites that never mocked
  `resolve_generation_provider_from_env` were making real network calls during `task verify` (confirmed by
  timing — one unmocked test took 23.5s of real, R-466-paced Groq traffic before giving up). All four now
  mock it explicitly.
- **R-466 — the hybrid engine compiles what the model wrote and paces rate limits (2026-09-17):** a
  capturing `tsc` executor turns compiler diagnostics into per-file errors; each LLM-written file's errors go
  back to the model through the same corrective channel, still-failing files revert to their templates, the
  repair is applied as a `ProjectDiff` and committed — deterministic files are never rewritten. HTTP 429 is
  typed and paced from the provider's own `Retry-After` (env-tunable cap); a request rejected as too large
  shrinks to a compact grounding and retries; every failed call's HTTP status is in the outcome record. Live
  (Groq free tier): the 3-step CLI ran end-to-end with the fallback repo compiling at 0 errors; pacing was
  verified live; the day's proofs hit the tokens-per-day cap. Next: R-467 product-UI shell.
- **R-465 — the HYBRID UI engine is grounded (2026-09-17):** the LLM writes the modern UI over the
  deterministic, typed data layer — the prompt embeds the REAL generated hooks/types/api (parsed from the same
  generators, so it cannot drift), the real component exports, and the real design tokens — with a bounded
  validation→feedback→retry loop and a deterministic template fallback; an explicit `synthesize_screens`
  switch (default off; default output byte-identical) and the opt-in `task agent-engine:ui:synthesize`. See
  `docs/HYBRID_UI.md`. Live proof with the founder's Groq key ran honestly into the free tier's 8k TPM limit:
  validation → repair → rate-limited → graceful fallback (a full LLM-page-compiles proof needs a Gemini key or
  Groq Dev tier). Next: R-466 compile-level repair + 429 pacing; R-467 product-UI shell.
- **250 tracker tasks Done, 1 Deferred, 210 Not Started** across **461 tasks** in the execution tracker
  (`R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx`, `Phase_Roadmap`). MVP completion: **250 / 356 = 70.2%**. Overall program completion: **250 / 461 = 54.2%**.
- **103 tasks (R-359 → R-461) formally tracked in the tracker workbook**:
  Rows inserted into `Phase_Roadmap` with full column data and audit evidence so the workbook remains the single authoritative tracker.
- **Built tasks include**: 57 reusable UI-component suites,
  four front-door bricks, R-420 generated-SQL hardening, R-421 managed embedded local preview,
  R-422 collision-free preview ports + status/stop/restart controls, R-423 build history + re-preview,
  R-424 live preview status, R-425 per-build repo actions, R-426 remove-from-history, R-427 a
  generated-JSX inline-style fix, R-428 generated-app compile fixes + an opt-in `tsc` gate, R-429
  strict-type cleanup so a generated app passes `tsc --noEmit` clean, **R-430 the Ecosystem Scope
  Compiler**, **R-431 Scope → Application IRs** (one prompt → multiple owned, clean-compiling app
  repos), **R-432 opt-in unknown-domain refinement**, **R-433 surface-specific data/capability
  scoping**, **R-434 immutable baseline Solution Packs**, **R-435 exact-compatible pack planning
  recommendations**, **R-436 pinned declarative customization manifests**, **R-437 deterministic
  configuration application**, **R-438 bounded typed AI-delta proposal schema**, **R-439 safe
  application of validated AI-delta proposals to Application IR**, **R-440 verified multi-repo
  builder pipelines and project generation with Solution Pack derived IRs**, **R-441 live Studio
  integration and UI controls for Solution Pack selection, customization, and provenance**, **R-442 Studio
  AI-delta feature modification controls above Solution Packs**, **R-443 Solution Pack Packaging,
  Verification, and Export CLI**, **R-444 Solution Pack Multi-Surface Ecosystem Pack Synthesis**,
  **R-445 Solution Pack Ecosystem Pack Registry Integration, Catalog Discovery, and Studio Multi-Surface Selection**,
  **R-446 Solution Pack Ecosystem Studio Live Multi-Surface Preview and Process Orchestration**,
  **R-447 Solution Pack Ecosystem Multi-Surface Cross-App Auth and Unified State Binding**,
  **R-448 Solution Pack Ecosystem Cross-Surface Webhook and Event Bridge**,
  **R-449 Solution Pack Ecosystem Cross-Surface Telemetry, Audit Trails, and Distributed Tracing**,
  **R-450 Solution Pack Ecosystem Multi-Surface Export, Deployment Manifest, and Live Gateway Orchestration**,
  **R-451 Solution Pack Ecosystem Cross-Surface Data Sync, Conflict Resolution, and Offline-First Sync Protocol**,
  **R-452 Solution Pack Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration**,
  **R-453 Solution Pack Ecosystem Comprehensive Multi-Surface Health Check, Smoke Testing, and Canary Verification**,
  **R-454 Solution Pack Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration**,
  **R-455 Solution Pack Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting**,
  **R-456 Solution Pack Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies**,
  **R-457 Solution Pack Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts**,
  **R-458 Solution Pack Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts**, and
  **R-459 Solution Pack Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts** —
  the first thirty bricks of the differentiating spine.
  The generated Next.js component library remains at **110 components**; its series is **PAUSED at R-415** and fully resumable.
- **R-459 adds Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts:**
  `DocPage`, `RunbookStep`, `ArchitectureRunbook`, `OpenAPIRoute`, `OpenAPIAggregationEntry`, `AggregatedAPISpec`, and `EcosystemDocsContract` formalize multi-surface documentation, architecture runbooks, and aggregated OpenAPI 3.1 specifications with deterministic SHA-256 digests and JSON roundtrips;
  `synthesize_ecosystem_docs` deterministically derives platform overview, data-flow, security pages, surface-specific architecture pages, operational runbooks (local dev setup, production deployment, incident triage), and OpenAPI 3.1 aggregated specs across web, admin, API, worker, and database surfaces offline (0 model calls);
  thread-safe `EcosystemDocsEngine` renders unified Markdown bundles, searches documentation with keyword and tag relevance scoring, aggregates OpenAPI specs with route collision detection, and simulates multi-format documentation exports (`markdown`, `json`, `openapi_bundle`, `runbook_checklist`);
  `EcosystemPackPackage` bundles and validates `docs_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks docs contract and engine, injecting `has_docs`, `page_count`, `runbook_count`, `api_endpoint_count`, and `docs_status` into preview payloads;
  Studio HTTP server exposes `GET /api/ecosystem/docs` and `POST /api/ecosystem/docs/export`;
  `studio/page.py` renders sky-blue/amber-themed `#preview-docs-info` with pages, runbooks, API endpoints badges, and 1-click "Export Docs" and "Refresh" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `docs` subcommand with formatted text, `--json`, `--search`, and `--export` options.
- **R-458 adds Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts:**
  `ComplianceStandard`, `CompliancePolicy`, `DataClassification`, `AuditEvidenceItem`, and `EcosystemGovernanceContract` formalize multi-surface governance and compliance controls with deterministic SHA-256 digests and JSON roundtrips;
  `synthesize_ecosystem_governance` deterministically derives surface-specific compliance policies, data privacy classifications, and cryptographic audit evidence items across web, admin, API, worker, and database surfaces offline (0 model calls);
  thread-safe `EcosystemGovernanceEngine` evaluates surface configurations against policy rules, verifies cryptographic audit evidence hashes, and simulates full audits across operational scenarios (`standard_audit`, `gdpr_dsar_request`, `data_breach_investigation`, `soc2_certification`, `high_risk_violations`);
  `EcosystemPackPackage` bundles and validates `governance_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks governance contract and engine, injecting `has_governance`, `standard_count`, `policy_count`, `evidence_count`, and `governance_status` into preview payloads;
  Studio HTTP server exposes `GET /api/ecosystem/governance` and `POST /api/ecosystem/governance/simulate`;
  `studio/page.py` renders indigo/violet-themed `#preview-governance-info` with standards, policies, audit evidence items, and 1-click "Simulate Audit" and "Refresh" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `governance` subcommand with formatted text, `--json`, `--simulate`, and `--scenario` options.
- **R-457 adds Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts:**
  `ServiceLevelIndicator`, `ServiceLevelObjective`, `ErrorBudget`, `ServiceLevelAgreement`, and `EcosystemSLAContract` formalize multi-surface reliability contracts with deterministic SHA-256 digests and JSON roundtrips;
  `synthesize_ecosystem_sla` deterministically derives surface-specific SLIs (availability, p95 latency, error rate, LCP), SLO targets with multi-window error budgeting, and customer tier SLAs (enterprise, business, developer);
  thread-safe `EcosystemSLAEngine` evaluates SLI metrics against SLO thresholds, tracks multi-window error budget burn rates (1h, 6h, 24h), and simulates SLA compliance across operational scenarios (`normal_operations`, `minor_degradation`, `severe_outage`, `budget_exhaustion`);
  `EcosystemPackPackage` bundles and validates `sla_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks SLA contract and engine, injecting `has_sla`, `sli_count`, `slo_count`, `sla_count`, and `sla_status` into preview payloads;
  Studio HTTP server exposes `GET /api/ecosystem/sla` and `POST /api/ecosystem/sla/simulate`;
  `studio/page.py` renders emerald/teal-themed `#preview-sla-info` with SLIs, SLO targets, error budget burn rates, SLA tiers, and 1-click "Simulate SLA" and "Refresh" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `sla` subcommand with formatted text, `--json`, `--simulate`, and `--scenario` options.
- **R-456 adds Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies:**
  `AlertRule`, `RunbookStep`, `IncidentRunbook`, `EscalationTier`, `EscalationPolicy`, and `EcosystemAlertingContract` formalize multi-surface alerting models with deterministic SHA-256 digests and JSON roundtrips;
  `synthesize_ecosystem_alerting` deterministically derives surface-specific alert rules (HTTP 5xx error spikes, p99 latency degradation, DB connection saturation, worker queue depth, Web LCP degradation), linked incident runbooks with remediation steps, and tiered escalation policies;
  thread-safe `EcosystemAlertingEngine` evaluates metric values against rules, dry-runs runbook steps, and executes end-to-end incident simulations across scenarios (api_error_spike, high_latency_degradation, db_connection_exhaustion, finops_budget_breach, healthy_baseline);
  `EcosystemPackPackage` bundles and validates `alerting_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks alerting contract and engine, injecting `has_alerting`, `alert_rule_count`, `runbook_count`, `escalation_policy_count`, and `alert_status` into preview payloads;
  Studio HTTP server exposes `GET /api/ecosystem/alerting` and `POST /api/ecosystem/alerting/simulate`;
  `studio/page.py` renders rose/crimson-themed `#preview-alerting-info` with alert rules, runbooks, escalation policies, and 1-click "Simulate Incident" and "Refresh" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `alerting` subcommand with formatted text, `--json`, `--simulate`, and `--scenario` options.
- **R-455 adds Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting:**
  `ResourceQuota`, `SurfaceCapacitySpec`, `UnitEconomicsCostModel`, and `EcosystemCapacityContract` formalize multi-surface capacity models with deterministic SHA-256 digests and JSON roundtrips;
  `synthesize_ecosystem_capacity` deterministically derives surface-specific resource quotas (CPU, memory, storage, concurrency, rate limits) and cost models across web, admin, API, worker, and database surfaces;
  thread-safe `EcosystemCapacityEngine` executes multi-tier workload simulation (base, peak, stress), capacity limits evaluation, and monthly unit economics / cloud cost projections;
  `EcosystemPackPackage` bundles and validates `capacity_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks capacity contract and engine, injecting `has_capacity`, `capacity_spec_count`, `monthly_base_cost_usd`, and `capacity_status` into preview payloads;
  Studio HTTP server exposes `GET /api/ecosystem/capacity` and `POST /api/ecosystem/capacity/simulate`;
  `studio/page.py` renders cyan-themed `#preview-capacity-info` with surface quotas, cost models, and 1-click "Simulate Capacity" and "Refresh" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `capacity` subcommand with formatted text, `--json`, `--simulate`, and `--tier` options.
- **R-454 adds Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration:**
  `BackupTarget`, `SnapshotManifest`, `RecoveryStep`, `RollbackTrigger`, and `EcosystemDisasterRecoveryContract` formalize multi-surface DR models;
  `synthesize_ecosystem_recovery` deterministically derives backup targets (database, state, configuration), ordered sequential recovery plan (isolation, quiescing, snapshot restoration, schema verification, phased service restart, cutover), and rollback triggers (health probe failures, database migration errors, timeout exceeded);
  thread-safe `EcosystemRecoveryEngine` executes dry-run simulation of snapshots, recovery steps, rollback triggers, and full DR exercises returning structured PASS/FAIL summaries;
  `EcosystemPackPackage` bundles and validates `recovery_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks disaster recovery contract and engine, injecting `has_recovery`, `backup_target_count`, `recovery_step_count`, `rollback_trigger_count`, and `dr_status` into preview payloads;
  Studio HTTP server exposes `GET /api/ecosystem/recovery` and `POST /api/ecosystem/recovery/simulate`;
  `studio/page.py` renders amber-themed `#preview-recovery-info` with backup targets, recovery steps, rollback triggers, and 1-click "Simulate DR" and "Refresh" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `recovery` subcommand with formatted text, `--json`, and `--simulate` options.
- **R-452 adds Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration:**
  `CIJobStep`, `CIJob`, `CIWorkflow`, and `EcosystemCICDContract` formalize multi-surface CI/CD models;
  `generate_github_actions_workflow` and `to_workflow_yaml` generate valid, deterministic GitHub Actions YAML specifications with 0 external dependencies (no PyYAML);
  `EcosystemCICDEngine` provides in-process DAG dependency validation (Kahn's algorithm cycle detection) and deterministic dry-run pipeline simulation offline;
  `synthesize_ecosystem_cicd` automatically derives surface verification jobs (Node.js/pnpm for web/admin, Python/pip + PostgreSQL for FastAPI, Go + PostgreSQL for Go backends) and overarching `ecosystem-integration` verification gate;
  `EcosystemPackPackage` bundles and validates `cicd_contract` with whole-package SHA-256 integrity;
  `StudioPreviewManager` tracks CI/CD contract and engine, injecting `has_cicd`, `cicd_workflow_count`, `cicd_job_count`, and `cicd_status` into preview status/payloads;
  Studio HTTP server exposes `GET /api/ecosystem/cicd`, `GET /api/ecosystem/cicd/yaml`, and `POST /api/ecosystem/cicd/simulate`;
  `studio/page.py` renders `#preview-cicd-info` with workflow triggers, job chips, and 1-click "Copy GitHub Actions YAML", "Simulate Pipeline", and "Refresh CI/CD" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `cicd` subcommand with formatted text, `--yaml`, `--json`, and `--simulate` options.
- **R-451 adds Ecosystem Cross-Surface Data Sync, Conflict Resolution, and Offline-First Sync Protocol:**
  `SyncEntitySpec`, `SyncMutation`, `SyncConflict`, `SyncCheckpoint`, and `EcosystemSyncContract` formalize multi-surface sync models;
  deterministic Python 3.13 stdlib-only conflict resolution algorithms (`resolve_sync_conflict` supporting `last_write_wins`, `source_of_truth`, `field_merge`) with 0 external dependencies;
  in-process thread-safe `EcosystemSyncEngine` with mutation log, state store, conflict log (bounded 500), push/pull checkpoints, and mutation base-version validation;
  deterministic contract synthesis (`synthesize_ecosystem_sync`) deriving sync entities, authority mappings, and conflict strategies across surfaces;
  `StudioPreviewManager` tracks sync contract and engine, injecting `has_sync`, `sync_entity_count`, `sync_conflict_count`, and `sync_version` into preview status/payloads;
  Studio HTTP server exposes `GET /api/ecosystem/sync`, `POST /api/ecosystem/sync/push`, `GET /api/ecosystem/sync/pull`, and `POST /api/ecosystem/sync/simulate`;
  `studio/page.py` renders `#preview-sync-info` with entity chips, conflict/version badges, and 1-click "Simulate Conflict" and "Refresh Sync" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `sync` subcommand with `--json` option.
- **R-450 adds Ecosystem Multi-Surface Export, Deployment Manifest, and Live Gateway Orchestration:**
  `GatewayRoute`, `SurfaceDeploymentSpec`, and `EcosystemDeploymentManifest` formalize multi-surface deployment topologies;
  `generate_docker_compose` and `to_compose_yaml()` generate valid, deterministic Docker Compose YAML for all surfaces and PostgreSQL with 0 external dependencies (no PyYAML);
  `EcosystemLiveGateway` provides an in-process HTTP reverse proxy on loopback routing requests via longest-prefix matching with header rewriting;
  `synthesize_ecosystem_deployment` deterministically derives non-colliding host ports, routes, and environment bindings across surfaces;
  `StudioPreviewManager` tracks deployment manifest and gateway status, injecting `has_deployment`, `deployment_surface_count`, `gateway_routes`, `gateway_port`, and `gateway_url` into preview status/payloads;
  Studio HTTP server exposes `GET /api/ecosystem/deployment` and `GET /api/ecosystem/deployment/compose`;
  `studio/page.py` renders `#preview-deployment-info` with surface counts, route chips, and 1-click "Copy Compose YAML" / "Refresh Deployment" buttons (0 external network requests);
  and `ecosystem_cli.py` adds `deploy` subcommand with `--json` and `--compose` options.
- **R-449 adds Ecosystem Cross-Surface Telemetry, Audit Trails, and Distributed Tracing:**
  `TelemetrySpan`, `AuditTrailEntry`, `DistributedTrace`, `TelemetrySamplingPolicy`, `TracedSurface`, and `EcosystemTelemetryContract` formalize distributed tracing and audit;
  Python 3.13 stdlib-only deterministic trace ID and span ID generation (uuid + hashlib, 0 external deps, 100% offline);
  `EcosystemTelemetryCollector` coordinates in-process span recording and audit trails with bounded ring-buffer storage (max 500 entries each);
  `synthesize_ecosystem_telemetry` deterministically derives traced surfaces, cross-surface operations, and audit actions from ecosystem definitions;
  `StudioPreviewManager` tracks telemetry contracts, injects `has_telemetry` and `span_count` into preview status/payloads, and exposes `get_ecosystem_telemetry()`;
  Studio HTTP server exposes `GET /api/ecosystem/telemetry`; `studio/page.py` renders `#preview-telemetry-info` with span counts and surface badges (0 external network requests);
  and `ecosystem_cli.py` adds `telemetry` subcommand.
- **R-448 adds Ecosystem Cross-Surface Webhook and Event Bridge:**
  `WebhookRetryPolicy`, `EcosystemWebhookSubscription`, `EcosystemEventPayload`, and `WebhookDeliveryRecord` formalize cross-surface event transport;
  `sign_webhook_payload` and `verify_webhook_signature` provide Python 3.13 stdlib-only HMAC-SHA256 signing and verification
  with constant-time comparison (`hmac.compare_digest`) and 0 external dependencies; `EcosystemEventBridge` provides in-process
  event routing and bounded delivery logging (max 100 entries); `synthesize_ecosystem_events` deterministically derives cross-surface
  event subscriptions from entity writers to readers; `StudioPreviewManager` tracks event bridge contracts, injects `has_events`,
  `event_count`, and `subscription_count` into preview status/payloads, and exposes `get_ecosystem_events()` and `dispatch_ecosystem_event()`;
  Studio HTTP server exposes `GET /api/ecosystem/events` and `POST /api/ecosystem/events/dispatch`; `studio/page.py` renders
  `#preview-events-info` with subscription count, "Simulate Event" panel, and live delivery logs (0 external network requests);
  and `ecosystem_cli.py` adds `events` subcommand.
- **R-447 adds Ecosystem Cross-App Auth and Unified State Binding:**
  `EcosystemAuthContract` and `CrossAppAuthMatrix` define shared HS256 JWT parameters and role isolation;
  `mint_ecosystem_token` and `verify_ecosystem_token` provide Python 3.13 stdlib-only JWT token signing and validation
  with 0 external dependencies; `EcosystemStateBinding` formalizes shared entities, lifecycle state flows with role-gated
  `can_transition`, cross-app endpoints, and per-surface env variables; `StudioPreviewManager` generates demo tokens, injects
  `active_role` and `active_token` into preview status/payloads, and exposes `get_ecosystem_auth()` and `get_ecosystem_state()`;
  Studio HTTP server exposes `GET /api/ecosystem/auth` and `GET /api/ecosystem/state`; `studio/page.py` renders `#preview-auth-info`
  with role badge and "Copy Demo JWT" button (0 external network requests); and `ecosystem_cli.py` adds `auth` and `state` subcommands.
- **R-446 adds Ecosystem Studio live multi-surface preview and process orchestration:**
  `StudioPreviewManager` provides multi-surface ecosystem preview lifecycle (`replace_ecosystem`, `switch_surface`,
  per-surface/global `stop` & `restart`), multi-session management (`_sessions: dict[str, LocalAppSession]`), collision-free loopback
  port allocation per surface, and liveness-aware status tracking, with `threading.RLock` eliminating reentrant deadlocks;
  Studio HTTP server adds `switch_surface_fn`, implementing `POST /api/preview/switch` and surface-scoping for `stop`, `restart`,
  and `history/preview`; `live_serve.py` automatically triggers multi-surface previews on ecosystem compilation;
  and `STUDIO_HTML` in `studio/page.py` renders `#preview-surface-tabs` with active highlights, pulsing live status dots,
  surface kind badges, and 1-click surface switching without iframe flicker (0 external network requests).
- **R-445 adds Ecosystem Pack Registry integration, catalog discovery, and Studio multi-surface selection:**
  `EcosystemPackRegistry` provides immutable registry management with built-in baselines (`minimal-blog-ecosystem`,
  `rideshare-favourites-ecosystem`), dynamic package registration, and `load_surface_ir()`; Studio HTTP server exposes
  discovery and recommendation endpoints (`GET /api/ecosystem-packs`, `POST /api/ecosystem-packs/recommend`);
  `POST /api/build` in `server.py` and `live_serve.py` accepts `ecosystem_id`, `ecosystem_version`, and `surface_slug`
  to compile individual surfaces or the entire multi-surface ecosystem with 0 model calls; `StudioBuildHistory`
  tracks ecosystem and surface metadata; `STUDIO_HTML` in `studio/page.py` adds single vs ecosystem tabs,
  ecosystem dropdown (`#eco-select`), surface selector (`#surface-select`), surface cards (`#surface-cards`), and real-time
  recommendations with 0 external network requests; and `ecosystem_cli.py` adds `catalog` subcommand (`task agent-engine:solution-pack:ecosystem -- catalog`).
- **R-444 introduces multi-surface Ecosystem Pack synthesis and lifecycle tooling:**
  `EcosystemPackPackage` bundles schema version (`"1.0"`), ecosystem metadata, and a collection of
  `EcosystemSurfacePackage` objects pinning each surface's Application IR, digest, and verify targets alongside
  the whole-ecosystem SHA-256 checksum; `parse_ecosystem_pack_package` strictly validates payloads and validates
  all embedded surface IRs with `validate_ir`; multi-surface synthesis in `intake/ecosystem.py` derives surface-specific
  Application IRs scoping entity visibility, mutation authority, actor roles, APIs, and screens per surface;
  `plan_ecosystem` marks synthesized secondary surfaces with `is_synthesized=True`; and `ecosystem_cli.py` exposes
  `synthesize`, `verify`, `inspect`, and `build` subcommands (`task agent-engine:solution-pack:ecosystem`).
- **R-443 introduces portable, verified Solution Pack packaging and export CLI:**
  `SolutionPackPackage` bundles schema version (`"1.0"`), metadata, canonical IR digest, canonical `ir_dict`,
  verify gate plans, and whole-package SHA-256 checksum; `parse_solution_pack_package` strictly validates
  JSON/dict payloads, verifies embedded Application IR with `validate_ir`, confirms `ir_sha256` digest matching,
  verifies whole-package SHA-256 integrity, and fails closed with `SolutionPackError` on corruption or drift;
  `SolutionPackRegistry` supports dynamic package registration via `register_package` and `SolutionPack.from_package`;
  and `package_cli.py` provides `export`, `verify`, and `inspect` subcommands (`task agent-engine:solution-pack:package`).
- **R-442 wires AI-delta feature modification controls into the Studio:**
  Updated `POST /api/build` to accept `ai_features` and `ai_delta_prompt`; extended `live_serve.py` to formulate
  `ai-delta` changes, call `generate_ai_delta_proposal` (bypassing the model with 0 calls when none requested),
  and apply the proposal safely via `apply_solution_pack_manifest`; tracked `applied_ai_delta_change_ids` in history;
  and updated `STUDIO_HTML` with `#ai-features` input, AI synthesis progress messaging, and AI delta badge chips (0 external resources).
- **R-441 connects Solution Packs to the Studio UI and HTTP server:**
  Added `/api/solution-packs` and `/api/solution-packs/recommend` endpoints; updated `/api/build` to accept pack options;
  wired `live_serve.py` to compile Solution Pack apps offline (0 model calls) with complete provenance; enhanced Studio history;
  and updated `STUDIO_HTML` with a Solution Pack selector, recommendation banner, customization inputs, and provenance rendering (0 external links).
- **R-440 wires derived Solution Pack IRs into verified multi-repo builder pipelines and project generation:**
  `build_solution_pack_project()` compiles a pack-derived `ApplicationIR` into an owned Git repo on disk,
  derives verify gate plans, and records complete provenance (pack id/version, base/derived digests,
  applied change IDs, verify targets, commit SHA). `plan_ecosystem()` and `build_ecosystem()` integrate
  pack-derived IRs seamlessly for targeted surfaces with full ecosystem domain safety checks.
- **R-438 defines the bounded AI-delta proposal schema and local model boundary:** manifests with
  zero AI deltas bypass the model completely (0 calls); pending AI deltas produce bounded, typed
  `AIDeltaProposal` objects strictly parsed and validated against base IR collisions and credential fields.
- **R-439 safely applies validated AI-delta proposals to Application IR:** `apply_solution_pack_manifest`
  revalidates pack pins, change IDs, entity/API/screen collisions, and relation targets, immutably merges
  entities, APIs, and screens with allowlisted configuration updates into a `validate_ir`-clean derived
  `ApplicationIR`, and tracks transparent provenance with `applied_ai_delta_change_ids` and remaining
  `unapplied_ai_delta_change_ids`. 100% offline, byte-stable, and repeatable.
- **R-433 stops cloning one full model into every app:** all ten curated domains have deterministic
  read/write surface policies; refined domains use bounded entity-name matching with a safe full-model
  fallback; relation targets remain read dependencies. Each surface declares only its actor role, only its
  writable entities get editors/mutations, and every mutation requires that role. Food delivery now plans
  Customer (catalog read + Order write), Merchant, Courier (Order + Restaurant dependency), and Admin as
  materially different IRs. Plan JSON exposes roles, permissions, and writable entities.
- **R-434 adds the verified-baseline registry:** `minimal-blog@1.0.0` and
  `rideshare-favourites@1.0.0` reference existing Application IR examples and pin canonical digests plus
  exact targets. The fail-closed registry validates drift and selects only exact domain/capability matches;
  `task agent-engine:solution-packs` lists or selects them deterministically without model/live work.
- **R-435 connects that registry transparently to ecosystem plans:** actual framework targets are derived
  from the already-planned surface IRs, then the plan reports minimal pack id/version/digest/targets or
  `no-exact-match`. Blog-CMS selects the Python baseline; rideshare does not misrepresent its Go baseline as
  compatible with today's Python plan. Recommendations are metadata only; generated output is unchanged.
- **R-436 defines the customization safety boundary:** a selected recommendation becomes a frozen manifest
  pinned to its pack id/version/digest and exact query. Configuration and AI-delta changes are bounded typed
  semantic intents with canonical JSON and strict registry revalidation. The schema cannot carry executable
  patches/source/commands/secrets; no pack is applied, no IR is mutated, and no model is called.
- **R-437 applies the first safe deterministic configuration subset:** manifest 1.1 carries explicit bounded
  project-name/description text while legacy 1.0 remains readable. Application revalidates the exact pin,
  preflights all changes, updates a fresh IR immutably, validates it, and records canonical base/derived
  digests plus applied/pending IDs. Unsupported config fails closed and every AI delta remains unapplied.
- The generated app was **run live locally end-to-end this session** (Next.js web on `:3000` +
  FastAPI on `:8000` + seeded PostgreSQL) — proving the offline builder output actually runs on a Mac.
- **R-420 closed both SQL defects exposed by that run:** generator-owned PostgreSQL identifiers are
  consistently quoted and entity tables/fixture groups are emitted in stable FK dependency order.
  A reserved-name User/Order migration passed a rollback-only live PostgreSQL proof.
- **R-421 connects RUN to PREVIEW:** an explicit trusted-local Studio command owns one generated-app
  session and embeds its actual Next.js URL in a sandboxed iframe; build-only mode still executes no
  generated code. Port collisions now fail before setup instead of showing a stale app as ready.
- **R-422 makes preview robust:** each preview allocates two distinct free loopback ports (never fixed
  3000/8000), so it never collides with an existing `task app:run` app or a prior preview; and the
  Studio exposes bounded `status`/`stop`/`restart` controls (`GET /api/preview`, `POST /api/preview/stop`,
  `POST /api/preview/restart`) in trusted-local mode.
- **R-423 gives the Studio memory:** a bounded, secret-free in-session build history (`GET /api/history`)
  and one-click re-preview of a recorded build (`POST /api/history/preview`), with a "Recent builds" list
  on the page.
- **R-424 keeps preview status live:** `LocalAppSession.is_alive()` + a liveness-aware
  `StudioPreviewManager.status()` detect a preview whose processes exited (reporting "stopped" instead of a
  stale "ready"), and the page polls `GET /api/preview` to re-render on change without reloading the iframe.
- **R-425 connects the Studio to disk:** each Recent-builds item has "Copy path" (client clipboard, both
  modes) and "Open folder" (`POST /api/history/open`, trusted-local) to jump to the owned generated repo.
- **R-426 makes the list manageable:** a per-build "Remove" action (`POST /api/history/delete`, in-memory
  only, both modes) clears a build from the Recent builds list without deleting anything on disk or in the DB.
- **R-427 makes generated apps actually compile:** running a generated app through the preview exposed a JSX
  bug — 14 f-string templates emitted single-brace `style={ … }` (invalid). Fixed to `style={{ … }}` with a
  regression test that forbids it, so a fresh build's web app now compiles and renders in the preview.
- **R-428 makes generated apps render + adds a compile gate:** an opt-in `task agent-engine:web-typecheck`
  runs `tsc --noEmit` on a generated app. It surfaced (and R-428 fixed) the run-blocking bugs — over-braced
  event handlers, a `pdf-viewer` literal newline, and screen import depth (`../components/` → the `@/` alias).
  A generated `minimal-blog` now serves `/`, `/post_list`, `/post_editor` at HTTP 200 (were 500).
- **R-429 makes generated apps type-check clean:** fixed the 8 strict-type classes the gate revealed
  (skipLibCheck, duplicate exports, `displayName` on sub-components, typed compounds, `HTMLAttributes` Omit,
  `RefObject<T>`, a terminal variant default, a missing type field, and the `api` object's `…WithCount`
  methods + hook request-params typing). A generated `minimal-blog` and `rideshare-favourites` now pass
  `tsc --noEmit` with **0** errors — `task agent-engine:web-typecheck` reports **PASSED** for both — so
  generated apps are no longer blocked from a production `next build`.
- **R-430 begins the differentiating spine — the Ecosystem Scope Compiler:** a business prompt →
  a framework-neutral multi-app ecosystem proposal (detected domain + actors + customer app +
  merchant/driver/admin portals + Complete/Customer-only/Custom build-scope options + ≤3 materiality
  questions), via a deterministic 10-domain keyword classifier (no model/network). See it:
  `task agent-engine:scope:propose -- "Create a food delivery app …"`.
- **R-431 makes the ecosystem real — Scope → Application IRs:** each proposed surface maps to a
  `validate_ir`-clean `ApplicationIR` (curated per-domain data model + a deterministic CRUD deriver that
  wires to real repositories), and `build_ecosystem` materializes the chosen scope as MULTIPLE owned Git
  repos from one prompt. A food-delivery prompt builds 4 apps (customer/merchant/courier/admin), and all
  four compile clean (`tsc --noEmit` → 0 errors; fixed 4 generator bugs the FK/multi-subcollection shapes
  exposed). See it: `task agent-engine:ecosystem:plan -- "…"` and `task agent-engine:ecosystem:build -- "…"`.
- **R-432 handles unknown domains safely:** `task agent-engine:ecosystem:refine -- "…"` runs the
  deterministic classifier first, makes zero model calls for curated domains, and uses local Ollama only
  when the fallback is `custom-application`. Strict bounded parsing rejects credentials, FK collisions,
  invalid actors/relations/types/rules, then reuses the R-431 planner. An apiary prompt yielded Beekeeper +
  Admin apps with four entities, 23 wired APIs, and eight screens per app; no cloud fallback.

## UI Component Series — status: PAUSED at R-415 (resumable)

The reusable Next.js component library (each component = a static `_X_COMPONENT` string + `render_x_*`
accessor in `codegen/nextjs.py`, registered in `NextjsWebAdapter.generate()`, exported from
`codegen/__init__.py`, with a 1:1 `test_<component>_component.py`) was built one Tracker ID at a time
from R-309 (Pagination) through **R-415 (Phone Number Input)** — 110 components in total.

**Why paused:** the tracker planned ~120 Builder components for MVP; with 110 built the series is past
the point of diminishing returns and is *not* on the critical path to a usable product (the chat →
create front door and the engine are). The founder chose to pivot to higher-value platform work.

**How to resume later (nothing decays — each component is independent and additive):**
1. Pick the next best non-duplicate component and assign it the next available task ID after the active
   front-door sequence (R-416 through R-421 are already used).
2. Follow the component-suite contract (see `.ai/HANDOFF.md` / any recent `.ai/tasks/R-4xx.md`):
   `'use client'`; `forwardRef` + `useImperativeHandle`; 4 variants / 3 sizes; WAI-ARIA; zero deps;
   100% diff-invariant; ASCII-only source; compound + alias exports with `displayName`; default export.
3. Test-first (`test_<component>_component.py`), wire `generate()` + `__init__.py`, run all gates
   (`task verify` / `lint` / `security:quick` / `env:check` / `builder:demo`), update the six state
   files, one commit `feat(R-###): <Title>`, push.

The full list of 110 registered components lives in `codegen/nextjs.py`
(`grep 'GeneratedFile("components/'`); the per-task detail is in `CHANGELOG.md` and `.ai/WORK_LOG.md`.
- The offline builder loop is complete end to end: **describe (IR) → generate (web with typed API client, React hooks, interactive master-detail screen components with field validation, page size selector & contextual empty states, bulk selection & batch deletion, CSV data export & bulk export, deep-linking & entity lifecycle in detail screens, global responsive navigation shell & header navbar with active route detection & quick-create CTA, post-submit contextual CTAs & record navigation with Cancel action in form footer, rich entity-aware dashboard overview page (live count cards, screen nav tiles, quick-create CTAs, diff-stable), record selector dropdown, prev/next record navigation & deep-link sync in detail screens, form screen dirty state tracking, unsaved changes guard & reset confirmation, collection screen boolean & enum field filtering with segmented controls, global notification toast system & action feedback with ToastProvider & useToast, subcollection navigation, child item deletion & mutation feedback, full-stack update/edit actions, foreign-key relation selectors & parent auto-population, App Router resilience quartet, full loading-skeleton coverage, consistent error & retry recovery, enterprise WAI-ARIA accessibility semantics, power-user collection, detail, and form keyboard navigation & shortcuts, form input constraints & live character counters, search clear affordances & form first-field autofocus, collection status badges & detail copy affordances, overview interactive entity links, health badge & metrics chips, accessible modal confirmation dialog replacing window.confirm(), keyboard shortcuts help modal & global discovery affordance, accessible breadcrumb navigation component & screen hierarchy, accessible EmptyState component & screen zero-state integrations, collection screen JSON data export & bulk selection export controls, accessible reusable Pagination component, accessible reusable Tabs component, collection table display density toggle (Compact, Comfortable, Spacious), accessible reusable Badge component, collection table column visibility dropdown & selector controls, accessible reusable Tooltip component, accessible reusable Card compound component, accessible reusable Alert & Notification component, accessible reusable Skeleton loader compound component, accessible reusable Drawer / Sheet compound component, accessible reusable Avatar & AvatarGroup compound component, accessible reusable Toggle Switch component, accessible reusable Accordion compound component, accessible reusable Dropdown Menu compound component, accessible reusable Popover compound component, Design Tokens & CSS Custom Properties Theming Engine (styles/tokens.css), accessible reusable Theme Switcher / Mode Toggle component (components/theme-toggle.tsx), accessible reusable Dialog / Modal component (components/dialog.tsx), accessible reusable Form Controls & Input Primitives suite (components/form-controls.tsx), accessible reusable Date Picker & Calendar component (components/date-picker.tsx), accessible reusable Data Grid / Table component (components/data-grid.tsx), accessible Command Palette / Search Menu component (components/command-palette.tsx), accessible reusable Slider & Range component (components/slider.tsx), accessible reusable Progress & Spinner component (components/progress.tsx), accessible reusable Rating & Review component (components/rating.tsx), accessible reusable Stepper / Multi-step Wizard component (components/stepper.tsx), accessible reusable File Upload / Dropzone component (components/file-upload.tsx), accessible reusable Timeline / Activity Feed component (components/timeline.tsx), accessible futuristic reusable Stat & Metric KPI Card component (components/stat-card.tsx), accessible reusable Hierarchical Tree View component (components/tree-view.tsx), accessible futuristic reusable Tag & Chip Input Tokenizer component (components/tag-input.tsx), accessible futuristic reusable Code Block & Syntax Presentation component (components/code-block.tsx), accessible futuristic reusable Radial Gauge & Activity Rings component (components/radial-gauge.tsx), accessible futuristic reusable Segmented Control & Mode Switcher component (components/segmented-control.tsx), accessible futuristic reusable Carousel & Slider Showcase component (components/carousel.tsx), accessible futuristic reusable Resizable Panels & Splitter component (components/resizable.tsx), accessible futuristic reusable Color Picker & Palette Swatch component (components/color-picker.tsx), accessible futuristic reusable PIN & OTP Code Input component (components/pin-input.tsx), accessible futuristic reusable Speed Dial & Floating Action Button component (components/speed-dial.tsx), accessible futuristic reusable Context Menu suite (components/context-menu.tsx), accessible futuristic reusable Hover Card suite (components/hover-card.tsx), accessible futuristic reusable Scroll Area suite (components/scroll-area.tsx), accessible futuristic reusable Collapsible component (components/collapsible.tsx), accessible futuristic reusable Aspect Ratio component (components/aspect-ratio.tsx), accessible futuristic reusable Separator component (components/separator.tsx), accessible futuristic reusable Keyboard Keycap component (components/kbd.tsx), accessible futuristic reusable Radio Group suite (components/radio-group.tsx), accessible futuristic reusable Checkbox & Checkbox Group primitive (components/checkbox.tsx), accessible futuristic reusable Announcement Banner & Callout suite (components/banner.tsx), accessible futuristic reusable Searchable Combobox & Autocomplete primitive (components/combobox.tsx) + API with
  working CRUD incl. PATCH/PUT update + pagination + sorting + total count header + keyword search + sub-collections + DB schema + data-access + JWT-verified auth
  & per-endpoint roles + field validation + CORS middleware + OpenAPI 3.1 contract)
  → verify → edit → commit to an owned Git repo.**

## Completion by phase

| Phase | Done | Total | % complete |
|-------|------|-------|-----------|
| **MVP** (current milestone) | 147 | 253 | **58.1%** |
| MID | 0 | 47 | 0% |
| ADVANCED | 0 | 29 | 0% |
| PRODUCTION | 0 | 29 | 0% |
| **Overall program** | **147** | **358** | **41.1%** |










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
| **Accessible futuristic Carousel & Slider Showcase component** (Carousel, touch/swipe gestures, autoplay, dot/fraction indicators, WAI-ARIA carousel) | ✅ Done | R-343 |
| **Accessible futuristic Resizable Panels & Splitter component** (Resizable, ResizablePanel, ResizableHandle, collapsible panels, WAI-ARIA separator) | ✅ Done | R-344 |
| **Accessible futuristic Color Picker & Palette Swatch component** (ColorPicker, spectrum area, hue/alpha sliders, HEX/RGB/HSL, EyeDropper API) | ✅ Done | R-345 |
| **Accessible futuristic PIN & OTP Code Input component** (PinInput, multi-slot auto-advance/retreat, clipboard paste distribution, masked modes) | ✅ Done | R-346 |
| **Accessible futuristic Speed Dial & Floating Action Button component** (SpeedDial, 4 directional cascades, FAB 45° rotation, WAI-ARIA menu) | ✅ Done | R-347 |
| **Accessible futuristic Context Menu suite** (ContextMenu compound, viewport boundary clamping, nested submenus, checkbox/radio items, WAI-ARIA menu) | ✅ Done | R-348 |
| **Accessible futuristic Hover Card suite** (HoverCard compound, entry/exit delay coordination, collision avoidance edge flipping, WAI-ARIA dialog) | ✅ Done | R-349 |
| **Accessible futuristic Scroll Area suite** (ScrollArea compound, cross-browser scrollbar concealment, proportional thumb drag tracking, WAI-ARIA scrollbar) | ✅ Done | R-350 |
| **Accessible futuristic Collapsible component** (Collapsible compound, CSS grid row expansion, rotating indicator chevron, WAI-ARIA disclosure) | ✅ Done | R-351 |
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

**Commercial platform kickoff (founder-approved direction, 2026-09-17 — see
`R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`):** the hybrid engine (R-465 grounding, R-466
compile repair + pacing, R-467 file browser + hybrid-UI toggle, R-468 multi-turn edit) and the Studio
(`studio/page.py`) stay exactly as they are — the agent-engine's own local proof harness, not the
product UI going forward. **R-469 (done)** built the real control-plane foundation: users,
authentication, and a plan/credit model on the existing Go `services/control-plane` skeleton.
**R-470 (done)** replaced the static `apps/console-web` with a real Next.js app wired to R-469's auth
endpoints via a server-side cookie proxy. **R-471 (done)** fixed a real dev-mode hydration bug the
founder hit trying it live, and added a required Name field to registration. Next is **R-472 (Phase
C)**: bridge the control-plane's Job API to the unmodified agent-engine so a real generation call
actually debits a user's credits (local-Ollama calls stay credit-exempt). After that, **Phase D**
rebuilds the Studio UX for real inside the new console (the Lovable/Dyad/Emergent pattern research
already done applies there), and **Phase E** adds plan-gated UI, an admin console, and — with its own
explicit sign-off — a payment processor. Previously-named follow-ups (wiring R-466's
`compile_and_repair` into the edit flow, an undo/revert UI, extending `app_delta` beyond
additive-only) remain real but lower priority than the platform foundation now underway. Founder
action to unlock a full live proof of a model-written page that compiles, or of the chat-edit delta
against a real model: after the Groq daily reset run with `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS=180`,
or add `GOOGLE_API_KEY` (Gemini) to the gitignored `.env`.

The local front door is built through robust browser preview with memory: R-416 prompt → IR, R-417 IR →
owned repo, R-418 local chat studio, R-419 turnkey local run, R-420 SQL hardening, R-421 managed embedded
preview, R-422 collision-free preview ports + status/stop/restart controls, R-423 build history + re-preview
(a bounded "Recent builds" list, `GET /api/history`, and `POST /api/history/preview` to re-open a prior
build), R-424 live preview status (liveness-aware `status()` + page polling of `GET /api/preview`, so a
preview whose processes exit is reported as stopped rather than shown stale), R-425 per-build repo actions
(Copy path + Open folder on each Recent-builds item, connecting the Studio to the owned generated repo on
disk), R-426 remove-from-history (a per-build Remove action that clears an entry from the in-memory Recent
builds list), R-427 a generated-JSX inline-style fix (single-brace `style={ … }` → valid double-brace),
R-428 generated-app compile fixes + an opt-in `tsc` gate (`task agent-engine:web-typecheck`; fixed
over-braced handlers, a `pdf-viewer` literal newline, and screen import depth via the `@/` alias — a generated
app now renders in the preview), and **R-429 strict-type cleanup** (fixed the 8 type-error classes the gate
revealed so a generated `minimal-blog` and `rideshare-favourites` pass `tsc --noEmit` with 0 errors; the gate
now reports PASSED for both — generated apps are no longer blocked from a production `next build`).

The differentiating spine's first nine bricks are in: **R-430** (Ecosystem Scope Compiler) *proposes* a
multi-app ecosystem, and **R-431** (Scope → Application IRs) *materializes* it — one prompt →
multiple owned, clean-compiling app repos (`task agent-engine:ecosystem:plan` / `:build`); **R-432** adds
opt-in local-model refinement for unknown domains with a strict validation boundary; **R-433** scopes each
surface's entities, read/write capabilities, and actor role; **R-434** registers the two existing verified
examples as immutable, versioned, digest-pinned baseline Solution Packs; **R-435** adds exact target-aware
recommendations to ecosystem planning without applying them; **R-436** adds the immutable, strict,
digest-pinned declarative customization manifest; **R-437** deterministically applies explicit allowlisted
project metadata to a fresh validated pack IR with provenance while leaving AI deltas pending; and **R-438**
defines the strict bounded typed AI-delta proposal schema (`AIDeltaProposal`) and explicit opt-in local
`ModelProvider` boundary (0 calls when no AI-delta changes exist, credential filtering, collision rejection).
Next is **R-439**: deterministic application of validated AI-delta proposals to derive a new Application IR.
An optional frontier model can improve generation quality later.
`task verify` must remain model/Docker/DB/install/network-free (any live/model path stays opt-in).

**The UI-component series remains PAUSED at R-415** and is independently resumable under a future free
task ID.

Later, on a network machine / with keys: live **Tier-2** cloud preview + deploy (E2B, Vercel) and
cloud-model verification. The plumbing (R-233/234 tier switch) is already built; it is a config flip.

This file is refreshed as tasks land.

