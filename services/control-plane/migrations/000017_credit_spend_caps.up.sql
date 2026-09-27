-- PC-010: spending caps sum the ledger by time, per user and for the whole platform.
CREATE INDEX IF NOT EXISTS credit_ledger_created_at_idx ON credit_ledger (created_at);
CREATE INDEX IF NOT EXISTS credit_ledger_user_created_at_idx ON credit_ledger (user_id, created_at);
