# Current Handoff

Task ID: R-286
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `3eb8bd1`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-286) — Race-Safe Generated Subcollection Refetches

Every generated `useList<Child>By<Parent>` hook now prevents superseded LIST_BY responses from
overwriting the current child state during rapid parent or query changes.

- Each subcollection hook owns an `AbortController` ref and aborts the prior request before checking
  for a missing parent ID, so deselection also cancels in-flight work.
- Valid requests install a fresh controller and pass its signal after caller options, preventing the
  internal race-safety signal from being replaced.
- Aborted successes and `AbortError` failures do not update data, total, error, or loading. Only the
  active request clears loading, and effect cleanup aborts on dependency change or unmount.
- Filterable hooks preserve flattened R-285 query params; non-filterable hooks preserve public state
  and signatures. No IR, backend, dependency, PostgreSQL, infrastructure, or layout change was made.

## Verification

- `task verify` — pass (810 agent-engine tests; 6 focused R-286 tests).
- All 69 `test_subcollection*.py` tests — pass.
- `task lint`, `task security:quick`, `task env:check` — pass.
- `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites` — pass.
- Generated filterable and non-filterable LIST_BY hook output inspected.
- Tracker — R-286 at `Phase_Roadmap!A9:M9`; table `A4:M294`; Dashboard formulas reach row 294; 286
  unique IDs; 75 Done, 1 Deferred, 210 Not Started; MVP 75/181 (41.4%); XLSX archive and visual render
  verified.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-287 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from R-287. Recommended smallest offline candidate: make generated `use<Entity>` detail
refetches race-safe with `AbortController`, ensuring rapid record selector/prev-next navigation cannot
let an older GET response overwrite the currently selected record. Record the R-287 Standard AI Task
Contract before coding.

## Next command

`task ai:status`
