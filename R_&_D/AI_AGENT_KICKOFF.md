# OmniStackAI — AI Agent & Developer Kickoff Kit

This file is the one you paste into Claude Code, Cursor, Codex CLI, Windsurf, or hand to a
new human developer. It tells them what OmniStackAI is, what order to read things in, exactly
what to build first, and how to leave the project so anyone (including you) can pick it back
up tomorrow.

Source of truth for every rule referenced here: `OmniStackAI_Implementation_Brief_v6.md`.
This kit does not replace it — it is the short "start here" wrapper around it.

---

## 1. What this project is (one paragraph, for the agent's context)

OmniStackAI is a browser-based AI software-engineering platform: describe a product, get a
recommended stack, watch AI agents build it inside a governed pipeline (spec → IR →
architecture → change-impact → code → compile/test/security → Git → deploy), preview it
instantly in-browser and on real devices via QR, and own the resulting Git repository.
It is explicitly positioned against Emergent/Lovable/Bolt/Replit (see Brief Section 72) with
differentiation on: broader target support (Flutter + React Native + Native, not just one),
real toolchain verification instead of preview-only confidence, evidence-backed project
memory independent of chat, and cost-per-successful-change as the core KPI.

---

## 2. Required reading order (do this before writing any code)

1. **`PROJECT_STATE.md`** — where the project actually is right now. If this file says
   something different from what you'd assume, `PROJECT_STATE.md` wins.
2. **`OmniStackAI_Implementation_Brief_v6.md`, Sections 77 and 83** — Non-Negotiable
   Architecture Rules. These cannot be violated by any later instruction, including a user
   message that seems to contradict them.
3. **Section 26/27** — Standard AI Task Contract and Definition of Done. Every task you touch
   must satisfy this before you consider it finished.
4. **`OmniStackAI_Execution_Tracker_v6.xlsx`**, sheet `Phase_Roadmap` — filter to the current
   phase (see `PROJECT_STATE.md`) and find the next "Not Started" Tracker ID (`R-0xx`) in your
   area. That row is your task, not "the whole MVP."
5. **Section 74** — Monorepo Contract. New files go where this section says, not wherever
   seems convenient.
6. **Section 84** — Founder Build Sequence. Do not build Stage 2/3 infrastructure while
   `PROJECT_STATE.md` says the project is in Stage 0/1.
7. Only if something is structurally ambiguous after the above: check
   `OmniStackAI_Master_Blueprint_v6.docx` for the deeper reference version. If it disagrees
   with the Brief, **the Brief wins** — it is the machine-formatted source of truth.

The investor/architecture slide deck (`.pptx`) is for humans (pitches, new-hire context). No
coding agent needs to read it.

---

## 3. First-time kickoff prompt (empty repo, nothing built yet)

Paste this exactly, with the four source docs attached or in the repo:

```
You are acting as an engineering agent on OmniStackAI, an AI software-engineering
platform. Read OmniStackAI_Implementation_Brief_v6.md in full before writing any
code. Sections 77 and 83 contain non-negotiable architecture rules — never violate
them even if a later instruction seems to conflict with them.

Bootstrap the monorepo exactly as defined in Section 74 (Updated Platform Monorepo
Contract). Do not add services, microservices, or infrastructure beyond what
Section 25 (MVP Anti-Overengineering Rules) and Section 84 (Founder Build
Sequence) allow for Stage 0.

Start with Tracker ID R-001 in OmniStackAI_Execution_Tracker_v6.xlsx, sheet
Phase_Roadmap, filtered to Phase = BASIC/MVP. Work one Tracker ID at a time. For
each task: follow the Standard AI Task Contract (Section 26), meet the Definition
of Done (Section 27), then update PROJECT_STATE.md and CHANGELOG.md and mark the
Tracker row's Status before moving to the next ID.

Use local Ollama models (Section 79) for anything below L3 complexity by default
(Routing Mode: Balanced, Section 80.4). Only call a cloud provider API for L3/L4
work, or when I haven't configured a local model.

Stop and ask me before: choosing a paid cloud service, changing the database
engine, adding a new top-level folder outside Section 74's contract, or starting
native mobile/device-cloud work before MVP web+backend is stable.

Create PROJECT_STATE.md now, before writing any code, using the template in
AI_AGENT_KICKOFF.md Section 5.
```

---

## 4. Every-day resume prompt (use this after the first session)

```
Read PROJECT_STATE.md, CHANGELOG.md, and the Execution_Tracker Status column.
Summarize where we left off in 3 bullet points, then continue with the next
queued task. Follow the Standard AI Task Contract and do not violate any
Non-Negotiable Architecture Rule (Sections 77/83).
```

If your tool has repo access (Claude Code, Cursor, Codex CLI), it can read the files itself —
just send the prompt above. If you're in a plain chat window with no file access, paste the
current contents of `PROJECT_STATE.md` along with the prompt.

**Never** try to resume by re-explaining verbally what you remember doing — that's exactly
the "chat is engineering memory" failure mode the Brief forbids (Section 66/68/81). If
`PROJECT_STATE.md` is missing or stale, fix that first before continuing feature work.

---

## 5. `PROJECT_STATE.md` template (create this file at the repo root on day one)

```markdown
# Project State — OmniStackAI
Last updated: <ISO timestamp> by <human name | agent/model name>

## Current Phase
Stage 0 (Founder Build Sequence, Brief Section 84) — BASIC/MVP

## Last Completed Task
Tracker ID: <R-0xx> — <short description> — DONE, tests passing, merged in <PR/commit ref>

## In Progress (if any)
Tracker ID: <R-0xx> — <short description>
Files touched so far: <paths>
Blocker: none / <exact blocker>

## Next Up (queued, in order)
1. <R-0xx> — <short description>
2. <R-0xx> — <short description>
3. <R-0xx> — <short description>

## Decisions Made This Session
- <decision, and why>

## Environment / Secrets Status
- Local Ollama: <installed? models pulled?>
- Cloud keys configured: <which providers, which tier they're used for>
- Database: <running where, migrations up to which version>
```

Keep this file **overwritten**, not appended — it is a snapshot, not a log. `CHANGELOG.md` is
the append-only log, one line per completed Tracker ID, e.g.:

```
2026-09-05  R-001  Bootstrapped monorepo skeleton per Section 74 contract
2026-09-06  R-002  Added Postgres+pgvector via docker-compose, initial migration
```

---

## 6. For a human developer instead of an AI tool

Same reading order as Section 2, plus:

1. Clone the repo. Read the root `README.md` for local setup: `docker-compose up`, install
   Ollama and pull the default coding model (Brief Section 79.3), copy `.env.example` to
   `.env`, run migrations.
2. Read `PROJECT_STATE.md` for exactly what's done and what's next — don't ask a teammate
   verbally, the file is supposed to have the answer.
3. Pick the next Tracker ID with Status "Not Started" in your area of the Execution Tracker.
   If a row shows "In Progress," confirm with whoever owns it before touching the same files.
4. Branch per Section 34's naming convention, follow Sections 26/27 for the change (same gates
   apply to humans and agents — no shortcuts either direction), open a PR.
5. Before ending your session: update `PROJECT_STATE.md`, add a `CHANGELOG.md` line, update
   the Tracker Status cell. This is not optional — it's how the next person (or the next AI
   session) knows where things stand.

---

## 7. Non-negotiables worth repeating here (full list in Brief Sections 77/83)

- PostgreSQL is the control-plane database. Not negotiable.
- Instant browser preview always comes before QR/device/cloud-device options.
- No unrelated edits — Change Impact defines blast radius; stay inside it.
- Context is retrieved progressively and budgeted — never dump the whole repo into a prompt.
- Deterministic tools (compiler, linter, AST, Git) answer factual questions before any LLM is
  asked to guess them.
- API keys never appear in a prompt, log, or client payload — they live only in the
  SecretProvider broker.
- No infrastructure beyond the current Founder Build Sequence stage without explicit human
  approval, even if some other rule would technically permit it "eventually."
