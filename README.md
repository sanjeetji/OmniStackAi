# OmniStackAI Platform

OmniStackAI is a governed AI software-engineering platform designed to turn product intent into
verified, customer-owned software changes. The repository is currently in Founder Stage 0.

## Current state

The repository has the canonical modular monorepo, local PostgreSQL+pgvector and Ollama foundations,
and the minimal Go control-plane health/readiness service. Read `docs/START_HERE.md` and
`.ai/PROJECT_STATE.yaml` before beginning work.

## Repository commands

```text
task doctor
task bootstrap
task lint
task test
task verify
task ai:status
task ai:handoff
task db:verify
task ollama:verify
task control-plane:verify
```

Install [Task](https://taskfile.dev/) before using the command interface. The validation scripts
under `scripts/` can also be run directly during initial toolchain setup.
