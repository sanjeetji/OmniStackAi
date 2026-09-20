-- migrations/000008_ai_usage.down.sql
ALTER TABLE projects
    DROP COLUMN IF EXISTS model_provider_id,
    DROP COLUMN IF EXISTS model_id;

DROP TABLE IF EXISTS model_calls;
DROP TABLE IF EXISTS user_provider_keys;
