-- PC-013: the last health test of every connected integration, per project or per account.
CREATE TABLE IF NOT EXISTS integration_checks (
    owner_kind  TEXT NOT NULL CHECK (owner_kind IN ('project', 'user')),
    owner_id    UUID NOT NULL,
    integration TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'unchecked')),
    message     TEXT NOT NULL DEFAULT '',
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_kind, owner_id, integration)
);
