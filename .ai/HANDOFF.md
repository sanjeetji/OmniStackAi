# Current Handoff

Task ID: R-289
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `b6a1af4`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-289) — Debounced Live Subcollection Search

The generated subcollection (master-detail) search is now live + debounced (300ms), matching the
top-level collection search (R-280). R-281 shipped a submit-only subcollection form; now that R-286 made
the `useList<Child>By<Parent>` hook race-safe, a live search-as-you-type is safe.

- New helpers `_subcol_search_names(s_var)` and `_subcol_search_state(s_var)` emit a per-subcollection
  controlled search `useState("")` plus a `setTimeout`/`clearTimeout` 300ms debounce `useEffect` that
  commits the trimmed value to `<s_var>.setSearch` (guarded by `!== (params.q ?? "")`).
- `_subcol_controls`'s search input is now controlled (`value`/`onChange`) instead of
  uncontrolled+`FormData`; the form submit still commits immediately (Enter). Wired into both the
  collection master-detail and detail screens; entities without a subcollection emit none.
- The `useList<Child>By<Parent>` hook, generated API client, backend, IR, and the sort/filter/pagination
  controls are unchanged; description-only IR generation stays byte-identical.

## Verification

- `task verify` — pass (834 agent-engine tests; 5 focused R-289 tests in
  `test_subcollection_search_debounce.py`, written test-first). R-281
  `test_subcollection_list_controls.py` search assertions updated to the controlled form.
- `task lint`, `task security:quick`, `task env:check` — pass. Both `task builder:demo` — pass.
- Generated `post_list` subcollection search inspected end-to-end.
- Tracker — R-289 at `Phase_Roadmap!A9:M9`; table `A4:M297`; Dashboard formulas reach row 297; 289
  unique IDs (0 dupes); 78 Done, 1 Deferred, 210 Not Started; MVP 78/184 (42.4%); no `#REF!`; XLSX valid.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-290 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from **R-290** (the next unstarted Tracker ID — do not begin it without kickoff). Generated-app
search is now consistent (top-level + subcollection both live/debounced) and all request paths (fetch and
mutation) are race-safe. Recommended offline candidate: a further generated-app UX or robustness
increment — e.g. optimistic UI updates with rollback, or loading skeletons for the collection/detail/
subcollection loading states. Record the R-290 Standard AI Task Contract before coding.

## Next command

`task ai:status`
