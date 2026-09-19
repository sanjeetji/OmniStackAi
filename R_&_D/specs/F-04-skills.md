# F-04 · Knowledge & Skills (proposed Tracker ID: R-502)

**Status:** specified, unblocked. **Depends on:** F-01.

## Why

The model currently receives only the user's sentence. Every serious builder wants to say once
"we use Tailwind and shadcn, our users are Indian SMEs, always add a settings page" and have it
apply to everything after. This is prompt context, not new machinery — cheap to build, and it
directly improves the product's core output.

Two layers, as agreed with the founder:

- **Knowledge — per project.** One brief that is injected into every build and edit of that
  project.
- **Skills — per user, reusable.** Named instruction sets, attachable to many projects, usable
  ad hoc in a single message.

## Design

### Skill

`{ name, description, body, is_default }`. `body` is Markdown, max **8 KB**. `name` is unique per
user, lower-kebab (used for `@mentions`). Examples the UI ships as one-click starters:
"Design system", "Coding standards", "Domain rules", "Copy & tone".

### How context is assembled (the part that must be exact)

On every build/edit the control-plane sends the agent-engine a `context` block:

```json
{ "knowledge": "…", "skills": [ {"name": "design-system", "body": "…"}, … ] }
```

The agent-engine injects it as a bounded system section ahead of the user prompt:

```
## Project knowledge
<knowledge>

## Active skills
### design-system
<body>
```

Rules, enforced server-side in `intake/` prompt assembly:

- Hard cap `OMNISTACKAI_CONTEXT_MAX_CHARS` (default 24 000) across knowledge + skills.
- Order: knowledge first, then explicitly `@mentioned` skills, then project-attached skills, then
  user defaults — truncating from the end.
- When truncation happens the response includes `context_truncated: true` and the chat says so.
  Never silently drop a user's instructions.
- Context is **never** echoed back to the browser in full (it may contain business detail); the UI
  shows which skills were active, not their text.

### Database

```sql
-- migrations/000006_skills.up.sql
CREATE TABLE IF NOT EXISTS skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name        TEXT NOT NULL CHECK (name ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL CHECK (length(body) <= 8192),
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS project_skills (
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    skill_id   UUID NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, skill_id)
);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS knowledge TEXT NOT NULL DEFAULT ''
        CHECK (length(knowledge) <= 16384);
```

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET`/`POST` | `/skills` | List / create. |
| `GET`/`PATCH`/`DELETE` | `/skills/{id}` | Read / update / delete (deleting detaches everywhere). |
| `GET` | `/projects/{id}/knowledge` · `PUT` | Read / replace the project brief. |
| `GET` | `/projects/{id}/skills` | Attached skills. |
| `PUT`/`DELETE` | `/projects/{id}/skills/{skillId}` | Attach / detach. |

Build and edit requests gain an optional `mention_skills: ["design-system"]` array parsed from the
composer's `@mentions`.

### UI

Reference: Lovable Settings → Knowledge (`Lova-31`).

- **Manage → Knowledge**: a large textarea with a character counter, examples placeholder, Save
  with a saved-at timestamp, and the honest note "Applied to every message in this project."
- **Manage → Skills**: the attached list with toggles, plus "Add from library" and "New skill".
- **Settings → Skills** (account level): the library — cards with title, description, default
  badge, used-in-N-projects, edit and delete. The editor is a Markdown textarea with the 8 KB
  counter and a live "what the model will see" preview.
- **Composer**: active skills render as small chips above the input ("Knowledge · design-system
  · coding-standards"); typing `@` opens a mention picker of the user's skills; a chip can be
  toggled off for the next message only.

## Acceptance criteria

- [ ] A skill written once is applied to a new build in another project and visibly changes the
      output (recorded in the task's evidence with the before/after prompt section).
- [ ] `@mention` applies a skill for exactly one message.
- [ ] Oversized context truncates deterministically, reports `context_truncated`, and the chat
      says which part was cut.
- [ ] Skill bodies never appear in any API response to the browser except the editor's own fetch.
- [ ] Gates as usual, including agent-engine unit tests for the assembly and truncation order
      (offline, no model calls).

## Out of scope

- Sharing skills between users or a public skill marketplace.
- Auto-generating a skill from an existing codebase (good idea, separate task).
