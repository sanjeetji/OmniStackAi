# Current Handoff

Task ID: R-262
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-262) — React Data-Fetching & Mutation Hooks Generator (apps/web/lib/hooks.ts)

- **React Hooks Generator (`codegen/nextjs.py`)**:
  - Emits `apps/web/lib/hooks.ts` with `"use client"` directive.
  - Relies solely on built-in React hooks (`useState`, `useEffect`, `useCallback`) and types (`Dispatch`, `SetStateAction`) — zero extra dependencies.
  - Emits shared parameter and state interfaces: `UseListParams`, `UseListState<T>`, `UseDetailState<T>`, `UseMutationState<TData, TResult = TData>`.
  - For each entity in the IR:
    - `useList<Entities>`: manages `params` state (`limit`, `offset`, `sort`, `order`, `q`), computes pagination (`page`, `pageSize`, `totalPages`), provides `setPage`, `setSearch`, `setSort`, `refetch`, calling `api.list<Entities>WithCount`.
    - `use<Entity>`: detail hook fetching entity by ID via `api.get<Entity>`.
    - `useCreate<Entity>`: mutation hook with `create`, `mutate`, `loading`, `error`, `reset`.
    - `useUpdate<Entity>`: mutation hook with `update`, `mutate`, `loading`, `error`, `reset`.
    - `useDelete<Entity>`: mutation hook with `remove`, `mutate`, `loading`, `error`, `reset`.
  - For subcollections: `useList<Entities>By<Rel>` with parent relation ID scoping, pagination, search, sorting.
  - Exports unified `hooks` object containing all generated hooks.
  - Exports `render_hooks(ir)` publicly and registers in `codegen/__init__.py`.
  - Included in `NextjsWebAdapter.generate` file set.

## Preceded by:
- **R-254**: Structured JSON validation error bodies in Go (`{"errors": [...]}`).
- **R-255**: Query parameter pagination (`limit` & `offset`) on LIST and LIST_BY in Go and FastAPI backends.
- **R-256**: Wired PUT handlers (full-replace update) in Go and FastAPI backends.
- **R-257**: Full-stack connectivity: Next.js typed API client (`lib/api.ts`) & backend CORS middleware.
- **R-258**: Query parameter sorting (`sort` & `order`) with SQL injection whitelist protection.
- **R-259**: Total count database queries and `X-Total-Count` header across Go, Python, and Next.js.
- **R-260**: OpenAPI 3.1 specification generation from Application IR.
- **R-261**: Full-text / keyword search filtering (`q` query param) on LIST endpoints.

## Verification

- `task verify` — pass (506 agent-engine tests; 15 new in `test_nextjs_hooks.py`).
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
