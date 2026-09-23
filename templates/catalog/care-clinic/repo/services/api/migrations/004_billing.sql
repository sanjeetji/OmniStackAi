-- 004_billing.sql: Clinic invoices, consultation fee payments, and cancellation refunds

CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_number TEXT UNIQUE NOT NULL,
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
  total_amount INT NOT NULL,
  discount_amount INT NOT NULL DEFAULT 0,
  tax_amount INT NOT NULL DEFAULT 0,
  net_payable INT NOT NULL,
  payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'refunded', 'partially_refunded')),
  payment_method TEXT CHECK (payment_method IN ('card', 'upi', 'cash', 'insurance', 'netbanking')),
  transaction_ref TEXT,
  paid_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_patient ON invoices(patient_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(payment_status);

CREATE TABLE IF NOT EXISTS invoice_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  item_type TEXT NOT NULL CHECK (item_type IN ('consultation_fee', 'video_fee', 'lab_test', 'procedure', 'pharmacy')),
  quantity INT NOT NULL DEFAULT 1,
  unit_price INT NOT NULL,
  amount INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inv_items ON invoice_items(invoice_id);

CREATE TABLE IF NOT EXISTS refunds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  refund_number TEXT UNIQUE NOT NULL,
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
  amount INT NOT NULL,
  cancellation_fee INT NOT NULL DEFAULT 0,
  reason TEXT NOT NULL,
  refund_status TEXT NOT NULL DEFAULT 'processed' CHECK (refund_status IN ('pending', 'processed', 'failed')),
  refund_method TEXT NOT NULL DEFAULT 'original_source',
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refunds_invoice ON refunds(invoice_id);
