# Git service (Brief §6/§20/§34/§71)

The Git service turns a `GeneratedProject` (from a framework adapter) into a real, customer-owned Git
repository on disk. It completes the first end-to-end builder slice:

```
Application IR  ->  FrameworkAdapter  ->  GeneratedProject  ->  Git service  ->  owned Git repo
```

Package: `omnistackai_agent_engine.git_service` (standard library + local `git`; no network).

## API

- `materialize_project(project, target_dir, *, overwrite=False) -> MaterializeResult`
  Writes every `GeneratedFile` under `target_dir`, creating parent directories. Refuses any path that
  would escape the target (defense-in-depth on top of the already-validated paths), and refuses a
  non-empty target unless `overwrite=True`. Executable files get the executable bit.
- `create_repository(project, target_dir, *, author_name, author_email, commit_message="Initial commit",
  overwrite=False) -> RepositoryResult`
  Materializes the project, then `git init`, stages everything, and makes **one commit** with the
  **customer** as author and committer. Returns the commit SHA and file count.

## Guarantees

- **Writes only inside the target directory** — never the platform repo; paths are validated and the
  resolved destination is checked to stay within the target.
- **No global git config dependency** — the commit identity is passed explicitly via `GIT_AUTHOR_*` /
  `GIT_COMMITTER_*`, so results are deterministic on any machine.
- **Offline** — no network; only the local `git` CLI.
- **Customer ownership** — the generated source is a normal Git repo the customer fully owns (Brief
  §71 client source ownership), not locked inside the platform.

Verified offline in a temp directory (materialization, escape/non-empty refusal, single-commit
init, author identity, and tree-matches-project). Running/previewing the generated app is a later
task that needs a sandbox/runtime environment.
