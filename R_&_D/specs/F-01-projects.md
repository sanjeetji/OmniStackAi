# F-01 · Projects & workspaces (proposed Tracker ID: R-499)

**Status:** specified, unblocked. **Depends on:** nothing. **Blocks:** everything else in Phase F/G.

## Why this is first

Proven live on 2026-09-19: after restarting the Studio, the founder's build 7 returned
`{"turns": []}` and `404` for its files, and the next build was numbered `1` again.
`studio/history.py` is an in-memory list with a size cap; `studio/session.py` holds the editable
IR in RAM. **Every project a user creates today is lost when the process restarts**, and there is
no per-user ownership at all — any signed-in user can pass any build id to `/jobs/build/{id}/files`
and read someone else's code. This task fixes both.

## Outcome

A user has **projects**: named, listed, reopenable after any restart, owned by them, each with its
own chat history, repo, entity list and credit spend. The Studio opens a project by URL. A
project panel ("Manage") becomes the home for every later feature.

## Design

### Ownership model (decided)

The **control-plane owns identity**; the **agent-engine owns the workspace on disk**. The project
UUID minted by the control-plane *is* the agent-engine's workspace id — no mapping table, and the
control-plane's ownership check is the only authorization needed.

```
console → control-plane  /projects/{uuid}/...   (auth + ownership check)
                         → agent-engine  /api/workspaces/{uuid}/...   (trusted, local)
```

### Agent-engine: workspaces on disk (replaces in-memory history)

- New `studio/workspace.py` — `StudioWorkspaceStore`, standard library only.
- Root: `OMNISTACKAI_STUDIO_WORKSPACE_ROOT`, default `~/.omnistackai/workspaces`.
- Layout per project:

  ```
  <root>/<project-uuid>/
    repo/                     the generated app (already a git repo)
    state.json                {schema, project_id, name, description, entities, file_count,
                               commit_sha, target_dir, kind, pack_id, created_at, updated_at}
    turns.jsonl               one JSON object per chat turn (append-only)
    ir.json                   the editable ApplicationIR, for follow-up edits after a restart
  ```

- Writes are atomic (`tmp` file + `os.replace`). `state.json` carries a `schema` integer so a
  future format change is detectable rather than silently misread.
- `ir.json` is what makes **edits survive a restart** — today `StudioSessionStore` loses it.
- Reads are lazy: listing a workspace never loads `ir.json`.
- Nothing secret is written here (no DB credentials, no tokens, no environment dump) — same rule
  `history.py` already documents.

### Control-plane: database

```sql
-- migrations/000004_projects.up.sql
BEGIN;

CREATE TABLE IF NOT EXISTS projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    entities        JSONB NOT NULL DEFAULT '[]'::jsonb,
    file_count      INTEGER NOT NULL DEFAULT 0,
    commit_sha      TEXT NOT NULL DEFAULT '',
    credits_spent   BIGINT NOT NULL DEFAULT 0 CHECK (credits_spent >= 0),
    message_count   INTEGER NOT NULL DEFAULT 0,
    last_prompt     TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_opened_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS projects_user_id_idx ON projects (user_id, updated_at DESC);

ALTER TABLE credit_ledger
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS credit_ledger_project_id_idx ON credit_ledger (project_id);

INSERT INTO schema_migrations (version) VALUES (4) ON CONFLICT (version) DO NOTHING;
COMMIT;
```

`projects.credits_spent` is a denormalised running total (updated in the same transaction as the
debit) so the project list needs no aggregate query; the ledger stays the source of truth.

### Control-plane: API

New package `internal/projects` (store + handler), mirroring `internal/users`' shape.

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/projects` | The caller's projects, newest-updated first. `?status=active\|archived\|all`, `?limit=`. |
| `POST` | `/projects` | `{name?}` → creates the row and the agent-engine workspace. Name defaults to "Untitled project" and is replaced by the model's app name after the first build. |
| `GET` | `/projects/{id}` | Detail for the General panel. |
| `PATCH` | `/projects/{id}` | `{name?, description?}`. |
| `DELETE` | `/projects/{id}` | Archives by default; `?purge=true` also removes the workspace directory. |
| `POST` | `/projects/{id}/build/stream` | Same SSE relay as `/jobs/build/stream`, scoped to the project; on `done`, updates name/entities/file_count/commit_sha/credits and appends to the ledger with `project_id`. |
| `POST` | `/projects/{id}/edit` | As `/jobs/build/{id}/edit`, scoped. |
| `GET` | `/projects/{id}/turns` · `/files` · `/file` | Proxies, after the ownership check. |
| `POST` | `/projects/{id}/preview` · `/problems`, `GET /problems` | Proxies, after the ownership check. |

**Every route resolves the project by `(id, user_id)` first and 404s if it is not the caller's.**
That closes the current cross-tenant read hole.

The existing `/jobs/*` routes stay exactly as they are — `scripts/test.sh` pins them — and are
marked deprecated in comments.

### Agent-engine: API

| Method | Route | Behaviour |
| --- | --- | --- |
| `POST` | `/api/workspaces/{id}/build` and `/build/stream` | Build into workspace `{id}` (created if absent). Same payload/stream shape as today. |
| `POST` | `/api/workspaces/{id}/edit` | Loads `ir.json` from disk, so edits work after a restart. |
| `GET` | `/api/workspaces/{id}/turns` · `/files` · `/file` · `/problems` | From disk. |
| `POST` | `/api/workspaces/{id}/preview` | Existing preview manager, keyed by the workspace repo path. |
| `DELETE` | `/api/workspaces/{id}` | Removes the directory (used by `?purge=true`). |

Legacy `/api/build/{id}/*` routes keep working against the same store (the old numeric ids simply
do not exist after this change; they return 404 as they already do after a restart).

### Console: UI

Reference: Lovable's project list and its left project header (`Lova-02`, `Lova-30`).

1. **Home (`/`)** — under the composer, a **Your projects** section: cards with name, last prompt,
   updated-at ("2 hours ago"), entity chips, file count, credits spent. Empty state keeps the
   current getting-started copy. "View all" → `/projects`.
2. **`/projects`** — full list, search box, Active/Archived filter, sort by updated/created/name.
   Row actions: Open, Rename, Duplicate name…, Archive, Delete (confirm dialog naming the project).
3. **`/studio/[projectId]`** — the Studio, replacing `?build=`. `/studio` with no id shows the
   composer and creates a project on first send; `/studio?prompt=…` (R-497) creates a project then
   redirects to `/studio/{id}`. Old `?build=` URLs redirect to the project if one matches, else to
   `/studio` with an honest "that session is gone" notice.
4. **Project switcher** — the chat rail's header name becomes a `DropdownMenu`: recent projects,
   "All projects…", "New app". This is the Lovable pattern the founder asked for.
5. **Manage panel** — `/studio/[projectId]/manage` with a left sub-nav. Ships with **General**
   (name, description, created, last updated, entity chips, file count, commit sha, credits spent
   in this project, Archive/Delete). Later tasks add their own sections here; the nav lists only
   sections that exist.

States: loading skeletons for the list and panel; empty state for no projects; error alert when
the control-plane is unreachable; every destructive action behind a typed confirm.

## Flow: first build, end to end

```
user types a prompt on /
 → POST /projects                      → project row (Untitled project) + workspace dir
 → redirect /studio/{id}
 → POST /projects/{id}/build/stream    → agent-engine /api/workspaces/{id}/build/stream
 → SSE deltas render as today
 → on done: engine writes state.json/ir.json/turns.jsonl; control-plane updates the row
            (name from the model, entities, files, commit, credits) and appends the ledger row
 → reload, restart, next week: /projects lists it; opening it hydrates chat from turns.jsonl
   and edits still work because ir.json is on disk
```

## Acceptance criteria

- [ ] A project created before a full `omnistack.sh down && up` is listed afterwards, opens, shows
      its chat history, its files, and accepts a follow-up edit that produces a new commit.
- [ ] `/projects` lists only the caller's projects; requesting another user's project id returns
      404 (regression test in `handler_test.go`).
- [ ] Credits spent are attributed per project and the total matches the ledger.
- [ ] Renaming, archiving and deleting work; delete with `?purge=true` removes the directory.
- [ ] Old `/jobs/*` routes still behave exactly as their existing tests assert.
- [ ] Gates: `go build/vet/test`, agent-engine `task verify` (offline, 0 model calls),
      console `typecheck/lint/build`, `scripts/test.sh` (new F-01 block), `task lint`,
      `security:quick`, `env:check`; live smoke covering the restart case above.

## Risks

- **Migration of existing in-memory builds:** none exist after a restart, so there is nothing to
  migrate. Say so in the release note rather than writing dead code.
- **Disk growth:** workspaces are full app repos plus `node_modules` once previewed. Add
  `OMNISTACKAI_STUDIO_WORKSPACE_LIMIT` (default 50 projects/user) and surface size in General;
  purge on delete.
- **Concurrency:** two tabs editing one project. The agent-engine already serialises per process;
  add a per-workspace lock file and return 409 on a second concurrent edit.
