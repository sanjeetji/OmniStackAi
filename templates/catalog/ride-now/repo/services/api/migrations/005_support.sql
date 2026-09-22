-- RideNow support and governance: tickets with threads, admin audit log.
CREATE SEQUENCE ticket_code_seq START 5001;

CREATE TABLE support_tickets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT NOT NULL UNIQUE DEFAULT ('T-' || nextval('ticket_code_seq')),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    trip_id     UUID REFERENCES trips (id),
    category    TEXT NOT NULL CHECK (category IN ('payment', 'safety', 'lost_item', 'driver', 'app', 'other')),
    subject     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'pending', 'resolved')),
    priority    TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX tickets_status_idx ON support_tickets (status, updated_at DESC);

CREATE TABLE ticket_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id   UUID NOT NULL REFERENCES support_tickets (id) ON DELETE CASCADE,
    author_id   UUID NOT NULL REFERENCES users (id),
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ticket_messages_idx ON ticket_messages (ticket_id, created_at);

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    actor_id    UUID REFERENCES users (id),
    action      TEXT NOT NULL,
    entity      TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_at_idx ON audit_log (at DESC);
