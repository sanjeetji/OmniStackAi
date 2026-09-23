-- 006_platform_revenue.sql: separate the platform's escrow cash from its earned commission.
--
-- accounts is unique on (holder_type, holder_id, currency), and both the cash account and the
-- revenue account were created as holder_type 'platform' with a NULL holder_id — so they were the
-- same row, and commission earned could never be told apart from money held for vendors.

ALTER TABLE accounts DROP CONSTRAINT IF EXISTS accounts_holder_type_check;

ALTER TABLE accounts
  ADD CONSTRAINT accounts_holder_type_check
  CHECK (holder_type IN ('platform', 'platform_revenue', 'vendor', 'shopper'));
