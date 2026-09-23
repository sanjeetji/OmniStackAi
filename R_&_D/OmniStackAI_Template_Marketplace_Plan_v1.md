# OmniStackAI: Template Marketplace (Phase T), plan and handoff (v1)

**Written 2026-09-22, after R-528; updated 2026-09-23, after R-530. Companion to `OmniStackAI_Platform_Buildout_v1.md` (Phase F).**

This document lets any engineer or AI coding tool (Claude Code, Cursor, Codex, Gemini, …) continue
Phase T without this conversation. It covers:

- what exists;
- how a template is built and verified;
- the exact remaining work, with a specification for every remaining template;
- how to demo the platform.

The repository's own rules still apply on top of this document: `AGENTS.md`, `CLAUDE.md` and
`.ai/`.

---

## 1. Where we are (2026-09-23)

**The core platform works end to end and is on `main`** (Phases A to E, the ungated Phase F items, and T-0 to T-4).

| Area | State |
| --- | --- |
| Prompt to app | Chat in the Studio produces a real repo (Next.js + API + DB) with git history. Streaming build, chat edits, Problems (tsc), live preview. |
| Projects | Persisted per user in the control-plane: list, rename, reopen, manage page. |
| Preview | Every project runs locally on demand, as a production build served behind the console's same-origin proxy (`/preview/<project>/<app>`), so it also works from other devices on the LAN. Multi-app template projects run all apps plus a fresh Postgres with migrations and seed. |
| Template marketplace (T-1 to T-3) | `/templates` (search, categories, cards) and `/templates/<slug>` (apps, roles, features, stack, demo logins, "Use template"). "Use template" copies the golden repo into a new project with its own git history. |
| Code-edit agent (T-4) | Template projects are customised by chat. It picks files, edits them, runs tsc and other checks, gets one repair round, then commits the touched paths or rolls back fully. |
| Model providers | Google Gemini (`gemini-3-flash-preview`, key in the untracked `.env`), local Ollama fallback. |
| Tests | `task verify`: 3,980 offline tests, 0 model calls. `./scripts/smoke-core.sh`: the full core loop against the running stack. |

**Templates: 1 of 10 published.** RideNow (mobility) is complete — API, rider app, driver app and
operations console — and listed as `templates/catalog/ride-now/` v1.0.0 with a cover and 48 screens
captured from the running apps. One item of the publish checklist still owes evidence: the three
scripted chat edits (§5, item 9) need a model provider, which the machine that finished R-530 did
not have.

| Task | What | Status |
| --- | --- | --- |
| R-518 | T-0 stabilise the core | done |
| R-519 to R-523 | T-1 format and registry, T-2 multi-app preview, T-3 marketplace UI | done |
| R-525 | T-4 code-edit agent | done |
| R-526 | RideNow 1/4: API, database, demo data | done |
| R-527 | RideNow 2/4: rider web app and `packages/shared` | done |
| R-528 | RideNow 3/4: driver PWA | done |
| R-529 | This document, the draft-template demo script, RideNow's draft manifest | done |
| R-530 | RideNow 4/4: operations console, 48 screenshots, published `ride-now` v1.0.0 | done |
| R-531 | Bazaar 1/4 (§6.1): API, database and demo data | done |
| R-532 | Bazaar 2/4 (§6.1): Shared library and buyer storefront web app | done |
| R-533 | Bazaar 3/4 (§6.1): Artisan vendor portal | done |
| R-534 | Bazaar 4/4 (§6.1): Operations console, 48 screenshots, published `bazaar` v1.0.0 | done |
| R-535 | CareClinic 1/4 (§6.2): Clinical care API, database and demo data | done |
| **R-536** | **CareClinic 2/4 (§6.2): Shared library and patient web app** | **next** |
| later | 8 more templates (§6), then T-5 workspace upgrades (§7) | planned |

**R-530 also fixed the preview path**, which no browser had ever driven before: previews now build
each app once and serve the production build (a dev server's hot-reload socket cannot pass the
console proxy, and a Turbopack dev app never hydrates without it), and the proxy no longer forwards
`content-encoding` for a body it has already decoded. One known limit remains: client-side link
navigation inside a preview falls back to a full page load, because the console is itself a Next app
and answers RSC navigation requests to `/preview/...` before the proxy code runs.

---

## 2. The template model (decided with the founder, 2026-09-21)

- **A template is a hand-built golden repository, not generated at request time.** It has real UI,
  API and database, and every app has the full page set for its role. The founder's rule is
  "maximum pages, deep domain features, never just a home page".
- **The original is identical for everyone and never changes for users.** "Use template" creates
  the user's own project: a copy with a fresh git history, recording template slug, version and
  content digest.
- **Users customise only their copy**, by chat through the code-edit agent, or with any tool after
  pushing to GitHub. They add, remove or change features. New template versions apply to new
  projects only.
- **Everything runs without credentials.** Payments, SMS, email, maps and storage are mocks behind
  interfaces, with a `.env.example` saying where a real provider plugs in.
- **Each template looks different**: its own tokens, typeface, layout and component styling.

Why not generate templates from the IR? The generator cannot express the needed depth: custom
actions, state machines, money, multi-app shared APIs, or distinct design systems.
IR-generated apps also all share one look. Templates are therefore written by hand, to a fixed
stack, and verified like product code.

---

## 3. Anatomy of a template

```
templates/catalog/<slug>/            (_<slug>/ while it is a hidden draft)
  template.json                      manifest: schema in templates/catalog/README.md
  capture.mjs                        how to screenshot this template (§4); not copied to users
  media/                             cover.jpg, screens.json and one image per page (§4)
  repo/                              the golden repository users receive
    package.json, pnpm-workspace.yaml (apps/*, services/*, packages/*), .gitignore, .env.example
    services/api/                    one TypeScript API for every app
      src/{config,db,app,index,openapi}.ts
      src/lib/…                      pure domain logic (unit-tested)
      src/auth/…                     HS256 JWT on node:crypto, scrypt, role middleware
      src/providers/…                mocks behind interfaces (payments, sms, maps, email, storage)
      src/services/…                 transactional domain services (ledger, notify, …)
      src/routes/…                   one Hono router per role + public + support + stream (SSE)
      migrations/NNN_*.sql           idempotent (the runner re-applies every file), no ";" in comments
      seed/001_demo.sql              generated by scripts/generate-seed.mjs (deterministic)
      scripts/generate-seed.mjs
      test/*.test.ts                 pure unit tests (offline) + workflow.test.ts (live, needs API_BASE)
      README.md
    packages/shared/                 API types, typed client (token refresh), SSE hook, formatters, shared widgets
    apps/<customer>/                 Next.js web app
    apps/<provider>/                 Next.js PWA (manifest, icons), shown in a phone frame
    apps/admin/                      Next.js operations app
```

**Pinned stack (identical in every template, so the code agent and maintenance stay simple).**

- **Apps:** Next 16.3.5 (Turbopack), React 19.3.0, Tailwind 4.3.3 via `@tailwindcss/postcss`,
  lucide-react 1.47.0, TypeScript 5.9.2.
- **API:** Hono 4.7.11, `@hono/node-server` 1.14.4, pg 8.13.1. It runs as `.ts` natively on
  Node ≥ 22.18 (`erasableSyntaxOnly`, `allowImportingTsExtensions`), with no build step.

**Next 16 facts that bite:**

- `params` are async. In client pages, use `useParams()`.
- `next.config.mjs` must set `basePath: process.env.BASE_PATH`, `transpilePackages` for the shared
  package, and `allowedDevOrigins`.
- A plain-string `title` in a nested layout resets the root title template. Parent segments must
  re-declare `{ default, template }`.
- Links must use `<Link href="/x">` (base-path aware), never a root-relative `<a href="/">`. The
  code agent's verifier rejects the latter.

**Preview contract:**

- Apps get `PORT` and `BASE_PATH`, plus `API_URL` and `NEXT_PUBLIC_API_URL` (a relative path
  through the console proxy).
- The API gets `DATABASE_URL`, `JWT_SECRET` and `PUBLIC_BASE_PATH`, and must answer `GET /health`.

**RideNow is the reference implementation.** Copy its structure, auth, ledger, SSE hub, providers,
seed generator, test layout and app shells, then change the domain and the design.

---

## 4. How to build one template (the method that worked for RideNow)

Split every template into **four tasks**, one Tracker ID each, one commit each:

1. **API + database + demo data.** Write the whole-template master plan in this task's contract:
   every app's page list, the domain rules and the seed plan. RideNow's is `.ai/tasks/R-526.md`.
2. **Customer app + `packages/shared`.**
3. **Provider app** (PWA).
4. **Admin app + publish.** This covers `template.json`, cover and screenshots, removing the `_`,
   the §5 checklist, and 3 scripted chat edits.

**Per-task discipline** (from `AGENTS.md`; do not skip any of it):

1. Write the contract first: `.ai/tasks/R-###.md` and `.ai/CURRENT_TASK.yaml`.
2. Build.
3. Record only real gate evidence in the contract.
4. Update `.ai/HANDOFF.md`, `.ai/PROJECT_STATE.yaml`, `.ai/WORK_LOG.md`, `PROJECT_STATE.md`,
   `CHANGELOG.md`, `docs/PROGRESS.md` and `docs/RESUME_PROMPT.md`.
5. Add a `scripts/test.sh` block.
6. Make one commit, authored `sanjeetji <sk698166@gmail.com>`, with the AI co-author trailer.
7. Push to `origin HEAD:main` and `HEAD:ai/R-517-node-backend`.
8. Verify `HEAD == origin/main` and a clean tree.

Never commit `.claude/`, `.env` or secrets. `task verify` must stay offline with 0 model calls.

**Build and test loop.**

- **Never install inside the catalogue** (the validator forbids `node_modules`). Copy to a scratch
  folder and work there:
  `rsync -a --exclude node_modules --exclude .next templates/catalog/_<slug>/repo/ $SCRATCH/x/`,
  then `pnpm install`, `tsc --noEmit` per app and service, `next build` per app, and
  `node --test test/*.test.ts` for the API unit tests.
  - Because of this, VS Code shows "JSX.IntrinsicElements" errors in the draft folder. They are
    harmless; trust the scratch type-check.
- **Live:** `./scripts/preview-drafts.sh` (drafts appear in the marketplace). Then in the console:
  Templates → the template → Use template → Preview.
  - Or by API with a console cookie jar: `POST /api/templates/<slug>/use`, then
    `POST /api/projects/<id>/preview`, then poll `GET /api/projects/<id>/preview` until `ready`.
- **Workflow test:** `API_BASE=<api_url from the preview status> node --test test/workflow.test.ts`
  runs the live end-to-end scenarios against a fresh database.
- **After editing a draft, run `./scripts/preview-drafts.sh` again.** The Studio computes each
  template's digest at start-up, and a changed file makes "Use template" refuse with "the copied
  files do not match the template digest". That refusal is the integrity check working.
- **Offline gates for the template** go in `services/agent-engine/tests/test_template_<slug>.py`
  (see `test_template_ride_now.py`):
  - the API unit tests pass;
  - the committed seed equals its generator's output;
  - every page exists;
  - every API path the apps call exists in the API's route table.

**Seed data rules.** Deterministic (seeded PRNG), realistic Indian names, places and prices, at least
40 records for every main entity, and a balanced money ledger. Include every status (active,
cancelled, pending, …) so every screen has data, and three documented demo logins.

---

## 5. The publish checklist ("§43"), required before `_` is removed

1. Every stakeholder role has its own app or area, with the **full page set** from the master
   plan.
2. The core workflows run **end to end live** across apps, proven by `workflow.test.ts` against
   the preview.
3. Auth really works: hashing, refresh rotation, and role-checked routes on both API and screens.
   A role cannot use another role's app (for example, 403 for a rider in the driver app).
4. Data is persisted and shared: every app reads and writes the one API and database.
5. At least 40 realistic seed records per main entity, and a balanced ledger where money exists.
6. Every screen has loading, empty and error states. Layouts work on phone and desktop.
   Accessibility basics are in place: labels, focus, `aria` on custom controls.
7. `template.json` is complete: description, apps, roles, entities, features, integrations,
   demo users, stack, **cover and at least 4 screenshots** in `media/`.
8. `repo/README.md` per service explains running, demo logins, architecture and where to plug in
   real providers.
9. **Three scripted chat edits pass through the code agent** on a fresh project, each re-passing
   tsc and the tests:
   - add a feature;
   - remove a feature;
   - change a workflow.
10. Offline gates are in `task verify`; `smoke-core.sh` passes.

**Screenshots: solved in R-530** with option (b), Playwright in a scratch folder only. Use the
runner and give the template its own plan:

```bash
npm i --prefix "$SCRATCH/pw" playwright && npx --prefix "$SCRATCH/pw" playwright install chromium-headless-shell
node scripts/capture-template-screens.mjs --template templates/catalog/<slug> --playwright "$SCRATCH/pw" \
  --api http://127.0.0.1:4000 --app <app>=http://127.0.0.1:3101 ...
```

`templates/catalog/<slug>/capture.mjs` lists the demo users, the storage key each app uses and one
`shot()` per page, and can stage live scenes through the API first (RideNow books a ride so the
driver's offer sheet, the rider's live trip and the ops live map are real). The runner writes
`media/<app>/<name>.jpg`, a `media/screens.json` describing every screen, and a composed cover. Run
the apps as production builds against a freshly seeded database; never capture a dev server.

---

## 6. The remaining templates: specifications

Order (from the approved plan): **Bazaar → CareClinic → Pocket → LearnHub → Glow → FreshCart →
Estately → FixIt → Inkwell Press.** Tracker IDs are assigned when each task starts (R-531
onwards), 4 tasks per template. Every template is Bengaluru/India-flavoured (INR, Indian names)
unless noted. All providers are mocks.

Each spec lists: apps, roles, look, pages, domain core, money, realtime, seed, and the live workflow
tests the template must pass. The first task of each template expands its spec into a full master
plan contract.

### 6.1 Bazaar: multi-vendor marketplace (commerce)

- **Apps:**
  - `storefront` (web)
  - `vendor` (web, responsive)
  - `admin`
  - `api`
- **Roles:** shopper, vendor, admin.
- **Look:** editorial retail. Warm off-white, ink black, one terracotta accent, serif display
  (Fraunces) with a sans body. Large product imagery (generated SVG/gradient placeholders, no
  stock photos).
- **Storefront:**
  - home (collections, deals, top vendors);
  - search with facets (category, price, rating, vendor, in stock) and sort;
  - category, product (gallery, variants size/colour, stock, delivery estimate by pincode, reviews
    with photos, Q&A);
  - vendor shop page;
  - wishlist; cart split by vendor; coupon; checkout (address book, delivery slot, payment:
    card/UPI mock/COD);
  - order confirmation; orders and order detail with per-shipment tracking; returns and refunds
    requests; reviews;
  - account, addresses, notifications, help.
- **Vendor:**
  - onboarding (KYC, bank, store profile);
  - dashboard (sales, orders to ship, low stock);
  - products (create/edit with variants, images, bulk price/stock edit, CSV import);
  - inventory;
  - orders (accept, pack, generate label, hand over), returns (approve/reject);
  - payouts (settlement statement), reviews (reply), coupons, store settings.
- **Admin:**
  - dashboard (GMV, orders, take rate);
  - vendors (approve, suspend, commission rate);
  - catalogue moderation; categories; orders and disputes; refunds; payouts run; coupons/banners;
  - users; audit.
- **Domain:**
  - one order per checkout, split into **shipments per vendor**;
  - shipment state machine `placed → accepted → packed → shipped → delivered` (plus
    `cancelled/returned`);
  - stock reserved at checkout and released on cancel/timeout;
  - commission per vendor/category; ledger for platform, vendors and shoppers (refunds to
    wallet/original);
  - weekly settlement.
- **Realtime:** new order to vendor, and shipment status to the shopper.
- **Seed:** 25 vendors, 400 products with variants, 60 shoppers, 600 orders over 60 days, reviews,
  returns and payouts.
- **Workflows:**
  - shopper buys from 2 vendors, both ship, delivered, and settlement nets correctly;
  - out-of-stock race is refused;
  - return: vendor approves, refund, stock restored;
  - vendor cannot see another vendor's orders.

### 6.2 CareClinic: clinic + telemedicine (healthcare)

- **Apps:**
  - `patient` (web)
  - `doctor` (web, tablet-first)
  - `admin` (front desk + clinic admin)
  - `api`
- **Roles:** patient, doctor, receptionist, admin.
- **Look:** calm clinical. Soft teal and white, generous whitespace, rounded, Plus Jakarta Sans.
  Accessible contrast is mandatory.
- **Patient:**
  - find a doctor (specialty, language, fee, next slot), doctor profile;
  - book in-clinic or video; slot picker; pay consultation fee (mock);
  - appointments (reschedule/cancel with policy);
  - video visit room (mock: WebRTC loopback or a clear "demo call" screen with a chat panel);
  - prescriptions (PDF-like view, download);
  - lab reports; health records (vitals, allergies, conditions); family members;
  - invoices; reminders/notifications; help.
- **Doctor:**
  - today's queue (checked-in, waiting, in consult);
  - schedule and availability rules (weekly hours, breaks, leave);
  - consultation screen: history, vitals, notes (SOAP), diagnosis (ICD-10 subset), prescription
    builder (drug search, dosage, duration, instructions), lab orders, follow-up;
  - patient list and chart; earnings; reviews.
- **Admin / reception:**
  - front desk (check-in, walk-ins, token numbers);
  - doctors (onboard, fees, schedules); rooms;
  - billing (invoices, refunds), lab results upload;
  - reports (footfall, revenue, no-shows); settings; audit.
- **Domain:**
  - slot generation from availability rules; double-booking impossible (DB constraint);
  - appointment machine `booked → checked_in → in_consult → completed` (plus
    `cancelled/no_show`);
  - cancellation policy fees;
  - prescriptions immutable once signed;
  - a patient sees only their own and their family's records;
  - doctors see only their patients; audit on every chart access.
- **Seed:** 12 doctors across 8 specialties, 150 patients, 900 appointments, prescriptions, lab
  reports.
- **Workflows:**
  - book, then check-in, consult, prescription, invoice paid, and the patient sees the
    prescription;
  - concurrent booking of the same slot: one wins;
  - a doctor cannot read another doctor's patient chart without an appointment;
  - reschedule and cancel fees.

### 6.3 Pocket: digital wallet (fintech)

- **Apps:**
  - `wallet` (PWA)
  - `merchant` (web)
  - `admin` (risk/ops)
  - `api`
- **Roles:** user, merchant, admin (ops, risk).
- **Look:** confident fintech. Deep indigo-black with electric lime, dense numerals in a tabular
  mono (JetBrains Mono for figures), Manrope for text.
- **Wallet:**
  - onboarding with phone OTP and KYC tiers (min/full KYC with limits);
  - home (balance, quick actions);
  - add money (card/UPI/netbanking mocks); send to contact/phone; request money;
  - scan & pay merchant (QR scanner with a camera fallback to code entry); bill payments (mock
    billers);
  - transactions with filters and statements (monthly PDF-like view); disputes;
  - cards (virtual card, freeze), limits;
  - security (PIN, devices); rewards/cashback; notifications; help.
- **Merchant:**
  - onboarding (KYB); QR codes; payment links; collect requests; transactions; refunds;
  - settlements (T+1); payouts; staff users; reports; API keys (mock) and webhooks log.
- **Admin:**
  - KYC review queue; user/merchant search; transaction monitor; risk rules (velocity, amount);
  - flagged transactions (hold/release); disputes; limits configuration; ledger explorer;
    reconciliation; audit.
- **Domain:**
  - **strict double-entry ledger** (every transfer is two postings; balances derived and checked);
  - idempotency keys on every money POST;
  - transaction PIN;
  - limits per KYC tier (daily, monthly, per transaction);
  - risk rules can hold a transfer for review;
  - refunds reverse postings; merchant MDR fee; T+1 settlement batch.
- **Seed:** 80 users, 20 merchants, 3,000 transactions with realistic patterns, a few flagged.
- **Workflows:**
  - P2P send with PIN; replaying the same idempotency key does not double-send;
  - over-limit refused; risky transfer held, admin releases;
  - merchant QR payment, refund, settlement;
  - ledger sums to zero across all accounts.

### 6.4 LearnHub: LMS + course marketplace (education)

- **Apps:**
  - `learner` (web)
  - `studio` (instructor, web)
  - `admin`
  - `api`
- **Roles:** learner, instructor, admin.
- **Look:** bright and friendly. Cream background, cobalt and sunflower accents, rounded cards,
  Nunito for text and Outfit for headings.
- **Learner:**
  - catalogue (search, filters: level, duration, price, rating); course page (curriculum,
    preview lessons, instructor, reviews);
  - cart and checkout (coupons);
  - my learning; course player (video via a placeholder/looping sample, text lessons, attachments,
    notes, progress, next/prev);
  - quizzes (MCQ, multi-select, timed, instant feedback); assignments (submit text/file);
  - certificates (verifiable page with id);
  - Q&A per lecture; reviews; wishlist; notifications; profile.
- **Studio:**
  - dashboard (enrolments, revenue, ratings);
  - course builder (sections, lectures, drag reorder, quiz builder, assignment rubric, pricing,
    publish for review);
  - learners and progress; grade assignments; Q&A inbox; announcements; coupons; payouts.
- **Admin:**
  - course review queue (approve/reject with notes); categories; users; instructors (revenue
    share); orders and refunds; payouts; featured; reports; audit.
- **Domain:**
  - course states `draft → in_review → published` (plus `rejected/archived`);
  - enrolment on payment;
  - progress per lecture; completion rules (all lectures and quizzes passed) issue a certificate;
  - revenue share ledger; a refund within 7 days if under 30% progress.
- **Seed:** 18 instructors, 60 courses (with real-looking curricula), 400 learners, enrolments and
  progress, reviews.
- **Workflows:**
  - enrol, complete lectures, pass the quiz, get the certificate (verify page works);
  - an instructor's course goes through review;
  - refund rule enforced;
  - a learner cannot open lectures of a course they have not bought (except previews).

### 6.5 Glow: salon & spa booking (services)

- **Apps:**
  - `booking` (web)
  - `staff` (PWA)
  - `admin` (salon manager)
  - `api`
- **Roles:** client, stylist/therapist, manager.
- **Look:** soft luxury. Blush and charcoal, lots of air, Cormorant Garamond headings, Inter
  Tight body, subtle grain.
- **Booking:**
  - salon home (services, offers, team, reviews, gallery);
  - service menu (categories, duration, price by stylist level);
  - book: service(s), then stylist or "any", then a slot, then add-ons, then pay a deposit;
  - packages and memberships; gift cards; appointments (reschedule/cancel); reviews; loyalty
    points; account; notifications.
- **Staff:**
  - my day (timeline); check-in client; service notes and client preferences/allergies;
  - mark complete (products used); availability and leave; tips and commissions; my reviews.
- **Admin:**
  - calendar (all staff, drag to move); walk-ins; clients (history, notes);
  - services and pricing; staff (skills, commission %); products/inventory (used and sold);
  - POS checkout (split payment, tip);
  - memberships, gift cards, offers; reports (revenue, utilisation, rebook rate); settings.
- **Domain:**
  - multi-service bookings need contiguous time on a qualified staff member;
  - buffers between appointments;
  - deposits and no-show fee; memberships deduct sessions; gift card balance ledger;
  - commission per service/product.
- **Seed:** 1 salon with 2 branches, 14 staff, 45 services, 200 clients, 1,500 appointments.
- **Workflows:**
  - book a 2-service visit, staff completes it, POS checkout with tip, commission booked;
  - overlapping booking refused;
  - membership session deducted; no-show fee charged.

### 6.6 FreshCart: quick-commerce grocery (commerce)

- **Apps:**
  - `shop` (PWA)
  - `rider` (delivery partner PWA)
  - `admin` (dark-store ops)
  - `api`
- **Roles:** customer, delivery partner, store picker, admin.
- **Look:** fresh and fast. White, leaf green, citrus yellow highlights, chunky rounded type
  (Rubik), big product tiles, a "10-minute" promise bar.
- **Shop:**
  - location to the serviceable dark store; home (categories, deals, reorder);
  - search; category and product; cart with a free-delivery threshold and substitutions
    preference;
  - slot or express; checkout (wallet/UPI/card mocks, COD);
  - live order tracking (picking, packed, rider on map, arriving); rate; orders; wallet;
    addresses; help (missing item, refund).
- **Rider:**
  - online/offline; order offers; pickup at store (verify items bag count); navigate;
  - deliver with OTP; cash collected; earnings; payouts; history.
- **Admin:**
  - store ops board (orders by stage with SLA timers); picker screen (pick list by aisle, mark
    missing, suggest substitute);
  - inventory per store (stock, expiry, reorder); catalogue; pricing and deals;
  - riders and zones; customers; refunds; reports (SLA, fill rate).
- **Domain:**
  - per-store stock with reservation;
  - order machine `placed → picking → packed → assigned → out_for_delivery → delivered`;
  - SLA timers; substitutions need customer approval (or auto by preference);
  - partial refunds for missing items; rider assignment by proximity; delivery OTP.
- **Seed:** 2 dark stores, 500 SKUs with stock, 120 customers, 900 orders, 20 riders.
- **Workflows:**
  - order, pick with 1 missing item substituted and approved, packed, rider delivers with OTP;
  - partial refund correct;
  - stock never negative under concurrent orders.

### 6.7 Estately: property marketplace + agent CRM (real estate)

- **Apps:**
  - `listings` (web)
  - `crm` (agent, web)
  - `admin`
  - `api`
- **Roles:** buyer/tenant, owner, agent, admin.
- **Look:** architectural. Stone and graphite, a brass accent, big imagery blocks, Space Grotesk
  headings, a restrained grid.
- **Listings:**
  - search (buy/rent, city/locality, price, BHK, area, furnishing, amenities) with list and map
    (offline SVG city map like RideNow's);
  - listing page (gallery, floor plan placeholder, amenities, price history, EMI calculator,
    nearby, similar);
  - shortlist; compare; schedule a visit; contact agent (lead);
  - owner: post a property (multi-step, photos), my listings, leads;
  - saved searches with alerts; account.
- **CRM:**
  - pipeline board (new, contacted, visit scheduled, negotiation, won, lost) with drag;
  - leads list and detail (timeline, notes, tasks, calls log);
  - visits calendar; listings I manage (edit, mark sold/rented);
  - deals (offer, token amount, agreement checklist); commissions; reports.
- **Admin:**
  - listing moderation (verify, reject, feature); agents (verify RERA id, assign areas); owners;
    leads distribution rules; localities; plans (featured listing payments, mock); reports; audit.
- **Domain:**
  - listing states `draft → pending_review → live → under_offer → sold/rented` (plus `expired`);
  - lead routing to the area agent by round-robin; visit slots per agent;
  - deal commission;
  - owners see only their leads; saved-search matching creates notifications.
- **Seed:** 350 listings across 25 localities, 40 agents, 200 leads in all stages, visits, deals.
- **Workflows:**
  - buyer shortlists and books a visit, the agent moves the lead through the pipeline, deal won,
    listing sold;
  - a new listing matching a saved search notifies the buyer;
  - routing assigns the right agent.

### 6.8 FixIt: home-services marketplace (services)

- **Apps:**
  - `customer` (web)
  - `pro` (technician PWA)
  - `admin`
  - `api`
- **Roles:** customer, technician, admin.
- **Look:** utilitarian-friendly. Safety orange and slate, bold icons, IBM Plex Sans, clear
  step UI.
- **Customer:**
  - services (AC repair, plumbing, cleaning, electrician, pest control, appliance) with fixed-price
    menus and inspection-based jobs;
  - book (address, slot, problem photos); quote approval for inspection jobs;
  - live job status (technician assigned, en route, started, done); pay (wallet/card mocks);
  - warranty claims (30 days); rate; bookings; wallet; addresses; subscriptions (AMC plans);
    help.
- **Pro:**
  - availability and service areas; job offers; job detail (checklist, photos before/after);
  - raise quote with parts; start/complete with a customer OTP; earnings; payouts;
  - training/certification status; ratings.
- **Admin:**
  - service catalogue and pricing; technicians (verify, skills, areas); dispatch board (unassigned
    jobs, manual assign); quotes review above a threshold; warranty claims; payouts; reports.
- **Domain:**
  - job machine `booked → assigned → en_route → in_progress → awaiting_quote_approval →
    completed` (plus `cancelled/rework`);
  - skill- and area-matched assignment; quote approval gate;
  - warranty rework job linked to the original at 0 cost; AMC visits scheduled automatically;
    commission.
- **Seed:** 30 services, 45 technicians, 150 customers, 1,000 jobs, quotes, warranty claims.
- **Workflows:**
  - book an inspection job, then technician quote, customer approves, complete with OTP, pay,
    commission;
  - warranty claim creates a free rework job;
  - a technician without the skill is never offered the job.

### 6.9 Inkwell Press: blogging/publishing platform (content)

- **Apps:**
  - `site` (public web)
  - `write` (writer studio, web)
  - `admin` (editorial)
  - `api`
- **Roles:** reader, writer, editor, admin.
- **Look:** literary. Paper white, deep ink, a crimson accent, Newsreader serif for reading,
  Inter for UI. Reading-first typography (65ch measure, drop caps).
- **Site:**
  - home (featured, latest, topics); article page (reading time, table of contents, footnotes,
    code blocks, images, related, claps/likes, comments with threads);
  - author pages; topics/tags; search; series;
  - newsletter subscribe (free/paid tiers, mock payments); paywalled posts with preview;
  - reading list/bookmarks; RSS feed; SEO (sitemap, OG, JSON-LD) done properly; account.
- **Write:**
  - dashboard (views, reads, subscribers); editor (Markdown with live preview, image upload to
    mock storage, embeds, code highlighting, footnotes);
  - drafts, scheduling, series; submit to editor; revision history with diff;
  - stats per post; newsletter sends (mock email log); earnings from paid subscribers.
- **Admin:**
  - editorial queue (review, comment inline, request changes, approve, schedule); homepage
    curation; tags; users and roles; comment moderation; reports; newsletter settings; audit.
- **Domain:**
  - post states `draft → in_review → changes_requested → approved → scheduled → published` (plus
    `unpublished`);
  - scheduler publishes at time; slug history with redirects; paywall enforcement on the server;
  - comment moderation rules; subscriber revenue share.
- **Seed:** 30 writers, 400 articles (real-looking, varied lengths), 1,000 readers, comments,
  subscriptions.
- **Workflows:**
  - writer submits, editor requests changes, resubmit, approve, scheduled publish goes live at
    time;
  - a paywalled post is hidden from free readers by the API;
  - a changed slug redirects.

---

## 7. After the templates: T-5 workspace upgrades

In the Studio for any project:

- **Editable code:** save means a commit, with Monaco-free lightweight editing.
- **Diff view** per chat edit.
- **API explorer:** reads the project's `openapi.json` and sends "try it" requests through the
  preview proxy.

It was deferred by the founder until after RideNow and can run between templates.

Out of scope for Phase T (founder hard gates):

- changing PostgreSQL to another database;
- native mobile apps (templates ship PWAs);
- paid hosting for always-on demos;
- any paid cloud service.

---

## 8. Demo guide: show the whole platform, including RideNow

**Start everything** (Docker Desktop running; `.env` holds the Google key):

```bash
cd ~/Documents/Projects/Startup/Omnistackai
./scripts/preview-drafts.sh        # starts the platform with draft templates (RideNow) listed
./scripts/omnistack.sh status      # all services "ok"
```

**Open:** `http://127.0.0.1:4321` on this Mac, or `http://<this Mac's LAN IP>:4321` from another
device on the same Wi-Fi. The start-up output prints the LAN URL, for example
`http://172.28.64.242:4321`.

**Tour** (about 15 minutes):

1. **Register or sign in** (`/register`, `/login`). The home page (`/`) is **Build**: the prompt
   box that starts a new app.
2. **Prompt to app:** type, for example, "A booking app for a yoga studio with
   classes, instructors and memberships". Watch the build stream. Then:
   - **Preview** (the generated app running);
   - **Files** and **Code**;
   - **Problems** ("Check for problems" runs tsc);
   - send a follow-up edit in chat ("add a waitlist when a class is full") and watch it commit.
3. **Projects:** `/projects` lists everything. Open one, then **Manage**
   (`/studio/<project>/manage`). It covers:
   - workspace, AI usage, logs;
   - database explorer, tests, security, SEO;
   - connectors, payments, publish, domain, analytics.

   Some of these are gated or limited as described in the Phase F doc.
4. **Templates:** `/templates`, then **RideNow**: the details page (apps, roles, features, demo
   logins). Click **Use template**, which creates your own copy.
5. **Run RideNow:** in the project, open **Preview** and wait for "All apps are running" (about
   10 s after the first install). Use the app switcher:
   - **Rider app:** sign in as `asha@ridenow.test` / `Rider@2026`. Book a ride (pick pickup and
     drop, choose Mini, wallet or cash). A simulated driver accepts; watch the car move, the PIN,
     the completion, the receipt and the rating.
   - **Driver app** (shown in a phone frame): sign in as `ravi@ridenow.test` / `Driver@2026`.
     **Go online.** Now book from the rider app near MG Road: the request pops up on the driver
     app. Accept, "I've arrived", enter the rider's PIN (shown in the rider app), complete. See
     earnings, wallet (withdraw), trips, ratings and account.
   - **API:** `…/preview/<project>/api/openapi.json` lists every endpoint.
6. **Customise by chat:** in the RideNow project's chat, ask for example "add a 'Women-only rides'
   toggle to the booking screen". The code agent edits the real files, type-checks and commits.
   Reload the preview to see it (hot reload does not pass through the proxy yet).
7. **Fabric / Settings:** `/fabric` shows the model routing ladder, providers, price book and
   usage. `/settings` covers model provider and AI keys, hosting keys and the theme.

**Stop:** `./scripts/omnistack.sh down`. To go back to the normal catalogue without drafts:
`./scripts/omnistack.sh restart`.

**Known limits to mention when demoing:**

- the RideNow admin app arrives in R-530;
- previews run on this machine on demand (not hosted);
- providers are mocks;
- Publish/domains are gated decisions (see the Phase F doc).

---

## 9. Resume checklist for a new session or tool

1. Read `AGENTS.md`, `.ai/HANDOFF.md`, `.ai/CURRENT_TASK.yaml`, this document, and the current
   template's master plan (for RideNow: `.ai/tasks/R-526.md` to `R-528.md`).
2. `./scripts/omnistack.sh doctor`, then `./scripts/preview-drafts.sh`.
3. Start the next Tracker ID (R-530) with its contract. Follow §4 and §5.
4. Stop and ask the founder only for hard gates:
   - a paid service;
   - a database engine change;
   - new infrastructure;
   - native mobile;
   - a materially different architecture.
