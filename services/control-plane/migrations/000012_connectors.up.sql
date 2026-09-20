-- migrations/000012_connectors.up.sql
-- G-03 (R-511) Connectors v1

CREATE TABLE IF NOT EXISTS connector_accounts (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                  UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider                 TEXT NOT NULL,
    external_account         TEXT NOT NULL DEFAULT '',
    refresh_token_ciphertext BYTEA,
    scopes                   TEXT NOT NULL DEFAULT '',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider, external_account)
);

CREATE TABLE IF NOT EXISTS project_connectors (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id           UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    provider             TEXT NOT NULL,
    connector_account_id UUID REFERENCES connector_accounts (id) ON DELETE SET NULL,
    config               JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_connector_accounts_user_provider ON connector_accounts (user_id, provider);
CREATE INDEX IF NOT EXISTS idx_project_connectors_project_id ON project_connectors (project_id);
