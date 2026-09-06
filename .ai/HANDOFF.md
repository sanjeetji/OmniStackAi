# Current Handoff

Task ID: R-226
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-226-adapter-contract`
Last verified implementation SHA: `f27bf416e99423d281e1c4e6f3eabc363848f95f`

## Completed

- Added the **code-generation boundary** in `omnistackai_agent_engine.codegen`:
  - `GeneratedFile` — one path→content record with a safe relative POSIX path (no absolute, no `..`,
    no backslashes/control chars, bounded; segments `[A-Za-z0-9._-]`).
  - `GeneratedProject` — immutable, path-unique, deterministically ordered set for one target; `get`,
    `paths`, `files`, `__len__`, `merge` (same target only). No disk writes.
  - `FrameworkAdapter` — runtime-checkable contract (`target` + `generate(ir) -> GeneratedProject`).
  - `AdapterRegistry` — register/get by target with stable `DuplicateAdapterError`/`UnsupportedTargetError`;
    `GenerationTarget` enum over the MVP targets. Adapters are chosen only via the registry.
- Depends on `application_ir`; standard-library only; deterministic; nothing executed.

## Verification

- `task verify` — pass (125 agent-engine tests; 10 new). `task agent-engine:lint`, `task security:quick` — pass.
- Compose unchanged; offline `task bootstrap` unchanged.
- Tracker — R-226 (Product) at `Phase_Roadmap!A9:M9` (rows 9..233 shifted to 10..234, ranges extended);
  no ID lost; MVP total 121, Done 15; chart/styles/workbook byte-identical; zip verified.

## Product roadmap (vertical slice toward an Emergent-class builder)

1. R-225 Application IR — done.
2. R-226 framework adapter contract + file-set model — done.
3. **R-227 (next)** Next.js web adapter — emit a real Next.js app *as files* from the IR; verified by
   asserting emitted file contents (offline, no install/build).
4. R-228 Git service v1 — materialize the file-set into a customer-owned repo with a commit.
5. Later (needs a cloud/network env): sandbox run → instant browser preview → deploy; plus the
   deferred R-224 Next.js console upgrade.

## Next action

Proceed to **R-227** — the Next.js web `FrameworkAdapter` that turns an Application IR into a real
Next.js project (pages/components/API routes/config), registered via `AdapterRegistry`, verified
offline by asserting the emitted `GeneratedProject`. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
