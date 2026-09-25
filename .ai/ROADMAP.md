# OmniStackAI — Roadmap after R-558

Written for the founder and for whoever (human or agent) picks this up in a later session. It is
the durable answer to "what do we build next, in what order, and why" so that work can stop and
resume without losing the thread.

Status of this file: **proposed, awaiting founder approval.** Nothing here is started.

Last audited against the code: 2026-09-25, at commit `8f5a3a7` (R-558).

---

## 1. The goal, in one paragraph

A user describes what they want, once, and receives a working system — one app or a whole
ecosystem — with a modern UI, a real API, a real database, and apps that can reach the stores.
They can come back days later and change it, bring their own existing project, or start from a
template. The platform remembers more than a chat log, and it says plainly when it cannot do
something rather than quietly doing less.

## 2. What is true today (verified, not assumed)

| Capability | State | Evidence |
|---|---|---|
| Prompt → ecosystem of apps over one API and one DB | Works | R-554/555, verified live: 4 apps, 1 API |
| Backends in Go, Python, Node | All three generate real code | `assemble_project` with each strategy |
| Web + admin in Next.js | Works, and now uses its design system | R-558 |
| Modern UI, tokens, hover/focus/reduced-motion | Works | R-558 |
| Mobile in React Native | Works for single-app builds | `apps/mobile` assembled |
| **Mobile inside an ecosystem** | **Never generated** — every planned app is `mobile=none` | `plan_ecosystem_from_prompt` |
| **`flutter` / `native` / `auto` profiles** | **Silently produce nothing** — no app, no error | assembly test across all four profiles |
| **PWA "by default"** | **Not implemented** — no manifest, no service worker in generated web apps | `nextjs.py` |
| Store publishing | Scaffolding exists | `codegen/mobile_release.py` (R-546/547) |
| **Compile-verify-repair loop** | **Built, tested, never called** | `hybrid_repair.py`, zero callers in product |
| **Feature ceiling** | **6 CRUD shapes; anything else is dropped** | `route_wiring.wire_endpoint` returns `None` |
| **Editing days later** | Workspaces persist `ir.json`; console path is an in-memory LRU of 10 | `studio/session.py`, `studio/workspace.py` |
| Import an existing / GitHub project | Does not exist | no import path in repo |
| Context beyond chat | Knowledge + Skills, capped 24k chars; pgvector installed but **no embeddings table** | `intake/context.py`, migrations |
| Native iOS / Android | Enum values with no adapter | `codegen/adapter.py` |

## 3. Stack policy

**Defaults when the prompt is silent**

| Layer | Default | Reason |
|---|---|---|
| Public web | Next.js | SEO and SSR; the surface the UI work lives on. **The only web stack for now** |
| Admin | Next.js | tables, forms, the component ecosystem |
| Mobile | PWA (+ QR) when no app was asked for; **React Native as soon as one was** | instant preview with no store account, but a request for an app is answered with an app — never a website in its place |
| Backend | Python | quickest to read and run |
| Database | PostgreSQL | one database per ecosystem |

**On demand, read from the prompt**

| User asks for | Result | Works today |
|---|---|---|
| Go / Node backend | backend switches | yes |
| an app for a named role | React Native surface | no — ecosystem forces `none` |
| Flutter | **built in React Native, with the reason stated** | no — currently dropped in silence |
| React / Vite web | **built in Next.js, with the reason stated** | no — currently dropped in silence |
| native apps | **built in React Native for now, with the reason stated**; Kotlin + Compose / Swift + SwiftUI after R-575/576 | no |
| store publishing | EAS build + submit | partial |

**Three deliberate decisions**

- **One web stack for now: Next.js.** No React/Vite target. `nextjs.py` is ~74,350 lines; a second
  web adapter re-implements most of it, and Next.js *is* React, so the spend buys the user almost
  nothing this early. Revisit only on real customer demand.
- **One mobile stack for now: React Native.** Flutter is another hybrid in the same category, so
  it does not differentiate. Native (Kotlin + Compose, Swift + SwiftUI) does — no competitor
  generates it — which is why Native stays on the roadmap and Flutter does not.
- **Substitute and explain, never refuse and never drop.** A request for Flutter, React or native
  builds the nearest supported thing and says why in plain words. The user gets a working project
  and an honest sentence, not an error and not a silent downgrade. The same rule governs surfaces,
  not just stacks: **a request for an app is answered with an app.** Handing someone a website
  because the planner found it easier is the same failure wearing a different hat (R-562).

**Staying expandable is a design requirement, not a hope.** The substitution above must be driven
by a single capability registry that records which targets are actually implemented. Adding the
Flutter or native adapter later must then require **no change** to intake, planning or messaging:
the target becomes supported, the registry says so, and the substitution and its explanation stop
happening on their own. If adding an adapter later means editing the intake prompt or a hardcoded
list of excuses, R-559 was built wrong.

Two concrete consequences worth writing down now, because they are cheap today and expensive to
retrofit:

- **`MobileProfile.FLUTTER` stays in the IR.** The IR records what the user *asked for*
  (`flutter`) separately from what was *built* (`react_native`). Deleting the enum value would
  throw away the request; keeping it means that when the adapter lands we can find every project
  that wanted Flutter and offer to regenerate it.
- **The intake prompt stops advertising what does not exist.** `nl_to_ir` currently instructs the
  model to choose `flutter` when a mobile app is requested, which is how a silent drop begins. The
  list of offerable targets should come from the same registry, so it is correct by construction
  rather than by remembering to edit a prompt string.

## 4. Sequencing rule

The verify loop comes before IR v2 and before agentic mode. Both of those generate far more code
than today, and nothing currently compiles what is generated. Three defects in one week
(`_prefixed`, the streaming twin, the `@ts-expect-error` regression) all shipped because the
product was never built during the tests that claimed to cover it. Expanding output before
closing that loop multiplies the problem.

---

## 5. The task list

Sizes are relative effort: **S** a day or so, **M** a few days, **L** a week-plus, **XL** a
multi-week programme. They are not commitments.

### By theme (the same tasks, grouped for review)

Execution order is the phases below. Ids are stable labels, not a sequence: R-584/585 were added
after the first numbering and belong to Phase 2.

| Theme | Tasks |
|---|---|
| Tech stack — defaults and on demand | R-559, R-565, R-583 *(React and Flutter adapters: not planned)* |
| Apps / mobile | R-562, R-573, R-574, R-575, R-576 |
| Web + admin | R-572, R-583 *(no dedicated work: Next.js web/admin already works, R-558 fixed the UI)* |
| Verify loop | R-560, R-561 |
| IR v2 | R-564, R-565, R-566, R-567, R-568, R-569, R-570, R-571, R-572, R-584, R-585 |
| Agentic mode and existing projects | R-577, R-578, R-579 |
| Editing and customisation | R-563, R-584, R-585 |
| Planning intelligence and memory | R-580, R-581, R-582 |

### Phase 1 — Foundations

| ID | Task | Size | Why it comes first |
|---|---|---|---|
| R-559 ✅ | **Substitute and explain, never drop.** Flutter/React/native requests build the nearest supported target (RN, Next.js) and state the reason. Driven by a **capability registry**, so a later adapter turns the substitution off by itself. | S | Converts the worst failure mode (silently wrong) into an honest one, and is the seam every later stack plugs into |
| R-560 ✅ | **Wire the compile-verify-repair loop into the real build path.** It exists and has zero callers. | M | Everything below generates more code that nothing checks |
| R-561 | **Extend verification beyond model-written files** — deterministic files, the backend, and the mobile app, not just `app/*.tsx`. | M | R-549's bug was in a deterministic file, which the current loop refuses to touch |
| R-562 | **An app means an app, not a website.** The ecosystem planner forces `mobile=none`, so "customer + driver apps" returns four Next.js sites. Every named role that asked for an app gets a React Native surface; the monorepo carries more than one mobile app and the preview gives each its own QR. | M | Asking for an app and being handed a website is the most frustrating silent downgrade we have |
| R-563 | **One persistence path.** Move the console onto workspaces so an IR survives a restart and a project is editable days later. | M | "Come back in a week" depends entirely on this |

### Phase 2 — IR v2 (removes the ceiling)

| ID | Task | Size | Notes |
|---|---|---|---|
| R-564 | **IR v2 core**: capability layer, schema versioning, migration of existing v1 IRs | L | Backward compatibility is a hard requirement — projects exist |
| R-565 | **Stack selection as first-class IR**: the chosen web/admin/mobile/backend stack is carried, honoured, or refused with a reason | M | Makes §3 real instead of advisory |
| R-566 | **Workflows and state machines** — order lifecycle, dispatch, approval chains | L | The single biggest unlock for delivery/logistics/commerce |
| R-567 | **Money** — ledgers, payments, payouts, refunds, commission | L | Templates already prove the shape (Bazaar's double-entry ledger) |
| R-568 | **Background jobs and scheduling** | M | Settlements, reminders, cleanup |
| R-569 | **Realtime channels** — tracking, notifications, live status | M | Required by every delivery-style product |
| R-570 | **Permissions beyond role-on-endpoint** — ownership and row-level rules | M | "A driver sees only their own orders" is unexpressible today |
| R-571 | **Escape hatch**: behaviour the IR *declares* but the model *implements*, verified by the loop | L | Guarantees there is never again a hard ceiling — only a typed boundary |
| R-572 | **Shared contract package** — one generated `packages/` for types, API client and validation instead of three copies | M | Web, admin and mobile currently each get their own |
| R-584 | **Edits that change, not only add.** `apply_app_delta` is additive-only and *raises* on any existing entity, endpoint or screen, so "rename Post to Article", "remove the published field" or "change the order flow" returns an error rather than a change. | L | Directly blocks "customise my project" and "customise a template"; rename/remove needs migrations, so it is real work, not a flag |
| R-585 | **Template customisation as a first-class flow** — start from a catalogue template and change it substantially, not just append to it | M | Depends on R-584 and R-564; today a template edit goes through the same additive-only delta |

### Phase 3 — Mobile reach

| ID | Task | Size | Notes |
|---|---|---|---|
| R-573 | **PWA actually by default** — manifest, service worker, QR for generated projects (works for templates only today) | M | Closes a claim already being made |
| R-574 | **Store publishing on demand** — EAS build and submit, both stores, end to end | M | Builds on R-546/547 |
| R-575 | **Native Android** — Kotlin + Jetpack Compose | XL | Needs explicit founder go-ahead; new toolchain |
| R-576 | **Native iOS** — Swift + SwiftUI | XL | Same; plus Apple signing and review |

### Phase 4 — Agentic mode and existing projects

| ID | Task | Size | Notes |
|---|---|---|---|
| R-577 | **Agentic mode core** — plan → edit files → verify → repair, bounded and auditable | L | Depends on R-560/561 |
| R-578 | **Import an existing local project** — agentic mode, not IR mode | L | Deriving an IR from arbitrary code is not reliable; do not attempt it |
| R-579 | **GitHub import and push-back** | L | `git_connections` table already exists |
| R-580 | **Domain knowledge in ecosystem detection** — "logistics" implies drivers and dispatchers without naming them | M | Today "Create a Logistic platform" yields a single app |

### Phase 5 — Memory and intelligence

| ID | Task | Size | Notes |
|---|---|---|---|
| R-581 | **Semantic project memory** on pgvector — beyond the 24k-char cap and beyond chat | L | Extension installed, no embeddings table |
| R-582 | **Smarter IR synthesis** — multi-pass planning and self-critique before generation | L | Where "more features per prompt" is actually won |

### Deferred on purpose

| ID | Task | Condition |
|---|---|---|
| — | **React / Vite web adapter** | Not planned. Next.js is the one web stack; revisit only on real customer demand |
| — | **Flutter adapter** | Not planned. Requests fall back to React Native with a stated reason (R-559) |
| R-586 ✅ | **Make the CareClinic seed deterministic.** Its generator builds timestamps from `new Date()`, so the committed seed goes stale when the date rolls over and `task verify` fails every day. Found during R-559; confirmed on a clean checkout. | S | Do this next — it breaks the gate daily |
| R-583 | Next.js **static export mode** — the cheap answer to "I don't want SSR or Vercel" | Optional; do this before ever considering a React adapter |
| — | Multi-repo output, plan limits, `super_admin` area (Phase E) | After Phase 2 |

Both deferrals are reversible by design: when an adapter is written and registered, R-559's
registry stops substituting and the stack becomes a real option with no other code change.

---

## 6. What "done" looks like for the six reference prompts

Once Phases 1-3 land:

| Prompt | Components | Stack |
|---|---|---|
| Blog website | web + admin | Next.js · Python · Postgres |
| News + admin panel | web + admin, categories and media | Next.js · Python |
| Food delivery, customer + driver apps | marketing web + admin + customer app + driver app + merchant portal | Next.js + RN · one API |
| "Logistic platform" | web + admin + driver app (roles inferred from domain) | Next.js + RN |
| E-commerce + customer/merchant native apps | storefront + admin + two apps | RN **with the reason stated**; native after R-575/576 |
| Logistic + native + Go backend | as above | **Go** backend honoured; apps in RN with the reason stated |

## 7. Open questions for the founder

Recorded rather than left in a chat log, because each one changes the plan.

1. **Is R-582 (smarter IR synthesis) in the right phase?** IR v2 raises the ceiling; R-582 is what
   makes the model actually reach it. A single-pass prompt will not populate a rich schema well,
   so "maximum features" may depend on R-582 more than on any single Phase 2 task. It currently
   sits in Phase 5 and may deserve to be earlier.
2. **Native (R-575/576) needs an explicit go-ahead.** Two languages, two toolchains, two store
   pipelines. It is the clearest differentiator against every competitor and the most expensive
   item on this list.
3. **How much does template customisation matter?** R-585 assumes it is a real flow. If templates
   are mainly a showcase, it drops down the list; if they are a main entry point for users, it
   moves up and R-584 becomes urgent.

## 8. How to resume after a stop

1. Read `.ai/PROJECT_STATE.yaml` for the last completed task.
2. Read this file for what is next and why.
3. The next unstarted task is the first unstarted row, reading the phases in order. Ids are
   stable labels, not a running sequence — do not infer order from the number.
4. Follow `AGENTS.md` for the task contract, path scopes, gates and the stop/resume protocol.
