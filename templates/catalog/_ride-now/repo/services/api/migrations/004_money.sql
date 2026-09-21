-- RideNow money: wallets with a signed ledger, payment intents (mock provider), payouts.
CREATE TABLE wallets (
    user_id     UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    balance     NUMERIC(12,2) NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every money movement is one row; the platform's commission is booked against the admin
-- "platform" user so the ledger always balances per trip.
CREATE TABLE wallet_transactions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    trip_id        UUID REFERENCES trips (id),
    kind           TEXT NOT NULL CHECK (kind IN (
                       'topup', 'trip_payment', 'trip_earning', 'commission', 'cash_commission',
                       'refund', 'payout', 'adjustment')),
    amount         NUMERIC(12,2) NOT NULL,
    balance_after  NUMERIC(12,2) NOT NULL,
    reference      TEXT NOT NULL DEFAULT '',
    note           TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX wallet_tx_user_idx ON wallet_transactions (user_id, created_at DESC);
CREATE INDEX wallet_tx_trip_idx ON wallet_transactions (trip_id);

CREATE TABLE payment_intents (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    amount         NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    provider       TEXT NOT NULL DEFAULT 'mock',
    status         TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'succeeded', 'failed')),
    card_last4     TEXT NOT NULL DEFAULT '',
    failure_reason TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at   TIMESTAMPTZ
);

CREATE TABLE payouts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id     UUID NOT NULL REFERENCES drivers (user_id) ON DELETE CASCADE,
    amount        NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    status        TEXT NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'paid', 'rejected')),
    bank_last4    TEXT NOT NULL DEFAULT '',
    reference     TEXT NOT NULL DEFAULT '',
    requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at  TIMESTAMPTZ
);
CREATE INDEX payouts_status_idx ON payouts (status, requested_at DESC);
