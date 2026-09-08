# Current Handoff

Task ID: R-265
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-265) — Subcollection Navigation & Master-Detail Views in Generated Screens

- **Subcollection Detection & Resolution (`codegen/nextjs.py`)**:
  - Emits `SubcollectionInfo` dataclass and `_subcollections_for_parent(parent_name: str, ir: ApplicationIR) -> list[SubcollectionInfo]`.
  - Discovers relations where `rel.target_entity == parent_name` and an `Op.LIST_BY` endpoint exists.
  - Automatically derives hook name `useList<Children>By<Rel>`, child type name, relation name, and display fields.
- **Collection Screen Master-Detail Layout (`_collection_screen_page`)**:
  - Conditionally imports subcollection hooks and child entity types when subcollections exist on dedicated lines, preserving exact substring matches for parent imports.
  - Declares `selectedId` state (`string | null`) and subcollection tab state for multi-subcollection parent entities.
  - Wires subcollection hooks at the component top level scoped to `selectedId` (e.g. `const commentsSubcol = useListCommentsByPost(selectedId);`), taking advantage of safe idle behavior when `selectedId === null`.
  - Enriches the master table with interactive row selection (`onClick={() => setSelectedId(selectedId === item.id ? null : item.id)}`), visual selection indicator, and an action column button ("View Details" / "Hide Details").
  - Renders master-detail subcollection section below table when an item is selected:
    - Selected item header banner with "Close Details" action.
    - Tab bar for multi-subcollection entities with interactive switching and live total count badges (`{subcol.total}`).
    - Child items list rendering loading state, error state with retry, empty state, and child item cards displaying key scalar attributes.
    - Subcollection refresh action button.
- **Dedicated Detail Screen Implementation (`_detail_screen_page`)**:
  - Implements screen generation for screens with `intent == "detail"`.
  - Fetches parent entity details by ID via `use<Entity>(id)`.
  - Renders parent attribute grid, back navigation link, and nested child subcollections section.
  - Updated `_screen_page` routing to dispatch `intent == "detail"` to `_detail_screen_page`.
- **Safety & Diff Invariance**:
  - Clean fallback safety: entities without subcollections (e.g. `rideshare-favourites`) emit zero subcollection code, state, or hooks.
  - Preserved diff invariance: generated screens do not reference `ir.description`, preventing diff drift in `test_console_snapshot.py`.

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
- **R-263**: Interactive Screen Component Generator with Real Data Binding (`apps/web/app/<screen>/page.tsx`).
- **R-264**: Field-Level Validation & Error Feedback in Generated Next.js Forms (`apps/web/app/<screen>/page.tsx`).

## Verification

- `task verify` — pass (546 agent-engine tests; 19 new in `test_subcollection_screens.py`).
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
