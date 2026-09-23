-- 001_core.sql: Core users, clinics, doctor profiles, patient profiles, and family members

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  phone TEXT,
  role TEXT NOT NULL CHECK (role IN ('patient', 'doctor', 'receptionist', 'admin')),
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS clinics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  code TEXT UNIQUE NOT NULL,
  address TEXT NOT NULL,
  city TEXT NOT NULL DEFAULT 'Bengaluru',
  pincode TEXT NOT NULL DEFAULT '560038',
  phone TEXT NOT NULL,
  email TEXT NOT NULL,
  lat NUMERIC(9,6) NOT NULL DEFAULT 12.9784,
  lng NUMERIC(9,6) NOT NULL DEFAULT 77.6408,
  opening_time TIME NOT NULL DEFAULT '08:00:00',
  closing_time TIME NOT NULL DEFAULT '21:00:00',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  amenities TEXT[] DEFAULT ARRAY['Pharmacy', 'Diagnostic Lab', 'ECG', 'Wheelchair Accessible', 'Parking'],
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctor_profiles (
  doctor_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  clinic_id UUID REFERENCES clinics(id) ON DELETE SET NULL,
  license_number TEXT UNIQUE NOT NULL,
  qualification TEXT NOT NULL,
  specialties TEXT[] NOT NULL DEFAULT '{}',
  experience_years INT NOT NULL DEFAULT 5,
  consultation_fee_inr INT NOT NULL DEFAULT 700,
  video_fee_inr INT NOT NULL DEFAULT 600,
  bio TEXT,
  room_number TEXT,
  rating_avg NUMERIC(3,2) NOT NULL DEFAULT 4.90,
  rating_count INT NOT NULL DEFAULT 0,
  is_accepting_patients BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doctor_clinic ON doctor_profiles(clinic_id);

CREATE TABLE IF NOT EXISTS patient_profiles (
  patient_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  dob DATE,
  gender TEXT CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
  blood_group TEXT,
  height_cm INT,
  weight_kg NUMERIC(5,2),
  emergency_contact TEXT,
  emergency_phone TEXT,
  address TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS family_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  primary_patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  relationship TEXT NOT NULL CHECK (relationship IN ('child', 'spouse', 'parent', 'sibling', 'other')),
  dob DATE,
  gender TEXT CHECK (gender IN ('male', 'female', 'other')),
  blood_group TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_family_patient ON family_members(primary_patient_id);
