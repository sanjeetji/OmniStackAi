# Current Handoff

Task ID: R-266
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-266) — Update/Edit Mode in Generated Next.js Forms & Collection Screen Edit Actions

- **Dual-Mode Form Screen Generation (`_form_screen_page`)**:
  - Detects `can_update = Op.UPDATE in ops` and `can_create = Op.CREATE in ops`.
  - When `can_update` is enabled, imports `use<Entity>`, `useUpdate<Entity>`, and `useSearchParams` from `"next/navigation"`.
  - Reads `editId = searchParams.get("id")` and sets `isEdit = Boolean(editId)`.
  - Wires mutation hook `const { update, loading: updating, error: updateError } = useUpdate<Entity>();` and fetch hook `const { data: initialData, loading: fetchingInitial } = use<Entity>(editId);`.
  - Declares `useEffect` to prefill `formData` when `initialData` arrives in edit mode.
  - Submits via `update(editId, formData)` when in edit mode, falling back to `create(formData)` when in create mode.
  - Dynamically switches header title (`{isEdit ? "Edit " + name : screen.name}`), submit button label (`{((submitting || updating) ? "Saving..." : (isEdit ? "Update " + name : "Save " + name))}`), initial loading banner, and success banner.
- **Collection Screen Edit Actions (`_collection_screen_page`)**:
  - When `Op.UPDATE in ops` and a form screen exists, renders an "Edit" action `<Link>` in the table row pointing to `/{form_screen.id}?id=${(item as any).id}`.
  - Includes `onClick={(e) => e.stopPropagation()}` on the Edit link to avoid accidentally triggering row selection.
- **Subcollection New Child Creation Link**:
  - In subcollection master-detail view, renders `+ New <Child>` link (`/{child_form.id}?{foreign_key_param}=${selectedId}`) when a form screen exists for the child entity.
- **Safety & Invariance**:
  - Clean fallback safety: entities without `Op.UPDATE` (e.g. `minimal-blog` Post) emit zero update code, state, or hooks.
  - Strict diff invariance: no references to `ir.description`, preventing diff drift.

## Preceded by:
- **R-265**: Subcollection Navigation & Master-Detail Views in Generated Screens.
- **R-254**: Structured JSON validation error bodies in Go (`{"errors": [...]}`).
- **R-255**: Query parameter pagination (`limit` & `offset`) on LIST and LIST_BY in Go and FastAPI backends.
- **R-256**: Wired PUT handlers (full-replace update) in Go and FastAPI backends.
- **R-257**: Full-stack connectivity: Next.js typed API client (`lib/api.ts`) & backend CORS middleware.
- **R-258**: Query parameter sorting (`sort` & `order`) with SQL injection whitelist protection.
- **R-259**: Total count database queries and `X-Total-Count` header across Go, Python, and Next.js.
- **R-260**: OpenAPI 3.1 specification generation from Application IR.
- **R-261**: Full-text / keyword search filtering (`q` query param) on LIST endpoints.
- **R-262**: React data-fetching & mutation hooks generation (`apps/web/lib/hooks.ts`).
- **R-263**: Interactive Screen Component Generator with Real Data Binding (`apps/web/app/<screen>/page.tsx`).
- **R-264**: Field-Level Validation & Error Feedback in Generated Next.js Forms (`apps/web/app/<screen>/page.tsx`).

## Verification

- `task verify` — pass (558 agent-engine tests; 12 new in `test_form_update_screens.py`).
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
