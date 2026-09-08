# Current Handoff

Task ID: R-248
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `9d34720`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. The tooling-required `Co-Authored-By:
  Claude Opus 4.8` trailer is permitted by the founder.

## Completed (R-248) — honest seed data from Application IR fixtures

- New `Fixture` IR record (entity + rows of column→JSON value): validated in `__post_init__`,
  cross-referenced by `validate_ir` (ERROR on unknown entity/column, WARNING on a missing required
  column), and round-tripped through `to_dict`/`from_dict`/`normalize_ir`. Additive field, empty
  default, no schema-version bump.
- `codegen/seed_sql.render_postgres_seed(ir)` emits a deterministic `migrations/0002_seed.sql` — one
  `INSERT` per row using ONLY the declared columns/values, never inventing/defaulting/guessing; it owns
  the codebase's first SQL literal quoter (quotes doubled; bool→TRUE/FALSE; None→NULL; dict/list→jsonb).
  Both backends emit it inside the existing `has_db` block, only when the IR has fixtures.
- `minimal-blog` gained example fixtures (two Post rows + a Comment with `post_id`); `task builder:demo`
  prints the seed. Deterministic/offline — no DB connection, no migration run, no fabricated value.

## Verification

- `task verify` — pass (316 agent-engine tests; 14 new in `test_seed_sql.py`). `task security:quick`,
  `task env:check` — pass. `task builder:demo -- minimal-blog` prints the seed INSERTs (escaped quotes,
  FK column); `rideshare-favourites`/non-postgres emit no `0002_seed.sql`; `0001_init.sql` unchanged.
- Tracker — R-248 at `Phase_Roadmap!A9:M9`; MVP total 142 / Done 37; a GENERAL row-insertion script
  (the sheet structure had diverged) bumped rows ≥9 across sqrefs/table/sheet1; rows 1..256 contiguous,
  table `A4:M256`, XML well-formed. 0 local / 0 cloud calls.

## Product state

The offline builder covers Application IR → validation/normalization → Next.js/FastAPI/Go generation
with PostgreSQL schema, repositories, wired CRUD/sub-collections, JWT auth + role enforcement, and now
honest seed data (migrations/0002_seed.sql from explicit IR fixtures) → owned Git monorepo →
preview/deploy plans → verification ladders → patch/rename-aware edits → commit. The static console
visibly proves the project plan and edit patch beside the 11-provider model fabric, Balanced routing,
resilience, price book, and usage accounting. 37 tracker tasks are Done; no paid cloud service is
selected and the platform PostgreSQL/Compose architecture is unchanged.

## Blockers and risks

- No blocker for the remaining offline R-249 candidates. Live generated-app preview/deploy and the
  deferred R-224 Next.js console upgrade still need a reliable network environment and/or authorized
  provider keys. Native mobile remains deferred per Brief §25/§91.

## Next action

Continue from R-249 with one offline-doable candidate:

1. Deepen IR + adapter coverage: entity indexes and unique constraints flowing into the schema
   (`schema_sql`), and richer field validation (e.g. length/enum) surfaced in the models + schema; or
2. Add a Fixtures section to the static console's builder proof (render the seed rows from R-248).

## Next command

`task ai:status`
