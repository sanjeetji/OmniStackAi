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

R-002 provides the control-plane database dependency only. Later Tracker IDs will add
language-specific commands without changing this root interface.
