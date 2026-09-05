BEGIN;

DELETE FROM schema_migrations WHERE version = 1;
DROP TABLE IF EXISTS schema_migrations;
DROP EXTENSION IF EXISTS vector;

COMMIT;
