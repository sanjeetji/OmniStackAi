# Current Handoff

Task ID: R-282
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `198e23e`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author (with the tooling `Co-Authored-By` trailer).

## Completed (R-282) — Server-Side Boolean/Enum Field Filters on Top-Level LIST Endpoints

Following the R-258 sort / R-261 search pattern, a top-level LIST endpoint now accepts `?<field>=<value>`
for each **boolean** field and each **enum** field (`enum:a|b|c` validation), composed into the SQL
`WHERE` alongside the existing `q` keyword search. Same whitelist discipline as sorting: **column
identifiers only ever come from validated IR field names; filter values are always parameterized
(`$N`/`%s`).**

- **`field_validation.filter_fields(entity)`** — new shared helper (`(field, kind)` for bool/enum, minus
  `id`) driving Go, FastAPI, and OpenAPI.
- **data_access** — filterable entities get a dynamic `WHERE` builder: Python `_list_filters(q, …)` helper;
  Go `<table>Filters(q, filters map[string]string)` helper (bool → `v == "true"`, enum → string) with
  correct `$N` numbering; `list_`/`List` + `count_`/`Count` take the filter params. Non-filterable
  entities are byte-identical.
- **backend_python / backend_go** — FastAPI router declares typed filter params (`bool | None` / `str |
  None`) and forwards them; Go handler calls `parseFilters(r)` (in `handlers.go` only when a filterable
  entity exists) and threads the map into the store calls.
- **openapi** — each filter param documented on `Op.LIST` (boolean / string+enum).

Scoped to `Op.LIST`; the FK-scoped `LIST_BY` subcollection queries are unchanged. No new IR field, no npm
dependency, standard-library-only platform code, diff-invariant across `ir.description`.

## Verification

- `task verify` — pass (786 agent-engine tests; 12 new in `test_field_filters_backend.py`).
  `task lint`, `task security:quick` — pass. Both `task builder:demo`s — pass. 0 model calls; no DB.
- Because `minimal-blog` Post is filterable (`published`), the exact Post assertions in `test_search.py`,
  `test_sorting.py`, `test_pagination.py`, `test_total_count.py`, and `test_route_wiring.py` were updated
  to the new dynamic-builder output (Comment/Driver, non-filterable, stayed byte-identical).
- Tracker — R-282 at `Phase_Roadmap!A9:M9` (R-281 → row 10); rows 1..290 contiguous; table `A4:M290`;
  Dashboard ranges `B4:B290`/`H4:H290`, no `#REF!`; Done 71.

## Founder note — Groq key available

A Groq API key is available; live model-fabric verification with it is deferred per founder choice. To
enable: put `GROQ_API_KEY` in the **gitignored `.env`** (never in chat/commits/source), then
`task agent-engine:gateway:run` with `OMNISTACKAI_CLOUD_PROVIDER=groq`. This AI sandbox may block outbound
calls to `api.groq.com`, so it may need a real terminal.

## Blockers and risks

- None for the offline R-283 candidates below. Live preview/deploy and the deferred R-224 Next.js console
  upgrade still need a network environment / provider keys. Native mobile remains deferred (Brief §25/§91).

## Next action

Continue from R-283 with one offline-doable candidate:

1. **Wire the Next.js collection filter controls (R-278) to the new backend `?field=` params** — R-278's
   boolean/enum filters are currently client-side over the loaded page (wrong across pagination). Point
   them at the R-282 backend params via the `useList` hook so filtering is server-side and correct. (The
   user-visible payoff of R-282.) Or
2. **Extend server-side field filtering to the FK-scoped `LIST_BY` subcollection endpoints** (mind the
   `$N` renumbering: relation id is `$1`).

## Next command

`task ai:status`
