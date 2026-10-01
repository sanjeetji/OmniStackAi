-- PC-115: R-512's payments toggle is gone. An app's payments come from its plan (R-567) and its
-- keys from the project's secrets.
ALTER TABLE projects DROP COLUMN IF EXISTS payment_gateway;
