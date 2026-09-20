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
    status        TEXT NOT NULL CHECK (status IN ('queued', 'building', 'ready', 'error', 'cancelled')),
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
