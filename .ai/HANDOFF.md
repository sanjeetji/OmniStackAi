# Current Handoff

Task ID: R-285
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `92c89b1`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-285) — Server-Side Subcollection Filter Wiring in Generated Next.js Screens

Generated Next.js subcollection hooks and both parent view variants now consume R-284's allowlisted
boolean/enum LIST_BY query parameters, so filtering occurs on the backend before pagination.

- Filterable `useList<Child>By<Parent>` hooks use typed collection-list filter state, validate values
  against IR-derived options, expose `setFilter`/`clearFilters`, reset offset, and flatten active filters
  into query params while preserving the parent relation ID as the path argument.
- Parent collection master-detail and dedicated detail screens render boolean pills, enum selects,
  active-filter count, Reset, and a filtered-empty Clear filters action.
- Screen components render the server-returned child page directly; they do not locally re-filter it.
- Non-filterable subcollection output and description-only IR generation remain byte-stable. No IR,
  backend, dependency, PostgreSQL, infrastructure, or Section 74 layout change was made.

## Verification

- `task verify` — pass (804 agent-engine tests; 7 focused R-285 tests).
- All 63 `test_subcollection*.py` tests — pass.
- `task lint`, `task security:quick`, `task env:check` — pass.
- `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites` — pass.
- Generated filterable hooks plus both collection/detail screen variants inspected.
- Tracker — R-285 at `Phase_Roadmap!A9:M9`; table `A4:M293`; Dashboard formulas reach row 293; 285
  unique IDs; 74 Done, 1 Deferred, 210 Not Started; MVP 74/180 (41.1%); XLSX archive and visual render
  verified.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-286 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from R-286. Recommended smallest offline candidate: make generated
`useList<Child>By<Parent>` refetches race-safe with `AbortController`, ensuring a stale request for an
old parent or filter cannot overwrite the current child list. Preserve non-filterable behavior and
record the R-286 Standard AI Task Contract before coding.

## Next command

`task ai:status`
