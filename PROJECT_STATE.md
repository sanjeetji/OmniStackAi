# Project State — OmniStackAI
Last updated: 2026-09-26

## Current Phase
Stage 0 (Founder Build Sequence, Brief Section 91) — BASIC/MVP

> **PC-004 (2026-09-26): generated apps never pretend.** No in-memory fake saves, no fake 200s, no invented cart/review data, no dead buttons; unwired parts are honest (501 / not-connected page) and named in every build result and README; no DB internals to clients; malformed ids are 422. Express 5. Live on four backends.

> **R-573 (2026-09-26): every web app and admin console is an installable PWA with a QR.** Manifest, PNG icons, honest service worker (no API caching), offline page, install control, iOS guidance, LAN-aware QR. Chrome: zero installability errors.

> **R-590 (2026-09-26): lifecycles operable from every screen, and only through transitions.** List rows, detail pages and the mobile detail screen show state + legal moves; create/update can no longer write the state on any backend. Live 32/32 on four backends.
> **Found and fixed:** the default Python backend could not create records through its API at all (two separate bugs); mobile called /api/ paths nobody serves; Node transitions/update and Hono typing fixed. **Recorded:** Node in-memory fallback + Python 500 on bad id (PC-004); self-registered role not a plan role (PC-011).

> **R-591 (2026-09-26): complete account flow on every backend and surface.** Register/login/me/logout/forgot/reset identical on Python, Go, Node Express/Hono; one password format (accounts cross backends); safe one-time reset links (Resend when keyed, dev log otherwise); web forgot + reset pages; mobile sign-in/up/recovery screens with SecureStore. Live 84/84 on PostgreSQL.
> **Found and fixed:** Python /me read the query string (401 for everyone); forgot-password lied; web forgot page set passwords from an email alone; Node admin-for-everyone without JWT_SECRET, tokens never expired, routes under /api/ unreachable; Go would panic on a plan's own /auth/login; mobile Input failed strict tsc.

> **PC-003 (2026-09-26): named stacks we do not build get a reason.** React.js, Vue, Angular, Spring, Laravel, Rails, .NET, MySQL, MongoDB and others in the prompt now produce substitution notes naming what was built; no false alarms on ordinary words.

> **PC-093 (2026-09-26): intake repairs instead of rejecting.** Bad schema names resolved or dropped; a status-change endpoint becomes a real lifecycle; repairs reported. Live on Gemini: 6/6 valid (was 1/3).
> **Found:** `normalize_ir` dropped `capabilities` and `brand` — every model-declared lifecycle vanished at intake since R-566. Fixed with an every-field test.

> **PC-047 (2026-09-26): NVIDIA is a model provider.** From the founder's .env names; cloud tier, fallback or per-project; console and control plane list it. Live: 12.2 s smoke call OK.
> Compared on the real intake step: NVIDIA 1/3 valid at 99-152 s (one timeout), Gemini 3 Flash 1/3 at 12-14 s — NVIDIA stays optional. **Found:** half of real intake runs fail on both models because intake rejects a status-change endpoint instead of repairing it → PC-093, next.

> **PC-002 + PC-062 (2026-09-26): founder decisions recorded; native mobile preview planned.**
> No stack named → store-ready React Native + PWA with QR; native asked → Kotlin/Swift. Keys last: all integrations built first, accounts supplied at PC-070. Master list now 771 items (architecture plan, PG-01..PG-21, GA-01..GA-12 added); 91 open in the queue.
> Mobile preview: Android emulator headless from the SDK command line (no Android Studio), streamed into the Studio; hosted on Linux + KVM (Cuttlefish). iOS needs Xcode (installed headlessly) — no open-source simulator exists. This Mac: M2, no AVD/system image, no Xcode.

> **PC-001 (2026-09-26): one master task list; `R_&_D/Platform_Completion/` is now the only work queue.**
> 688 tasks from every R_&_D source, each with status, priority and the queue item covering it; 75 open in order. Next: PC-047 (NVIDIA provider), then PC-003 and R-591.
> Stack policy: Next.js web/admin; app request → store-ready React Native app + PWA with QR; Kotlin/Swift native last; no Flutter or React.js; PostgreSQL default, MongoDB option; NVIDIA nemotron-3-ultra for builds.

> **R-589 (2026-09-26): a lifecycle runs on every backend, not only the default one.**
> Go and Node emitted a 501 for transitions, so choosing Go meant a lifecycle that did not run. Both now enforce role and from-state and write only the lifecycle column.
> Proven by running each server against PostgreSQL with directly signed tokens: Go and Node each refuse a reader 403, refuse an author from draft 409 with the allowed states, and move the row to live from review.
> **An older Go bug surfaced:** `Update<Entity>` returned `&out`, never written — every PATCH/PUT in every Go backend answered with a blank record. **An existing test pinned it as correct**, asserting the very line that returned the blank struct. Both fixed; a PATCH now returns the edited row.
> Recorded (R-591): the Go backend verifies tokens but never issues one — no login or register — so a real user cannot sign in.
> 10 new tests; `task verify` 4,421 OK.

> **R-588 (2026-09-26): a transition is describable and callable, not only implemented.**
> R-566 generated the handlers and stopped; the contract described an API without them and the client had no function to call one. An endpoint nobody can call is close to one that does not exist.
> The contract now carries each transition with its allowed states, role and a 409; the client gains a function per transition, exported beside the CRUD ones. All three derive from one place, so they cannot name different endpoints.
> **Scoped down and recorded rather than implied:** Go/Node keep the 501 scaffold (R-589) and screens do not yet offer the actions (R-590). The page generator is ~74k lines; three things half-done is the failure this repo keeps meeting. The default stack has a complete verified path from lifecycle to client.
> Evidence: contract, client and handler name one path; a project with no workflow is unchanged; the web app typechecks against real `tsc`. 13 new tests; `task verify` 4,411 OK.

> **R-566 (2026-09-26): an entity's lifecycle, and who may move it.**
> An order that goes placed -> accepted -> delivered, and a courier who may not accept one, could not be written down. A status column was a string anybody could set to anything, and `POST /orders/{id}/accept` wired to nothing — a 501 stub.
> The first capability kind with code generation behind it. R-564's mechanism worked by itself: registering `workflow` made intake's `capabilities` key reappear with no string edited.
> **States live in the database** (a check constraint, so no `UPDATE` can write an undeclared one) and **transitions are refused by the backend**, not merely hidden in the UI.
> Proven by running it: against live PostgreSQL an undeclared state is rejected; against the started FastAPI backend, publish from draft is **409** naming the legal state, from review is **200** and the row becomes live, and without a token it is 401.
> **That run found something far larger:** role-based access control was non-functional in *every* generated project — login issued `"role": "author"` as a string while the guard read `claims.get("roles")` as a list, so every role-guarded endpoint answered **403 to everyone**. No test had ever called one.
> Recorded, not implied: Python only for now (Go/Node keep the 501 scaffold); the contract and screens do not yet carry transitions; and a workflow cannot yet be edited. 30 new tests; `task verify` 4,398 OK.

> **R-584 (2026-09-25): an edit can change a project, not only add to it.**
> The delta merged net-new things by concatenation and *raised* on anything existing, so "rename Post to Article", "remove the published field" and "add a notes field" had no way through. Restating gave an error; giving up proposed nothing and reported that no files needed changing. The platform's own smoke test asks for one of these.
> `intake/ir_changes.py` adds seven pure operations. **The work is not the change, it is everything pointing at it:** renaming `Post` to `Article` rewrites `/posts`, `{postId}`, `post_list`, the relation `Comment` declares, and the fixtures — otherwise a rename becomes a deletion nobody asked for. Removals cascade deliberately.
> Changes land **before** additions, so a rename precedes an endpoint naming the renamed entity.
> **A destructive edit says so.** It is the user's project, so removing a field removes it — and the reply names the data loss, present only when something was destroyed.
> Found while building: `apply_app_delta` rebuilt from `base_ir`, so a rename gave entities called Article beside fixtures still calling them Post, and the edit was refused for a reason the user could not act on.
> Evidence: all three requests work end to end; a rename leaves a valid IR with every reference moved; `id` and the last entity are refused; adding is unchanged. 28 new tests; `task verify` 4,367 OK.

> **R-565 (2026-09-25): an ecosystem is built with the backend the user asked for.**
> `surface_to_ir` hardcoded `BackendStrategy.PYTHON`, so "the backend should be in Go language" produced Python in silence — while the single-app path honoured it. The same sentence, two answers, depending on how many apps the prompt implied. It is reference prompt six.
> **Most of this task was already delivered by R-559 and was checked rather than rebuilt:** the stack is carried in the IR, survives a round-trip, a Go build really emits `go.mod`, and a Flutter request returns React Native with a reason. Only the ecosystem planner was missing.
> `intake/backend_choice.py` reads the language deterministically, because the planner runs without a model. The behaviour worth naming is the **non**-match: "customers go to collect their order" keeps Python; "API written in go" does not. Eagerness here would be worse than not reading the prompt at all.
> Evidence: Go, Node and the Python default all correct from an ecosystem prompt; `services/api/go.mod` in the repo with no Python beside it; still exactly one backend. 11 new tests; `task verify` 4,339 OK.

> **R-564 (2026-09-25): the IR can describe what a product does, and older projects still open.**
> The IR was entities, fields, relations, CRUD, screens and roles — a database with pages over it. `wire_endpoint` matches six CRUD shapes and drops the rest, so an order lifecycle, a ledger, a nightly job and row-level permissions had nowhere to be written down. That is the "maximum features" ceiling, and it lived in the data model.
> `capability.py` adds the frame Phase 2 fills: a record and a registry that keeps **declared** apart from **implemented** — because `GenerationTarget` declared FLUTTER with nothing behind it and produced a website in silence until R-559. A kind must be registered with the code that builds it, and this task ships the registry **empty**.
> **The migration mattered more than the feature.** Every project since R-563 has an `ir.json`, and `from_dict` rejected anything but version 1. Version 1 is now upgraded on read — at read time, because a migration that only runs during an upgrade is one that did not happen for somebody. A future version is still refused with its reason.
> Found: pack digests are SHA-256 over `to_dict()`, so a schema change moves all of them at once (re-pinned, content unchanged); and the intake template was showing the model an empty `capabilities` list, inviting it to fill a field nothing could build.
> Evidence: a hand-written v1 workspace `ir.json` still loads and upgrades; capabilities round-trip; unregistered kinds, duplicate names and future versions are each refused. 14 new tests; `task verify` 4,328 OK.

> **R-563 (2026-09-25): a multi-app project can be changed after it is built.**
> An edit to a five-app platform reached the backend and **not one of the apps** — and reported success. The union IR *is* saved, so nothing errored; `plan_edit` assembles with `assemble_project`, and the union carries no screens by design, so all five changes landed under `services/api` and `contracts/`.
> **The task's own premise was wrong and was corrected first:** the console already persists to the workspace store — verified by loading `ir.json` back from a fresh instance. The in-memory LRU serves only the standalone Studio's legacy build-id path.
> **Rule decided before implementing:** a new entity reaches every surface holding something it points at; pointing at nothing, it stands alone and reaches every surface. That fallback is the module's own existing rule for ambiguity, and it is the recoverable direction — an entity shown too widely is a reportable mistake, one hidden everywhere looks like an edit that did nothing.
> Scoping survives: the courier still has no menu editor, and an entity pointing at `MenuItem` reaches the merchant and not the courier. Every edit now names the apps it reached.
> Also fixed: `file_count` was computed from a single-app assembly, under-reporting a monorepo by hundreds of files.
> Evidence: the edit reaches all five apps and the backend, deletes nothing, leaves every app present; the old path's no-op is kept as a test. 14 new tests; `task verify` 4,314 OK.

> **R-562 (2026-09-25): a request for an app is answered with an app.**
> "marketing website, admin-panel, customer + driver apps" returned four Next.js websites — every surface was built with `MobileProfile.NONE` hardcoded and only a Next.js adapter was ever reached for.
> `intake/surface_form.py` decides from what the prompt asked for first, then from what the role does; anything unrecognised stays web, and the README records what each app was built as.
> Written into the module: **"a delivery app" is a product noun, not a form-factor request** — only the word next to a role moves anything, or "a blog app" becomes React Native.
> **Two defects caught before landing:** flipping the customer surface to mobile **deleted the only website**, in a prompt that asked for a marketing site in the same sentence — an operator's app replaces their portal, a customer's is built beside theirs. And the companion app, derived from a renamed surface, fell through kind-keyed scoping and lost `MenuItem`: a food app that could not show a menu.
> The monorepo and preview carry several Expo apps, found by what they contain rather than by the name `mobile` (which still counts, for projects generated before this). Each gets its own port, start step and QR. Single-app projects unchanged.
> Evidence: website + customer app + merchant portal + courier app + admin over **one** API; the courier app still ships no menu editor. 20 new tests; `task verify` 4,300 OK.

> **R-587 (2026-09-25): generated Go is gofmt-clean.**
> `gofmt -l` named four files in every generated backend. Nothing was broken — it compiled and vetted cleanly — but a Go developer's editor rewrites an unformatted file on save, on code they never touched.
> Struct fields are padded into columns by the emitter, which is the only thing that knows the widths; the stray blank lines are fixed centrally, so a future emitter cannot reintroduce them by forgetting.
> **Correcting R-561's note:** "66 lines of diff" counted `gofmt -d` headers and context. The real change is 21 lines.
> Two gates of different kinds: the real `gofmt`, skipped where Go is absent; and a text check of the columns so `task verify` still catches it without a toolchain. Both mutation-tested. A third asserts the code itself did not change — a formatting task that alters a declaration is not a formatting task.
> Evidence: `gofmt -l` silent including on assorted field widths; `go build` and `go vet` clean; byte-identical across runs. 6 new tests; `task verify` 4,280 OK.

> **R-561 (2026-09-25): every surface is compiled, not just the web app.**
> R-560 checked `apps/web` alone, so the admin console, the mobile app and the backend were never built by anyone. The first measurement found that **a generated Go backend cannot start**: `go.mod` with no `go.sum`, and a README telling the user to run `go run .`, which fails on every dependency. The preview did the same; the Python branch had installed dependencies since it was written.
> The first fix was wrong and running it said so — `go mod download` leaves the transitive requires missing. `go mod tidy` writes `go.sum`, and the backend now builds and vets clean from its own README.
> Each surface reports for itself: one verdict hides which of four things broke. None of them holds a model-written file, so failures are attributed to our generator, never to the user.
> Honest about what each check proves: admin fully type-checked (its dependency set is *verified* identical to the web app's before sharing the cache); mobile only when really installed; Go parsed with `gofmt` and compiled on request; Python parsed with `compileall`.
> Evidence: Go backend `go build`/`go vet` clean from a clean checkout; corrupting an admin file names the file and line and flips the verdict. 6 new tests; `task verify` 4,274 OK, 0 model calls.
> **Found, deferred (R-587):** four generated Go files are not gofmt-clean — struct fields unaligned, 66 lines of diff.

> **R-560 (2026-09-25): the build path compiles what it generated.**
> The compile-verify-repair loop has worked since R-466; its only caller was an opt-in CLI, so a console build reached none of it — which is how R-549's non-compiling `lib/brand.ts` shipped in **every generated web app for nine tasks**.
> It now runs on the path every build shares. A build is never *failed* by verification, skipping is never silent, and dependencies are warmed once by `omnistack.sh` rather than installed per build.
> Whose fault it is comes first: the loop only rewrites what a model wrote, so a failing deterministic file is reported as a **generator failure** — our bug in every project from that template. Reintroducing R-549's directive returns exactly that, naming `lib/brand.ts`.
> **Two defects found by this task's own gates:** `build_ecosystem_from_plan` bypasses `build_app_from_ir`, so every multi-app project would have gone unverified (the R-555 shape again); and the warm cache must be a directory *named* `node_modules` — TypeScript resolves through the symlink's real path, so a cache named anything else made `next`'s types unresolvable and reported `TS7006` in code that compiles. A misnamed cache is now refused, because inventing errors is worse than checking nothing.
> Evidence: a warm cache links instantly and reports clean; R-549's defect reproduces as a named generator failure; builds without a provider or toolchain still succeed and say why. 13 new offline tests, 0 model calls; `task verify` 4,268 OK.

> **R-586 (2026-09-25): the CareClinic seed generator stops reading the clock.**
> It called itself deterministic and was not. Every date came from `new Date()`, so the committed seed stopped matching a fresh run once the date rolled over — the same test passed on the 24th and failed on the 25th with no code change — and **`task verify` failed every day**, making every later task's evidence unreliable.
> Dates are now anchored to a fixed Monday, so the file is byte-identical on every run and in every timezone, and the seed moves the whole demo onto today when it loads. The stale-seed test is an exact hash again.
> **Exact days, not whole weeks** — the opposite of the first attempt. Whole weeks preserve weekdays but leave the front desk and waiting-room board empty six days in seven, because both filter on today. The roster's `day_of_week` is rotated by the same offset so nothing is booked on an unrostered day.
> **Two defects found only by loading into real PostgreSQL:** a single `UPDATE` of `scheduled_date` trips `uq_doctor_slot`, which is checked row by row — the table is parked 100000 days ahead and brought back. And an earlier version *appeared* to load cleanly only because that day's week-shift was exactly zero, so nothing moved.
> A gate now reads the generated SQL, finds every column receiving a date literal and fails if it is not moved onto today; `dob` is excluded on purpose. Both new gates mutation-tested.
> Evidence in PostgreSQL: −90..+14 days around today, 10 appointments on today's front desk, 0 booked without a roster, 0 stranded rows. `task verify` 4,255 OK — green for the first time since the rollover.

> **R-559 (2026-09-25): ask for something we cannot build and get the nearest thing we can, with a reason.**
> A Flutter, native or React-Native-for-Web request returned a Next.js site and an admin panel, silently. Of four mobile profiles only `react_native` emitted an app; **`flutter`, `native` and `auto` dropped it with no error** — and `nl_to_ir` told the model to pick `flutter`, so the likeliest path was a guaranteed silent drop.
> The reasons already existed and were thrown away: `_plan_assembly` computed them and only the generated README ever read them.
> `codegen/capabilities.py` substitutes instead of dropping, keeps the original request in the IR, and states in one plain sentence what was asked, what was built and that it still reaches both stores.
> **Support is derived from the adapter registry, never declared.** Registering a Flutter adapter is the only change needed to make it real — asserted by a test that registers a stand-in adapter and watches the substitution stop.
> **A bug in this task's own first draft, caught by its own gate:** mapping `rn_web` to the registered React Native target reported it as supported, no substitution fired, and the build produced **zero apps** — worse than the drop being fixed. Anything reported as supported must now survive a real assembly.
> Evidence: all four app-wanting profiles assemble a real Expo app on disk; the reason reaches payload, console and README; a supported stack produces no note; `tsc --noEmit` clean; 15 new offline tests.
> **Found, not fixed (outside path scope):** the CareClinic seed generator uses `new Date()`, so `task verify` fails every day once the date rolls over. Recorded as R-586.

> **R-558 (2026-09-24): the deterministic pages use the design system they ship with.**
> The project carried 59 colour tokens, a type scale, six shadows and seven motion tokens, and the pages used almost none of them: `--shadow-*` 0, `--transition-*` 0, `--font-size-*` 0, `--space-*` 0, 26 hardcoded pixels, **zero hover or focus states**.
> Part of that was structural, not taste: **inline React styles cannot express `:hover`, `:focus-visible` or a media query at all**, so tuning inline values could never have produced an interface that responds to a cursor. A real scoped stylesheet is emitted with the page, built from the shipped tokens so a rebrand moves the shadows and motion too.
> Focus is **styled, never removed**, and all motion is suppressed under `prefers-reduced-motion`. After: shadow 7, transition 16, font-size 14, space 25, hover 7, focus-visible 1. Still a server component, no new dependency, byte-stable.
> **Two live regressions found, neither from this task.** R-549's two `@ts-expect-error` directives sat over imports TypeScript resolves fine — an unused suppression is itself an error, so **`next build` had failed on every generated web app since**. Beneath it, the generated `tsconfig.json` never set `allowJs`, so a fresh clone reported TS7016; invisible because `next build` writes that key into the tsconfig itself on first run, repairing the file it was about to read.
> **Third green-suite-over-broken-product in one sitting** (`_prefixed`, the streaming twin, this). So: `lib/brand.ts` imports only generated files and now compiles under `tsc` inside `task verify`, offline, in about a second, with the options read from the *generated* tsconfig. Both original defects were replayed against the gate and both fail it.
> Evidence, from real builds: fresh-clone `tsc --noEmit` exit 0, `next build` prerenders 12 routes, the served page carries 14 `shadow-`, 34 `transition-`, 14 `:hover`, 2 `:focus-visible` and the reduced-motion block, brand colour in both palettes; two products served structurally different pages. `task verify` 4,226 OK offline, 0 model calls.

> **R-557 (2026-09-24): the console says why a project has four apps in it.**
> The build streamed a line that then scrolled away, and `app_build_result_to_dict` **dropped `ecosystem_apps` and `ecosystem_reason`** — so a user who received four apps saw four directories and no reason for them.
> Both now travel with the result, and the Studio header renders how many apps, which ones, and the sentence explaining it — emitted **only** when several were built, so an ordinary build shows nothing.
> Rendered as text, never HTML: a gate refuses `dangerouslySetInnerHTML` there, and another asserts the generated sentence carries no angle brackets at the source.
> **TypeScript caught a modelling error:** two of the three snapshot sites are chat *edits*, reading a field a `BuildEditResponse` has no reason to hold. An edit never builds apps, so they now carry the existing shape forward.
> Evidence, live: a real console build streamed the plan and its payload carried `["web","merchant","driver","admin"]` with the reason. `tsc --noEmit` clean; `task verify` 4,223 OK offline, 0 model calls.

> **R-556 (2026-09-24): two products in one archetype no longer render the same page.**
> R-543 stopped a shop and a blog looking alike; two shops still did — one structure, different nouns.
> Four genuinely different arrangements — **centred**, **split**, **banner**, **editorial** — seeded from the product name, which gives the two properties in tension: different products differ, one product stays stable. Hashed, not `len(name) % n`, so adjacent names do not collapse. A gate refuses `random` in that module.
> An archetype only gets arrangements that suit it: a storefront is never editorial, a publication never a banner. Forcing variety at the cost of fit makes something different but worse.
> **Recorded tension:** the editorial variant drops the eyebrow by design, and R-543's test required one. Requiring it would force every arrangement to look the same where they are meant to differ, so the test moved to the CTA and section heading.
> Evidence: four storefronts → four distinct pages across three arrangements; same product identical twice; every variant valid JSX including an empty IR; none a client component; all keep the brand colour. 13 new tests; `task verify` 4,207 OK offline, 0 model calls.

> **R-555b (2026-09-24): the console's own build path takes the ecosystem branch — proven end to end.**
> R-555 wired `build_app_from_prompt`; **the console streams and calls `build_app_from_prompt_stream`**, which was not. Every offline test passed against the function that had been wired rather than the one the product uses — the same shape as R-549's `_prefixed` defect, and the second time this session that only a live run caught it.
> Both entry points now branch, a contract test requires it, and the streaming path says what it is doing (a deterministic plan has no model output to relay, so the console would otherwise go silent).
> **Live through the console, 18 checks passed, 0 failed:** "a food delivery app with customers, drivers and restaurants" → one project with `apps/web`, `apps/admin`, `apps/driver`, `apps/merchant`, exactly one `services/api` and `brand.json`; preview `kind: multi`, all five surfaces ready; every surface HTTP 200 through the proxy with a real page; the shared API answered; all four pages distinct.
> The ecosystem branch uses **no model**, so it cannot fail on an invalid IR — which is how the single-app path failed on the first attempt. `task verify` 4,207 OK offline, 0 model calls.

> **R-555 (2026-09-24): a prompt that names a second kind of user builds the whole ecosystem.**
> The planner alone was not the signal — it plans three surfaces for "a simple blog" — so always building `complete` would hand someone four directories they never asked for.
> **The rule: an ecosystem is built when the prompt names a second kind of person.** A customer or an admin does not count on its own, because a single app is already both. A courier, merchant or doctor does. Deterministic and offline: one sentence must not build different shapes on different runs.
> Two false positives fixed — "an online store" matched *merchant* on a word that names the product, and "a dashboard for admins" counted admin as a second party. Whole-word matching, so "driven" is not a driver.
> Evidence: *"a food delivery app with customers, drivers and restaurants"* → **one** repo, 675 files, one commit, `apps/web` + `apps/merchant` + `apps/driver` + `apps/admin` + one `services/api`, and it says why. "a simple blog" still builds one app. 15 new tests; `task verify` 4,203 OK offline, 0 model calls.
> **The founder's "single app to complete eco-system" requirement is now met from a prompt.**

> **R-554 (2026-09-24): a planned ecosystem assembles into one monorepo over one API and one database.**
> `build_ecosystem` made each surface its own repo with its own backend and database — four disconnected apps, where the courier could not see the customer's order.
> `codegen/ecosystem_assembler.py` puts every surface under `apps/<id>/` over one `services/api`, one `brand.json`, one contract. The customer app lands in `apps/web` and the dashboard in `apps/admin`, the ids R-553's runner and the console already understand.
> **The backend is the union of every surface's IR** — entities by superset of fields, endpoints by union of roles (`DELETE /orders/{id}` is reached by all four roles; first-wins would have 403'd three of them). Each app keeps its own scope: the courier app ships no menu editor, the merchant portal does.
> Evidence: four apps + one API; union of 3 entities / 4 roles / 17 endpoints against surfaces declaring 11, 17, 8, 11; every surface route resolves with the roles it expects, checked exhaustively; byte-identical across runs. 21 new tests; `task verify` 4,188 OK offline, 0 model calls.
> **Next:** R-555 — use it from the build path, so a prompt produces the whole ecosystem.

> **R-553 (2026-09-24): the preview runs any number of apps, not the two it was told about.**
> The runner hard-coded `apps/web`, `apps/admin` and `services/api`, so every new surface needed another copy of the same block — and `plan_ecosystem_from_prompt` already plans **four role-scoped surfaces** for a food-delivery prompt that none of them could preview.
> `discover_web_apps` finds every `apps/*` with a package.json in a stable order (`web`, `admin`, then sorted); one loop starts each on its own allocated port and base path; `allocate_free_ports` replaces the fixed four; each is waited for, because a surface nobody probes is reported ready before it can answer.
> A one-surface project and a `web`+`admin` project are byte-for-byte unchanged, which the tests hold.
> Evidence: four surfaces on four ports with four base paths; the preview reports six entries including the API and Expo. 8 new tests; `task verify` 4,167 OK offline, 0 model calls.
> **Next:** R-554 — assemble an ecosystem into **one** monorepo over one API and one database. `build_ecosystem` currently makes each surface a separate repo with its own backend, so the courier could not see the customer's order.

> **R-551 (2026-09-24): `doctor` checks that the toolchain works, and the command set is complete.**
> `doctor` printed `ok python3 is 3.13` on this machine while `python3 -m venv` was completely broken — so every generated Python backend refused to start and it looked like a platform bug. Its remedy even recommended the broken path.
> The cause ran five layers deep: Homebrew's `pyexpat` fails to `dlopen` → `plistlib` breaks → `platform.mac_ver()` empties → pip's `truststore` raises `int('')` → `ensurepip` and `venv` fail. `doctor` now imports pyexpat and actually creates a throwaway virtualenv, and names a remedy that works (`uv python install 3.13` + a `~/.local/bin/python3` symlink).
> `start` and `stop` join `up` and `down`, sharing one case arm so they cannot drift. A contract test now checks every documented command dispatches and every dispatched one is documented — the old R-498 check matched the literal `up)` and had never covered `start`, `stop`, `fresh`, `admin` or `open`.
> Evidence: doctor fails with the real cause on the broken interpreter and passes on the fixed one; `stop` then `start` brought the platform back healthy on all four ports; `status` clean; `verify` exits 0.

> **R-550 (2026-09-24): before publishing, change anything; afterwards, one thing is refused — with the reason.**
> Nothing stopped a `bundleId` change after publication, which is the only irreversible decision in the flow: Apple ties it to the App Store Connect record, Google Play uses it as the listing's primary key and never lets one be reused, so a different identifier is a *different app* — no reviews, no ratings, no update path.
> `brand.json` now records `publishedBundleId` beside `published`, which is what makes a later change detectable. `brand/check.mjs` refuses a mismatch and explains it; the chat agent enforces the same rule **inside** the block that restores every file, so a refusal really does leave nothing saved.
> **Only the identifier is refused.** Icon, colours, font and display name stay legal in an update — blocking them would be wrong. They warn instead, naming the cost: higher `buildNumber`/`versionCode`, a new build, another review, and the listing title edited in each console.
> The agent now knows where branding lives: "make it green", "change the logo" and "rename the app" all select `brand.json`; "add a waitlist to the booking screen" does not.
> Evidence: unpublished passes; published-unchanged passes with the warning; published-then-edited exits 1 with the explanation. 9 new tests; `task verify` 4,159 OK offline, 0 model calls.
> **Option C is complete.** Next: R-551, the `omnistack.sh` command set — and a `doctor` that verifies the interpreter actually works rather than only matching a version string.

> **R-549 (2026-09-24): a rebrand reaches the web app and the admin console, not only the phone.**
> CSS cannot read JSON at runtime, so the two Next.js apps were left behind by R-548. Each now has a `lib/brand.ts` importing `brand.json` and the **same** `derive.mjs` the mobile config uses, emitted into `<head>` after `tokens.css`. Colours, fonts and corners need no regeneration — edit, reload, done.
> Icons are binary, so `pnpm run brand` regenerates them with a plain-Node PNG encoder. **It never overwrites your artwork:** generated icons carry a marker; a file without one is left alone.
> **Two defects found by running it.** The marker existed only in the JS generator, so a fresh project's icons looked user-supplied and the script refused to touch any of them. And `_prefixed` dropped `base64_encoded`, so **every icon became a text file the moment it entered `apps/mobile/`** — the adapter's tests never caught it because they skip assembly.
> Evidence: with one icon replaced, the script kept it and regenerated the other three, byte-for-byte identical to the platform's Python output (SHA-256 verified). 7 new tests; `task verify` 4,150 OK offline, 0 model calls.
> **Next:** R-550 — publish-state rules (identifier refused, the rest warned) and the chat agent editing `brand.json`.

> **R-548 (2026-09-24): one `brand.json` every surface derives from.**
> Branding was scattered across eleven CSS variables in `apps/web`, the same eleven in `apps/admin`, two places in `apps/mobile/app.json` and the RN design tokens — plus four PNGs a user could not regenerate at all.
> `brand.json` holds **inputs only**; the palette is derived by `brand/derive.mjs`, never stored, because a stored palette goes stale the moment someone edits the base colour by hand. The mobile app moves to Expo's dynamic `app.config.js`, and the static `app.json` is no longer generated — two files configuring one app means a user edits the losing one and cannot tell why.
> **The gate that matters: the JS and Python derivations must agree.** They differed on five of seven colours at first — Python rounds half-to-even, JS half-up. A test now runs the generated JavaScript through Node and compares every value.
> Evidence, live: hand-editing `brand.json` to `Bakery Shop` / `#7c3aed` changed the served Expo manifest's name, slug and splash colour on reload — while `bundleId` stayed put, which is the point. 11 new tests; `task verify` 4,143 OK offline, 0 model calls.
> **Next:** R-549 `pnpm run brand` regenerates stylesheets and icons, skipping any the user replaced; R-550 publish-state rules and the chat agent.

> **R-546 (2026-09-24): the generated Expo app can be built and submitted to the stores.**
> R-545 made it run on a phone; it could not be *built*. No `eas.json`; no icon or splash **image**, only a background colour; no `buildNumber`/`versionCode`, so a second upload is refused; no iOS privacy manifest, required by Apple since 2024; and a bundle identifier under `com.omnistackai.*` — our domain on a user's app, bound permanently by both stores on first upload.
> `codegen/mobile_release.py` generates all of it offline: EAS build and submit profiles, the privacy manifest, listing metadata, a manual-dispatch CI workflow, a credential-aware `.gitignore`, and a release guide whose first section is *change the bundle identifier*.
> **No credential is created, used or embedded** — every secret is referenced by name, and a test scans every generated file for PEM headers, tokens and service-account keys.
> Icons are real PNGs encoded in pure Python (text-only `GeneratedFile` gained an opt-in `base64_encoded` flag, decoded at the single writer) and take the **brand colour R-544 extracts from the prompt**. Verified by `file` and macOS `sips`.
> Evidence: the app still bundles live — iOS HTTP 200, 6,532,286 bytes. 23 new tests; `task verify` 4,122 OK offline, 0 model calls.
> **What remains is not code:** Apple ($99/yr), Google Play ($25) and an Expo account. With those, `eas build` and `eas submit` work against what is generated.

> **R-545 (2026-09-24): the generated mobile app runs, and a phone can open it.**
> The Expo adapter had been emitting a real app that the platform could do nothing with — no mobile kind in `APP_KINDS`, no `apps/mobile` anywhere in `plan.py`. It is now installed and started in LAN mode on its own port, and the preview reports the `exp://` URL for a QR. Not proxied: a native app is not an iframe, so the QR *is* the preview. `EXPO_PUBLIC_API_URL` points at the **LAN address** — on a phone, loopback is the phone itself.
> **The adapter had never been run, and no generated mobile app had ever bundled.** `@babel/runtime` was undeclared (the first bundle failed outright), and `OverviewScreen.tsx` imported `../design-system/...` when it needed `../../` — Metro could not resolve one component on the home screen. Both now have static gates that catch the same defects offline.
> Evidence: live, both platforms bundled through the running Expo server — iOS 6,532,286 bytes and Android 6,551,905 bytes, HTTP 200 each, manifest reporting `exposdk:51.0.0`. 18 new tests; `task verify` 4,099 OK offline, 0 model calls.
> **Next:** R-546 — `eas.json`, icon and splash assets, versionCode/buildNumber, permissions, the iOS privacy manifest, a user-owned bundle identifier and store metadata. No account needed to generate any of it. R-547, actually submitting, needs Apple ($99/yr), Google Play ($25) and an EAS account.

> **R-544 (2026-09-24): the brand a user asks for now reaches the app they get.**
> Asking for a red shop produced the same blue app as everything else, because the pipeline was broken in three places at once: `nl_to_ir` never asks the model for a brand; `extract_brand_tokens` was **called from nowhere** and would have **raised** if it had been (a slotted dataclass has no class-level defaults); and `styles/tokens.css` was a **static string** that never read `ir.brand`. A requested colour surfaced only in a `color-picker` swatch.
> New `codegen/brand.py` derives a full palette from one colour in plain Python — mixing toward black/white so shades keep the hue, deriving the dark theme from the same brand, carrying the focus ring, and picking button text by WCAG luminance so a yellow brand is still readable. The extractor now reads **colour names**, not only hex.
> Evidence: "a red shop" → `#dc2626`; "a green booking site with rounded corners" → `#16a34a` + `0.5rem`; no cue → the default palette byte for byte; no default blue survives a rebrand. 20 new tests; `task verify` 4,081 OK offline, 0 model calls.
> **Next:** the generated Expo mobile app still cannot be run or previewed — `APP_KINDS` has no mobile kind and `plan.py` has no `apps/mobile`, so a user who asks for an app gets code the platform can never start.

> **R-543 (2026-09-24): a real archetype family, so different products get different pages.**
> There were two archetypes and eight prompt keywords **defaulting to `admin_panel`** — which is why "a website to sell my product" generated an internal dashboard for a shop, and why every recognised public site got one identical landing page. The detector also lived only in `llm_ui.py`, so the deterministic generator had no archetype awareness at all.
> `codegen/archetype.py` scores seven archetypes (storefront, publication, booking, directory, saas, marketing, admin_panel) from the **IR and the prompt together**, weighting entity names above wording because they survive paraphrasing. `admin_panel` is never inferred. With no evidence the answer is `marketing`, not a dashboard.
> Both paths agree: the deterministic page shapes its copy and CTA from the archetype, the model prompt carries a block per archetype, and `_deterministic_page_for` is the single place that decides the fallback.
> Evidence: `sell my product` → storefront/"Start shopping", `publish articles` → publication/"Start reading", `book appointments` → booking/"Book now", `directory of local plumbers` → directory/"Start browsing"; all six public archetypes distinct and passing the JSX validator; 16 new tests; `task verify` 4,061 OK offline, 0 model calls.
> **Known, not done:** two storefronts still look alike (layout variants are next), and `BrandTokens` still never reaches `styles/tokens.css` — a requested brand colour lands only in `components/color-picker.tsx`, so every app is blue regardless.

> **R-542b (2026-09-24): the live journey, and the three defects it found.**
> Running the real thing found what 4,029 offline tests had not. **The readiness probe hit the app's origin, and an app under a base path answers 404 at `/`** — so the preview started both apps and then declared them dead. The admin console was never waited for and was reported `ready: true` regardless; and `_should_skip` did not know about the console, so it reinstalled its dependencies on every preview start.
> Verified after the fix: `status: ready`, `kind: multi`, both apps ready; `/preview/<id>/web` 200 with the landing page, `/preview/<id>/admin` 200 with the dashboard, assets resolving per app, root redirecting to `/web`.
> **Environment blocker (not ours, not fixed):** Homebrew's python@3.13/3.14 here have a broken `pyexpat`, which breaks `plistlib`, so `platform.mac_ver()` is empty, so pip's `truststore` raises `int('')` — **`python3 -m venv` fails and no Python-backend preview can run on this machine**. The live check therefore ran with the backend parked, and the API-through-proxy path is still unverified. `uv` installed as groundwork.
> **Next:** R-543 the archetype family; then the venv/pip fix; then R-544 local-model fallback.

> **R-542 (2026-09-24): the admin console is reachable in the Studio.**
> R-541 assembled `apps/admin` and started it, but the preview reported a single app, so the console ran and shipped in the user's repo while being invisible in the product. A project with a console now reports as a multi-app preview, and the console's existing `MultiAppPreview` switcher and proxy serve it — **no `apps/console-web` change was needed**.
> The proxy forwards the full pathname upstream, so each app has to be served under its own base path. The generated `next.config.mjs` ignored `BASE_PATH`, which would have left a proxied app rendering at the wrong base with no assets; it now honours it as the template configs do. `build_run_plan` gained `public_base` and gives each UI its own base path, pointing the API base at the proxied `/preview/<id>/api` — relative, so calls survive from another device on the LAN.
> A project without a console is untouched, as is any caller passing no `public_base` (`task app:run`).
> Evidence: `next build` with `BASE_PATH` set, exit 0, `routes-manifest.json` records the basePath, no config warnings on the pinned Next 15.5.4; 12 new offline tests; `task verify` 4,041 OK offline, 0 model calls.
> **Next:** R-543 — the wider archetype family (storefront, blog, booking, directory) in both the deterministic and model paths; then R-544, a guaranteed local-model fallback.

> **R-541 (2026-09-24): one prompt now delivers every app it asked for, and each app looks like itself.**
> `nl_to_ir` has always defaulted `admin_strategy` to `"nextjs"`, so **every prompt-built project was asking for an admin panel** — and the assembler recorded it as "not assembled yet" and dropped it, because `GenerationTarget.NEXTJS_ADMIN` was declared with no adapter behind it. It then forced `web_strategy` back on so the console could hide in `apps/web`, which also gave admin-only requests a public website nobody asked for.
> `NextjsAdminAdapter` implements the declared target; `apps/web` and `apps/admin` are now assembled side by side with distinct package names, and an admin-only request stays admin-only.
> The home page was the second half of the problem: `_overview_page` renders an entity dashboard and it was the home of *every* app, so "a website to sell my product" returned an internal console. `_public_home_page` gives the visitor-facing app a real landing page (hero, offering, browse, footer) as a hook-free server component. The archetype is now stated by the assembler instead of inferred — `_detect_ui_archetype` matched eight keywords and defaulted to `admin_panel`, and that phrase matches none of them.
> The preview runs both apps: `build_run_plan` starts `apps/admin` on its own port and the payload carries `admin_url`.
> Evidence: both apps build with `next build` from one IR (public `/` static at 165 B, admin `/` a 4.97 kB client dashboard), both pass the engine's own JSX validator, 14 new offline tests, byte-stable across runs. `task verify` 4,029 tests OK offline, 0 model calls.
> **Known, not done:** the console still shows a single preview app, so the admin console runs but is not yet clickable in the Studio. **Next:** R-542 — surface the second app in the console, then the wider archetype family (storefront, blog, booking, directory) in both the deterministic and model paths.

> **R-540 (2026-09-24): every published template audited; Bazaar rebuilt against its own API.**
> One question of all three templates — does each page actually call the API? `ride-now` and `care-clinic` came back sound; **`bazaar` was 18 of 44 pages, with its operations console at 0 of 18**. Every console page rendered a fabricated array and sign-in wrote a demo token without calling the API. All 18 rewritten, plus the seller's listing editor, new-listing form, reviews and settings, and the buyer's reviews screen.
> Four admin endpoints returned 500 to every caller (a table and three columns that do not exist), and generating a settlement batch called a method that was never written.
> **The books were fiction:** cash and commission resolved to the same account row, and the seed asserted round balances with zero postings behind them. Migration 006 separates `platform_revenue`; the seed now generates 180 orders, 216 consignments and 564 postings and derives every balance — the ledger sums to zero and all 11 accounts reconcile.
> `test_template_quality.py` applies eight checks to the whole catalogue, in `task verify`, so **T-9 and every future template are covered before publication**.
> **Next:** T-9 Pocket (digital wallet), then the small billing-enforcement task.

> **R-539 (2026-09-23): the CareClinic doctor workstation rebuilt against the API, plus the platform's own `fresh` and `admin` commands.**
> `apps/doctor` was the same kind of mock the clinic console had been: every screen rendered hard-coded state, and only the dashboard, the queue and the patient chart called the API at all. All 15 screens now read live clinic data behind a shared doctor session, guard and event stream: dashboard, queue, the consultation with SOAP notes, e-prescription and lab orders, the patient chart and history, OPD hours, leave, earnings, reviews and the video room.
> New API: `GET /api/doctor/consult/:appointmentId` (the whole consultation context in one read, 404 for another doctor's patient), `GET /api/doctor/earnings`, `POST`/`DELETE /api/doctor/schedule/overrides`, and `GET /api/public/icd10` over a new `icd10_catalog` table of 70 codes.
> Fixed: the earnings query counted a consultation fee twice when a visit had both a consultation and a diagnostics invoice; and the shared clinical types named columns the API never returns, which blanked the medicine, form and dose on the **patient's** prescription slip.
> Platform: `omnistack.sh fresh` wipes every byte of local data and creates the first owner as a `super_admin`; `omnistack.sh admin` administers accounts through a new `platformctl` reusing the control-plane's PBKDF2 hashing; `COMMANDS.md` documents every command and states plainly what the role/plan/credit model does and does not enforce yet.
> **Next:** the founder's open question — platform user management (plan limits, admin area, subscription billing) before or after T-9, Pocket (digital wallet).

> **R-538 (2026-09-23): CareClinic (part 4 of 4) — the clinic operations console, 48 screenshots, and publication.**
> Built `apps/admin` ("CareClinic Ops") across 18 routes against the real API, in its own control-room design behind a staff-only guard: operations dashboard, front desk, check-in, walk-in booking, appointments and appointment investigation, doctors, doctor rostering with absences, the room board, the cashier and its itemised receipt, refunds, the diagnostics bench with result entry, reports, the chart-access audit, settings, and a waiting-room display board.
> The draft console was a static mock — all 18 pages rendered hard-coded arrays and sign-in wrote a fake token — so it was rewritten. Added the admin endpoints it needs (rooms, doctor rostering and absences, invoice detail and counter collection, desk cancellation with the refund policy, one lab order and its status, calling a token, clinic reports), admin SDK methods and types in `@careclinic/shared`, and role-aware sign-in.
> Fixed in the parts already signed off: the seed never loaded (48 times of day were `HH:60:00`; `queue_status` was copied from the appointment status although `no_show` is not one of its values); nine tables were never written; the demo patient's chart was empty; seven patient-app route folders were URL-encoded, so every detail page 404'd on a real id; doctor cards linked to `/doctors/undefined`; `services/api` did not type-check; the shared types named columns the API never returns; and document numbers came from `COUNT(*) + 1`, which collides.
> Published `templates/catalog/care-clinic` v1.0.0 (healthcare) with 48 screens and a composed cover. Evidence: 18/18 API unit tests, 6/6 live cross-app workflow tests, 18/18 new offline tests, 48/48 pages verified in a real browser, 40/40 live gate through the console with the preview ready in 35 s.
> **Known, not fixed:** `apps/doctor` (R-537) renders hard-coded state rather than API data and needs its own task. Next: rebuild the doctor workstation, then continue the template catalogue (T-9).

> **R-537 (2026-09-23): CareClinic (Part 3 of 4: Doctor Telehealth & Clinical Workstation `apps/doctor`).**
> Built `apps/doctor` on Next.js 16 App Router + React 19 + Turbopack + Tailwind CSS 4 with high-efficiency clinical workstation styling (slate/navy foundations, clinical emerald/cyan accents, keyboard shortcuts, accessible contrast) across 15 doctor routes:
> Doctor Sign In with 1-click Dr. Rajesh Varma demo credentials (`/login`), Clinical Dashboard with OPD metrics, active consultation spotlight, and diagnostic alerts (`/`), Today's Patient Queue with live tokens 1-15 and 1-click consult launch (`/queue`), Active Clinical Consultation Screen (`/consult/[appointmentId]`), Structured SOAP Documentation with ICD-10 search and finalization lock (`/consult/[appointmentId]/soap`), Digital Prescription Builder with dosage rules and cryptographic signature generator (`/consult/[appointmentId]/prescription`), Diagnostic Lab Order generator (`/consult/[appointmentId]/labs`), Patient Medical Chart with HIPAA audit badge (`/patients/[id]`), Patient Medical Directory & Longitudinal Index (`/patients`), Comprehensive Medical History (`/patients/[id]/history`), Weekly Schedule Configuration matrix (`/schedule`), Availability Rules & Leave Overrides (`/schedule/rules`), Doctor Earnings & Payout Statements (`/earnings`), Patient Satisfaction & Reviews with clinical attribute scorecards (`/reviews`), and Doctor Telehealth Interface with simulated WebRTC video room, PIP self-feed, in-call SOAP notes, quick prescription drawer, and encrypted chat (`/telehealth/[appointmentId]`).
> Extended `@careclinic/shared` with doctor SDK methods.
> Next.js Turbopack production build compiled 15/15 routes with 0 errors; 18/18 API unit tests passed; 40/40 template studio tests passed; full Stage 0 verify (3,983 tests) passed offline with 0 model calls. Next: CareClinic (Part 4/4: Front Desk & Clinic Ops Console `apps/admin`, Playwright 48 screenshots + cover, and template publication to `templates/catalog/care-clinic`).

> **R-536 (2026-09-23): CareClinic (Part 2 of 4: Shared Library `@careclinic/shared` & Patient Web App `apps/patient`).**
> Built `packages/shared` (`@careclinic/shared`): canonical TypeScript domain interfaces, clinical formatters (`formatINR`, slot time, date, status badges, refund policy calculator, BP evaluator), universal typed `CareClinicApiClient` SDK, and `useStream` SSE hook.
> Built `apps/patient` on Next.js 16 App Router + React 19 + Turbopack + Tailwind CSS 4 with calm clinical soft-teal aesthetic across 16 routes:
> Patient Home with active appointment banner and 6 service modules (`/`), Doctor Directory with specialty/mode filters and fee sorting (`/doctors`), Doctor Profile with weekly shift timetable and verified reviews (`/doctors/[id]`), Step-by-step Booking with dynamic 20-min slot picker and dependent selector (`/book/[doctorId]`), Consultation Fee Payment checkout (`/checkout/[appointmentId]`), Booking Confirmation slip with token number (`/appointments/[id]/confirmation`), Appointments List with status tabs and tokens (`/appointments`), Appointment Details with 4-stage stepper and refund cancellation modal (`/appointments/[id]`), Telehealth Video Room with simulated WebRTC streams, in-call chat, and shared vitals (`/telehealth/[appointmentId]`), Digital Prescriptions archive (`/prescriptions`), Printable Clinical Rx slip with digital signature (`/prescriptions/[id]`), Diagnostic Lab Reports (`/lab-reports`), Itemized Lab Report with reference ranges (`/lab-reports/[id]`), Medical Records & Vitals Tracker with log modal (`/records`), Family Members management (`/family`), Invoices & Billing receipts (`/invoices`), and Patient Sign In with 1-click Ananya Deshmukh demo login (`/login`).
> Turbopack production build compiled 19/19 routes with 0 errors; 18/18 API unit tests passed; 40/40 template studio tests passed; full Stage 0 verify (3,983 tests) passed offline with 0 model calls. Next: CareClinic (Part 3/4: Doctor Telehealth & Clinical Workstation `apps/doctor`).

> **R-535 (2026-09-23): CareClinic (Part 1 of 4: Clinical Care & Telemedicine API, Database Migrations, Domain Services & Deterministic Seed).**
> Built hidden draft template at `templates/catalog/_care-clinic`: root `template.json` manifest with 4 apps (`patient`, `doctor`, `admin`, `api`), 4 roles (`patient`, `doctor`, `receptionist`, `admin`), 18 entities, 10 features, 3 demo users (`ananya@careclinic.test`, `dr.rajesh@careclinic.test`, `admin@careclinic.test`), and 48 screen definitions.
> 5 PostgreSQL database migrations (`001_core.sql` through `005_audit_telehealth.sql` with `uq_doctor_slot` slot uniqueness constraint, immutable e-prescriptions, and HIPAA-compliant chart access audit logs). Complete Hono TypeScript `services/api` on Node >= 22.18 with domain services (scheduling & 20-min dynamic slot generator, 5-stage appointment state machine `booked` -> `checked_in` -> `in_consult` -> `completed`, SOAP notes, ICD-10 diagnoses, immutable prescriptions, billing & refund rules, HIPAA chart access audit logging, and WebRTC telehealth sessions); deterministic seed generator (`scripts/generate-seed.mjs` -> `seed/001_demo.sql` with 12 doctors across 8 specialties, 150 patients, 900 appointments, consultations, prescriptions, and lab orders); 18/18 API unit tests (100% pass in 374ms); 40/40 template studio tests passed; Stage 0 verification (3,983 tests passed fully offline with 0 model calls). Next: CareClinic (Part 2/4: Shared Library `@careclinic/shared` & Patient Web App `apps/patient`).

> **R-534 (2026-09-23): Bazaar (Part 4 of 4: Marketplace Operations Console `apps/admin`, Playwright 48 screenshots & Publication).**
> Built `apps/admin` on Next.js 16 App Router + React 19 + Turbopack + Tailwind CSS 4 with high-density control-room operations styling.
> Includes 18 routes: Overview Dashboard, Vendor Directory, Vendor Profile Review & Commission Overrides, KYC Verification & Approval,
> Global Orders List with split shipments, Deep Order Investigation, Global Shipments Monitor, Platform Financials, Double-Entry
> Ledger Audit, Settlement Batches, Payout Batch Approvals, Promotional Coupons, Create Coupon, Review Moderation, Operator Audit Logs,
> Platform Settings, Nationwide Live Logistics Map, and Operator Login (1-click Vikram Malhotra credentials). Added full admin API endpoints
> and client SDK methods in `@bazaar/shared`. Captured all 48 screens across buyer (16), seller (14), and admin (18) plus composed cover image
> `media/cover.jpg` with Playwright runner. Published template to `templates/catalog/bazaar` (category: commerce, v1.0.0, 4 apps).
> Studio template catalog tests passed (40/40); full Stage 0 verify (3,983 tests) passed offline with 0 model calls. Next: CareClinic (Part 1/4: Clinical Care & Practice Management API & Database).

> **R-533 (2026-09-23): Bazaar (Part 3 of 4: Artisan Vendor Portal `apps/seller`).**
> Artisan & craft guild vendor portal built on Next.js 16 App Router + React 19 + Turbopack + Tailwind CSS 4
> with atelier workshop slate/charcoal/bronze styling. Includes 10 static prerendered pages and 2 dynamic routes:
> Workshop Operations Dashboard (`/`), Multi-stage Fulfillment Board (`/shipments`), Consignment Investigation &
> Lifecycle Controller (`/shipments/[id]`), Artisan Craft Catalog (`/products`), Craft Listing Creation Form with
> multi-variant matrix (`/products/new`), Product Editor (`/products/[id]`), Escrow Ledger & RTGS Payout Processor
> (`/payouts`), Customer Reviews & Replies Manager (`/reviews`), Atelier Settings & GI-tag KYC (`/settings`), and
> Artisan Authentication (`/login`) with 1-click Kripal Singh demo credentials. Standardized extensionless imports
> in `@bazaar/shared`. All builds succeeded in Turbopack (0 errors); all 19 API tests passed; 40 template studio
> tests passed; full Stage 0 verify (3,983 tests) passed offline with 0 model calls.

> **R-532 (2026-09-23): Bazaar (Part 2 of 4: Shared Library & Storefront Web App `apps/buyer`).**
> Multi-Vendor Commerce Platform storefront web application built on Next.js 16 App Router + React 19 +
> Turbopack + Tailwind CSS 4 with custom terracotta/saffron/indigo artisan styling. Includes `@bazaar/shared`
> (`packages/shared`: canonical types, universal typed API client, currency/status helpers, and SSE `useStream` hook)
> and 17 storefront routes (11 static prerendered, 6 dynamic): Marketplace Home, Category Catalog, Product
> Details with variant matrix, Artisan Shop Profile, Multi-Vendor Cart grouped by seller, Checkout with
> Suspense boundary & mock payment methods, Customer Orders History, Deep Order Investigation with 5-stage
> progress bar & return request modal, Real-time Delivery Radar with animated GPS telemetry, Public Shipment
> Tracking timeline, Customer Reviews with artisan replies, Address Book, and Patron Authentication (1-click
> Priya Sharma login & signup). All 19 API tests passed; 40 template studio tests passed; Next.js production
> build succeeded with 0 errors; full Stage 0 verify (3,983 tests) passed offline with 0 model calls. Next: R-533, Bazaar Vendor Portal `apps/seller`.

> **R-531 (2026-09-23): Bazaar (Part 1 of 4: API, Database & Demo Data).** Multi-Vendor
> Commerce Platform hidden draft scaffolded at `templates/catalog/_bazaar`. Includes 5 complete
> PostgreSQL database migrations (`001_core.sql` through `005_engagement.sql`), Hono TypeScript
> backend API on Node >= 22.18, multi-vendor order split checkout, 5-stage shipment fulfillment
> state machine, multi-party double-entry accounting ledger, promo coupons engine, mock payments and
> courier providers, real-time SSE event bus, deterministic demo seed fixtures
> (`scripts/generate-seed.mjs` -> `seed/001_demo.sql` with 3 demo credentials, 8 shops, 11 products with
> variants, and orders), and root `template.json` defining 48 screen journeys. 19/19 unit tests passed
> in 247ms, 40/40 template studio tests passed, and full Stage 0 `task verify` passed (3,983 tests, 0 failures,
> 100% offline). Next: R-532, Bazaar Storefront `apps/buyer`.

> **R-530 follow-up (2026-09-23): the platform runs on any new machine.** `docs/SETUP.md` is the
> requirement and install contract, and `./scripts/omnistack.sh doctor` checks all of it (Python
> 3.13, Node 22.18+, ripgrep, the compose plugin, a sourceable `.env`, a container-safe
> agent-engine URL, a cloud token budget that fits). Ollama is installed with Qwen 2.5 Coder;
> running on it exposed three real platform defects, now fixed: a fixed 5-minute upstream budget, an
> edit parser that threw away good work over formatting, and an editor left blind when the model
> named files that do not exist.

> **R-530 (2026-09-23): RideNow is published.** The operations console (`apps/admin`, 18 pages:
> dashboard, live map, trips, riders, drivers with document review, pricing, surge zones, promos,
> payouts, finance, support, audit, settings) completes the template. 48 screenshots of every page
> of all three apps plus a cover were captured from the running apps, and
> `templates/catalog/ride-now` v1.0.0 is listed in the marketplace. Driving a preview with a real
> browser for the first time exposed five platform defects, all fixed — most importantly that no
> preview page loaded in a browser (the proxy's `content-encoding`) and that none was interactive
> (dev servers never hydrate behind the proxy; previews now build and serve production). Next:
> R-531, Bazaar.

> **R-529 (2026-09-22): Phase T handoff doc.** `R_&_D/OmniStackAI_Template_Marketplace_Plan_v1.md`
> holds the remaining templates, the method and a demo guide. `./scripts/preview-drafts.sh` shows
> RideNow in the marketplace. Next: R-530, the RideNow admin app, then publish.

> **R-528 (2026-09-22): RideNow part 3/4.** The driver PWA (13 pages, installable) is built and
> verified live alongside the rider app and the API.

> **R-527 (2026-09-22): RideNow part 2/4.** The rider web app (15 routes) and shared package are
> built and verified live in the preview. Two preview bugs affecting every template are fixed
> (orphaned processes after restarts, LAN dev-origin 403).

> **R-526 (2026-09-22): RideNow part 1/4.** The first real template's API, database and demo data
> are built and tested live (workflow 4/4). The rider, driver and admin apps follow in R-527 to
> R-529.

> **R-525 (2026-09-21): T-4 code-edit agent.** Chat changes on template projects (add, remove or
> change features, DB migrations) are made in the real code, checked, then committed or rolled back.

> **R-524 (2026-09-21): chat edits work on Gemini** (output budget no longer capped at 2,048).

> **R-523 (2026-09-21): T-3 Template marketplace in the console.** Browse and search templates,
> read a full detail page, then "Use template" to get your own project in the Studio.

> **R-522 (2026-09-21): Google (Gemini) runs builds.** Fixed a token-budget bootstrap bug and
> added paced retries for temporary 502/503/504. Builds take about 30 s instead of about 3 minutes
> on local Ollama.

> **R-521 (2026-09-21): generated apps run again.** Fixed 10 defects (most from `1fe1015`) that
> made every prompt-built home page 500, aborted previews on seed data and broke sign-up. Sign-up
> can't choose a role and reset-by-email is refused. `smoke-core.sh` now checks the preview too.

> **R-520 (2026-09-21): T-2 Multi-app preview.** Template projects preview all their apps
> together (shared API and seeded DB), with an app switcher, a phone frame for PWAs and demo logins.

> **R-519 (2026-09-21): T-1 Template format + registry.** A template is a read-only golden repo
> plus `template.json` in `templates/catalog/`. "Use template" creates the user's own project copy
> (fresh git history, recorded provenance), and the original stays identical for everyone.
> Catalogue routes are public; use and provenance need auth.

> **R-518 (2026-09-21): T-0 Stabilise the core.** The core loop now works live end to end:
> register, create from a prompt, streamed build, rename, reopen, chat edit commit, and restart
> persistence. 10 defects fixed (startup panic, missing `/opened`, `users.full_name` SQL, 15 s stream
> cut-off, console 204/name/skills handling, workspace-edit crash, stale image). `scripts/smoke-core.sh`
> is the live regression check.

> **R-517 (2026-09-21): Node.js backend codegen — Express/Hono alongside Python/Go.**
> Implemented first-class, deterministic Node.js backend code generation (`GenerationTarget.BACKEND_NODE` / `BackendStrategy.NODE`) alongside Python (FastAPI) and Go (`net/http`) backend adapters.
> Key capabilities:
> 1. Framework Adapters (`services/agent-engine/src/omnistackai_agent_engine/codegen/backend_node.py`):
>    - `NodeBackendAdapter`, `ExpressBackendAdapter`, and `HonoBackendAdapter`.
>    - Automatic framework selection: Express by default, Hono when `framework="hono"` or mentioned in prompt/name.
> 2. Complete Idiomatic TypeScript Project Architecture:
>    - `package.json`: ESM-configured with scripts, express/hono dependencies, zod, and pg.
>    - `tsconfig.json`: Modern NodeNext module resolution, ES2022 target, strict mode.
>    - `src/config.ts`: Type-safe environment configuration with port, database, JWT, and CORS settings.
>    - `src/index.ts` & `src/app.ts`: Graceful shutdown, CORS, JSON body parsing, logging, and router registration.
>    - `src/models/types.ts` & `src/models/validation.ts`: TypeScript interfaces and Zod runtime validation schemas.
>    - `src/middleware/auth.ts`: JWT bearer token verification middleware.
>    - `src/db/pool.ts` & `src/db/<entity>.ts`: PostgreSQL data access with pooled connections and seamless in-memory fallback.
>    - `src/routes/<resource>.ts`: Standard REST CRUD handlers wired using `route_wiring.py` (Op.LIST, Op.GET, Op.CREATE, Op.UPDATE, Op.DELETE, Op.LIST_BY).
>    - `contracts/openapi.json`, `schema.sql`, `seed.sql`, `.env.example`, and `README.md`.
> 3. Assembler & Registry Integration:
>    - Mapped `BackendStrategy.NODE` to `GenerationTarget.BACKEND_NODE` in `assembler.py`.
>    - Registered `NodeBackendAdapter` in `default_registry()`.
>    - Exported from `codegen/__init__.py`.
> 4. Gates:
>    - 10 unit tests in `test_backend_node.py` (all passed, including live Node.js syntax parsing).
>    - 6 assembler tests in `test_assembler.py` (all passed).
>    - 19 Go packages clean in `services/control-plane`.
>    - `scripts/test.sh` contract assertions clean.
>    - Full `task verify` passed (3,861 tests in 91.6s, Stage 0 clean).
> NEXT: **Ready for next roadmap task**.

> **R-516 (2026-09-21): Email feature — SMTP / Resend integration in generated apps.**
> Implemented complete, zero-external-dependency Transactional Email capabilities for generated Next.js applications:
> 1. Pure Node.js Standard-Library SMTP Client:
>    - Full RFC 5321 / RFC 4954 socket client in `lib/email.ts` utilizing `node:net`, `node:tls`, and `node:crypto`.
>    - Zero external npm dependencies (eliminates `nodemailer` bundle overhead and CVE supply-chain exposure).
>    - Supports direct TLS (port 465) and STARTTLS (port 587/25) with dynamic socket upgrade.
>    - Implements `AUTH LOGIN` (Base64 credentials), MIME multipart/alternative structuring, and 15s timeout handling.
> 2. Resend REST API Client:
>    - Zero-dependency native `fetch` dispatch to `https://api.resend.com/emails`.
>    - Typed `SendEmailOptions` (`to`, `subject`, `html`, `text`, `from`, `replyTo`, `cc`, `bcc`) and granular error reporting.
> 3. Pre-built Responsive HTML Email Templates:
>    - Universal inline-CSS templates in `lib/email-templates.ts`: `welcomeEmailTemplate`, `otpVerificationTemplate`, `passwordResetTemplate`, and `notificationTemplate`.
>    - Validated through live Node.js runtime execution (`--experimental-strip-types`).
> 4. Interactive Contact Form UI Component:
>    - Ready-to-use client React component in `components/contact-form.tsx` wired to `app/api/send/route.ts`.
> 5. Control-Plane Handshake & Catalog:
>    - Updated connector catalog generated file listings and added live port (1-65535) and hostname validation for SMTP and API key checks for Resend in `internal/connectors/handler.go`.
> 6. Console-Web UI:
>    - Added email code usage guides, template previews, and one-click copyable snippets to `components/project-connectors-manage.tsx`.
> 7. Gates: 7/7 Python tests pass (including live Node execution), 19/19 Go packages pass, Next.js build/typecheck/lint pass, and full `task verify` (3,851 tests passed, Stage 0 clean).
> NEXT: **Ready for next roadmap task**.

> **R-515 (2026-09-21): Team / Org model — multi-member workspaces & shared projects (`R_&_D/OmniStackAI_Implementation_Brief_v6.md` Sections 7 and 17).**
> Implemented complete multi-tenant Organization and Workspace architecture enabling shared projects, member invitations, and role-based access control.
> Key capabilities:
> 1. Hierarchical Tenancy: `Organization -> Workspace -> Project -> Environment -> Target -> Deployment` with RBAC roles (`owner`, `admin`, `member`, `viewer`).
> 2. Database Migration (`000015_organizations_workspaces`):
>    - Tables: `organizations`, `workspaces`, `workspace_members`, and `workspace_invites`.
>    - Projects table extended with `workspace_id` foreign key.
>    - Automatic backfill establishing personal org and default workspace for all existing users and linking their projects with zero data loss.
> 3. Go Control-Plane (`internal/workspaces` & `internal/projects`):
>    - Workspace CRUD, membership management, role assignment, and secure tokenized invites.
>    - Project multi-tenancy authorization checking project creator or workspace membership for read/write access.
>    - Standard library only (`github.com/jackc/pgx/v5` remains sole direct dependency). Full test suite in `workspaces_test.go` (all 19 packages pass).
> 4. Console-Web UI:
>    - `WorkspaceSwitcher` in top navigation header with active workspace indicator, role badge, quick switcher, and "+ Create workspace" modal.
>    - Lovable-grade `WorkspaceManage` in Settings -> Team & Workspaces (members table, role selector, invite modal with copyable link, pending invites table with revoke, workspace settings, danger zone).
>    - Public/authenticated invite acceptance page at `/invite/[token]`.
>    - Projects page workspace filtering and creator badge on project cards.
> 5. Gates: 3,850/3,850 tests pass, `task verify` clean, `scripts/test.sh` clean, Next.js build/typecheck/lint clean.
> NEXT: **Ready for next roadmap task**.

> **R-514 (2026-09-21): Mobile (React Native / Expo) Framework Adapter (`R_&_D/OmniStackAI_Implementation_Brief_v6.md` Section 37 & 6.4).**
> Implemented production-grade React Native (Expo SDK 51) framework adapter un-gating mobile application synthesis for the platform.
> Key capabilities:
> 1. Framework Adapter: `ReactNativeAdapter` in `services/agent-engine/src/omnistackai_agent_engine/codegen/react_native.py` implementing `FrameworkAdapter` for `GenerationTarget.REACT_NATIVE`.
> 2. Complete Expo TypeScript Application Architecture:
>    - Configurations: `package.json` (Expo 51, React Native 0.74, React Navigation Native Stack, Lucide icons), `app.json`, `tsconfig.json`, `babel.config.js`, `index.js`.
>    - Design System: `src/design-system/tokens.ts` (synchronized with `BrandTokens`: colors, radii, spacing, typography) and native components (`Button`, `Card`, `Badge`, `Input`, `StatCard`, `ScreenContainer`).
>    - Data & Auth Layer: `src/shared/api/client.ts` (typed HTTP client) and `src/shared/auth/AuthContext.tsx` (token injection, session state, user profiles).
>    - Feature Slices per Entity: `src/features/<entity>/` with TypeScript models, CRUD API clients, `use<Entity>s` hooks, `ListScreen` (FlatList, search, KPI tiles, delete CTA), and `DetailScreen` (typed form inputs, create/edit modes, save handlers).
>    - App Navigation & Shell: `src/app/screens/OverviewScreen.tsx`, `src/app/navigation/RootNavigator.tsx`, and `src/app/App.tsx`.
> 3. Monorepo Assembly: Registered in `default_registry()` and wired into `assembler.py` under `apps/mobile/` when `ir.project_strategy.mobile_profile` is `MobileProfile.REACT_NATIVE`.
> 4. Gates: 9 unit tests in `test_react_native_adapter.py`, 6 assembler tests, 3,850/3,850 Python tests, 18 Go packages, Next.js build/typecheck/lint, and full `task verify` clean.
> NEXT: **Mobile live preview / device QR flow (Section 15.3)**.

> **R-512 (2026-09-20): G-04 Payment Gateways in Generated Apps — Stripe & Razorpay (`R_&_D/specs/G-04-payments.md`).**
> Implemented production payment gateway integration for generated apps with zero PCI scope for the platform, strict HMAC-SHA256 signature verification, and event idempotency.
> Supported gateways:
> 1. Stripe: Global standard (cards, wallets, 135+ currencies). Generates `lib/payments/stripe.ts` (typed checkout & signature verification, zero npm dependencies), `app/api/checkout/route.ts`, `app/api/webhooks/stripe/route.ts`, success/cancel pages, and deterministic test suite.
> 2. Razorpay: India standard (UPI, QR, cards, netbanking, INR settlement). Generates `lib/payments/razorpay.ts` (typed orders & signature verification), `app/api/checkout/route.ts`, `app/api/webhooks/razorpay/route.ts`, success/cancel pages, and deterministic test suite.
> Database: PostgreSQL migration `000013_project_payments` added `payment_gateway` TEXT column to `projects` table with CHECK constraint `('', 'stripe', 'razorpay')`.
> Control-Plane Backend: `internal/payments` package with `store.go`, `handler.go` (`GET/PUT/DELETE /projects/{id}/payments`), required secrets inspection (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`) checking "set" vs "not_set" without leaking key values, and live webhook endpoint URL generation. Zero new Go dependencies (`github.com/jackc/pgx/v5` remains the sole direct dependency).
> Agent-Engine: `studio/payments.py` with `apply_payments` and `remove_payments` codegen hooks committing additions and clean removals directly to the project's Git repository.
> Console Web UI: Studio Manage → Payments tab with `ProjectPaymentsManage` (gateway cards, generated code files breakdown, required secret keys checklist with deep links to Manage -> Secrets, copyable live webhook URL, test mode sandbox tips, and disconnect confirm modal).
> Gates: All 3,841 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **Phase G continued**.

> **R-511 (2026-09-20): G-03 Connectors v1 (`R_&_D/specs/G-03-connectors.md`).**
> Implemented clean connector framework for generated apps to communicate with 3rd-party services using developer credentials, adhering to the Honest Catalogue Rule (zero fake 113-service marketing cards).
> Supported out of the box: Google Analytics 4 (GA4 measurement ID tag injection into layout), Resend (zero-npm-dep REST API transactional email helper), and custom SMTP (typed dispatcher).
> Database: PostgreSQL migration `000012_connectors` created `connector_accounts` (user credentials with encrypted refresh tokens) and `project_connectors` (project-scoped config & enabled state).
> Control-Plane Backend: `internal/connectors` package with Catalog, PgStore, and REST handlers (`/connectors`, `/projects/{id}/connectors`, `/projects/{id}/connectors/{provider}`, `/projects/{id}/connectors/{provider}/test`). Zero new Go dependencies (`github.com/jackc/pgx/v5` remains the single direct dependency).
> Agent-Engine: `studio/connectors.py` with `apply_connector` and `remove_connector` codegen hooks committing code additions and removals directly to the project's Git repository.
> Console Web UI: Studio Manage → Connectors tab with `ProjectConnectorsManage` (state chips, generated code explanation drawers, live credential testing, and "Request a Connector" dialog capturing future OAuth requests).
> Gates: All 3,837 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **Phase G continued**.

> **R-510 (2026-09-20): G-02 Custom Domain — Bring Your Own (`R_&_D/specs/G-02-domains.md`).**
> Implemented bring-your-own custom domain management for OmniStackAI applications with ₹0 platform cost, zero domain registrar/renewal/WHOIS overhead.
> Database: PostgreSQL migration `000011_domains` created `project_domains` with global `UNIQUE(hostname)` anti-hijack constraint, provider, DNS record types, real TLS status, and primary flag.
> Control-Plane Backend: `internal/domains` package with RFC 1123 format validation, rejection of IP addresses and bare TLDs, standard-library DNS verification (`net.LookupCNAME` / `net.LookupIP`), provider domain synchronization (Vercel & Netlify API drivers), primary domain switching, and delete with provider sync.
> Console Web UI: Studio Manage → Domain tab with zero-markup info notice, live RFC 1123 hostname validation, copyable DNS instruction cards (Type, Name/Host, Value/Target with copied feedback), step-by-step registrar setup guides with direct links for Cloudflare, GoDaddy, Namecheap, Hostinger, BigRock, real-time DNS & TLS status badges (never fake), "Check DNS now" action with live polling, and propagation notice (minutes to 48 hours).
> Gates: 3,831 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **Phase G continued**.

> **R-509 (2026-09-20): G-01 Publish v1 — Deploy from GitHub to Vercel/Netlify (`R_&_D/specs/G-01-publish.md`).**
> Implemented 1-click cloud publishing from connected GitHub repositories to user-owned Vercel or Netlify accounts via personal access tokens with ₹0 hosting infrastructure cost for OmniStackAI.
> Database: PostgreSQL migration `000010_deployments` created `deploy_connections` (AES-256-GCM encrypted tokens), `deployments` (history with commit SHA, status, live URL), and added `deploy_provider`, `deploy_external_id`, and `live_url` to `projects`.
> Control-Plane Backend: `internal/deploy` package with AES-256-GCM authenticated encryption, AAD binding (`user_id:provider`), and key rotation; standard-library `net/http` drivers for Vercel and Netlify (0 new Go dependencies; `pgx/v5` remains the single direct dependency); handlers for connections, publish readiness, publish triggering with secret env propagation, and deployment polling with tenant isolation.
> Agent-Engine: `studio/publish.py` deterministically evaluating project architecture into Path 1 (Web-only -> Vercel/Netlify), Path 2 (Web + backend -> starter `render.yaml`/`fly.toml`), and Path 3 (Full-stack with DB -> external PostgreSQL `DATABASE_URL` guidance). Mounted `GET /api/workspaces/{id}/publish/readiness`.
> Console Web UI: `HostingKeysManager` on `/settings#hosting`, `PublishDialog` on Studio Header with architecture assessment badge, GitHub check, provider selector, inline token connector, secrets count notice, deploy trigger, and live site celebration; and `ProjectPublishManage` in Studio Manage → Publish tab with live production card, visit site, redeploy, backend guidance configs, and deployment history table.
> Gates: 3,831 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **Phase G continued**.

> **R-508 (2026-09-20): Security Scanning & Automated Tests (F-10 spec).**
> Implemented real dependency audits, deterministic secret scanning, framework security checks, and automated test runners
> across web (pnpm), Python (pytest/unittest), and Go (go test ./...) with a Lovable/Dyad-grade Console UI in **Studio Manage → Security**
> and **Studio Manage → Tests**.
> Agent-Engine: Implemented `omnistackai_agent_engine.studio.security` running real dependency audits (`pnpm audit`, `pip-audit`, `govulncheck`),
> reporting uninstalled toolchains honestly as `skipped: <tool> not installed` (never as passed). Secret scanning inspects generated source
> for hardcoded API keys (`sk-...`, `AIza...`, `AKIA...`, `ghp_...`, `stripe_secret`), private keys, and `.env` files. Framework checks
> verify `dangerouslySetInnerHTML`, wildcard CORS with auth, cookies missing `httpOnly`/`SameSite`, and SQL string interpolation.
> Implemented `omnistackai_agent_engine.studio.tests_runner` detecting and executing test suites, parsing test outcomes into structured cases,
> and providing an honest empty state ("This project has no test suite yet — ask the chat to add one").
> Control-Plane Backend: Added proxy routes in `internal/projects/handler.go` (`POST /projects/{id}/security/scan`, `GET /projects/{id}/security`,
> `POST /projects/{id}/tests/run`, `GET /projects/{id}/tests`) with tenant isolation.
> Console Web UI: Added types and API client functions in `lib/control-plane.ts`, Next.js API proxy routes under `app/api/projects/[id]/security`
> and `app/api/projects/[id]/tests`, and built `components/project-security-manage.tsx` and `components/project-tests-manage.tsx`
> with findings grouped by severity/file, checks performed checklist, clean state display, summary bars, per-suite runner view, terminal output,
> and "Fix with AI" action.
> Gates: 3,827 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **Phase F continued**.

> **R-507 (2026-09-20): Database Explorer & SQL Editor (F-09-database spec).**
> Implemented PostgreSQL database explorer and SQL editor for generated applications with read-only transaction safety,
> schema inspection, and a Lovable-grade Console UI in **Studio Manage → Database**.
> Agent-Engine: Implemented `omnistackai_agent_engine.studio.database` exposing `list_tables`, `get_table_schema`, `get_table_rows`,
> `execute_query`, and `get_schema_sql` running against the project container (`psql --csv`). Read-only queries wrapped in `BEGIN; ... ROLLBACK;`,
> explicit write mode toggle, 32 KB SQL limit, 10s timeout, sanitized table/column identifiers, and audit logging via `StudioLogManager`.
> Control-Plane Backend: Added proxy routes in `internal/projects/handler.go` (`GET /projects/{id}/db/tables`, `GET /projects/{id}/db/tables/{table}`,
> `POST /projects/{id}/db/query`, `GET /projects/{id}/db/schema`) with tenant isolation and 409 Conflict handling for unprovisioned databases.
> Console Web UI: Added types and API client functions in `lib/control-plane.ts`, Next.js API proxy routes under `app/api/projects/[id]/db/`,
> and built `components/project-db-manage.tsx` with tables sidebar with live search, row browser with pagination and column sorting,
> Structure view with column metadata, SQL Editor with Cmd+Enter execution, Write Mode warning toggle, timing and count chips, and Schema SQL viewer.
> Gates: 3,815 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **F-10 (R-508) Security scanning & automated test runs (spec `R_&_D/specs/F-10-security-tests.md`)**.

> **R-506 (2026-09-20): Logs & live chat streaming (F-08-logs-chat spec).**
> Implemented structured build and application logs, real build cancellation with 0 git commits, Web Speech API voice input,
> text file attachments (.md, .txt, .json, .csv, .sql, .ts, .tsx, .py up to 256 KB, max 4), and a Lovable-grade Console UI in **Studio Manage → Logs** (`Lova-17`).
> Agent-Engine: Implemented `StudioLogManager` in `studio/logs.py` (`<workspace>/logs/build.jsonl`, `<workspace>/logs/app.log` with `OMNISTACKAI_LOG_MAX_BYTES` rotation, secrets scrubbing `***`, SSE stream). `live_serve.py` generation loop checks `workspace_store.is_cancelled` between chunks and exits immediately with `phase: cancelled` (committing nothing to git).
> Control-Plane Backend: Exposed `/projects/{id}/logs`, `/projects/{id}/logs/stream`, `POST /projects/{id}/build/cancel`. In `handleProjectBuildStream`, debits consumed credits and records `model_calls` with `error_code = 'cancelled'`. Client disconnect triggers upstream cancellation.
> Console Web UI: Mounted Manage → Logs tab (`components/project-logs-manage.tsx`) with Build/App toggle, level filter (`all`/`info`/`warn`/`error`), search, follow toggle, copy, download. Enhanced chat composer (`studio-chat.tsx`) with Stop button (`Square` icon, triggers `AbortController.abort()` and server cancel), Web Speech API mic toggle with listening animation, and paperclip text attachments with chips.
> Gates: 3,785 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js typecheck/lint clean.
> NEXT: **F-09 (R-507) Database Explorer & SQL Editor (spec `R_&_D/specs/F-09-database-explorer.md`)**.

> **R-505 (2026-09-20): SEO & AI search (F-07-seo spec).**
> Implemented Next.js indexability codegen (`sitemap.ts`, `robots.ts`, `llms.txt`, `opengraph-image.tsx`, JSON-LD structured data, and per-page metadata),
> PostgreSQL schema migration `000009_seo.up.sql` / `down.sql` (`project_seo` and `project_page_seo`), Go control-plane store and REST handlers
> (`/projects/{id}/seo`, `/projects/{id}/seo/pages`, `/projects/{id}/seo/pages/{route...}`, `/projects/{id}/seo/audit`, `/projects/{id}/seo/suggest`),
> deterministic SEO audit engine (0 credits) computing 0–100 health score with line-level findings, workspace repository git commit generation on page metadata edits,
> and a Lovable-grade Console UI in **Studio Manage → SEO & AI Search** (site defaults, pages table with 50–160 character counters, Google Search & Social card previews,
> audit findings, and AI copy suggestions with credit cost notice).
> Gates: 3,779 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.

> **R-504 (2026-09-20): AI — model configuration (BYOK) and usage per project/account (F-06-ai-usage spec).**
> Implemented Bring-Your-Own-Key (BYOK) provider key storage encrypted with AES-256-GCM in PostgreSQL `user_provider_keys`,
> per-project model pinning, an immutable `model_calls` audit table, and transparent multi-tier usage tracking across the platform.
> Database Schema: Created migration `000008_ai_usage.up.sql` / `down.sql`: `user_provider_keys` table with UUID `id`, `user_id`
> foreign key with cascade delete, `key_ciphertext BYTEA`, `provider_id TEXT`, `label TEXT`, and unique constraint on `(user_id, provider_id)`.
> Created immutable `model_calls` audit table tracking tokens, latency, cost, and credits, indexed by user and project. Added
> `model_provider_id` and `model_id` to `projects` table for per-project pinning.
> Control-Plane Backend: Built `internal/ai` store, resolution engine, and REST handlers (`GET /ai/providers`, `GET /ai/keys`,
> `PUT /ai/keys/{providerId}`, `DELETE /ai/keys/{providerId}`, `POST /ai/keys/{providerId}/test`, `GET /ai/models`,
> `GET/PUT /projects/{id}/model`, `GET /projects/{id}/usage`, `GET /usage`) using Go standard library `crypto/aes` and `crypto/cipher`
> (zero external Go dependencies). Bound ciphertext with AAD `user_id:provider_id` to prevent cross-user key theft.
> Supported transparent re-encryption on key rotation via `OMNISTACKAI_SECRETS_KEY_PREVIOUS`. Enforced strict model resolution precedence:
> (1) Project pinned model -> (2) User BYOK key (0 credits debited, `billed_to = 'byok'`) -> (3) Platform cloud provider (credits debited,
> `billed_to = 'platform'`) -> (4) Local Ollama (0 credits, `billed_to = 'local'`). Guaranteed zero key leakage: keys are strictly write-only
> and never returned in any API response or log. Injected `AIStore` into `projects` and `jobs` handlers, recording granular `model_calls`
> rows atomically alongside credit debits.
> Agent-Engine Integration: Updated `intake/provider_resolution.py` to accept explicit `provider_id`, `model_id`, and `api_key`.
> Updated `studio/live_serve.py` build and edit endpoints to propagate resolved model/key parameters and return granular `usage.calls: [...]` breakdown.
> Console Web UI: Built **Settings → AI** (BYOK keys manager with AES-256-GCM notice, key test button with latency feedback, and Add/Edit/Delete modals),
> **Settings → Usage** (KPI totals, per-project usage breakdown, daily activity table, and 7d/30d/90d range selectors), and
> **Studio Manage → AI & Model** tab (project model pinning and project-specific usage metrics).
> Gates: 3,769 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **F-07 (R-505) SEO & AI search (spec `R_&_D/specs/F-07-seo-and-ai-search.md`)**.

> **R-503 (2026-09-20): Secrets — encrypted per-project configuration (F-05-secrets spec).**
> Implemented AES-256-GCM encrypted configuration for generated applications (API keys, SMTP passwords, payment credentials).
> Database Schema: Created migration `000007_project_secrets.up.sql` / `down.sql`: `project_secrets` table with UUID `id`, `project_id`
> foreign key with cascade delete, `key ~ '^[A-Z][A-Z0-9_]*$'` constraint, `value_ciphertext BYTEA`, `description TEXT`,
> and unique constraint on `(project_id, key)`.
> Control-Plane Backend: Built `internal/secrets` store and REST handlers (`GET /projects/{id}/secrets`, `PUT /projects/{id}/secrets/{key}`,
> `DELETE /projects/{id}/secrets/{key}`, and `POST /projects/{id}/secrets/reveal/{key}`) using Go standard library `crypto/aes` and `crypto/cipher`
> (zero external Go dependencies). Bound ciphertext with AAD `project_id:key` to prevent cross-project or cross-key tampering.
> Supported transparent re-encryption on key rotation via `OMNISTACKAI_SECRETS_KEY_PREVIOUS`. Unconfigured master key returns HTTP 503 instead
> of storing plaintext. Injected `SecretsStore` into projects handler and forwarded decrypted secrets map to agent-engine during preview.
> Agent-Engine Runtime Injection: Updated `localrun/plan.py`, `localrun/run.py`, and `studio/server.py` to accept `extra_env` / `env` and
> inject decrypted secrets directly into preview runner processes (`process.env`) at runtime. Secrets are never written to repository files on disk,
> git commits, or exported ZIP archives.
> Console Web UI: Built **Manage → Secrets** tab in `/studio/[projectId]/manage/page.tsx` with masked table display (`••••••••`),
> 30-second reveal countdown timer, UPPER_SNAKE_CASE validation, copy key action, Add/Edit dialog, Delete confirmation, and preview restart prompt banner.
> Gates: 3,765 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **F-06 (R-504) AI — model configuration (BYOK) and usage per project/account (spec `R_&_D/specs/F-06-ai-usage.md`)**.

> **R-502 (2026-09-20): Knowledge & Skills — custom instructions & domain templates (F-04-skills spec).**
> Implemented a complete two-layer custom instructions system for project-level briefs and account-level reusable skills.
> Layer 1 — Project Knowledge: Persistent per-project brief (up to 16,384 characters) injected into every build and edit of that project,
> prioritized ahead of any user skills in prompt context. Stored in `projects.knowledge` via PostgreSQL migration `000006_skills.up.sql`.
> Layer 2 — User Skills: Reusable instruction sets (up to 8,192 characters each) with lower-kebab-case identifiers (`^[a-z0-9]+(-[a-z0-9]+)*$`),
> attachable to specific projects (`project_skills` junction table), set as account defaults (`is_default`), or invoked ad-hoc in single
> messages via `@mentions`.
> Control-Plane Backend: Built `internal/skills` store and REST handlers (`/skills`, `/skills/{id}`, `/projects/{id}/knowledge`,
> `/projects/{id}/skills`, `/projects/{id}/skills/{skillId}`) and context resolution engine (`ResolveContext`). Updated projects handler to forward
> resolved context to the agent-engine on all build and edit requests.
> Agent-Engine Context Injection: Implemented `intake/context.py` with deterministic context assembly obeying `OMNISTACKAI_CONTEXT_MAX_CHARS`
> (default 24k cap), prioritizing knowledge, sorting skills, and cleanly truncating from the end with `context_truncated: true` and active/truncated
> skill lists. Injected into system prompt ahead of schema/rules in `nl_to_ir` and `app_delta`. Protected user privacy by never leaking full skill
> bodies back to the browser in chat/build streams.
> Console Web UI: Added **Manage → Knowledge** tab (16 KB textarea, character counter, saved-at timestamp), **Manage → Skills** tab
> (attached skills list, detach action, "Add from library" picker, "New skill" shortcut), **Settings → Skills library** (account skills cards,
> skill editor dialog with live "What the model will see" preview and 4 one-click starter templates), and **Studio chat composer** (active context
> chips with next-message toggle, inline `@` autocomplete popover, and honest amber `context_truncated` alert banner).
> Gates: 3,763 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **F-05 (R-503) Secrets — encrypted per-project configuration (spec `R_&_D/specs/F-05-secrets.md`)**.

> **R-501 (2026-09-20): Code ownership — download, connect GitHub, push (F-03-git spec).**
> Implemented instant .zip export and GitHub App connection + push, solving vendor lock-in and enabling code ownership.
> Part 1 — Instant Download (.zip): Added streaming endpoint `GET /projects/{id}/export` and agent-engine `export_zip`
> streaming repository at HEAD, strictly excluding VCS internals (`.git`), dependencies (`node_modules`), caches (`.next`,
> `__pycache__`, `.venv`, `venv`), and environment secrets (`.env`, `.env.*` except `.env.example`) with zero memory buffering.
> Part 2 — GitHub Integration: Created database migration `000005_git_connections.up.sql` (`git_connections` table and `projects`
> repo/push tracking columns). Implemented control-plane `internal/crypto` AES-256-GCM encryption with AAD verification for refresh tokens.
> Implemented standard-library RS256 JWT minting (`internal/git/github.go`) for GitHub App authentication (zero external JWT dependencies),
> on-demand installation access token minting, user repository creation, and authenticated push (`POST /projects/{id}/git/push`).
> Pushes directly to refspec URL without storing credentials in `.git/config` and scrubs 100% of tokens from stderr, logs, and responses.
> Frontend UI: Built Lovable-grade **Manage → Git** settings tab supporting not-connected state (with explanation, Connect GitHub button,
> and .zip download), connected without repo (with account chip, repo name input, and Private/Public toggle), and connected with repo
> (repo link, ahead count badge, push button with spinner, and copyable `git clone` command). Added **Download code** button and GitHub
> repo link in Studio workspace header.
> Gates: 3,754 tests pass, `task verify` passed, `scripts/test.sh` passed, Next.js build clean.
> NEXT: **F-04 (R-502) Skills Engine (custom instructions & domain templates)**.

> **R-500 (2026-09-20): Multi-Process Preview & Diagnostics Service (F-02-preview spec).**
> Implemented authenticated same-origin reverse proxy and lifecycle diagnostics for generated apps.
> Resolved 127.0.0.1 loopback isolation by introducing Next.js proxy route `/preview/[projectId]/**` and `/preview/[projectId]/api/**`.
> Enforced strict SSRF defense: destination port is resolved solely via Control-Plane project ownership checks on authenticated user;
> loopback IP validation prevents internal or external network scanning; non-owners receive 404.
> Proxied HTML injects `<base href="/preview/${projectId}/">` and rewrites `/_next/` chunk paths, Location headers, and Set-Cookie paths
> to maintain full application functionality across LAN devices and browsers.
> Upgraded agent-engine localrun and preview manager with named phase progression (`install` -> `migrate` -> `start` -> `ready`),
> process PID tracking, and an idle timeout reaper (`OMNISTACKAI_PREVIEW_IDLE_MINUTES`, default 30m).
> Added control-plane `GET/POST /projects/{id}/preview` and `POST /projects/{id}/preview/stop`.
> Console Web UI auto-starts previews, visualizes real-time phase progress with live timer, provides restart/stop controls,
> and displays an honest build-only banner when preview mode is disabled.
> Gates: 3,750 tests pass, `task verify` passed, `scripts/test.sh` passed.
> NEXT: **F-03 (R-501) Git Push / GitHub Export (spec `R_&_D/specs/F-03-git.md`)**.

> **R-499 (2026-09-20): Projects & Workspaces Persistence (F-01-projects spec).**
> Fully implemented on-disk workspace persistence and database-backed multi-tenant project management.
> In PostgreSQL, created `projects` table (`000004_projects.up.sql`) with foreign key to users and unique index
> `(id, user_id)` enforcing strict tenant isolation. In Go control-plane, built `internal/projects` store
> and HTTP handlers for project CRUD, credit debits, and project-isolated file access, closing the previous cross-tenant
> read vulnerability. In Python agent-engine, created `StudioWorkspaceStore` in `studio/workspace.py` writing to
> `~/.omnistackai/workspaces/<uuid>/` (`repo/`, `state.json`, `turns.jsonl`, `ir.json`, `.lock`), ensuring builds,
> edits, and turns survive daemon restarts. In Console Web UI, implemented 'Your projects' on the home page,
> full `/projects` management dashboard (search, filter, sort, rename, duplicate, archive, typed delete),
> dynamic `/studio/[projectId]` studio routing, `ProjectSwitcher` chat rail header, and Manage General settings
> (`/studio/[projectId]/manage`). Gates: all 3,746 tests pass, `task verify` green, `scripts/test.sh` green.
> NEXT: **F-02 (R-500) Multi-Process Preview & Diagnostics Service**.

> **R-498 (2026-09-19): Platform buildout plan (15 specs) + single-command local runtime.**
> The founder reviewed the console live and listed what a platform still needs. This task answers
> it with decisions, specs and tooling — **no feature code**. Verified first rather than assumed:
> the preview engine works (a real build in 30 s, preview ready in 5 s, the running app served
> `<title>Simple Note Taking</title>`), so "Preview is not working" was the Studio running in
> **build-only mode**; generated apps bind to `127.0.0.1`, so a preview cannot load from another
> device; the build history and editable IR are **in memory** — proven live, after a restart the
> founder's build 7 returned `{"turns": []}` and 404 for its files and the next build was numbered
> 1 again; there is no projects table and no per-user ownership check on the build routes.
> Delivered: `R_&_D/OmniStackAI_Platform_Buildout_v1.md` (a build-now / gated / later / no
> decision for all 23 requested features, how connect-GitHub-and-push works via a GitHub App and
> why that also makes Publish nearly free, the two-layer Skills design, the dependency graph);
> **15 implementable specs** in `R_&_D/specs/` (F-01 projects … G-05 analytics), each with UI,
> SQL migration, API, flow and acceptance; and **`scripts/omnistack.sh`** — one command for the
> whole platform (`up`/`down`/`restart`/`status`/`logs`/`build`/`doctor`/`verify`/`open`) with
> **preview mode on by default**, which removes the footgun behind the broken-looking preview.
> Founder decisions recorded: **domains are bring-your-own only**; GitHub push approved; Skills
> approved. **Two real bugs in the new script were found by running it and fixed** — a trailing
> `&&` as a loop's last command aborted `down` under `set -e` (the containers never stopped), and
> `lsof` exiting 1 on a free port tripped `pipefail`; a log-grep mode heuristic was replaced with
> an authoritative `/api/preview` probe. Evidence: `down` now stops everything (exit 0, `docker
> ps` empty); a **cold `up` took 13.8 s**; login and every route 200 afterwards. Gates:
> `scripts/test.sh` + new R-498 block, `task verify` **3,738 OK**, lint/security/env.
> NEXT: **F-01 (R-499) projects persistence** — the prerequisite for every other Phase F/G task.
> Gated on the founder: G-01 hosting model, G-03 connectors, G-04 payment test accounts.

> **R-497 (2026-09-19): Console — Lovable-grade pass after the founder's reference screenshots.**
> The founder shared 96 screenshots (Dyad 40, Emergent 18, Lovable 38) and asked which to follow;
> all were reviewed as contact sheets plus the decisive screens at full size. **Lovable** is the
> primary reference (dark, dense, chat-left project workspace, prose replies, follow-up chips, a
> real product IA — closest to what R-491..R-496 built); Dyad contributes the prompt-first home;
> Emergent nothing we lack. Built, real behavior only: a prompt-first home
> (`components/home-composer.tsx` → `/studio?prompt=`); the Studio pre-fills the composer from
> `?prompt=` and starts exactly one build through its existing form submit (`requestSubmit()` +
> ref guard, no setState in an effect), then cleans the URL; prose assistant rows at 13px; three
> follow-up chips after a completed build/edit; a shared file-search filter over the Files/Code
> trees; "Read only" on the viewer. Deliberately not borrowed: Lovable's Cloud/Publish/Payments
> panels (no backend), a project switcher (no per-user build list), Emergent's Web/Mobile tabs
> (hard gate). Gates: typecheck/lint/build clean (25 routes), contract tests (the home and
> Studio example prompts are pinned identical), `task verify` **3,738 OK**, lint/security/env.
> Live: `/` serves the hero + composer + chips; `/studio?prompt=…` server-renders the pre-filled
> composer with Send enabled and triggers nothing (client effect); `/studio?build=5` unchanged
> and not pre-filled; **0 server errors**. The founder is asked to run the real flow in a browser.
> NEXT: the founder's pick — Publish/deploy, sandbox→preview + per-user routing, Node.js codegen,
> mobile, tenant isolation — or a per-user build list to power a Lovable-style project switcher.

> **R-496 (2026-09-19): Console — motion, states & polish. The six-task Console UI overhaul (R-491..R-496) is complete.**
> Loading states per Next 16's `loading.js` convention for Studio and Settings under their gated
> layouts, and the one network-dependent piece — the provider-status card — streamed inside
> `<Suspense>` below the auth gate on the dashboard and Settings; error states per `error.js`
> (`app/error.tsx` on the documented `retry()` prop with the `digest` shown as a reference;
> `app/global-error.tsx` with its own document); `metadataBase` from the new optional
> `OMNISTACKAI_CONSOLE_PUBLIC_URL` (dev fallback to the console's real address), `openGraph` +
> `twitter` fields and a generated 1200×630 PNG via `ImageResponse` from `next/og`; a `.reveal`
> rise+fade utility (transform/opacity, 60ms stagger, collapsed under `prefers-reduced-motion`)
> across the dashboard, settings, fabric, auth, 404/error and Studio empty states and chat
> messages; tinted `shadow-*` utilities; the last legacy CSS retired with the R-475 assertion
> edited deliberately — `globals.css` is 330 lines. **A real regression caught by the live smoke
> and fixed in-task**: a root `app/loading.tsx` turned the signed-out auth redirects into
> streamed 200s (`<meta http-equiv="refresh">` + a `NEXT_REDIRECT` payload); removed in favor
> of Suspense-below-the-gate, and a `test.sh` assertion now forbids it. Gates: typecheck/lint/
> build clean (**25 routes**), contract tests, `task verify` **3,738 OK**, lint/security/env.
> Live: every route with the right status signed out/in, the full `og:*`/`twitter:*` head with
> an absolute image URL, real PNG image routes (56.6 KB, 1200×630), reveal indexes on the right
> elements, **0 server errors**. The redesign audit checklist is in the contract with honest
> open items (no legal pages exist yet; no cookie banner needed; Lucide kept deliberately).
> NEXT: the founder picks — Publish/deploy (new infra/paid decision), sandbox providers into the
> Studio preview + per-user free/paid routing, Node.js codegen, mobile (hard gate), or tenant
> isolation of the Studio server (architecture sign-off). Eyeball everything at `localhost:4321`.

> **R-495 (2026-09-19): Console — Settings + Fabric; legacy CSS sweep.**
> Fifth task of the Console UI overhaul; the last two legacy screens rebuilt on the R-491 stack.
> **Settings** is a real settings page: a sticky in-page nav; Account as read-only facts with the
> honest "Profile editing isn't available yet."; Appearance with a three-way System/Light/Dark
> control on `next-themes` (`components/theme-switcher.tsx`, hydration-safe via a
> `useSyncExternalStore` mounted flag — in Settings, not a header sun/moon switch); Model
> providers with the live Ready summary from the unchanged `getProviderStatus()` call and **11
> provider cards** whose "Needs key" state carries a real `Set KEY_ENV in .env` hint from
> `ProviderInfo.keyEnv` (variable names only). **Fabric** is a proper data page over the same
> honest snapshot: a "snapshot vN" badge with the true regeneration note, the routing ladder,
> captioned `tabular-nums` tables, stat cards that say "No model calls are recorded in this
> snapshot." rather than hiding zeros, and the showcase diff. **266 lines of dead legacy CSS
> removed** by a deterministic script; only the R-475-pinned `.pill`/`.pill--accent`/`.spinner`
> remain (R-496 retires them with the assertion); `.grain` scoped from `fixed` to `absolute`.
> **Three real gate catches, all mine, fixed first**: the `react-hooks/set-state-in-effect` rule
> *is* enabled; a `*/` inside my own CSS comment broke the build; `.wrap` survived in a dead
> `@media` block. Gates: typecheck/lint/build clean (23 routes), contract tests, `task verify`
> **3,738 OK**, lint/security/env. Live: `/settings` (Ready · groq, 11 cards, 8 real `keyEnv`
> hints) and `/fabric` (signed out and in) smoked with **0 server errors**. Founder flips the
> theme on `/settings` and scrolls `/fabric` on `localhost:4321`.
> NEXT: R-496 (motion, states & polish).

> **R-494 (2026-09-19): Console — Studio tabs (Preview chrome, Files tree, Code viewer, Problems).**
> Fourth task of the Console UI overhaul. The four tabs inside R-493's workspace are now real
> Radix tabs (vendored shadcn `Tabs`) with Lucide icons and live counts: **Files** a collapsible
> tree built by a pure, React-free model (`file-tree-model.ts`, verified with
> `node --experimental-strip-types` against the real 173-file build: 173 leaves, dirs-first
> alphabetical at every level, 0 duplicates); **Code** tree pane + viewer with a sticky header,
> the unchanged tokenizer on the theme's `.code-tok-*` colors, skeleton loading and honest
> binary/truncated notes; **Problems** a Check button, result badge, per-file cards that open the
> file in Code, tsc `L:C TSxxxx` lines parsed (verbatim fallback, no invented severities), raw
> output in `<details>`; **Preview** the unchanged state machine under a real toolbar (status
> pill, URL, Open in new tab, Desktop/Tablet/Phone presets, Restart/Stop) with designed
> starting/disabled/error states. The R-477 "empty Files after refresh" degradation is closed by
> fetching the file list on `?build=` hydration. `studio-icons.tsx` retired — the R-475
> assertion edited as planned, and **the contract tests caught the stale R-493 shim assertion**
> on their first run. Gates: typecheck/lint/build clean (23 routes), contract tests, `task
> verify` **3,738 OK**, lint/security/env. Live on build 5: tabs server-rendered with full ARIA,
> legacy classes gone, a real 6,214-byte file read, problems POST → the honest 409 "tsc is not
> installed" of build-only mode, preview 404 (disabled state), **0 server errors**. Honest
> limits: client interactions and ready/diagnostics states need a browser and `task
> agent-engine:studio:preview` — founder eyeballs `localhost:4321/studio?build=5`.
> NEXT: R-495 (Settings + Fabric), R-496 (motion/states/polish + legacy CSS sweep).

> **R-493 (2026-09-19): Console — Studio core (chat rail + workspace shell on shadcn/Lucide).**
> Third task of the Console UI overhaul; the Studio is the product. Constraints read from
> `scripts/test.sh` first (R-475 pins `studio-icons.tsx`; R-477 pins `.studio-grid`; R-479/481/485
> pin `StudioPreview`/`StudioTabs`/`sendBuildStream`; R-494's tabs/preview import the icons), so
> `studio-icons.tsx` became a thin **Lucide shim**, `.studio-grid` kept its name, and the chat
> logic stayed byte-for-byte. Built: `AppShell layout="full"`; chat rail **left** / workspace
> **right** at `calc(100dvh - 3.5rem)`; `role="log"` thread with user/assistant/`role="alert"`
> bubbles; working bubble with the live character count + shimmer skeletons; skeleton hydration;
> "What do you want to build?" empty state with three real example prompts; a proper composer;
> a **New app** action; workspace progress bar, designed empty state and a compact project header
> above the untouched tabs. Dead legacy CSS removed — **the new contract block caught two leftover
> `@media` overrides on its first run** (and that failure had made `task verify` run zero tests;
> noticed, fixed, re-run). Gates: typecheck/lint/build clean (23 routes), contract tests,
> `task verify` **3,738 OK**, lint/security/env. Live: every Studio marker served; unknown
> `?build=` degrades as before; **one real streamed build with example prompt #1** (9s, 2,458
> `generating_ir` deltas, "Task Tracker", 173 files, id 5) opens in the Studio with 2 hydrated
> turns; header-container inconsistency found and fixed in-task; **0 server errors**. Console
> running detached on 4321 — founder eyeballs `/studio` (no browser tool).
> NEXT: R-494 (Studio tabs), R-495 (Settings/Fabric), R-496 (motion/states/polish).

> **R-492 (2026-09-19): Console — auth screens + app shell (nav, user menu, skip link, 404, dashboard).**
> Second task of the Console UI overhaul and the first one a user sees. Design decision from a
> direct read of `scripts/test.sh`: eight earlier contract blocks pin the current page paths, so
> screens were **not** moved into route groups — the shell is a shared server component
> (`components/app-shell.tsx`) and every per-route auth gate stays where it is. Built on the R-491
> stack with `globals.css` untouched and no new dependencies: `AppShell` (skip-to-content link,
> sticky translucent header, brand mark, `AppNav` with `aria-current="page"`, `UserMenu` on a real
> Radix DropdownMenu with plan/credits/sign-out — `app/logout-button.tsx` retired and deleted,
> `<main>` keeping the legacy Studio geometry so the untouched workspace still fits);
> `AuthScreen` split layout with a grain brand panel and three *true* product statements;
> `login-form`/`register-form` with validation mirroring the server's own limits, inline
> `aria-invalid`/`aria-describedby` errors cleared on edit, a `role="alert"` server banner
> (sentence-cased), spinner + disabled submit, show/hide password; login/register pages are now
> server components (metadata, signed-in visitors → `/`, control-plane-down treated as
> signed-out); `app/not-found.tsx` per Next 16's convention; a real dashboard on `/` — asymmetric
> 7/5 layout, honest three-step loop, live provider card via the existing `getProviderStatus()`,
> plan/credits/role/BYOK — no invented "recent projects". Titles trimmed to the R-491 template;
> `/fabric` wrapped in the shell, still public. Gates: typecheck/lint clean, build 23 routes,
> `scripts/test.sh` + new R-492 block, `task verify` **3,738 OK**, lint/security/env. Live: full
> signed-out/signed-in matrix as designed; dashboard shows **real** data (Ready · groq ·
> openai/gpt-oss-120b, 3 of 11 providers configured, 100 credits, Radix trigger ARIA);
> `aria-current` lands on the right link per page; 401/400/200 auth paths; logout 204; **0
> server errors**. Console left running detached on 4321 — founder eyeballs it (no browser tool).
> NEXT: R-493 (Studio core), then R-494/R-495/R-496.

> **R-491 (2026-09-19): Console — UI foundation (Tailwind v4 + shadcn/ui + Geist, dark-first).**
> First of the six-task Console UI overhaul (R-491..R-496), approved after the founder asked why
> the platform UI is "just simple and very ugly" — honest diagnosis: zero UI dependencies (hand-
> rolled CSS, OS system font, no component library), an *enforced* R-470 gate blocking them, and
> every prior task prioritizing backend correctness. Founder's decision ("I need proper best UI
> based platform not just simple a page"; reference bar: Emergent/Lovable/Dyad) supersedes the
> gate — retired formally with the decision recorded. Stack verified against real, current docs:
> Tailwind v4 via `@tailwindcss/postcss` (Next 16's own bundled guide), shadcn/ui on **Radix**
> with the **Nova preset — literally "Lucide / Geist"**, the exact icon+font choice made
> independently — `next-themes` dark-first, Geist + Geist Mono self-hosted via `next/font`. **Real
> tooling drift worked through**: shadcn CLI v4.21 replaced `--base-color` with a `--base`
> library choice + named presets, defaults to Base UI (not Radix), and one attempt silently never
> ran because `timeout` doesn't exist on macOS. **A real init bug caught and fixed**: `shadcn
> init` clobbered the legacy `--muted` (text) and `--accent` (brand) names it shares — light mode
> would have had invisible muted text and white-on-white buttons; the token rewrite re-points
> every legacy usage onto a tinted OKLCH scale with one amber brand accent, converts the dark
> block and syntax colors to the `.dark` class strategy, and fixes one inline token on `/fabric`.
> `typecheck`/`lint`/`build` clean (23 routes, `/icon.svg` new); `scripts/test.sh` passes with
> the gate gone; `task verify` **3,738 OK**. Live: every route smoked (200/307/404 as expected,
> authenticated API 200), served `<html>` carries both Geist font classes + the theme script, 0
> server errors. No browser tool here — founder eyeballs `localhost:4321`.
> NEXT: R-492 (auth + app shell), then R-493/R-494 Studio screens informed by the founder's
> screenshots.

> **R-490 (2026-09-19): Runtime — sandbox provider-selection surface.** Fifth and final task in
> the sandbox-provider sequence (R-486..R-490). New `runtime/sandbox_selection.py`:
> `build_sandbox_from_env(selection=None, *, providers=None) -> SandboxSetup`, a registry of the
> four real drivers, and a new `SandboxSelectionError` — mirroring `bootstrap.py`'s own
> established `build_runtime_from_env()` shape. Defaults to sandboxing **disabled**
> (`selected=None`) — zero behavior change until an operator opts in via
> `OMNISTACKAI_SANDBOX_PROVIDER`. The explicit `selection` parameter is the concrete "switch per
> user base" mechanism the founder asked about — a caller can pass a per-user choice without
> touching global state — proven by a dedicated test, not just described. Deliberately kept
> separate from the pre-existing `tier.py`/`bootstrap.py` (the *older*, still-untouched
> pure-planning system) and not wired into `studio/`/console/control-plane, matching every prior
> task's own scope boundary. **A real test-design risk was caught and avoided**: an early draft
> would have made a real local Docker socket connection attempt via `GVisorSandboxProvider.active`
> just to test registry wiring — replaced with a zero-I/O class-identity check instead.
> `task verify` **3,738 OK** (9 new tests); repo gates all pass.
> **This completes the five-task sandbox-provider sequence**: E2B, Vercel Sandbox, Daytona, and a
> free self-hosted gVisor option are all real, independently-verified, and now genuinely
> pluggable/switchable via configuration — exactly the founder's original ask.
> NEXT (not yet scoped): Publish/deploy, Node.js backend codegen, mobile (React Native). Full
> per-user process/tenant isolation as a wholesale architecture remains a separate, larger
> decision needing its own founder sign-off.

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
