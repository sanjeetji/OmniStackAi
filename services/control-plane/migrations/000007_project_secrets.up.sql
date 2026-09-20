CREATE TABLE IF NOT EXISTS project_secrets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    key              TEXT NOT NULL CHECK (key ~ '^[A-Z][A-Z0-9_]*$'),
    value_ciphertext BYTEA NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at     TIMESTAMPTZ,
    UNIQUE (project_id, key)
);

CREATE INDEX IF NOT EXISTS idx_project_secrets_project_id ON project_secrets (project_id);
