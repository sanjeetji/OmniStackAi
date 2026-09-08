# Current Handoff

Task ID: R-264
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-264) — Field-Level Validation & Error Feedback in Generated Next.js Forms

- **API Client Error Extraction (`codegen/nextjs.py`)**:
  - Emits `extractFieldErrors(error: unknown): Record<string, string>` export in `apps/web/lib/api.ts`.
  - Normalizes Go backend validation error payloads (`{"errors": [{"field": "...", "rule": "...", "message": "..."}]}`).
  - Normalizes FastAPI/Pydantic validation error payloads (`{"detail": [{"loc": ["body", "..."], "msg": "..."}]}`).
  - Gracefully returns empty object for network or non-validation errors.
- **Form Screen Validation & Error States (`_form_screen_page`)**:
  - Imports `extractFieldErrors` from `../lib/api`.
  - Declares `fieldErrors` state (`const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});`).
  - Client-side pre-validation inside `handleSubmit`: validates required fields, string `max_length`, numeric `min`/`max` constraints, and enum values prior to network requests.
  - Server-side error mapping: catches submission errors, extracts per-field messages via `extractFieldErrors(err)`, and populates `fieldErrors`.
  - Dynamic input styling: red borders (`fieldErrors[f.name] ? "1px solid #ef4444" : "1px solid #cbd5e1"`) and accessibility attributes (`aria-invalid={!!fieldErrors[f.name]}`).
  - Per-field error messages rendered directly beneath inputs (`<span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>`).
  - Interactive error clearing: edits to an input reactively clear its field error (`onChange`).
  - Interactive `<select>` dropdown rendering with declared options for enum fields.
  - Reset button resets `fieldErrors` and form data.
  - Warning alert banner shown when field errors are present; hides generic `submitError` to prioritize specific field feedback.
  - Byte-identical diff invariance maintained across IR description changes.

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

## Verification

- `task verify` — pass (527 agent-engine tests; 12 new in `test_form_validation_screens.py`).
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
