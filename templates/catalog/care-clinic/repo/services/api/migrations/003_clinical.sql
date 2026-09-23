-- 003_clinical.sql: Medical history, vitals, SOAP consultations, ICD-10 diagnoses, e-prescriptions, and lab investigations

CREATE TABLE IF NOT EXISTS medical_histories (
  patient_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  allergies TEXT[] NOT NULL DEFAULT '{}',
  chronic_conditions TEXT[] NOT NULL DEFAULT '{}',
  current_medications TEXT[] NOT NULL DEFAULT '{}',
  past_surgeries TEXT[] NOT NULL DEFAULT '{}',
  family_history TEXT,
  lifestyle_notes TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vitals_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
  recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  bp_systolic INT,
  bp_diastolic INT,
  heart_rate INT,
  temperature_f NUMERIC(4,1),
  spo2_percent INT,
  respiratory_rate INT,
  blood_glucose_mg_dl INT,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_vitals_patient ON vitals_records(patient_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS consultations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appointment_id UUID UNIQUE NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  subjective TEXT, -- Chief complaint & history of present illness
  objective TEXT,  -- Physical examination & clinical observations
  assessment TEXT, -- Clinical diagnosis summary & interpretation
  plan TEXT,       -- Treatment advice, diet, lifestyle, investigations
  follow_up_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consultations_patient ON consultations(patient_id);
CREATE INDEX IF NOT EXISTS idx_consultations_doctor ON consultations(doctor_id);

CREATE TABLE IF NOT EXISTS diagnoses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  consultation_id UUID NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
  icd10_code TEXT NOT NULL,
  condition_name TEXT NOT NULL,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_diagnoses_consultation ON diagnoses(consultation_id);

CREATE TABLE IF NOT EXISTS prescriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prescription_number TEXT UNIQUE NOT NULL,
  consultation_id UUID UNIQUE NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  diagnosis_summary TEXT NOT NULL,
  signed_at TIMESTAMPTZ,
  is_immutable BOOLEAN NOT NULL DEFAULT FALSE,
  digital_signature TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id);

CREATE TABLE IF NOT EXISTS prescription_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
  medicine_name TEXT NOT NULL,
  generic_name TEXT,
  dosage_form TEXT NOT NULL CHECK (dosage_form IN ('tablet', 'capsule', 'syrup', 'injection', 'inhaler', 'drops', 'ointment')),
  strength TEXT NOT NULL,
  frequency TEXT NOT NULL, -- e.g. "1-0-1", "0-0-1", "1-1-1"
  timing TEXT NOT NULL CHECK (timing IN ('after_food', 'before_food', 'with_food', 'empty_stomach', 'as_needed')),
  duration_days INT NOT NULL DEFAULT 5,
  instructions TEXT
);

CREATE INDEX IF NOT EXISTS idx_rx_items_rx ON prescription_items(prescription_id);

CREATE TABLE IF NOT EXISTS lab_test_catalog (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('hematology', 'biochemistry', 'cardiology', 'radiology', 'microbiology', 'endocrinology')),
  standard_fee_inr INT NOT NULL DEFAULT 500,
  turnaround_hours INT NOT NULL DEFAULT 24,
  sample_type TEXT NOT NULL DEFAULT 'Blood',
  fasting_required BOOLEAN NOT NULL DEFAULT FALSE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS lab_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_number TEXT UNIQUE NOT NULL,
  consultation_id UUID REFERENCES consultations(id) ON DELETE SET NULL,
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'ordered' CHECK (status IN ('ordered', 'sample_collected', 'processing', 'completed', 'cancelled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_lab_orders_patient ON lab_orders(patient_id);

CREATE TABLE IF NOT EXISTS lab_order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lab_order_id UUID NOT NULL REFERENCES lab_orders(id) ON DELETE CASCADE,
  test_id UUID NOT NULL REFERENCES lab_test_catalog(id) ON DELETE CASCADE,
  result_value TEXT,
  reference_range TEXT,
  unit TEXT,
  flag TEXT NOT NULL DEFAULT 'normal' CHECK (flag IN ('normal', 'high', 'low', 'critical')),
  technician_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lab_items_order ON lab_order_items(lab_order_id);
