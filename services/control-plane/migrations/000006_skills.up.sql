BEGIN;

CREATE TABLE IF NOT EXISTS skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name        TEXT NOT NULL CHECK (name ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL CHECK (length(body) <= 8192),
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS skills_user_id_idx ON skills (user_id);

CREATE TABLE IF NOT EXISTS project_skills (
    project_id UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    skill_id   UUID NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, skill_id)
);

CREATE INDEX IF NOT EXISTS project_skills_project_id_idx ON project_skills (project_id);
CREATE INDEX IF NOT EXISTS project_skills_skill_id_idx ON project_skills (skill_id);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS knowledge TEXT NOT NULL DEFAULT ''
        CHECK (length(knowledge) <= 16384);

INSERT INTO schema_migrations (version) VALUES (6) ON CONFLICT (version) DO NOTHING;

COMMIT;
