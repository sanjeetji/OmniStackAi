# Current Handoff

Task ID: R-263
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-263) — Interactive Screen Component Generator with Real Data Binding (apps/web/app/<screen>/page.tsx)

- **Interactive Screen Component Generator (`codegen/nextjs.py`)**:
  - Emits `apps/web/app/<screen.id>/page.tsx` as an interactive React client component with `"use client"` directive.
  - Automatically matches screens to IR entities using multi-token score matching across screen IDs, component tags, and actions (`_match_entity`).
  - Classifies screen intent as collection, form, or generic (`_screen_intent`).
  - Emits collection screens binding to `useList<Entities>()`:
    - Live search input bound directly to `setSearch` with form submission.
    - Sortable table headers bound to `setSort` with `↓`/`↑` indicators.
    - Pagination controls (`Previous`, `Next`, `Page X of Y`) bound to `setPage`.
    - Loading states, error alerts with retry button, and empty state cards.
    - Delete button calling `useDelete<Entity>()` when `Op.DELETE` is wired for the entity.
    - Top header with role badge, overview link, and navigation to complementary editor screens (`+ New <Entity>`).
  - Emits form/editor screens binding to `useCreate<Entity>()`:
    - Schema-derived inputs for each entity field: checkbox for `BOOL`, textarea for `TEXT`, number input for `INT`/`FLOAT`, datetime-local for `DATETIME`, text for `STRING`.
    - Required indicators (`*`) and HTML `required` attributes.
    - Submit handler calling `create(formData)`, success feedback banner, error capture banner, and reset/cancel controls.
  - Emits clean fallback screens without broken imports when entities or operations are unwired.
  - Preserves byte-identical screen output across IR description changes, keeping `test_console_snapshot.py` diff invariance intact.
  - Public `render_screen_page(screen, ir) -> str` exported in `codegen/__init__.py`.

## Preceded by:
- **R-254**: Structured JSON validation error bodies in Go (`{"errors": [...]}`).
- **R-255**: Query parameter pagination (`limit` & `offset`) on LIST and LIST_BY in Go and FastAPI backends.
- **R-256**: Wired PUT handlers (full-replace update) in Go and FastAPI backends.
- **R-257**: Full-stack connectivity: Next.js typed API client (`lib/api.ts`) & backend CORS middleware.
- **R-258**: Query parameter sorting (`sort` & `order`) with SQL injection whitelist protection.
- **R-259**: Total count database queries and `X-Total-Count` header across Go, Python, and Next.js.
- **R-260**: OpenAPI 3.1 specification generation from Application IR.
- **R-261**: Full-text / keyword search filtering (`q` query param) on LIST endpoints.
- **R-262**: React data-fetching & mutation hooks generation (`apps/web/lib/hooks.ts`).

## Verification

- `task verify` — pass (515 agent-engine tests; 9 new in `test_screen_generation.py`).
- `task lint`, `task security:quick`, `task env:check` — all pass.
- 0 local model calls, 0 cloud calls. Offline and deterministic.


## Product state

The offline builder covers Application IR → validation/normalization → Next.js/FastAPI/Go generation
with PostgreSQL schema (unique constraints, indexes, max_length/enum/min/max validation via
CHECK/VARCHAR), repositories, wired full CRUD (LIST/GET/CREATE/PATCH/PUT/DELETE) on both backends,
pagination query parameters (`limit`/`offset`) and sorting query parameters (`sort`/`order`) with
SQL injection whitelist protection on list endpoints, sub-collections, JWT auth + role enforcement,
and field validation enforced at every layer: FastAPI (Pydantic, at construction), Go
(go-playground `validator.Struct` → structured 400 JSON errors in create + update handlers), and the DB schema.
Typed Next.js API client (`lib/api.ts`) and backend CORS middleware are fully connected.
Seed data only from explicit IR fixtures → owned Git monorepo → preview/deploy plans → verification
ladders → patch/rename-aware edits. 46 tracker tasks Done; no paid cloud service; platform PostgreSQL/Compose unchanged.

## Blockers and risks

- No blocker for remaining offline tasks. Live generated-app preview/deploy and R-224 Next.js
  console upgrade still need a reliable network environment and/or authorized provider keys.
  Native mobile remains deferred per Brief §25/§91.

## Next action

All 5 sequential tasks (R-254, R-255, R-256, R-257, R-258) are implemented, verified, and complete.
Await founder review and permission to commit/push before proceeding.

## Next command

`task verify`
