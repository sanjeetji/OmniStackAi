BEGIN;

DELETE FROM schema_migrations WHERE version = 3;
ALTER TABLE users DROP COLUMN IF EXISTS full_name;

COMMIT;
