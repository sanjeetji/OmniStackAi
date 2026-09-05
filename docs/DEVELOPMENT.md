# Development

Use the root Taskfile as the stable command interface:

- `task doctor` checks the repository and available toolchains.
- `task bootstrap` installs only declared local dependencies.
- `task lint`, `task test`, and `task verify` run deterministic checks.
- `task ai:status` reports durable task state and Git context.
- `task ai:handoff` validates the handoff payload.

R-001 provides repository checks only. Later Tracker IDs will add language-specific commands
without changing this root interface.

