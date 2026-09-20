BEGIN;

DROP TABLE IF EXISTS project_skills;
DROP TABLE IF EXISTS skills;

ALTER TABLE projects
    DROP COLUMN IF EXISTS knowledge;

DELETE FROM schema_migrations WHERE version = 6;

COMMIT;
