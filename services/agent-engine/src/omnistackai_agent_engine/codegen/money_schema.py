"""R-567: the money tables every backend shares - one schema, so Python, Go and Node agree.

Amounts are integers in the currency's minor unit. A balance is never stored: it is the sum of an
account's ledger entries (credits minus debits), so the books balance by construction.
"""

from __future__ import annotations

MONEY_SCHEMA = """\
-- R-567: money. Integer minor units (paise, cents); balances are ledger sums, never stored.
CREATE TABLE IF NOT EXISTS "money_account" (
    "id"         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "kind"       VARCHAR NOT NULL CHECK ("kind" IN ('external', 'escrow', 'revenue', 'user')),
    "holder_id"  UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- One account per kind and holder (the platform's three have no holder).
CREATE UNIQUE INDEX IF NOT EXISTS "uq_money_account_holder"
    ON "money_account" ("kind", COALESCE("holder_id", '00000000-0000-0000-0000-000000000000'::uuid));
INSERT INTO "money_account" ("kind") VALUES ('external'), ('escrow'), ('revenue') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS "payment" (
    "id"           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "entity"       VARCHAR NOT NULL,
    "record_id"    UUID NOT NULL,
    "payer_id"     UUID,
    "payee_id"     UUID,
    "amount"       BIGINT NOT NULL CHECK ("amount" > 0),
    "commission"   BIGINT NOT NULL DEFAULT 0 CHECK ("commission" >= 0 AND "commission" <= "amount"),
    "currency"     CHAR(3) NOT NULL,
    "status"       VARCHAR NOT NULL DEFAULT 'created' CHECK ("status" IN ('created', 'succeeded', 'failed')),
    "refunded"     BIGINT NOT NULL DEFAULT 0 CHECK ("refunded" >= 0 AND "refunded" <= "amount"),
    "provider"     VARCHAR NOT NULL,
    "provider_ref" VARCHAR UNIQUE,
    "created_at"   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at"   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- A record is paid once.
CREATE UNIQUE INDEX IF NOT EXISTS "uq_payment_paid_once" ON "payment" ("entity", "record_id") WHERE "status" = 'succeeded';
CREATE INDEX IF NOT EXISTS "idx_payment_record" ON "payment" ("entity", "record_id");

CREATE TABLE IF NOT EXISTS "payout" (
    "id"         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "holder_id"  UUID NOT NULL,
    "amount"     BIGINT NOT NULL CHECK ("amount" > 0),
    "status"     VARCHAR NOT NULL DEFAULT 'requested' CHECK ("status" IN ('requested', 'paid', 'rejected')),
    "reference"  VARCHAR,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "decided_at" TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS "ledger_entry" (
    "id"         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "debit"      UUID NOT NULL REFERENCES "money_account" ("id"),
    "credit"     UUID NOT NULL REFERENCES "money_account" ("id"),
    "amount"     BIGINT NOT NULL CHECK ("amount" > 0),
    "kind"       VARCHAR NOT NULL CHECK ("kind" IN ('payment', 'sale', 'commission', 'refund', 'payout')),
    "payment_id" UUID REFERENCES "payment" ("id"),
    "payout_id"  UUID REFERENCES "payout" ("id"),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ("debit" <> "credit")
);
CREATE INDEX IF NOT EXISTS "idx_ledger_debit" ON "ledger_entry" ("debit");
CREATE INDEX IF NOT EXISTS "idx_ledger_credit" ON "ledger_entry" ("credit");

-- A provider retries webhooks; each event is acted on once.
CREATE TABLE IF NOT EXISTS "processed_event" (
    "provider"   VARCHAR NOT NULL,
    "event_id"   VARCHAR NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("provider", "event_id")
);"""
