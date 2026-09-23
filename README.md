# OmniStackAI Platform

OmniStackAI is a governed AI software-engineering platform designed to turn product intent into
verified, customer-owned software changes. The repository is currently in Founder Stage 0.

## Current state

The repository has the canonical modular monorepo, local PostgreSQL+pgvector and Ollama foundations,
the minimal Go control-plane health/readiness service, and the vendor-neutral Python model-provider
contract. Read `docs/START_HERE.md` and `.ai/PROJECT_STATE.yaml` before beginning work.

## Set up a new machine

`docs/SETUP.md` lists every requirement (Node 22.18+, pnpm, Go, Python 3.13, Task, ripgrep, Colima
- [Commands](COMMANDS.md) — every command to run, administer and verify the platform.
and the Docker CLI), the install commands, the three pieces of `.env` configuration that are easy
to miss, and a troubleshooting table. Run `./scripts/omnistack.sh doctor` first on any new machine:
it checks all of it and prints the exact fix for anything missing.

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
task agent-engine:test
```

Install [Task](https://taskfile.dev/) before using the command interface. The validation scripts
under `scripts/` can also be run directly during initial toolchain setup.
