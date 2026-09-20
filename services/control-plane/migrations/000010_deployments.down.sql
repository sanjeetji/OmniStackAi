ALTER TABLE projects
    DROP COLUMN IF EXISTS live_url,
    DROP COLUMN IF EXISTS deploy_external_id,
    DROP COLUMN IF EXISTS deploy_provider;

DROP INDEX IF EXISTS deployments_project_idx;
DROP TABLE IF EXISTS deployments;
DROP TABLE IF EXISTS deploy_connections;
