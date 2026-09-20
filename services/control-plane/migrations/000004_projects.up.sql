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
