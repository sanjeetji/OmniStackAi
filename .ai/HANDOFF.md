# Current Handoff

Task ID: R-295
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `2454a43`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author (with a permitted tooling co-author trailer).
- **Founder authorized autonomous continuation**, but on 2026-09-10 asked to STOP after R-295 and be given
  a paste-anywhere resume prompt (see `docs/RESUME_PROMPT.md`). Resume from **R-296** when ready. Still
  stop-and-ask only for paid cloud / DB engine / new infra / native-mobile / a materially different
  architecture decision.

## Completed (R-295) — Consistent Error + Retry Affordance Across Every Generated Fetch State

The generated collection list already rendered a "Retry" button (calling `refetch()`) in its error
banner. R-295 brings the remaining fetch error states to parity so every failed load offers recovery:

- **Detail-screen main error banner** (`_detail_screen_page`) now renders "Error loading `<name>`:
  `<message>`" inside a `<span>` beside a `<button onClick={() => refetch()}>Retry</button>` (in a flex
  row); `refetch` is already destructured from `use<Entity>(selectedId)`.
- **Both subcollection (master-detail) error banners** — the collection master-detail block and the
  detail block, byte-identical (updated via `replace_all`) — now render "Error: `<message>`" inside a
  `<span>` beside a `<button onClick={() => <s_var>.refetch()}>Retry</button>`.
- Retry buttons reuse the collection error banner's flex layout and dark-red (`#991b1b`) styling. The
  collection top-level error banner is unchanged, as are loading/empty/data-render states, delete-error
  toasts, and form field errors. No hook/API-client/backend/IR change (`refetch` already exists on every
  affected hook); description-only IR generation stays byte-identical.

## Verification

- `task verify` — pass (881 agent-engine tests; 8 focused R-295 tests in `test_fetch_error_retry.py`,
  written test-first; the existing `test_subcollection_screens.py` `commentsSubcol.error.message`
  assertion is preserved).
- `task lint`, `task security:quick`, `task env:check` — pass. Both `task builder:demo` — pass.
- Generated detail-main and both subcollection error banners inspected.
- Tracker — R-295 at `Phase_Roadmap!A9:M9`; table `A4:M303`; Dashboard formulas reach row 303; 295
  unique IDs (0 dupes); 84 Done, 1 Deferred, 210 Not Started; MVP 84/190 (44.2%); no `#REF!`; XLSX valid.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-296 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

**Stopped at the founder's request after R-295.** When ready, resume from **R-296** using the
paste-anywhere prompt in `docs/RESUME_PROMPT.md`. The generated app now has full loading-skeleton coverage
(R-292/293), the App Router resilience quartet (R-294), and consistent Error + Retry across every fetch
state (R-295). Recommended offline R-296 candidate: another generated-app UX/robustness increment — e.g. a
reusable EmptyState/error inline-state component to DRY the screens, an accessibility pass, or optimistic
create/update reflected in the collection list. Record the R-296 Standard AI Task Contract before coding.

## Next command

`task ai:status`
