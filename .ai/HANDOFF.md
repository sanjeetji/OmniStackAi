# Current Handoff

Task ID: R-284
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Implementation SHA: `0bfb91d`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. A permitted tooling co-author trailer may be
  added, but the founder remains the primary author.

## Completed (R-284) — Server-Side Field Filters for FK-Scoped Subcollections

R-282's allowlisted boolean/enum server filters now cover unambiguous foreign-key-scoped `LIST_BY`
endpoints as well as top-level `LIST` endpoints.

- Generated Python repositories compose mandatory relation scope, optional `q`, and equality filters in
  one parameterized predicate shared by list and count calls; FastAPI routes expose typed filter query
  parameters and forward identical values to both calls.
- Generated Go stores emit a shared relation-scoped predicate builder. Relation ID remains `$1`, a
  present `q` uses the next argument, allowlisted bool/enum filters follow, and limit/offset placeholders
  follow every predicate. Go handlers parse/forward filters only for filterable child entities.
- Generated OpenAPI documents the matching boolean and enum query schemas on `LIST_BY` operations.
- Non-filterable subcollections keep their previous output, and description-only IR changes remain
  byte-stable. Application IR, Next.js behavior, dependencies, PostgreSQL, infrastructure, and the
  Section 74 layout are unchanged.

## Verification

- `task verify` — pass (797 agent-engine tests; 8 focused R-284 tests).
- `task lint`, `task security:quick`, `task env:check` — pass.
- `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites` — pass.
- Generated FastAPI repository/router output parsed with Python AST; generated Go store/handler output
  parsed through `gofmt`; OpenAPI filter parameters and SQL placeholder ordering inspected.
- Tracker — R-284 at `Phase_Roadmap!A9:M9`; table `A4:M292`; Dashboard formulas reach row 292; 284
  unique IDs; 73 Done, 1 Deferred, 210 Not Started; MVP 73/179 (40.8%); XLSX archive and visual render
  verified.
- 0 local model calls / 0 cloud calls; no generated app installed/run, no DB connection.

## Blockers and risks

- No blocker for the offline R-285 candidate. Live preview/deploy and R-224 still need a
  network-capable environment and/or authorized provider keys. Native mobile remains deferred under
  Brief Sections 25 and 91.
- A Groq key may be available for a future separately authorized live model-fabric verification. Keep
  it only in a gitignored `.env`; never place it in chat, source, state, logs, tests, or commits.

## Next action

Continue from R-285. Recommended smallest offline candidate: wire generated Next.js subcollection
filter controls and `useList<Child>By<Parent>` hook state to R-284's server-side `LIST_BY` query
parameters. Avoid page-local filtering and preserve byte-stable output for non-filterable children.
Record the R-285 Standard AI Task Contract before coding.

## Next command

`task ai:status`
