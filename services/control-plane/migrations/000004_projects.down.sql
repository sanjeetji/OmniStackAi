BEGIN;

DROP INDEX IF EXISTS credit_ledger_project_id_idx;

ALTER TABLE credit_ledger
    DROP COLUMN IF EXISTS project_id;

DROP TABLE IF EXISTS projects;

DELETE FROM schema_migrations WHERE version = 4;

COMMIT;
