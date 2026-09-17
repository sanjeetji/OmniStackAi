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

**Phase B — Real Next.js console-web (proposed R-470)**
- Replace `apps/console-web`'s static HTML/JS with a Next.js (App Router, TypeScript) app.
- Login/signup/session screens wired to Phase A's endpoints.
- Carry forward the existing `overview.json` data contract and visual design as one section of
  the new app (the README already promises this continuity) rather than throwing it away.
- This is the point where `task bootstrap`/`task doctor` gain a real Node/npm toolchain
  requirement — a deliberate, explicit scope change from "dependency-free Stage 0," recorded
  here so it isn't a silent surprise later.

**Phase C — Bridge to agent-engine via the control-plane's Job API (proposed R-471)**
- Control-plane proxies "build this app" requests to the existing, unmodified `agent-engine`
  (hybrid UI synthesis, compile-repair, multi-turn edit — all of R-465–R-468 reused as-is).
- Every generation call is attributed to the authenticated user and debits their credit balance
  per Section 2's model; local-Ollama calls are logged but never debited.
- This is the only place credit enforcement actually lives — agent-engine itself stays
  credit-agnostic, matching "agents depend on provider interfaces, not billing logic."

**Phase D — The actual Studio UX, inside the real console-web (proposed R-472+)**
- This is where the earlier Lovable/Dyad/Emergent pattern research gets used for real: persistent
  chat + top tabs (Preview/Files/Code/Problems/Publish/More), one unified UI for every user with
  progressive disclosure (not persona branching), Model Provider settings surfacing the existing
  `model_gateway` (cloud + local Ollama, Dyad-style "Ready" state), a Problems tab wired to the
  already-existing `verify/compile.py`.
- Built as real Next.js components against the real API — not retrofitted into `studio/page.py`.

**Phase E — Plan/credit UX + admin surface (proposed R-473+)**
- Plan-gated feature access in the UI, a credit top-up flow, a `super_admin` console (user
  management, usage, plan overrides — the Dyad "Danger Zone" / Emergent admin-adjacent idea).
- Actual payment processor integration (Stripe or similar) is intentionally **not** included
  here — that is a "paid cloud service" decision under this project's standing rule ("stop and
  ask before choosing a paid cloud service") and gets its own explicit sign-off when this phase
  is reached, not bundled in silently.

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

- Exact free-tier credit grant amount and paid-tier pricing/limits — business decision.
- Credit metering unit: per-token, per-generation-call, or a hybrid — affects Phase C's ledger
  schema shape, worth deciding before Phase A's migration is finalized so the column shapes
  don't need a breaking change.
- Payment processor choice and timing (Phase E) — explicit "paid cloud service" sign-off needed
  when reached.
- Hosting target for the real deployment (which cloud, which region) — a "new infra" decision
  under this project's standing rules, needs explicit founder sign-off before Phase B/C ship to
  a real URL rather than local dev.
- Whether email verification / password-reset flows are required for the Phase A v1 cut, or can
  follow once the core auth loop works.

---

## 6. How to resume this if the session stops here

1. Read this file in full before touching code.
2. Read `.ai/PROJECT_STATE.yaml` and `.ai/CURRENT_TASK.yaml` — if they show a different
   in-progress task than "start Phase A," they win (per `AGENTS.md`'s source-of-truth order);
   reconcile before proceeding.
3. Write `.ai/tasks/R-469.md` for Phase A following the Standard AI Task Contract (Brief
   Section 26) and this file's Phase A description, then follow the project's normal
   contract-first, test-first, one-commit discipline.
4. Do not start Phase B before Phase A is done and gated; do not start Phase C before Phase B's
   login flow actually works end-to-end.
