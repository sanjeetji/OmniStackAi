BEGIN;

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

CREATE INDEX IF NOT EXISTS git_connections_user_id_idx ON git_connections (user_id);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS repo_full_name  TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS repo_url        TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS repo_private    BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_pushed_sha TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS last_pushed_at  TIMESTAMPTZ;

INSERT INTO schema_migrations (version) VALUES (5) ON CONFLICT (version) DO NOTHING;

COMMIT;
