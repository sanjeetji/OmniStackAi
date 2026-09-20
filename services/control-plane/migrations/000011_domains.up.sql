-- migrations/000011_domains.up.sql
-- G-02 (R-510) Custom Domain: Bring Your Own

CREATE TABLE IF NOT EXISTS project_domains (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id         UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    hostname           TEXT NOT NULL UNIQUE,
    provider           TEXT NOT NULL,
    record_type        TEXT NOT NULL DEFAULT 'CNAME',
    record_name        TEXT NOT NULL DEFAULT '',
    record_value       TEXT NOT NULL DEFAULT '',
    status             TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','verifying','verified','failed','removed')),
    tls_status         TEXT NOT NULL DEFAULT 'pending',
    is_primary         BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at    TIMESTAMPTZ,
    verified_at        TIMESTAMPTZ,
    error              TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_domains_project_id ON project_domains (project_id);
CREATE INDEX IF NOT EXISTS idx_project_domains_hostname ON project_domains (hostname);
