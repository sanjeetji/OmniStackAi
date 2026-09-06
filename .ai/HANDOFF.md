# Current Handoff

Task ID: R-228
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-228-git-service`
Last verified implementation SHA: `28801ef396f7ead743a1d0cdc68657de23cefe1a`

## Milestone — first end-to-end builder slice is complete

`Application IR (R-225) → framework adapter contract (R-226) → Next.js code adapter (R-227) → Git
service (R-228)` turns a structured app spec into a **real Next.js app inside a customer-owned Git
repo**, fully offline and tested.

## Completed (R-228)

- `omnistackai_agent_engine.git_service`:
  - `materialize_project(project, target_dir, *, overwrite=False)` — writes every `GeneratedFile`
    under the target, refuses path escapes and (unless overwrite) a non-empty target, sets exec bits.
  - `create_repository(project, target_dir, *, author_name, author_email, commit_message=...)` —
    `git init` + stage + **one commit** with the customer identity via explicit env (no global git
    config); returns the commit SHA and file count.
- Writes only inside the caller's target directory; offline; local `git` only.
- End-to-end demo: demo IR → 13-file Next.js app → a real one-commit customer-owned repo.

## Verification

- `task verify` — pass (140 agent-engine tests; 6 new). `task agent-engine:lint`, `task security:quick` — pass.
- Compose unchanged; offline `task bootstrap` unchanged.
- Tracker — R-228 (Product) at `Phase_Roadmap!A9:M9` (rows 9..235 → 10..236, ranges extended); no ID
  lost; MVP total 123, Done 17; chart/styles/workbook byte-identical; zip verified.

## What exists now (product)

- **Model fabric** (R-005..R-223): gateway, local Ollama + 5 cloud adapters (key-activated), streaming,
  fallback + circuit breaking, usage/cost accounting, a static console + snapshot exporter.
- **Builder slice** (R-225..R-228): Application IR → adapter contract → Next.js generator → Git service.

## Next action (needs a cloud/network-capable environment)

The remaining builder-slice steps require real runtime/infra and are the right next tasks once such an
environment is available:
1. **Sandbox/runtime provider + instant browser preview** of the generated app (Brief §15/§51).
2. **Backend (Go/Python) framework adapter** to pair with the Next.js web adapter (multi-target from
   one IR — the core differentiator).
3. **R-224 Next.js console upgrade** (needs npm registry access).
Native mobile / device-cloud stays deferred per Brief §25/§91 until web/backend stability.

Confirm the next Tracker ID with the founder.

## Next command

`task ai:status`
