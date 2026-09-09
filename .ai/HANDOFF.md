# Current Handoff

Task ID: R-287
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `793804e`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-287) — Race-Safe Generated Detail Refetches

The generated `use<Entity>` detail hook now cancels a superseded GET so a stale response cannot
overwrite the currently selected record during rapid record-selector / prev-next / deep-link / id
changes. This was the last generated fetch path without cancellation (R-280 covered `useList<Entities>`,
R-286 covered `useList<Child>By<Parent>`).

- The hook owns an `AbortController` ref; `refetch` aborts the previous request before the `if (!id)`
  reset (which now also clears `error`), and a valid id registers a fresh controller.
- The GET call passes the internal signal AFTER caller options
  (`api.get<Entity>(id, { ...options, signal: controller.signal })`), so callers cannot replace the
  cancellation signal. The generated API client already forwards `signal` — no client change.
- Aborted successes and `AbortError` failures are ignored; only the active request clears loading; the
  effect returns `() => abortRef.current?.abort()`.
- Public hook name/params/return, list and LIST_BY hooks, backend, IR, and description-only stability
  are all preserved.

## Verification

- `task verify` — pass (823 agent-engine tests; 13 focused R-287 tests in
  `test_detail_request_cancellation.py`, written test-first).
- `task lint`, `task security:quick`, `task env:check` — pass.
- `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites` — pass.
- Generated `useArticle` detail hook inspected end-to-end. Only one existing assertion changed
  (`test_nextjs_hooks.py`, the `getPost` call → signal-bearing form).
- Tracker — R-287 at `Phase_Roadmap!A9:M9`; table `A4:M295`; Dashboard formulas reach row 295; 287
  unique IDs (0 dupes); 76 Done, 1 Deferred, 210 Not Started; MVP 76/182 (41.8%); no `#REF!`; XLSX
  archive validated.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-288 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from **R-288** (the next unstarted Tracker ID — do not begin it without kickoff). All three
generated data-fetch paths (LIST, LIST_BY, detail GET) are now race-safe. Recommended offline candidate:
harden any remaining generated fetch path not yet race-safe/debounced (e.g. debounced subcollection
search, or mutation in-flight guards), or a further generated-app UX increment. Record the R-288
Standard AI Task Contract before coding.

## Next command

`task ai:status`
