# Current Handoff

Task ID: R-225
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-225-application-ir`
Last verified implementation SHA: `ad5e4ddf5918ddf3e4005c21a07c21601faf2ee6`

## Completed

- Started the actual product per the brief. Added the framework-neutral **Application IR** (Brief §9)
  in `omnistackai_agent_engine.application_ir` — the source of truth every codegen adapter will
  consume:
  - Immutable, validated records: `ApplicationIR`, `ProjectStrategy`, `Role`, `Entity`
    (`Field`/`Relation`), `ApiEndpoint`, `Screen`, `AcceptanceCriterion`, with the Brief §9 enums.
  - Cross-validation (a relation targets a declared entity; a screen role references a declared role),
    unique ids, well-formed API method+path, enum checks → stable `InvalidIRError`.
  - `IR_SCHEMA_VERSION = 1`; lossless `to_dict`/`from_dict`; `from_dict` rejects an unknown/newer
    version with `UnsupportedIRVersionError` (migration hook).
  - Standard-library only; no network, infra, codegen, or framework knowledge.
- Also (this session): showed the platform live (`task agent-engine:gateway:run`) and published the
  console UI as a private Artifact; recorded R-224 (Next.js upgrade) as Deferred (env can't install
  front-end bundlers — tried Next 3× and Vite).

## Verification

- `task verify` — pass (115 agent-engine tests; 17 new IR tests).
- `task agent-engine:lint`, `task security:quick`, `task env:check` — pass.
- Compose unchanged (`postgres`, `control-plane`); offline `task bootstrap` unchanged.
- Tracker — R-225 (category Product) at `Phase_Roadmap!A9:M9` (rows 9..232 shifted to 10..233, ranges
  extended); no ID lost; MVP total 120, Done 14; chart/styles/workbook byte-identical; zip verified.

## Product roadmap (vertical slice toward an Emergent-class builder)

1. **R-225 Application IR** — done.
2. **R-226** framework adapter contract — the interface adapters implement + an in-memory generated
   file-set model (path → contents), all offline/unit-testable.
3. **R-227** Next.js code adapter — emit a real Next.js app *as files* from the IR; verified by
   asserting emitted file contents (no install/build needed offline).
4. **R-228** Git service v1 — materialize the file-set into a customer-owned repo with a commit.
5. Later (needs a cloud/network env): sandbox run, instant browser preview, deploy; plus the
   deferred R-224 Next.js console upgrade.

## Next action

Proceed to **R-226** — framework adapter contract + generated file-set model. Native mobile /
device-cloud stays deferred per Brief §25/§91 until web/backend stability.

## Next command

`task ai:status`
