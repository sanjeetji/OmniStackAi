-- 004_ledger.sql: Multi-party financial ledger, commission accounting, and vendor settlement batches

CREATE TABLE IF NOT EXISTS accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  holder_type VARCHAR(32) NOT NULL CHECK (holder_type IN ('platform', 'vendor', 'shopper')),
  holder_id UUID, -- NULL for platform, user_id or shop_id
  currency VARCHAR(8) NOT NULL DEFAULT 'INR',
  balance_cents BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_account_holder UNIQUE (holder_type, holder_id, currency)
);

CREATE INDEX IF NOT EXISTS idx_accounts_holder ON accounts(holder_type, holder_id);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  journal_id UUID NOT NULL DEFAULT gen_random_uuid(),
  debit_account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
  credit_account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  entry_type VARCHAR(32) NOT NULL CHECK (entry_type IN ('order_payment', 'commission_fee', 'vendor_credit', 'shopper_refund', 'payout_settlement')),
  reference_type VARCHAR(32) NOT NULL CHECK (reference_type IN ('order', 'shipment', 'settlement', 'return')),
  reference_id UUID NOT NULL,
  description TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ledger_journal ON ledger_entries(journal_id);
CREATE INDEX IF NOT EXISTS idx_ledger_debit ON ledger_entries(debit_account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_credit ON ledger_entries(credit_account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_ref ON ledger_entries(reference_type, reference_id);

CREATE TABLE IF NOT EXISTS settlement_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE RESTRICT,
  batch_number VARCHAR(64) NOT NULL UNIQUE,
  status VARCHAR(32) NOT NULL DEFAULT 'approved' CHECK (status IN ('draft', 'approved', 'processed')),
  gross_sales_cents BIGINT NOT NULL,
  commission_cents BIGINT NOT NULL,
  refund_deductions_cents BIGINT NOT NULL DEFAULT 0,
  net_payout_cents BIGINT NOT NULL,
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  payout_reference VARCHAR(120),
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_settlements_shop ON settlement_batches(shop_id);
CREATE INDEX IF NOT EXISTS idx_settlements_status ON settlement_batches(status);
