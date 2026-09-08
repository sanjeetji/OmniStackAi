# Current Handoff

Task ID: R-253
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: TBD (pre-commit)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.

## Completed (R-253) — PATCH/update handlers wired in Go and FastAPI backends

- `route_wiring` gains `Op.UPDATE`. A `PATCH /entities/{id}` endpoint whose `request_schema` names
  a known repo entity is now wired (not 501). Everything else keeps the conservative 501 scaffold.
- **Go store** (`data_access._go_entity_store`): emits `Update<Entity>(ctx, db, id, m)` —
  `UPDATE … SET col=$1, … WHERE id=$N RETURNING <cols>` scanning into `*models.<Entity>`; returns
  `nil, nil` on `sql.ErrNoRows`.
- **Go handler** (`_handlers_file_wired`): decodes body → `validateStruct(m)` (if entity has rules,
  reusing the R-252 helper) → `store.Update<Entity>` → `404` on nil / `200 + writeJSON` on success.
  `has_validation` now activates for UPDATE + CREATE (validator dep emitted whenever either has rules).
- **FastAPI repo** (`_python_repository`): emits `update_<table>(id, data)` — `UPDATE … SET col=%s,
  … WHERE id=%s RETURNING *` using only data keys (excluding `id`); `fetchone()` returns `None` on
  not-found.
- **FastAPI router** (`_router_file`): emits `@router.patch` route with `id_param + payload` →
  `update_<table>` → `HTTPException(404)` on `None`.
- All SQL values parameterized (`$N` / `%s`); identifiers are fixed IR-derived strings.
- Rule-free entities: no `validateStruct` call in update handler.
- Example IRs (`minimal-blog`, `rideshare-favourites`): unchanged (no PATCH endpoints in either).

## Verification

- `task verify` — pass (374 agent-engine tests; 24 new in `test_patch_update_handlers.py`). `task
  security:quick`, `task env:check` — pass. Demo (Marketplace IR: `Listing` entity with rules,
  `PATCH /listings/{listingId}`): Go store emits `UpdateListing`; handler calls `validateStruct`
  before `store.UpdateListing`; rule-free Listing handler has no `validateStruct`; FastAPI repo
  emits `update_listing` with `UPDATE … RETURNING *`; router emits `@router.patch`. Nothing runs;
  no DB connection.
- Tracker — R-253 at `Phase_Roadmap!A9:M9`; Done 42; general row-insertion; 0 local / 0 cloud calls.

## Product state

The offline builder covers Application IR → validation/normalization → Next.js/FastAPI/Go generation
with PostgreSQL schema (unique constraints, indexes, max_length/enum/min/max validation via
CHECK/VARCHAR), repositories, wired **full CRUD** (LIST/GET/CREATE/PATCH/DELETE) on both backends,
sub-collections, JWT auth + role enforcement, and field validation enforced at every layer: FastAPI
(Pydantic, at construction), Go (go-playground `validator.Struct` → 400 in create + update handlers),
and the DB schema. Honest seed data (migrations/0002_seed.sql) only from explicit IR fixtures →
owned Git monorepo → preview/deploy plans → verification ladders → patch/rename-aware edits →
commit. 42 tracker tasks Done; no paid cloud service; platform PostgreSQL/Compose unchanged.

## Blockers and risks

- No blocker for remaining offline R-254 candidates. Live generated-app preview/deploy and R-224
  Next.js console upgrade still need a reliable network environment and/or authorized provider keys.
  Native mobile remains deferred per Brief §25/§91.

## Next action

Continue from R-254 with one offline-doable candidate (founder to pick):

1. **Field-level validation error bodies** — return structured JSON `{"errors":[{"field":"price",
   "rule":"min","value":"must be >= 0.01"}]}` instead of the flat `"validation_failed"` in both
   FastAPI (Pydantic `.errors()`) and Go (`validator.FieldError` loop).
2. **Another real CRUD/behaviour gap** — e.g. `PUT` handlers (full replace), or pagination params
   on LIST endpoints.

## Next command

`task ai:status`
