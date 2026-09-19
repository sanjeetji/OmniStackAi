# OmniStackAI — Platform Buildout (v1)

**Written 2026-09-19, after R-497. Companion to `OmniStackAI_Commercial_Platform_Kickoff_v1.md`.**
That document records how we got here (Phases A–E). This one records **what is still missing to
be a platform**, the decision behind every feature the founder asked for, and a per-task spec
(UI + database + API + flow) that a new session can pick up cold and implement.

Every task below has its own file in `R_&_D/specs/`. Each spec is self-contained: read it, and
you can start writing code without re-deriving anything.

---

## 1. Where we actually are

**The engine is strong; the platform around it is thin.** We can take a sentence and produce a
real multi-service codebase with a git history, stream it live, edit it in chat, type-check it,
and charge credits for the model calls. What we cannot do is *keep* that project, give it to the
user, or put it on the internet.

The founder's test on 2026-09-19 (build 7, "Simple CRM", opened from `172.28.64.242:4321`) found
exactly this, and every point was correct:

| Symptom | Real cause (verified in code, not assumed) |
| --- | --- |
| "Preview is not working" | The Studio was started in **build-only mode**; the preview manager is only wired in preview mode. And even in preview mode the generated app binds to `127.0.0.1:<port>`, so the iframe cannot load from another device. |
| "No option for Git / how does the user get the code?" | Every build **is** a real git repo with commits on the server — there is simply no UI, no download, and no remote. |
| "No publish, no domain" | No deployment backend exists anywhere in the repo. |
| "No project list / multiple projects" | `studio/history.py` is **in-memory only**. Proven live: after restarting the Studio, build 7's turns came back `[]` and its files `404`. Every project the founder made is gone. |
| "No Secrets / DB / SQL / Logs / Analytics / Connectors / Payments" | None of these exist as backend services. The UI honestly shows nothing rather than faking them. |

**Are we on the right track?** Yes on the two things that are hard to retrofit — a real codegen
engine with verification, and a real credit/provider fabric — and yes on discipline (284 shipped
task contracts, 3,738 offline tests, every change gated). **No on sequencing:** we polished the UI
(R-491…R-497) before the platform could remember a project. Phase F fixes the order, starting
with persistence.

---

## 2. Decisions on everything the founder listed

Legend — **Build now**: unblocked, starts immediately. **Gated**: needs an explicit founder
decision because it costs money or adds infrastructure. **Later**: real, but must wait for a
dependency. **No**: deliberately not building.

| # | Feature | Decision | Why |
| --- | --- | --- | --- |
| 1 | Projects: multiple, listed, switchable, named, with a home | **Build now — F-01** | Everything else keys off a project row. Today a restart erases the user's work. This is the single highest-value fix. |
| 2 | General (name, description, credits used in this project) | **Build now — F-01** | Real data once projects persist. |
| 3 | Preview that actually works | **Build now — F-02** | Two defects: wrong mode by default, and a loopback URL. Both fixable without new infrastructure. |
| 4 | Git: connect GitHub, push, user owns the code | **Build now — F-03** | The repo already exists per build. Needs one GitHub App registration (free, founder's account). Full mechanics in §3. |
| 5 | Skills + project Knowledge | **Build now — F-04** | Cheap, no gate, and it measurably improves generation because it is real prompt context. Design in §4. |
| 6 | Secrets (payment keys, third-party keys) | **Build now — F-05** | Prerequisite for payments, connectors and publish. AES-256-GCM with Go stdlib — no new dependency. |
| 7 | AI usage per project and overall; model configuration (API keys, model choice) | **Build now — F-06** | Makes the free-vs-paid strategy real: a user brings their own key or uses platform credits, and sees exactly what each project costs. |
| 8 | SEO & AI search (per-page SEO) | **Build now — F-07** | Pure codegen + a checklist. Generated apps get real metadata, sitemap, robots, `llms.txt`, JSON-LD. Differentiator: most competitors ship none of it. |
| 9 | Logs | **Build now — F-08** | Build logs and the generated app's own process logs already exist as streams; they just are not surfaced. |
| 10 | Chat: Stop, voice input, attachments | **Build now — F-08** | Stop is a real abort + server cancel. Voice is the browser's Web Speech API (free). Attachments are context (images need a vision model — stated in the UI). |
| 11 | Database explorer + SQL editor | **Later — F-09** (after F-02) | Preview already creates a **real per-app PostgreSQL** with the generated migrations, so this is honest data. Needs preview to be reliable first. |
| 12 | Security scan + Tests | **Later — F-10** | Same shape as the existing Problems tab (run a real tool, show real output). |
| 13 | Configuration (models, commands, env) | **Build now — folded into F-05/F-06** | It is Secrets + model settings; a separate "Configuration" page would duplicate them. |
| 14 | Publish the app | **Gated — G-01** | Decision needed: publish through the **user's own** Vercel/Netlify account (free for us, recommended) vs managed hosting we pay for. §3 shows how GitHub makes option 1 nearly free. |
| 15 | Domain: bring your own | **Gated — G-02** (founder approved the approach on 2026-09-19) | CNAME + verification on top of Publish. |
| 16 | Domain: buy through us | **No (not now)** | Requires a registrar reseller contract, pricing and money handling. Founder's decision: do not take on domain billing. Revisit after platform billing exists. |
| 17 | Payments **inside generated apps** (Stripe, Razorpay) | **Gated — G-04** | Codegen + Secrets; costs us nothing, but needs test accounts to verify honestly. |
| 18 | Payments **for our own billing** | **Gated — Phase E of the kickoff doc** | A paid-service decision, unchanged from the original rule. |
| 19 | Connectors (Google Calendar, Gmail, Analytics, …) | **Gated — G-03** | Each provider needs an OAuth app you register. Start with Google Analytics + transactional email; Calendar/Gmail next. |
| 20 | Google **Ads** connector | **No (not now)** | Near-zero value for a builder at this stage; high review burden on Google's side. |
| 21 | Analytics for published apps | **Later — G-05** | Nothing to measure until apps are public. |
| 22 | Web app / Mobile app tabs | **No (not now)** | Mobile is a hard gate the founder set. |
| 23 | Builder contests / community / marketing surfaces (Emergent) | **No** | Not a product feature; pure growth theatre at this stage. |

---

## 3. Git: exactly how "the customer gets the code in their repo" works

**Yes, a single "Connect GitHub" button can create the repo and push every change.** This is
standard, it is what Lovable does, and nothing about our architecture blocks it.

**What we already have.** Each build is a real git repository on the server with one commit per
build and one per edit (the founder's screenshot shows `Commit 90ba73984533`). We never had a
remote, a token, or a UI.

**The mechanism (F-03).**

1. **Register one GitHub App** for OmniStackAI (free, on the founder's GitHub account). A GitHub
   App — not a classic OAuth App — because it gets *fine-grained, revocable* permissions
   (`contents: write`, `administration: write` to create repos), the user picks which repos it
   may touch, tokens are short-lived (1 hour, auto-refreshed), and rate limits are per
   installation rather than per user.
2. **User clicks "Connect GitHub"** in Project → Git. Standard OAuth web flow → GitHub asks them
   to install the app on their account or organisation → callback to the control-plane → we store
   the installation id and the refresh token **encrypted** (F-05's key).
3. **"Create repository"**: `POST /user/repos` (or the installation's repo endpoint) with the
   name and private/public choice → GitHub returns the repo.
4. **Push**: the control-plane asks the agent-engine to push the project's existing repo with a
   short-lived installation token in the remote URL
   (`https://x-access-token:<token>@github.com/<owner>/<repo>.git`). First push sends the whole
   history; later edits push a single new commit.
5. **From then on** the user can `git clone`, run it locally, branch, open PRs — it is *their*
   repository in *their* account. We never need write access again if they revoke it.

**Why this also solves Publish cheaply.** Once the code lives in the user's GitHub, **Vercel and
Netlify can deploy it themselves** from that repo — their own free tier, their own account, no
hosting bill for us and no infrastructure to operate. That is why G-01 recommends
"Publish = GitHub + the user's Vercel/Netlify" as v1 instead of building managed hosting.
(GitHub Pages is *not* a candidate: it serves static files only, and our apps have a real backend
and database.)

**Token safety rules (binding for F-03):** tokens are encrypted at rest, never logged, never sent
to the browser, never written into a generated file, and scoped to the single repository the user
selected. The user can disconnect, which deletes the stored token.

---

## 4. Skills & Knowledge — the recommended design

The founder's instinct is right, and it is cheap because it is *prompt context*, not new
machinery. Two layers:

- **Knowledge (per project).** A free-text brief — purpose, audience, tech preferences, coding
  guidelines, domain rules. Injected into **every** build and edit for that project. This is
  Lovable's "Knowledge" page, and it is the single biggest quality lever a user has.
- **Skills (per user, reusable).** Named, versioned instruction sets the user writes once and
  reuses across projects: "Our design system", "Fintech compliance rules", "Hindi-first copy",
  "Always use Tailwind + shadcn". A user can:
  - mark skills as **default** (applied to every new project),
  - **attach** several to a specific project (applied to every message in it),
  - **mention one ad hoc** in the composer (`@design-system`) for a single message.

Active skills are shown as chips above the composer, so the user always knows what is steering
the model. Each skill is size-bounded (8 KB) and the total injected context is capped so a long
skill library can never blow the model's context window — the cap is enforced server-side and
reported honestly when it truncates.

**Why it is worth building now:** it is a few tables, a text editor and a prompt-assembly change;
it needs no gate; and it directly improves output quality, which is the product.

---

## 5. Why there were two commands — and the fix

The Studio has two modes on purpose:

- `agent-engine:studio:serve` — **build-only**. Generates code, never executes it. No Node
  toolchain, no PostgreSQL, no generated process running on your machine.
- `agent-engine:studio:preview` — **preview**. Installs the generated app's dependencies, applies
  its migrations to a real per-app PostgreSQL database and runs it.

The split is a genuine safety boundary (running model-generated code is the single riskiest thing
this product does, and it stays opt-in per the standing rule recorded in the kickoff doc). **But
exposing it as two commands the operator must remember was wrong** — the founder hit exactly that
and concluded the feature was broken.

**Fixed now** by `scripts/omnistack.sh`: one command starts the whole platform, **with preview on
by default** for local development, and `--no-preview` selects the safe mode explicitly:

```bash
./scripts/omnistack.sh up          # db + control-plane + Studio (preview) + console
./scripts/omnistack.sh status      # every component, port, health, and which Studio mode is live
./scripts/omnistack.sh logs studio -f
./scripts/omnistack.sh down
```

`task up` / `task down` / `task status` / `task logs` are thin aliases. The remaining half of the
problem — the preview URL being loopback-only, so it never loads from a phone or another laptop —
is **F-02**.

---

## 6. Build order and dependencies

```
F-01 Projects ─┬─ F-02 Preview ──┬─ F-09 DB explorer + SQL
               │                 └─ G-01 Publish ─┬─ G-02 Domain
               ├─ F-03 Git ──────────────────────┘        └─ G-05 Analytics
               ├─ F-04 Knowledge + Skills
               ├─ F-05 Secrets ──┬─ G-03 Connectors
               │                 └─ G-04 Payments in generated apps
               ├─ F-06 AI usage + model config
               ├─ F-07 SEO & AI search
               ├─ F-08 Logs + chat controls
               └─ F-10 Security + Tests
```

**Phase F — platform foundation (no gates; start immediately).**

| Task | Tracker | Title | Spec |
| --- | --- | --- | --- |
| F-01 | R-499 | Projects & workspaces — persistence, list, switcher, General | `specs/F-01-projects.md` |
| F-02 | R-500 | Preview that works — reachable URL, auto-start, honest status | `specs/F-02-preview.md` |
| F-03 | R-501 | Code ownership — download ZIP, connect GitHub, push | `specs/F-03-git.md` |
| F-04 | R-502 | Knowledge & Skills | `specs/F-04-skills.md` |
| F-05 | R-503 | Secrets — encrypted per-project configuration | `specs/F-05-secrets.md` |
| F-06 | R-504 | AI — model configuration (BYOK) and usage per project/account | `specs/F-06-ai-usage.md` |
| F-07 | R-505 | SEO & AI search | `specs/F-07-seo.md` |
| F-08 | R-506 | Logs + chat controls (Stop, voice, attachments) | `specs/F-08-logs-chat.md` |
| F-09 | R-507 | Database explorer + SQL editor | `specs/F-09-database.md` |
| F-10 | R-508 | Security scan + Tests | `specs/F-10-security-tests.md` |

**Phase G — publish & integrate (each needs a founder decision first).**

| Task | Tracker | Title | Gate | Spec |
| --- | --- | --- | --- | --- |
| G-01 | R-509 | Publish v1 — deploy from the user's GitHub to their Vercel/Netlify | Which hosting model? | `specs/G-01-publish.md` |
| G-02 | R-510 | Custom domain (bring your own) | After G-01 | `specs/G-02-domains.md` |
| G-03 | R-511 | Connectors — framework + Google Analytics + email | Which providers; OAuth apps to register | `specs/G-03-connectors.md` |
| G-04 | R-512 | Payments in generated apps — Stripe + Razorpay | Test accounts | `specs/G-04-payments.md` |
| G-05 | R-513 | Analytics for published apps | After G-01 | `specs/G-05-analytics.md` |

---

## 7. Conventions every spec follows

- **Contract first.** Each task starts with `.ai/tasks/R-###.md` + `.ai/CURRENT_TASK.yaml`, then
  code, then gates, then one commit — unchanged discipline.
- **The `/jobs/*` control-plane routes stay.** `scripts/test.sh` pins them (R-472…R-485). New work
  adds `/projects/*` alongside; the old routes keep working.
- **agent-engine stays Python-standard-library only** and `task verify` stays offline with zero
  model calls.
- **Go control-plane stays at exactly one direct dependency** (`scripts/test.sh` asserts it), so
  crypto, HTTP and JSON use the standard library.
- **No facades.** A screen ships only when the thing behind it is real. Where something is
  genuinely unavailable (no toolchain, no key, no deployment), the UI says so plainly.
- **Secrets never reach the browser**, never enter a log, never enter a generated file.
- **UI reference:** Lovable (`~/Desktop/AI_Platform_Screenshots/Lovable Screenshots`), per the
  R-497 decision. Each spec cites the screens it follows.
