# Current Handoff

Task ID: R-283
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `d0c9e84`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author (with the permitted tooling
  `Co-Authored-By: Claude Opus 4.8` trailer).

## Completed (R-283) — Server-Side Collection Filter Wiring in Generated Next.js Screens

R-278's boolean/enum collection controls no longer filter only the currently loaded page. Generated
filterable top-level `useList` hooks now carry an allowlisted `filters` map and flatten active values into
the exact R-282 `?<field>=<value>` request parameters before the API client builds the query string.

- `setFilter(field, value)` accepts only generated field/value pairs, removes `all`/empty values, and
  resets `offset` to zero; `clearFilters()` removes all filters and returns to page one.
- The R-280 URL flow hydrates and syncs only known filter fields with allowed values, alongside existing
  `q`/sort/order/page/pageSize state.
- Collection screens drive those hook setters, render the server-returned `data` directly, and retain the
  current toolbar, active-count badge, Reset, and filtered no-results CTA.
- Removed `useMemo` and page-local `data.filter`; non-filterable screens emit no controls/options.
- Top-level LIST only: subcollection `LIST_BY`, backends, Application IR, dependencies, and infrastructure
  are unchanged.

## Verification

- `task verify` — pass (789 agent-engine tests; 3 new focused server-filter wiring tests).
- `task lint`, `task security:quick` — pass.
- `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites` — pass.
- Inspected generated minimal-blog `apps/web/app/post_list/page.tsx`, `apps/web/lib/hooks.ts`, and
  `apps/web/lib/api.ts`; rideshare has no entity filter options.
- Tracker — R-283 at `Phase_Roadmap!A9:M9`; rows 1..291 contiguous; table `A4:M291`; Dashboard references
  extended; ZIP/XML valid; 283 unique IDs; Done 72. Artifact-tool render visually checked.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-284 candidate. Live preview/deploy and R-224 still need a network-capable
  environment and/or authorized provider keys. Native mobile remains deferred under Brief §25/§91.
- A Groq key is available for a future live model-fabric verification. Keep it only in gitignored `.env`;
  never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from R-284. Smallest offline candidate: extend R-282 boolean/enum filters to FK-scoped
`LIST_BY` subcollection endpoints, preserving the relation ID as Go `$1`, search as the next placeholder,
and parameterizing all filter values. Do not start it until its task contract is recorded.

## Next command

`task ai:status`
