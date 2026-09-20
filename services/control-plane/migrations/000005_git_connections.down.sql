BEGIN;

ALTER TABLE projects
    DROP COLUMN IF EXISTS repo_full_name,
    DROP COLUMN IF EXISTS repo_url,
    DROP COLUMN IF EXISTS repo_private,
    DROP COLUMN IF EXISTS last_pushed_sha,
    DROP COLUMN IF EXISTS last_pushed_at;

DROP TABLE IF EXISTS git_connections;

DELETE FROM schema_migrations WHERE version = 5;

COMMIT;
