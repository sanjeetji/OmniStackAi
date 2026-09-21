BEGIN;

-- R-519 (Phase T, T-1): which template a project was started from. A separate table keeps every
-- existing projects query unchanged. The row is written once, when "use template" succeeds, and
-- records the exact original (slug, version, content digest) the user's copy began as.
CREATE TABLE IF NOT EXISTS project_templates (
    project_id       UUID PRIMARY KEY REFERENCES projects (id) ON DELETE CASCADE,
    template_slug    TEXT NOT NULL,
    template_version TEXT NOT NULL,
    template_digest  TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_templates_slug_idx ON project_templates (template_slug);

INSERT INTO schema_migrations (version) VALUES (16) ON CONFLICT (version) DO NOTHING;

COMMIT;
