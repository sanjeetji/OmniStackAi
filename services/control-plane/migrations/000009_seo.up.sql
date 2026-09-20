-- 000009_seo.up.sql
-- F-07 SEO & AI search: project_seo (site-level defaults) and project_page_seo (per-page metadata)

CREATE TABLE IF NOT EXISTS project_seo (
    project_id     UUID PRIMARY KEY REFERENCES projects (id) ON DELETE CASCADE,
    site_name      TEXT NOT NULL DEFAULT '',
    default_title  TEXT NOT NULL DEFAULT '',
    description    TEXT NOT NULL DEFAULT '',
    canonical_host TEXT NOT NULL DEFAULT '',
    discourage     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_page_seo (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    route       TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    noindex     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, route)
);

CREATE INDEX IF NOT EXISTS idx_project_page_seo_project_id ON project_page_seo (project_id);
