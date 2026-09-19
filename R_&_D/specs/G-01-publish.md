# G-01 · Publish (proposed Tracker ID: R-509)

**Status:** specified, **GATED — needs the founder to choose a hosting model.**
**Depends on:** F-01, F-03 (GitHub), F-05 (secrets as deployment env).

## The decision you need to make

| Option | What the user does | What it costs us | What we must operate |
| --- | --- | --- | --- |
| **A. Deploy from their GitHub to their own Vercel/Netlify** *(recommended v1)* | Connects GitHub (F-03), then connects Vercel or Netlify with a personal token; we create the project there and trigger deploys. | **₹0.** Their account, their free tier, their limits. | Nothing. We call two well-documented APIs. |
| **B. Managed hosting we run** | Clicks Publish; we deploy to infrastructure we pay for. | Real money per app: web host + backend host + Postgres, growing with every user, including abandoned projects. | On-call infrastructure, quotas, abuse handling, a billing system to recover cost. |
| **C. Static export only** | Publish to GitHub Pages / Cloudflare Pages. | ₹0. | Nothing — but **only works for apps with no backend and no database**, which is not what we generate. |

**Recommendation: A now, B later behind paid plans.** It delivers "my app is live on the internet"
this month with no infrastructure and no bill, and it composes with F-03: the code is already in
their GitHub, and Vercel/Netlify deploy from GitHub natively. B becomes attractive only once
platform billing exists (Phase E of the kickoff doc) and we can charge for what we spend.

Everything below specifies **A**. If you pick B, the UI and data model stay the same and only the
deployment driver changes — the abstraction below is deliberately provider-shaped.

---

## Design (option A)

### Providers

A `DeployProvider` interface with two implementations, mirroring how the sandbox providers were
built in R-486…R-490:

```
create_project(repo_full_name, framework, env) -> external_id
trigger_deploy(external_id, commit_sha)        -> deployment_id
get_deployment(deployment_id)                  -> {status, url, log_url, error}
set_env(external_id, secrets)                  -> ()
attach_domain(external_id, hostname)           -> {cname_target, status}   # used by G-02
```

- **Vercel**: `POST /v10/projects`, `POST /v13/deployments`, `GET /v13/deployments/{id}`,
  `POST /v10/projects/{id}/env`. Auth: the user's personal access token.
- **Netlify**: `POST /api/v1/sites`, build hooks, `GET /api/v1/sites/{id}/deploys/{id}`.
- Tokens are stored with F-05's encryption, per user, and are revocable from Settings.

### The backend problem, stated honestly

Our generated apps are **web + backend + PostgreSQL**. Vercel and Netlify host the web app
natively; the Python/Go backend and the database are not theirs to run. So Publish v1 has three
honest paths, chosen per project and shown plainly in the UI:

1. **Web-only app** (no entities/backend): deploys completely. Nothing missing.
2. **Web + backend**: the web app deploys; the backend needs a host. v1 shows the exact
   `render.yaml` / `fly.toml` we generate and a "Deploy the backend" link with the user's own
   account. We do not pretend the API is live when it is not.
3. **Needs a database**: the user supplies a PostgreSQL URL (Neon/Supabase free tier, or their
   own) as a project secret; we run the generated migrations against it from the publish step.

The UI states which path a project is on **before** the first publish, so nobody is surprised.

### Database

```sql
-- migrations/000010_deployments.up.sql
CREATE TABLE IF NOT EXISTS deploy_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider        TEXT NOT NULL CHECK (provider IN ('vercel', 'netlify')),
    token_ciphertext BYTEA NOT NULL,
    account_label   TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);

CREATE TABLE IF NOT EXISTS deployments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    provider      TEXT NOT NULL,
    external_id   TEXT NOT NULL DEFAULT '',
    commit_sha    TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL CHECK (status IN ('queued','building','ready','error','cancelled')),
    url           TEXT NOT NULL DEFAULT '',
    error         TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS deployments_project_idx ON deployments (project_id, created_at DESC);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS deploy_provider    TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS deploy_external_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS live_url           TEXT NOT NULL DEFAULT '';
```

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET`/`PUT`/`DELETE` | `/deploy/connections/{provider}` | The user's hosting token. |
| `GET` | `/projects/{id}/publish` | Readiness: which path (1/2/3), what is missing, last deployment. |
| `POST` | `/projects/{id}/publish` | Creates the provider project if needed, pushes env from secrets, triggers a deploy. |
| `GET` | `/projects/{id}/deployments` | History. |
| `GET` | `/projects/{id}/deployments/{depId}` | Status + log URL; polled while building. |

### UI

Reference: Lovable's Publish flow and Dyad's Publish tab (`Dyad-04`).

- **Project header**: a **Publish** button (primary once a build exists).
- **Publish dialog**: shows the path this project is on with a plain sentence; provider choice
  (Vercel/Netlify) with Connect if absent; environment variables pulled from Secrets with a
  warning for any the app reads but that are unset; **Publish** action.
- **Manage → Publish**: live URL with copy + open, last deploy status and time, a deployment
  history table (commit, status, duration, link), **Redeploy**, and the backend/database guidance
  for paths 2 and 3.
- While deploying: a progress row with the provider's real status, never a fake progress bar.

## Acceptance criteria

- [ ] A web-only generated app publishes to a real URL from the user's own account, and the URL
      serves the app.
- [ ] Secrets reach the deployment as environment variables; none are logged.
- [ ] Paths 2 and 3 state exactly what is missing before publishing; nothing claims to be live
      when it is not.
- [ ] Deployment history shows real provider statuses, including a genuine failure with its error.
- [ ] Disconnecting the provider deletes the token and disables Publish with a clear message.
- [ ] Gates as usual; live evidence uses a real throwaway Vercel or Netlify account.

## Open questions for the founder

1. **Option A or B?** (Recommendation: A.)
2. Vercel first, Netlify first, or both in the same task? (Recommendation: Vercel first — better
   Next.js support and a simpler API.)
3. For path 3, is "bring your own PostgreSQL URL" acceptable for v1? (Recommendation: yes, with
   a Neon/Supabase free-tier walkthrough in the UI.)
