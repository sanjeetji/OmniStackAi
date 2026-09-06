# Start Here

OmniStackAI is in Founder Stage 0. The repository contains its portable engineering contract,
local PostgreSQL/Ollama dependencies, the minimal Go control-plane service, and bounded platform
contracts added by completed Tracker IDs. Read the state files for the exact current task.

## Start or resume work

1. Read `AGENTS.md`.
2. Read `.ai/PROJECT_STATE.yaml` and `.ai/CURRENT_TASK.yaml`.
3. Read only the IR, ADR, and policy files referenced by the current task.
4. Inspect Git branch, HEAD, status, and diff.
5. Run `task doctor`.
6. Run `task bootstrap` only when dependencies are missing.
7. Run `task ai:status` and the smallest relevant baseline check.

The implementation brief at `R_&_D/OmniStackAI_Implementation_Brief_v6.md` is the normative
architecture source. Sections 77 and 92 are non-negotiable, and the V6 addendum overrides
older sections when they conflict.

## Stop safely

Run verification, then update `.ai/CURRENT_TASK.yaml`, `.ai/PROJECT_STATE.yaml`,
`.ai/WORK_LOG.md`, `.ai/HANDOFF.md`, root `PROJECT_STATE.md`, the changelog, and tracker
evidence. Record one exact next action and command.
