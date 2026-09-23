-- 005_audit_telehealth.sql: Telehealth sessions, HIPAA chart access audit logs, reviews, and notifications

CREATE TABLE IF NOT EXISTS telehealth_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appointment_id UUID UNIQUE NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
  room_token TEXT UNIQUE NOT NULL,
  doctor_joined_at TIMESTAMPTZ,
  patient_joined_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'active', 'ended')),
  call_duration_seconds INT NOT NULL DEFAULT 0,
  connection_quality TEXT DEFAULT 'good' CHECK (connection_quality IN ('excellent', 'good', 'fair', 'poor')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chart_access_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  accessed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  access_type TEXT NOT NULL CHECK (access_type IN ('view_chart', 'view_soap', 'view_prescription', 'edit_soap', 'issue_prescription', 'view_labs', 'order_labs')),
  resource_id TEXT,
  ip_address TEXT DEFAULT '127.0.0.1',
  user_agent TEXT,
  accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chart_audit_patient ON chart_access_logs(patient_id, accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_chart_audit_actor ON chart_access_logs(accessed_by_user_id, accessed_at DESC);

CREATE TABLE IF NOT EXISTS patient_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  appointment_id UUID UNIQUE REFERENCES appointments(id) ON DELETE SET NULL,
  rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  feedback TEXT NOT NULL,
  is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_doctor ON patient_reviews(doctor_id);

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('appointment_booked', 'appointment_confirmed', 'token_called', 'consultation_started', 'prescription_ready', 'lab_results_ready', 'payment_received', 'appointment_cancelled')),
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  link TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);
