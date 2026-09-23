-- 002_scheduling.sql: Doctor availability rules, schedule overrides, and appointments

CREATE TABLE IF NOT EXISTS doctor_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Sunday, 6=Saturday
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  slot_duration_mins INT NOT NULL DEFAULT 20,
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT check_time_order CHECK (start_time < end_time)
);

CREATE INDEX IF NOT EXISTS idx_doc_avail ON doctor_availability(doctor_id, day_of_week);

CREATE TABLE IF NOT EXISTS schedule_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  is_leave BOOLEAN NOT NULL DEFAULT FALSE,
  custom_start_time TIME,
  custom_end_time TIME,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sched_override ON schedule_overrides(doctor_id, date);

CREATE TABLE IF NOT EXISTS appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appointment_number TEXT UNIQUE NOT NULL,
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  for_family_member_id UUID REFERENCES family_members(id) ON DELETE SET NULL,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  clinic_id UUID REFERENCES clinics(id) ON DELETE SET NULL,
  appointment_type TEXT NOT NULL CHECK (appointment_type IN ('in_clinic', 'video')),
  scheduled_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  status TEXT NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'checked_in', 'in_consult', 'completed', 'cancelled', 'no_show')),
  token_number INT,
  queue_status TEXT DEFAULT 'waiting' CHECK (queue_status IN ('waiting', 'called', 'with_doctor', 'done', 'cancelled')),
  fee_amount INT NOT NULL DEFAULT 700,
  is_paid BOOLEAN NOT NULL DEFAULT FALSE,
  payment_method TEXT,
  cancellation_reason TEXT,
  cancelled_by TEXT,
  cancelled_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- Absolute double-booking prevention at DB engine level:
  CONSTRAINT uq_doctor_slot UNIQUE (doctor_id, scheduled_date, start_time)
);

CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date ON appointments(doctor_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
