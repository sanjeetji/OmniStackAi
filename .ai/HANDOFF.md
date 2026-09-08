# Current Handoff

Task ID: R-250
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `1eed171`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author. The tooling-required `Co-Authored-By:
  Claude Opus 4.8` trailer is permitted by the founder.

## Completed (R-250) — richer field validation into the schema + FastAPI models

- New `codegen/field_validation.parse_field_rules` reads the IR `Field.validation` rules
  `max_length:<int>` and `enum:<a>|<b>|<c>` (unknown rules ignored). The PostgreSQL schema renders a
  STRING with `max_length` as `VARCHAR(n)` and an enum as `CHECK (<col> IN ('a','b'))` (values escaped,
  `id` PK unaffected); the FastAPI Pydantic models render `Field(max_length=n)` (or `Field(default=None,
  max_length=n)`) and a `Literal[...]` type, importing `Field`/`Literal` only when used.
- Go request-validation tags deferred (the schema already constrains Go writes at the DB). Example IRs
  unchanged so existing outputs stay byte-stable; feature exercised by constructed-IR tests.

## Verification

- `task verify` — pass (337 agent-engine tests; 10 new in `test_field_validation.py`). `task
  security:quick`, `task env:check` — pass. Demo: `title VARCHAR(120)`, `status … CHECK (status IN
  ('draft','published','archived'))`; Pydantic `title: str = Field(max_length=120)`, `status:
  Literal[...]`. Rule-free models keep the plain `from pydantic import BaseModel`. Nothing runs.
- Tracker — R-250 at `Phase_Roadmap!A9:M9`; MVP total 144 / Done 39; general row-insertion; rows 1..258
  contiguous, table `A4:M258`, XML well-formed. 0 local / 0 cloud calls.

## Product state

The offline builder covers Application IR → validation/normalization → Next.js/FastAPI/Go generation
with PostgreSQL schema (now incl. unique constraints, indexes, and max_length/enum validation),
repositories, wired CRUD/sub-collections, JWT auth + role enforcement, honest seed data
(migrations/0002_seed.sql from explicit IR fixtures) →
owned Git monorepo → preview/deploy plans → verification ladders → patch/rename-aware edits → commit.
The static console visibly proves the project plan and edit patch beside the 11-provider model fabric,
Balanced routing, resilience, price book, and usage accounting. 39 tracker tasks are Done; no paid
cloud service is selected and the platform PostgreSQL/Compose architecture is unchanged.

## Blockers and risks

- No blocker for the remaining offline R-251 candidates. Live generated-app preview/deploy and the
  deferred R-224 Next.js console upgrade still need a reliable network environment and/or authorized
  provider keys. Native mobile remains deferred per Brief §25/§91.

## Next action

Continue from R-251 with one offline-doable candidate:

1. Extend R-250 to the Go backend: request-validation struct tags (go-playground `validate:"max=120,
   oneof=draft published"`) + numeric `min`/`max` rules into schema `CHECK` and Pydantic `ge`/`le`; or
2. Render the R-248 seed rows / R-249 indexes / R-250 validation in the static-console builder proof.

## Next command

`task ai:status`
