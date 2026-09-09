# Current Handoff

Task ID: R-280
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `7a6b9b5`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author (with the tooling `Co-Authored-By` trailer).

## Completed (R-280) — Deep-Linked Collection List State + Debounced, Race-Safe Search

The founder-chosen "best, optimised, futuristic" pairing of two survey-identified gaps, both on one
surface (`nextjs.py` `_collection_screen_page` + `_hooks_file`):

- **Deep-linked list state.** The generated `useList<Entities>` hook hydrates `sort/order/q/page/pageSize`
  from `window.location.search` once on mount (client-only, guarded `typeof window`) and reflects the
  current params to the URL via `new URL(...)` + `window.history.replaceState`, writing only non-default
  values. Refresh / bookmark / share restore the exact list view (mirrors the R-276 detail pattern).
- **Race-safe fetch.** `refetch` creates an `AbortController` per call (added `useRef` to the import),
  aborts the previous in-flight request, forwards `signal` through the existing `ApiOptions` (no
  `lib/api.ts` change), ignores aborted/stale responses, and aborts in-flight on unmount.
- **Debounced search.** The collection search input debounces its committed query 300ms
  (`setTimeout`/`clearTimeout`, guarded so it never clobbers a hydrated page offset); `onChange` only
  updates local state; the form submit still searches immediately; the hydrated `q` is reflected back.
- Subcollection hook (`useList<Child>By<Parent>`) and subcollection UI controls intentionally out of
  scope. No new IR field, no npm dependency, `"use client"` preserved, diff-invariant across
  `ir.description`.

## Verification

- `task verify` — pass (768 agent-engine tests; 12 new in `test_collection_deeplink_state.py`).
  `task lint`, `task security:quick` — pass. Both `task builder:demo`s — pass.
- Updated three existing assertion sets to the new behavior (`test_nextjs_hooks.py` import + refetch
  signal; `test_screen_generation.py` debounced `onChange`; `test_collection_field_filters.py` `useEffect`
  import). 0 local / 0 cloud model calls; no DB.
- Tracker — R-280 at `Phase_Roadmap!A9:M9` (R-279 → row 10); rows 1..288 contiguous; table `A4:M288`;
  Done 69.

## Tracker reconciliation (this session, before R-280)

- The execution tracker had drifted: it was maintained only through R-252 while R-253..R-279 shipped in
  code/tests/docs. All 27 missing rows were backfilled as Done (commit `b4537c7`) from `.ai/tasks/R-###.md`
  + `CHANGELOG.md`; `docs/PROGRESS.md` was synced to the live tracker figures. The tracker is now current
  and should be kept so going forward (WORK_LOG.md also carries a bulk bridge note for R-253..R-279).

## Blockers and risks

- None for the offline R-281 candidates below. Live preview/deploy and the deferred R-224 Next.js console
  upgrade still need a network environment / provider keys. Native mobile remains deferred (Brief §25/§91).

## Next action

Continue from R-281 with one offline-doable candidate:

1. Wire pagination + sortable headers + search into the **subcollection master-detail lists** — the
   backend endpoints and the generated `useList<Child>By<Parent>` hook already support
   `limit/offset/sort/order/q`; only the render is inert today. (Direct continuation of R-265/R-280.)
2. Promote the **boolean/enum collection filters to server-side `?field=` query params** (currently
   client-side over the loaded page only) — needs a matching backend filter capability, so it is
   cross-cutting.

## Next command

`task ai:status`
