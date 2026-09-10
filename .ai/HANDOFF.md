# Current Handoff

Task ID: R-291
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `51f33c8`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author (with a permitted tooling co-author trailer).
- **Founder authorized autonomous continuation**: proceed to the next Tracker ID without asking, until
  manually stopped (still stop-and-ask only for paid cloud / DB engine / new infra / native-mobile / a
  materially different architecture decision).

## Completed (R-291) — Optimistic Subcollection Child Delete with Rollback

Extends R-290's optimistic delete to the subcollection (master-detail) child lists in both the collection
master-detail and detail screens: deleting a child row hides it immediately and reappears (with the
existing error toast) only if the server rejects. The optimistic-delete story now spans the collection
screen (R-290) and subcollection child lists (R-291).

- Each deletable subcollection gets a `<s_var>Deleting` overlay (`useState<string[]>`) + a reconcile
  `useEffect(... , [<s_var>.data])`; the child delete handler adds the id before `await remove<Child>(id)`
  and rolls it back in `catch` before `toast.error`; the child row map iterates the deleting-filtered
  list. Non-deletable subcollections are byte-identical to before.
- Safe on the deduped mutation hooks (R-288) and the race-safe R-286 `useList<Child>By<Parent>` hook. The
  mutation/list hooks, generated API client, backend, and IR are unchanged; description-only IR generation
  stays byte-identical.

## Verification

- `task verify` — pass (849 agent-engine tests; 6 focused R-291 tests in
  `test_subcollection_optimistic_delete.py`, written test-first). No existing assertion needed changing.
- `task lint`, `task security:quick`, `task env:check` — pass. Both `task builder:demo` — pass.
- Generated deletable subcollection inspected end-to-end.
- Tracker — R-291 at `Phase_Roadmap!A9:M9`; table `A4:M299`; Dashboard formulas reach row 299; 291
  unique IDs (0 dupes); 80 Done, 1 Deferred, 210 Not Started; MVP 80/186 (43.0%); no `#REF!`; XLSX valid.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-292 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from **R-292** (autonomously, per the founder's standing authorization). Recommended offline
candidate: loading skeletons for the collection/detail/subcollection loading states (replace the plain
"Loading..." text with layout-preserving skeleton placeholders), or another generated-app UX/robustness
increment. Record the R-292 Standard AI Task Contract before coding.

## Next command

`task ai:status`
