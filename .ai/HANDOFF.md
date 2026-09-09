# Current Handoff

Task ID: R-288
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `3d6eecf`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-288) — Deduplicated In-Flight Generated Mutation Requests

The generated `useCreate<Entity>` / `useUpdate<Entity>` / `useDelete<Entity>` hooks now dedupe concurrent
invocations, so a double-clicked Create/Save/Delete (or a programmatic re-call) can no longer fire a
duplicate POST/PUT/DELETE. This extends the race-safety work from fetches (R-280 LIST, R-286 LIST_BY,
R-287 detail GET) to writes — all generated request paths are now race-safe.

- Each hook owns `pendingRef = useRef<Promise<T> | null>(null)`; the callback returns the pending promise
  when a request is already in flight (a concurrent call awaits the same result — no second request).
- The try/catch/finally body runs in an IIFE captured as `pendingRef.current = request;` and returned;
  `finally` keeps `setLoading(false)` and adds `pendingRef.current = null;`.
- Public hook names, callback signatures, and return shapes (`{ …, mutate, loading, error, reset }`), the
  underlying `api.create|update|delete<Entity>` calls, the fetch hooks, the API client, backend, and IR
  are all unchanged; description-only IR generation stays byte-identical.

## Verification

- `task verify` — pass (829 agent-engine tests; 6 focused R-288 tests in
  `test_mutation_inflight_guard.py`, written test-first). Existing `test_nextjs_hooks` mutation assertions
  unchanged (substrings survive inside the IIFE).
- `task lint`, `task security:quick`, `task env:check` — pass. Both `task builder:demo` — pass.
- Generated `useCreatePost` inspected end-to-end.
- Tracker — R-288 at `Phase_Roadmap!A9:M9`; table `A4:M296`; Dashboard formulas reach row 296; 288
  unique IDs (0 dupes); 77 Done, 1 Deferred, 210 Not Started; MVP 77/183 (42.1%); no `#REF!`; XLSX valid.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-289 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from **R-289** (the next unstarted Tracker ID — do not begin it without kickoff). All generated
data-fetch (LIST, LIST_BY, detail GET) AND mutation (create/update/delete) request paths are now
race-safe. Recommended offline candidate: a further generated-app UX or robustness increment (e.g.
optimistic UI updates with rollback, loading skeletons, or a debounced/live subcollection search).
Record the R-289 Standard AI Task Contract before coding.

## Next command

`task ai:status`
