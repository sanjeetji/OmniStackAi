-- 006_icd10.sql: the ICD-10 subset the diagnosis picker searches.
-- The codes a general multi-specialty clinic actually reaches for; the doctor's SOAP screen
-- searches this table rather than shipping a list inside the app.

CREATE TABLE IF NOT EXISTS icd10_catalog (
  code TEXT PRIMARY KEY,
  condition_name TEXT NOT NULL,
  chapter TEXT NOT NULL,
  specialty TEXT,
  is_common BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_icd10_name ON icd10_catalog (LOWER(condition_name));
CREATE INDEX IF NOT EXISTS idx_icd10_specialty ON icd10_catalog (specialty);
