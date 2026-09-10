# Current Handoff

Task ID: R-290
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `1ed88b6`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-290) — Optimistic Delete with Rollback in the Collection Screen

The generated collection screen's deletes are now optimistic: single (`handleDelete`) and batch
(`handleBatchDelete`) removals hide the affected rows immediately and reappear (with the existing error
toast) only if the server rejects — instead of waiting for the round-trip. Founder chose this over
loading skeletons.

- A `pendingDeleteIds` overlay is added to via the delete handlers before `await remove(...)`, rolled
  back in `catch`, and pruned by a reconcile `useEffect(... , [data])` once `refetch` removes the ids (no
  flash-back). The row map iterates a `visibleRows` list filtered by `pendingDeleteIds`.
- `pendingDeleteIds`/`visibleRows` are emitted unconditionally (like the existing `checkedIds` selection
  state); the delete handlers only exist when delete is wired. Safe on the deduped mutation hooks (R-288)
  and race-safe list fetch (R-280). Self-contained in `_collection_screen_page`; detail/subcollection
  delete, the mutation/list hooks, the API client, backend, and IR are unchanged; description-only IR
  generation stays byte-identical.

## Verification

- `task verify` — pass (843 agent-engine tests; 9 focused R-290 tests in
  `test_collection_optimistic_delete.py`, written test-first). Two `test_collection_field_filters.py`
  row-map assertions updated to `visibleRows`.
- `task lint`, `task security:quick`, `task env:check` — pass. Both `task builder:demo` — pass.
- Generated collection page inspected end-to-end.
- Tracker — R-290 at `Phase_Roadmap!A9:M9`; table `A4:M298`; Dashboard formulas reach row 298; 290
  unique IDs (0 dupes); 79 Done, 1 Deferred, 210 Not Started; MVP 79/185 (42.7%); no `#REF!`; XLSX valid.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-291 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from **R-291** (the next unstarted Tracker ID — do not begin it without kickoff). Recommended
offline candidate: extend optimistic delete to the detail-screen and subcollection deletes for
consistency (currently collection-only), or loading skeletons for the collection/detail/subcollection
loading states. Record the R-291 Standard AI Task Contract before coding.

## Next command

`task ai:status`
