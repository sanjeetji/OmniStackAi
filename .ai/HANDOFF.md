# Current Handoff

Task ID: R-249
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `28e7cd5`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. The tooling-required `Co-Authored-By:
  Claude Opus 4.8` trailer is permitted by the founder.

## Completed (R-249) — schema indexes + unique constraints from the IR

- `Field.unique: bool = False` → a single-column `UNIQUE` constraint in the schema (never on the `id`
  PK). New `Index` record on `Entity` (`fields` + `unique` + optional `name`) → composite/named indexes;
  index fields are validated against the entity's own fields at construction. Both additions round-trip
  through `to_dict`/`from_dict` (false/empty defaults, no schema-version bump); `normalize_ir` preserves
  them (entities pass through as objects).
- `schema_sql.render_postgres_schema` emits `UNIQUE` on unique non-id columns and one
  `CREATE [UNIQUE] INDEX <name> ON <table> (<cols>);` per entity index under an `-- Indexes` section,
  with a deterministic default name (`<table>_<cols>_idx`, `_key` when unique) when unnamed.
- `rideshare-favourites` `Driver` gained a demo `Index(("name",))`. Schema-only change — the seed,
  data-access, route-wiring, and auth code are untouched.

## Verification

- `task verify` — pass (327 agent-engine tests; 11 new in `test_schema_indexes.py`). `task
  security:quick`, `task env:check` — pass. Demo: `email TEXT NOT NULL UNIQUE`, `CREATE UNIQUE INDEX
  account_tenant_handle_key …`, `CREATE INDEX driver_name_idx ON driver (name);`; `id` marked unique
  stays a plain PK; a bad index field is a construction `InvalidIRError`. Nothing connects to or runs a
  database.
- Tracker — R-249 at `Phase_Roadmap!A9:M9`; MVP total 143 / Done 38; general row-insertion bumped rows
  ≥9 across sqrefs/table/sheet1; rows 1..257 contiguous, table `A4:M257`, XML well-formed. 0 local / 0
  cloud calls.

## Product state

The offline builder covers Application IR → validation/normalization → Next.js/FastAPI/Go generation
with PostgreSQL schema (now incl. unique constraints + indexes), repositories, wired CRUD/sub-collections,
JWT auth + role enforcement, and honest seed data (migrations/0002_seed.sql from explicit IR fixtures) →
owned Git monorepo → preview/deploy plans → verification ladders → patch/rename-aware edits → commit.
The static console visibly proves the project plan and edit patch beside the 11-provider model fabric,
Balanced routing, resilience, price book, and usage accounting. 38 tracker tasks are Done; no paid
cloud service is selected and the platform PostgreSQL/Compose architecture is unchanged.

## Blockers and risks

- No blocker for the remaining offline R-250 candidates. Live generated-app preview/deploy and the
  deferred R-224 Next.js console upgrade still need a reliable network environment and/or authorized
  provider keys. Native mobile remains deferred per Brief §25/§91.

## Next action

Continue from R-250 with one offline-doable candidate:

1. Richer field validation into the generated models + schema: e.g. a `Field.validation` like
   `max_length:120` / `enum:...` → Pydantic constraints + Go struct tags + `VARCHAR(n)`/`CHECK`; or
2. Render the R-248 seed rows and R-249 indexes/unique constraints in the static-console builder proof.

## Next command

`task ai:status`
