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

Through R-003 the repository provided local database and local model dependencies only. R-004 adds
the first language-specific service commands without changing the root interface.

The R-004 Go control-plane foundation is checked with `task control-plane:lint`,
`task control-plane:test`, and `task control-plane:build`. With Colima/Docker and PostgreSQL running,
`task control-plane:verify` builds the pinned container and verifies `/healthz` plus
PostgreSQL-backed `/readyz`.

The Python model-provider boundary and loopback Ollama adapter have no third-party runtime
dependencies. Run `task agent-engine:lint` to compile and policy-check them, then
`task agent-engine:test` for offline contract, registry, and adapter tests. With Ollama running,
`task agent-engine:ollama:verify` makes two bounded local calls to prove generation and streaming.
