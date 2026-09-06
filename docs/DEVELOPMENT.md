# Development

Use the root Taskfile as the stable command interface:

- `task doctor` checks the repository and available toolchains.
- `task bootstrap` installs only declared local dependencies.
- `task lint`, `task test`, and `task verify` run deterministic checks.
- `task ai:status` reports durable task state and Git context.
- `task ai:handoff` validates the handoff payload.
- `task db:config` validates the local database definition without starting a container.
- `task db:up`, `task db:status`, `task db:verify`, and `task db:down` manage and verify the
  local PostgreSQL+pgvector dependency. `db:down` preserves the named data volume.

Before the first database start, copy `.env.example` to ignored `.env` and replace
`OMNISTACKAI_POSTGRES_PASSWORD` with a local-only password. Then run `task db:verify`.

For local model setup, use `task ollama:config`, start Ollama.app or run `task ollama:serve`, then
run `task ollama:verify`. The live check discovers the configured model and makes one short local
inference call. See `docs/LOCAL_MODELS.md`.

Through R-003 the repository provides local database and local model dependencies only. Later
Tracker IDs will add language-specific commands without changing this root interface.
