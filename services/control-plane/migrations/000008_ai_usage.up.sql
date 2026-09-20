-- migrations/000008_ai_usage.up.sql
CREATE TABLE IF NOT EXISTS user_provider_keys (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider_id    TEXT NOT NULL,
    key_ciphertext BYTEA NOT NULL,
    label          TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at   TIMESTAMPTZ,
    UNIQUE (user_id, provider_id)
);

CREATE TABLE IF NOT EXISTS model_calls (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    project_id       UUID REFERENCES projects (id) ON DELETE SET NULL,
    provider_id      TEXT NOT NULL,
    model_id         TEXT NOT NULL,
    tier             TEXT NOT NULL CHECK (tier IN ('local', 'cloud')),
    purpose          TEXT NOT NULL DEFAULT 'build',
    input_tokens     BIGINT NOT NULL DEFAULT 0,
    output_tokens    BIGINT NOT NULL DEFAULT 0,
    cost_micros_usd  BIGINT NOT NULL DEFAULT 0,
    credits_spent    BIGINT NOT NULL DEFAULT 0,
    billed_to        TEXT NOT NULL CHECK (billed_to IN ('platform', 'byok', 'local')),
    success          BOOLEAN NOT NULL DEFAULT TRUE,
    error_code       TEXT NOT NULL DEFAULT '',
    latency_ms       INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS model_calls_user_created_idx    ON model_calls (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS model_calls_project_created_idx ON model_calls (project_id, created_at DESC);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS model_provider_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS model_id          TEXT NOT NULL DEFAULT '';
