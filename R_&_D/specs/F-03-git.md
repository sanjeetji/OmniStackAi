# F-03 · Code ownership — download, connect GitHub, push (proposed Tracker ID: R-501)

**Status:** specified. **Depends on:** F-01 (projects), F-05 (token encryption — or ship the
encryption helper here and let F-05 reuse it). **Gate:** the founder registers one GitHub App.

## Why

The promise is "you own the code". Today the code exists as a real git repo with one commit per
build and one per edit — on our server, with no way to get it. This task delivers it two ways:
instantly (ZIP) and properly (the user's own GitHub repository).

## Part 1 — Download (no accounts, ships first)

- `GET /projects/{id}/export` streams a `.zip` of the project's repo at HEAD.
- Excludes `.git`, `node_modules`, `.next`, `__pycache__`, `.venv`, and any real `.env*`
  (`.env.example` is kept) — the same exclusion list `studio/files.py` already uses.
- Built with Python's `zipfile` into a temporary file and streamed; size is bounded and reported.
- UI: **Download code** button in the project header and in Manage → Git.

## Part 2 — GitHub

### One-time setup (founder)

Register a **GitHub App** (not a classic OAuth App) named OmniStackAI:

- Permissions: `Contents: Read & write`, `Metadata: Read-only`, `Administration: Read & write`
  (only needed to create repositories).
- "Request user authorization (OAuth) during installation": on.
- Callback URL: `{CONSOLE_URL}/api/git/github/callback`.
- Webhooks: off for v1.
- Store in `.env`: `GITHUB_APP_ID`, `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET`,
  `GITHUB_APP_PRIVATE_KEY` (PEM, base64) — all added to `.env.example` as empty placeholders.

A GitHub App is chosen over an OAuth App because the user grants access **per repository**,
tokens expire in an hour, permissions are narrow, and the user can revoke the installation from
GitHub's own settings. A classic OAuth App's `repo` scope would give us write access to every
repository the user owns — unacceptable for a product whose whole pitch is "your code".

### Database

```sql
-- migrations/000005_git_connections.up.sql
CREATE TABLE IF NOT EXISTS git_connections (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                  UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider                 TEXT NOT NULL DEFAULT 'github' CHECK (provider IN ('github')),
    external_login           TEXT NOT NULL,
    installation_id          BIGINT NOT NULL,
    refresh_token_encrypted  BYTEA,
    scopes                   TEXT NOT NULL DEFAULT '',
    connected_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS repo_full_name  TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS repo_url        TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS repo_private    BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_pushed_sha TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS last_pushed_at  TIMESTAMPTZ;
```

Installation access tokens are **never stored** — they are minted on demand from the App's private
key (JWT → `POST /app/installations/{id}/access_tokens`), used once, and discarded.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/git/github/authorize` | Returns the GitHub install/authorize URL with a signed `state`. |
| `GET` | `/git/github/callback` | Exchanges the code, records the installation, redirects back to the project. |
| `GET` | `/git/status` | `{connected, login, installation_id, repo_count}` for Settings. |
| `DELETE` | `/git/connection` | Disconnects and deletes stored tokens. |
| `GET` | `/projects/{id}/git` | `{connected, repo_full_name, repo_url, last_pushed_sha, ahead_by}` |
| `POST` | `/projects/{id}/git/repo` | `{name, private}` → creates the repository on GitHub. |
| `POST` | `/projects/{id}/git/push` | Pushes HEAD; returns the commit pushed and the repo URL. |
| `GET` | `/projects/{id}/export` | ZIP (Part 1). |

Agent-engine: `POST /api/workspaces/{id}/git/push` with `{remote_url, token, branch}` — it runs
`git push` in the workspace repo using the token in the URL, then scrubs the remote so no token
is left in `.git/config`. `git` is already a dependency of the build path.

### Flow

```
Connect        → /git/github/authorize → GitHub install screen → callback → git_connections row
Create repo    → mint installation token → POST /user/repos (or org) → projects.repo_full_name
Push           → mint token → agent-engine push https://x-access-token:<token>@github.com/... 
               → projects.last_pushed_sha/at
Every edit     → "Push" button shows "N commits ahead"; one click pushes
Disconnect     → delete row; the repo stays in the user's account, untouched
```

### UI

Reference: Lovable's Settings → Git (`Lova-33`).

- **Manage → Git** section:
  - Not connected: explanation ("Your code is a real git repository. Connect GitHub to own it."),
    **Connect GitHub** button, and **Download .zip** as the no-account path.
  - Connected, no repo: account chip (`@login`, Disconnect), repo name input pre-filled with the
    project slug, Private/Public toggle, **Create repository**.
  - Connected with a repo: repo link, last pushed commit + time, "N commits ahead", **Push**
    button with a spinner, and a copyable `git clone` command.
- Errors are shown verbatim from GitHub (name already exists, insufficient permission, rate
  limited) — never a generic failure.
- Project header gains a small **GitHub** link once connected.

## Acceptance criteria

- [ ] Download produces a ZIP that unzips to a project that `pnpm install && pnpm build` can run.
- [ ] Connect → create repo → push results in a real repository in the user's account whose file
      tree matches the workspace and whose history has one commit per build/edit.
- [ ] A second push after an edit adds exactly one commit.
- [ ] Disconnect deletes the stored token; a push afterwards fails with a clear "reconnect" error.
- [ ] No token appears in any log, in `.git/config`, or in any response body (explicit test).
- [ ] Gates as usual; the live smoke uses a real throwaway GitHub account and is recorded honestly.

## What this unlocks

Once the code is in the user's GitHub, **Vercel and Netlify can deploy it from there on their own
free tiers** — which is why G-01 proposes exactly that as Publish v1 instead of us operating
hosting. GitHub Pages is not a candidate: it serves static files only, and these apps have a
backend and a database.
