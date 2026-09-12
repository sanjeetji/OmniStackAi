# Project State — OmniStackAI
Last updated: 2026-09-13T03:30:00+05:30

## Current Phase
Stage 0 (Founder Build Sequence, Brief Section 91) — BASIC/MVP

> **Front-door pivot: the local "chat → create → RUN" loop works end to end.** UI-component series PAUSED at R-415 (110 components, resumable). Front door: **R-416** intake (sentence→IR) · **R-417** builder (IR→owned repo) · **R-418** chat **web UI** (`task agent-engine:studio:serve` → http://127.0.0.1:4173) · **R-419** turnkey **run** (`task agent-engine:app:run -- <dir>` → DB+migrations+backend:8000+web:3000 in one command; blog app verified fully booted). Next: **R-420** — fix two schema-generator bugs R-419 exposed (unquoted reserved words like `order`; FK/table ordering) so chat-generated apps run.

## Last Completed Task
Tracker ID: R-419 — Turnkey local run (`omnistackai_agent_engine/localrun/`) — DONE, `task verify` (2,801
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

**Notes:** (1) R-414 complete with 2,735 tests passing. (2) Advancing autonomously to R-415 via a self-paced /loop (posture is advancing, not stopped).









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
