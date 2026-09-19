# OmniStackAI — Commercial Platform Kickoff (v1)

Date: 2026-09-17
Status: Planning doc — no code written yet. This is the "if we stop today, anyone (founder,
another AI session, another tool) can pick this up tomorrow" artifact the founder asked for.
Parent contracts: `AGENTS.md`, `OmniStackAI_Implementation_Brief_v6.md` (Sections 22, 25, 33,
63, 76, 77, 91, 92), `OmniStackAI_OS_Master_Architecture_Specification.md`.

This doc does not replace the Brief — it records a specific, dated decision (advance from the
Stage 0 static console/prototype Studio to the real commercial platform) and turns it into a
concrete, Tracker-ID-ready sequence. Once Phase A below gets its own `.ai/tasks/R-469.md`
contract, that contract is the authority for that slice of work; this file stays the map.

---

## 1. What was decided today (2026-09-17), and why it's not a new idea

The founder asked for "a proper platform, not a single page" — real frontend framework, real
API+DB, real authentication, role-based access, hosted for real (multiple independent users),
matching what Emergent/Bolt/v0 actually are.

**This was already the plan.** Three facts found by re-reading the existing R&D corpus before
writing anything new (so this doc doesn't contradict work already done):

1. `OmniStackAI_Implementation_Brief_v6.md` Section 33 has always specified the real MVP shape:
   `Next.js console` → `Go control-plane (Auth/Orgs/Workspaces/Projects/Job API/Billing)` +
   `Python agent-engine (planning/model gateway/tool execution)`, on `PostgreSQL`. Section 76's
   BASIC/MVP roadmap explicitly lists "product/org/workspace/project model" as an **MVP-stage**
   item, not a later phase — so building real auth/roles now is not skipping ahead, it's picking
   up a piece of the current phase that hasn't been started yet.
2. `apps/console-web/README.md` already says, in its own words: *"Why static (for now): this
   slice is intentionally dependency-free so it builds and runs in the offline Stage 0
   environment... **The forward path is a Next.js (App Router, TypeScript) app** once the build
   environment can install the front-end toolchain; the data contract (`overview.json`) and the
   design carry over unchanged."* Today's decision is exactly that forward path.
3. `services/control-plane` already exists as a real Go module (`go.mod`, `cmd/control-plane`,
   `internal/config`, `internal/health`, one migration `000001_platform_foundation` that only
   creates `schema_migrations` and enables `pgvector`). It is a genuine skeleton with **no
   business tables yet** — health/liveness only. This is Phase 0's exit gate (Section 91), already
   met; Auth/Users/Plans/Credits is the next layer on top of it, not a new service.

**Correction to my own earlier suggestion in this conversation:** I proposed FastAPI for the
Studio's backend before finding the above. That was wrong given what already exists — the
platform's control-plane (auth, orgs, billing, job API) is Go, per Section 33 and the existing
skeleton. Python (`agent-engine`) stays scoped to AI orchestration (model gateway, codegen,
compile/repair, hybrid UI, editing) and is called *by* the control-plane, exactly as already
diagrammed. Going with Go here unless the founder says otherwise — it's not a new choice, it's
the one already on disk.

**Decisions confirmed (via the founder's answers this session):**
- Deployment: hosted, multi-user — real signup/login over the internet, not local-only.
- Frontend: Next.js (App Router, TypeScript) — replacing the static `apps/console-web`.
- Platform backend (auth/orgs/billing/job API): Go, `services/control-plane` — extending the
  existing skeleton, not a new service.
- AI orchestration: unchanged — `services/agent-engine` (Python), called by the control-plane.
- Database: PostgreSQL (already the non-negotiable control-plane DB, Section 63.1;
  `pgvector` already enabled in the existing migration).
- UI must be **one interface for everyone** — no persona branching, no "tech mode / non-tech
  mode" fork. Depth (files, diffs, logs, commit history) is progressive disclosure inside the
  same screens, not a different product for a different user type.
- Fully commercial intent — this is meant to become a real product with paying users, not an
  internal tool. (Payment processor integration itself is a separate, later decision — see
  Section 5, "paid cloud service" is one of this project's standing hard gates.)

**This supersedes the "R-469: Studio UI/UX overhaul" direction discussed earlier in this
session.** That plan (persistent chat rail + tabs, borrowing Lovable/Dyad/Emergent patterns)
was scoped against `studio/page.py` — the dependency-free Python-stdlib page that has been the
**agent-engine's own local proof harness** through R-465–R-468 (hybrid UI, compile-repair,
multi-turn edit). That harness stays — it's still how agent-engine Tracker IDs get proven
end-to-end without needing the full platform up. But it is not, and was never meant to be, the
commercial product surface. All of the UI/UX pattern research already done (the Lovable/Dyad/
Emergent comparison table) is not wasted — it now targets the real Next.js console-web instead
(see Phase D below).

---

## 2. Role, plan and credit model (resolves "which is best approach")

Kept deliberately small for v1 — no team/org/workspace roles yet (Owner/Admin/Member), since
nothing has asked for multi-person collaboration yet. Section 25's anti-overengineering rule
applies directly: one IR, one project model, add complexity when a real requirement forces it.

**Roles** (access control — who can do what on the platform itself):
- `super_admin` — full platform access: user management, plan/credit overrides, platform-wide
  usage, impersonation for support. Internal/operator role, not a purchasable tier.
- `user` — the only role a signup gets. Every access restriction for a `user` comes from their
  **plan**, not a second role tier. This directly answers "should regular users have a role" —
  they have one role, and their plan does the gating.

**Plans** (reusing the tier names already named in Brief Section 22 — Billing and Cost Rules,
so this doesn't invent new vocabulary):
- `free` — signup grant of free credits (exact number is a business decision, not an
  engineering one — Emergent grants 10 on first prompt as a reference point) **plus unrestricted
  use of the user's own local Ollama model, which never consumes credits.** This directly
  satisfies "a simple logged-in user should be able to explore and start working right after
  register/login, using local Ollama or free credits."
- `developer` / `pro` / `agency` / `enterprise` — more credits, higher-tier cloud model access,
  (later) team seats. Exact pricing/limits per tier: business decision, not specified here.
- `byok` — an add-on flag (bring-your-own cloud API key), not a separate tier, per Section 22.

**Credits**: a `credit_ledger` (or `usage_events`) table in the control-plane's Postgres schema.
Every cloud-model-backed generation call debits it (metered by tokens or by "generation unit" —
open decision, Section 5). **Local-model (Ollama) usage is always credit-exempt** — it costs the
platform nothing, so there's no reason to meter it, and it becomes a real differentiator to
market ("bring your own local model = always free," matching what Dyad shows as a "Ready, free"
state and going further than any of the three competitors reviewed, none of which appear to
offer a genuinely free local-inference path in what was shown).

**Access gating logic:**
- `super_admin` bypasses all plan/credit checks.
- `user` is gated by (a) their plan's feature entitlements and (b) remaining credit balance —
  but only for cloud-model-backed actions. Local-model actions are always available regardless
  of balance.

---

## 3. Phased roadmap (each phase becomes its own `.ai/tasks/R-###.md` contract in order)

Per Section 91 ("do not ask an AI tool to build the whole platform in one prompt") and this
project's own one-Tracker-ID-at-a-time discipline, this is a sequence, not one task. Next
available ID per `.ai/tasks/` is **R-469** (R-468 is the last shipped task).

**Phase A — Control-plane foundation: users, auth, plans, credits (R-469 — DONE, 2026-09-17)**

> Shipped exactly as designed below. Full evidence in `.ai/tasks/R-469.md`: `go test` all green
> (migrations 4, password 8, auth 15, health 3, config 2/9 subtests), `task verify` 3,593 OK, and a
> real Docker Compose + PostgreSQL smoke test proving register → login → me → logout →
> me-after-logout end to end, including a byte-identical 401 body for wrong-password vs.
> unknown-email (no enumeration leak). One deliberate implementation choice beyond what's written
> below: password hashing is PBKDF2-HMAC-SHA256 built directly on Go stdlib
> (`crypto/hmac`+`crypto/sha256`+`crypto/subtle`) rather than a new dependency — mechanically
> enforced by a `scripts/test.sh` check that `go.mod`'s direct-dependency count stays exactly 1.

- Migration `000002_...` on top of the existing `000001_platform_foundation`: `users` (id, email,
  password_hash, role, plan, credit_balance, created_at), `sessions` (or JWT + a revocation
  table), `credit_ledger` (user_id, delta, reason, created_at).
- Go endpoints: register, login, logout, session check, "me" (current user + plan + balance).
- Password hashing (bcrypt/argon2 — Go stdlib-adjacent, no exotic dependency), secure session
  tokens, basic rate limiting on auth endpoints (Section 90's threat model already calls out
  credential/endpoint abuse).
- Signup grants the `free` plan + starting credit balance immediately (no email verification
  gate needed for v1 — can be added later without breaking the schema).
- Deterministic, offline-testable (Go `httptest` + a real Postgres in CI/compose, matching the
  existing `control-plane:verify` pattern) — no dependency on the frontend or agent-engine yet.

**Phase B — Real Next.js console-web (R-470 — DONE, 2026-09-17)**

> Shipped as designed below. Full evidence in `.ai/tasks/R-470.md`: `apps/console-web`
> `typecheck`/`lint`/`build` all clean, `task verify` 3,593 OK, and a real Docker Compose
> control-plane + a real `next start` server proved the full register → home → fabric → logout →
> login round trip live (with cookies, not a bearer token), run twice — the second time after
> fixing a genuine bug found along the way: the session cookie's `Secure` flag was derived from
> `NODE_ENV` (always "production" under `next start`) instead of the actual request protocol,
> which would have silently broken login in a real browser over local HTTP. Also found and fixed:
> `pnpm`'s default fetch timeout was too short for this network on large packages; `typescript@7`
> (npm's real current `latest`) isn't yet supported by `typescript-eslint` (pinned to `6.0.3`); the
> documented ESLint `FlatCompat` pattern crashed on a circular-reference bug (fixed by importing
> `eslint-config-next`'s native flat-config export directly); pnpm 11.19 moved build-script
> allowlisting from `package.json` to `pnpm-workspace.yaml`.

- Replace `apps/console-web`'s static HTML/JS with a Next.js (App Router, TypeScript) app.
- Login/signup/session screens wired to Phase A's endpoints.
- Carry forward the existing `overview.json` data contract and visual design as one section of
  the new app (the README already promises this continuity) rather than throwing it away.
- This is the point where `task bootstrap`/`task doctor` gain a real Node/npm toolchain
  requirement — a deliberate, explicit scope change from "dependency-free Stage 0," recorded
  here so it isn't a silent surprise later.

**Phase C — Bridge to agent-engine via the control-plane's Job API (R-472 — DONE, 2026-09-18)**

> Renumbered from R-471: that slot went to a real, unplanned fix instead (R-471 — the founder's
> first live try of the R-470 console hit a real dev-mode hydration bug that broke all forms, plus
> a request to add a Name field to registration). See `.ai/tasks/R-471.md`.

- Control-plane's new `POST /jobs/build` proxies "build this app" requests to the agent-engine's
  real plain-prompt build path, verbatim, via a configured `OMNISTACKAI_AGENT_ENGINE_URL` (not
  Docker Compose). **Not literally unmodified**, as originally planned here: the build path
  returned a raw `ModelProvider` bypassing the gateway's own accounting entirely, so a small,
  additive `model_gateway.RecordingProvider` decorator (agent-engine) was needed to record real
  usage/cost — zero changes to any existing provider or call site. See `.ai/tasks/R-472.md`'s
  "Correction to the kickoff doc's own framing" for the full reasoning.
- Every generation call is attributed to the authenticated user and debits their credit balance
  (`users.Store.DebitCredits`, row-locked, clamped so the balance never goes negative); local-Ollama
  calls are recorded but debit `0` credits (priced at `$0` in `DEFAULT_PRICE_BOOK`, not
  special-cased).
- This is the only place credit enforcement actually lives — agent-engine itself stays
  credit-agnostic, matching "agents depend on provider interfaces, not billing logic."
- Scoped to the plain-prompt build path only for v1 (matching this task's actual allowed-paths
  scope); Solution Pack and Ecosystem builds report no `usage` key yet and so debit `0` credits —
  named, not silent, follow-up work, not a regression.

**Phase D — The actual Studio UX, inside the real console-web (in progress: R-473, R-474, since 2026-09-18)**
- This is where the earlier Lovable/Dyad/Emergent pattern research gets used for real: persistent
  chat + top tabs (Preview/Files/Code/Problems/Publish/More), one unified UI for every user with
  progressive disclosure (not persona branching), Model Provider settings surfacing the existing
  `model_gateway` (cloud + local Ollama, Dyad-style "Ready" state), a Problems tab wired to the
  already-existing `verify/compile.py`.
- Built as real Next.js components against the real API — not retrofitted into `studio/page.py`.
- **R-473 (DONE, 2026-09-18) shipped the first slice, not the full vision above**: a new `/studio`
  page in `apps/console-web` — a prompt textarea, a Build button, and a result panel — calling the
  now-real `POST /jobs/build` (R-472) and showing the real post-debit credit balance. Deliberately
  scoped small, matching how the agent-engine's own hybrid-UI engine shipped across four separate
  gated Tracker IDs (R-465–R-468) rather than one large task. Still needed for the full vision: a
  file browser + live preview (porting R-467's `studio/page.py` capabilities), persistent chat /
  multi-turn edit (porting R-468's), Solution Pack/Ecosystem build selection, Model Provider
  settings, and a Problems tab — each a named, separately-scoped follow-up. See `.ai/tasks/R-473.md`.
- **R-474 (DONE, 2026-09-18) shipped the file-browser half of the item above**: each filename in
  the `/studio` result panel is now a button showing real generated file content in a read-only
  viewer, bridged through two new authenticated control-plane proxy routes
  (`GET /jobs/build/{id}/files`, `GET /jobs/build/{id}/file?path=...`) to the agent-engine's
  existing R-467 file-serving endpoints — no agent-engine changes, no credit debit for browsing.
  Still needed: live preview (a materially different trust posture, since it executes generated
  code, unlike read-only file access — needs its own scoped decision before starting), persistent
  chat/multi-turn edit, Solution Pack/Ecosystem build selection, Model Provider settings, and a
  Problems tab. Honest, named limitation not fixed by this task: the agent-engine's Studio server
  has no per-user build scoping (a single shared in-memory process, unchanged since R-467) — any
  signed-in console user who knows a build id can browse its files. See `.ai/tasks/R-474.md`.

### Remaining Phase D roadmap (planned 2026-09-18, approved 2026-09-19, **completed 2026-09-19**)

**Status: all seven tasks shipped.** R-475 (visual foundation), R-476 (multi-turn edit bridge),
R-477 (chat UI), R-478 (live preview proxy), R-479 (live preview UI), R-480 (Problems/compile-report
support), and R-481 (tabbed workspace) are all committed and pushed to `origin/main`. The Studio is
now a real chat-driven, multi-pane workspace — persistent chat plus a tabbed Preview/Files/Code/
Problems main pane — genuinely closer to Lovable/Dyad/Emergent parity than at the start of this
roadmap. See "Beyond R-475–481" below for the two structural gaps that remain even so (real-time
streaming, per-user multi-tenancy), and each task's own `.ai/tasks/R-###.md` for full verification
detail. A real, pre-existing codegen bug was found live during R-481's own manual smoke test — a
Next.js dynamic-route slug-name collision (`counterId` vs `counter_id`) introduced by the edit-delta
path — not fixed as part of this roadmap (out of scope), worth its own future Tracker ID once
scoped. No pre-approved task remains queued after this roadmap; the next Tracker ID needs explicit
founder direction on priority (see "Named, deliberately not in the seven above" and "Beyond
R-475–481" for the candidates).

The founder asked, after seeing R-473/R-474 live, for the full "rich, upgraded, advanced UI" the
Lovable/Dyad/Emergent screenshot research was originally for — not just the functional loop
R-472–R-474 proved. This section was first drafted as a six-task sketch on 2026-09-18, then turned
into a fully-researched, founder-approved execution plan on 2026-09-19 (full detail, including
verified code-level findings, in that session's plan record) — two research passes over the real
code plus two direct founder decisions changed the count from six tasks to **seven**. This section
now reflects the approved plan; the six-task version is superseded, not preserved separately.

**Honest scope assessment (unchanged in spirit, one task longer):** contract-first / test-first /
one-commit / real-gate-evidence discipline, same as every prior Tracker ID. Roughly 30–90 minutes
of continuous gated work per task at this session's established pace, likely spanning more than one
sitting once real model flakiness, live-verification time, and ordinary mid-implementation
discoveries are accounted for (every prior phase in this doc has found at least one real,
unanticipated thing while implementing).

**Resolved decision (2026-09-18, founder confirmed): live preview stays local-only.** Reuses the
exact trust boundary that already exists (`task agent-engine:studio:preview`'s
`StudioPreviewManager`, a single trusted-local developer's own machine) — the console/control-plane
only add a way to *reach* that mechanism, not new hosted/sandboxed execution. Full multi-tenant
redesign is out of scope until the platform is genuinely multi-tenant-hosted.

**Two further decisions (2026-09-19, founder confirmed, both change the plan):**
- **Problems (compile-error reporting) gets built for real, not deferred as a placeholder** — even
  though nothing in this codebase calls `compile_web_project()` from the Studio path today, so this
  is genuinely new backend work (confirmed by exhaustive grep: the only caller anywhere is a
  standalone CLI script, never `_build()`/`_edit()`). Given it back its own task (**R-480**, backend
  only) rather than folding it into tab assembly, keeping every task's scope consistent with the
  rest of this session's tasks — this is what took the roadmap from six tasks to seven.
- **Files and Code stay as two separate, real tabs** — a Files tab for browsing/getting oriented
  (tree only) and a Code tab for actually reading one file (full syntax-highlighted content),
  sharing one lifted "selected file" state — rather than collapsing them into a single tab.

Sequence (each gets its own `.ai/tasks/R-###.md` contract before code, per this project's standing
rule — this section is the map, not the contract):

1. **R-475 — Studio visual foundation** *(in progress, 2026-09-19)*. A real app shell (top bar,
   refined design tokens — `--radius-*`, `--surface-2`, a CSS-only `.spinner`, hand-rolled inline-SVG
   icons rather than a new dependency) the later chat (R-477) and tabbed workspace (R-481) tasks
   build on top of, not a one-off skin of the current form. No backend changes.
2. **R-476 — Backend: multi-turn edit bridge.** New control-plane routes
   (`POST /jobs/build/{id}/edit`, `GET /jobs/build/{id}/turns`) proxying the agent-engine's existing
   R-468 endpoints, mirroring `POST /jobs/build`'s exact proxy+debit shape (R-472). Also fixes two
   real, verified gaps in the Python edit path: `_edit()` has no `usage_ledger` at all today (so
   every edit currently debits 0 credits regardless of real cost — confirmed by direct comparison
   with `_build()`), and `_build()` never records a chat turn (only `_edit()` does — so a chat that
   hydrates history from `/turns` after a refresh would silently lose the first message). Both
   fixed here, mirroring `_build()`'s own existing patterns.
3. **R-477 — Console: chat UI.** Replaces `/studio`'s one-shot prompt form with a persistent,
   multi-turn chat thread wired to R-476, built on R-475's shell. `buildId` (`null` vs. set) is the
   single piece of state deciding whether the composer calls `/jobs/build` or
   `/jobs/build/{id}/edit`; `buildId` persists in the URL so a refresh can rehydrate history from
   `/turns`.
4. **R-478 — Backend: live preview proxy (local-only).** Four new control-plane routes, not three —
   the agent-engine's preview API turned out to be two different surfaces on inspection: a
   singleton "whichever preview is running" surface (`GET/POST /api/preview*`) and a build-scoped
   one (`POST /api/history/preview`) that a chat-per-build UI actually needs. The build-scoped
   route has a real, unusual error shape worth documenting here since it's easy to get wrong: an
   unknown build returns **200** `{"status":"error","message":...}`, not a 404 like every other
   build-scoped route in this codebase. No agent-engine changes, no credit debit (viewing/
   controlling a preview isn't a billable model call).
5. **R-479 — Console: live preview UI.** An iframe wired to R-478, with real status. The
   agent-engine's preview start/restart calls are synchronous (block until ready/error), so there
   is no server-side "starting" state to poll for — polling's real job is crash detection (a 5s
   interval while status is "ready"), not progress-watching. Since `_edit()` never restarts the
   preview on its own (only `_build()` does), this task also triggers its own re-preview call after
   every successful edit rather than assuming hot-reload alone keeps the iframe correct.
6. **R-480 — Backend: Problems/compile-report support** *(new — this is the task that took the
   roadmap from six to seven, per the founder decision above)*. Builds real `tsc`-backed
   compile-error reporting from scratch: a new agent-engine function calling the already-existing
   (but until now, never invoked from the Studio path) `compile_web_project()`, a small new
   bounded store keyed by build id, and new routes (agent-engine `POST`/`GET /api/build/{id}/problems`,
   control-plane proxy). **Deliberately on-demand (an explicit "Check for problems" trigger), not
   automatic on every build/edit** — the Node toolchain/`node_modules` only exists in a generated
   repo after a live-preview install, so an automatic check would make the normally fast,
   network-light core build loop slower and toolchain-dependent by default; a real regression risk
   worth avoiding by design rather than discovering later.
7. **R-481 — Tabbed workspace.** Restructures `/studio` into four real tabs — Preview, Files, Code,
   Problems — chat persisting alongside (not itself a tab), assembling R-474 (files), R-477 (chat),
   R-479 (preview), R-480 (problems). Files and Code stay separate per the founder decision above.
   Code's syntax highlighting is hand-rolled (there is already real in-house precedent — the
   generated apps' own `CodeBlock` component ships a regex tokenizer in `codegen/nextjs.py`) rather
   than a new dependency, with a documented, non-default fallback (`prismjs`) if real usage during
   this task's own live verification shows the hand-rolled version visibly failing on real
   generated files. **"Publish" is still explicitly not a tab** — no deployment/hosting backend
   exists anywhere in this codebase; a placeholder would be dishonest UI, the same principle now
   also guiding Problems' honest "not yet checked" state rather than fabricated data.

**Named, deliberately not in the seven above:**
- **Model Provider settings UI** (surfacing `model_gateway`'s cloud/local Ollama status, Dyad-style
  "Ready" state) — a real, smaller, independent UI surface. Slot in as **R-482** whenever
  convenient after R-475; no hard dependency on the chat/preview/tabs work.
- Solution Pack / Ecosystem build selection in the Studio UI — still real follow-up work, lower
  priority than the seven above since it's about build-type breadth, not depth of the core loop.
- Per-user build/session scoping in the agent-engine's Studio server (the honest limitation named
  in R-474) — needed before this is genuinely multi-tenant, not needed for the single-operator demo
  this roadmap targets.

### Beyond R-475–481: what "exact target" still needs (asked and answered 2026-09-18)

The founder asked directly whether R-475–481 gets this platform to "exact" Lovable/Dyad/Emergent
parity. Honest answer, recorded here rather than left as a spoken claim: **substantially closer,
but not exact or complete.** Two structural gaps remain that are bigger than UI polish and are not
closed by any task above:

- **R-484 — Real-time build/edit streaming** *(renumbered again: R-482 went to the real Model
  Provider settings UI shipped 2026-09-19, and R-483 went to a real bug fix found live during
  R-481's own smoke test — a dynamic-route slug-name collision and a duplicate `lib/types.ts`
  identifier, both in the edit-delta codegen path)*. **Shipped 2026-09-19 as R-484 (backend SSE
  through all three layers) + R-485 (console streaming UI with a live character count).** The
  paragraph below is kept as the original scoping record. Lovable/Dyad/Emergent's signature "smoothness" is watching the model write code live
  (token-by-token, file-by-file) as it happens. Every task above still uses one blocking HTTP call
  that takes seconds to a few real minutes and then returns everything at once — R-477's chat UI
  would show "Building…" and then a result, not a live-updating stream, without this task. Requires
  a materially different transport (Server-Sent Events or a WebSocket) threaded through all three
  layers: the agent-engine's build/edit path would need to emit incremental progress events (not
  just a final JSON response), `internal/jobs`'s proxy would need to relay a stream instead of
  buffering a whole response body (a real change to the "read the whole body, then decide" pattern
  every Job API route uses today), and the console would need to consume and render it live. Scope
  this as its own task once R-475–481 exist to stream progress *into* — do not start it before then.
- **Per-user backend multi-tenancy — not a Tracker ID here, a prerequisite for calling this "done."**
  Even after R-475–483 all ship, the agent-engine's Studio server is still the same single shared
  in-memory process named as a limitation in R-474 and re-confirmed in the "Resolved decision" above
  for live preview. A polished UI on top of it does not change what it is: **a single, trusted
  operator's own tool that looks like a multi-user SaaS, not yet an actual one.** Lovable/Dyad/
  Emergent are real multi-tenant products where many mutually-untrusted strangers can safely build
  at the same time. Getting there needs the Studio server itself (build history, sessions, preview
  processes) to become genuinely multi-tenant-aware — a real architecture project, not a UI task,
  and not proposed with a Tracker ID yet because it needs its own scoping conversation first.
- **Publish/deploy — still Phase E+ territory**, unchanged from the note already above: no
  deployment/hosting backend exists anywhere in this codebase, and standing this up is very likely
  its own "new infra" decision requiring explicit founder sign-off before any code gets written for
  it, per this project's standing rules.

**Phase E — Plan/credit UX + admin surface (proposed, not yet numbered)**
- Plan-gated feature access in the UI, a credit top-up flow, a `super_admin` console (user
  management, usage, plan overrides — the Dyad "Danger Zone" / Emergent admin-adjacent idea).
- Actual payment processor integration (Stripe or similar) is intentionally **not** included
  here — that is a "paid cloud service" decision under this project's standing rule ("stop and
  ask before choosing a paid cloud service") and gets its own explicit sign-off when this phase
  is reached, not bundled in silently.

### Sandbox providers (R-486 → R-490, shipped 2026-09-19)

Between the streaming work and the UI overhaul below, the founder chose to build **every**
per-user sandbox provider pluggably behind one `SandboxLifecycleProvider` contract so the
platform can later switch on cost/speed/smoothness per user base: **R-486** E2B, **R-487**
Vercel Sandbox, **R-488** Daytona (all managed/paid, verified against each vendor's live API
shape), **R-489** gVisor via the local Docker Engine socket (free, self-hosted, loopback-only —
the founder's requested zero-cost development tier; WebContainers was researched and rejected
because it needs a paid commercial license), and **R-490** the `OMNISTACKAI_SANDBOX_PROVIDER`
selection surface (default `none`). No cloud keys exist in this environment, so live-cloud
verification is honestly deferred; each driver is unit-tested against recorded API shapes. None of
this is wired into the Studio's preview path yet — that, and per-user plan-based routing between
free and paid providers, are named follow-ups that need the UI overhaul first.

### Phase E-UI — Console UI overhaul (R-491 → R-496, approved 2026-09-19, **R-491 shipped**)

After the sandbox sequence, the founder asked directly why the platform UI is "just simple and
very ugly." The honest diagnosis, recorded here rather than softened: the console had **zero UI
dependencies** (only `next`/`react`/`react-dom` — no component library, icon set, font, or motion),
all styling was ~860 lines of hand-rolled CSS with one indigo accent, this was a deliberate and
*enforced* constraint (the R-470 `scripts/test.sh` gate blocked `tailwind|shadcn|…`, and the
Phase D plan carried a "no new UI dependency without strong justification" rule — visible above in
R-475's and R-481's "rather than a new dependency" choices), and every task since had prioritized
backend correctness over visual quality. Offered three options; the founder chose **Full UI
overhaul now** ("I need proper best UI based platform not just simple a page"; reference bar:
Emergent / Lovable / Dyad, screenshots to be re-shared).

**That decision supersedes the no-UI-dependency rule and the R-470 gate.** R-491 retired the gate
formally, with the decision recorded in its contract and in `scripts/test.sh`'s own comment — the
same way every earlier hard gate in this doc was revised only with explicit founder direction.

Stack (each verified against real, current docs during R-491, not assumed): Tailwind CSS v4 via
`@tailwindcss/postcss` (Next 16's own bundled guide); shadcn/ui on **Radix** with the **Nova**
preset (literally "Lucide / Geist" — the exact icon+font choice made independently; Radix chosen
deliberately over the CLI's new Base UI default); Geist + Geist Mono self-hosted via `next/font`;
`next-themes`, dark-first (every reference platform is a dark-first dev tool); Lucide icons;
`tw-animate-css` + CSS motion (no Framer Motion unless a later task proves a need). Design
language: a cool-tinted OKLCH neutral scale, **one** desaturated amber brand accent (no purple/blue
"AI gradient"), tinted shadows, real type scale, visible focus rings, skeletons over spinners,
designed empty/error states, sentence case.

Sequence (each its own `.ai/tasks/R-###.md` contract, full gates, one commit — unchanged
discipline):

1. **R-491 — UI foundation** *(shipped 2026-09-19)*. Gate retired; stack installed; dark-first
   token system with every legacy CSS name re-pointed so all existing pages keep rendering; new
   root layout (fonts, theme provider, toaster, metadata, branded `icon.svg`). Two real things
   found while doing it, both worked through rather than glossed over: the installed shadcn CLI
   (v4.21) had materially changed its flags and defaults, and `shadcn init` clobbered two legacy
   token names (`--muted`, `--accent`) that would have made light mode unreadable — fixed in the
   token rewrite. Every route live-smoked; 3,738 agent-engine tests unaffected.
2. **R-492 — Auth + app shell** *(shipped 2026-09-19)*. Login/register redesign with real inline
   validation and loading states; top navigation with current-page state; user menu on a real
   Radix menu; skip-link; branded 404; a real home/dashboard with live provider status instead of
   a link list. Kept the existing file layout rather than route groups because eight earlier
   `scripts/test.sh` contract blocks pin the current page paths — the shell is a shared component.
3. **R-493 — Studio core.** Chat rail + workspace shell rebuilt on shadcn primitives: a premium
   chat thread, the streaming state (shimmer/skeleton, live character count kept), composer, a
   designed "getting started" empty state; Lucide replaces the hand-rolled `studio-icons.tsx`.
4. **R-494 — Studio tabs.** Files as a real tree; Code viewer polish (line numbers, highlighting);
   Preview frame chrome (status pill, open-in-new-tab, width presets); Problems grouped by file
   with severity.
5. **R-495 — Settings + Fabric.** Provider status as real settings cards (Ready / Needs key), the
   theme toggle (in Settings, not a sun/moon switch), fabric/cost overview with proper data
   typography.
6. **R-496 — Motion, states & polish.** Staggered entries, hover/active/focus sweep, loading/
   empty/error audit, responsive pass, OG/meta, final audit checklist.

**Verification caveat, stated once here and in every task's evidence:** no browser-automation tool
exists in these sessions. Structure (served HTML, fonts, theme script, every route's status) is
verified by `curl` against the real running stack; visual quality is the one thing that cannot be,
so the founder is asked to eyeball `http://localhost:4321` after each task.

---

## 4. What does not change

- `services/agent-engine` stays Python-stdlib for its own tests (`task verify` stays offline/
  deterministic, 0 model/network calls) — Phase C adds a caller, not a rewrite.
- `studio/page.py` (the stdlib prototype) is not deleted. It remains the agent-engine's fast,
  dependency-free local proof harness for new agent-engine Tracker IDs.
- PostgreSQL stays the only control-plane database (Section 63.1/77 rule 11 — non-negotiable).
- Every standing rule from `AGENTS.md` / Brief Sections 77 & 92 still applies: contract before
  code, one Tracker ID at a time, real gate evidence, no secrets in source/logs/commits, stop
  and ask before a new paid cloud service or a materially different architecture beyond what's
  recorded here.

---

## 5. Open decisions (not blocking Phase A, but need an answer before later phases)

- Exact free-tier credit grant amount and paid-tier pricing/limits — business decision. `.env`'s
  current defaults (100 signup credits, `OMNISTACKAI_CREDITS_PER_USD=1000` i.e. 1 credit = $0.001)
  are reasonable v1 starting points, not a final pricing decision.
- ~~Credit metering unit: per-token, per-generation-call, or a hybrid~~ — **answered by R-472**:
  real dollar cost (derived from real token counts via `model_gateway`'s existing `PriceBook`,
  crossing the Go/Python boundary as an integer `cost_micros_usd`), converted to credits via a
  tunable `OMNISTACKAI_CREDITS_PER_USD` ratio — not literally per-token or per-call, a cost-based
  hybrid of both.
- Payment processor choice and timing (Phase E) — explicit "paid cloud service" sign-off needed
  when reached.
- Hosting target for the real deployment (which cloud, which region) — a "new infra" decision
  under this project's standing rules, needs explicit founder sign-off before Phase B/C ship to
  a real URL rather than local dev.
- Whether email verification / password-reset flows are required for the Phase A v1 cut, or can
  follow once the core auth loop works.
- ~~Live preview's execution trust model~~ — **answered 2026-09-18**: stays local-only, reusing the
  existing trusted-local `StudioPreviewManager` mechanism exactly as it runs today
  (`task agent-engine:studio:preview`); the console/control-plane only add a way to reach it, not a
  new hosted/sandboxed execution path. Revisit fully if/when this platform becomes genuinely
  multi-tenant-hosted — see the "Remaining Phase D roadmap" note under Phase D.

---

## 6. How to resume this if the session stops here

**Immediate next action as of 2026-09-19: R-493 (Studio core), the third item in "Phase E-UI —
Console UI overhaul" above; R-475 → R-481, R-482 → R-485, R-486 → R-490, R-491 and R-492 are all
shipped.** `.ai/PROJECT_STATE.yaml`'s `next_action` and `.ai/CURRENT_TASK.yaml` are the
authoritative pointers per `AGENTS.md`'s source-of-truth order (they win over this paragraph if
they ever disagree) — read them first, but they should already agree with this. The founder's
Emergent / Lovable / Dyad screenshots, once shared, shape R-493/R-494's Studio screens; R-492 does
not depend on them.

*(The numbered steps below are the original 2026-09-18 resume instructions for R-475, kept as the
historical record of how Phase D was resumed; the same discipline applies to every task above.)*

1. Read this file in full before touching code.
2. Read `.ai/PROJECT_STATE.yaml` and `.ai/CURRENT_TASK.yaml` — if they show a different
   in-progress task than the Phase D roadmap above, they win (per `AGENTS.md`'s source-of-truth
   order); reconcile before proceeding.
3. Write `.ai/tasks/R-475.md` following the Standard AI Task Contract (Brief Section 26) and this
   file's R-475 description above, then follow the project's normal contract-first, test-first,
   one-commit discipline — exactly as R-469 through R-474 already did.
4. Work through R-475 → R-481 in the order listed (each depends on visual/backend pieces the prior
   ones build) — do not start R-477 (chat UI) before R-476 (its backend) is done and gated; do not
   start R-480 (tabs) before R-475/R-477/R-479 all exist to assemble.
