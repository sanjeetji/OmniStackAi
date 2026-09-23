/**
 * Canonical domain types for CareClinic: Clinical Care & Practice Management Platform.
 */

export type UserRole = "patient" | "doctor" | "receptionist" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: UserRole;
  avatar_url?: string | null;
  created_at?: string;
}

export interface Clinic {
  id: string;
  name: string;
  slug: string;
  code?: string;
  lat?: number;
  lng?: number;
  tagline?: string | null;
  phone: string;
  email: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  opening_time?: string;
  closing_time?: string;
  is_active: boolean;
}

export interface DoctorProfile {
  id?: string;
  doctor_id: string;
  clinic_id?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  avatar_url?: string;
  license_number: string;
  qualification: string;
  specialties: string[];
  experience_years: number;
  consultation_fee_inr: number;
  video_fee_inr: number;
  bio?: string | null;
  room_number?: string | null;
  rating_avg: number;
  rating_count: number;
  is_accepting_patients: boolean;
  clinic_name?: string;
  clinic_address?: string;
  clinic_city?: string;
  clinic_phone?: string;
}

export interface DoctorShift {
  id?: string;
  doctor_id?: string;
  day_of_week: number; // 0=Sunday, 1=Monday ... 6=Saturday
  start_time: string;
  end_time: string;
  slot_duration_mins: number;
  is_available: boolean;
}

export interface PatientProfile {
  id?: string;
  patient_id: string;
  dob?: string | null;
  gender?: "male" | "female" | "other" | null;
  blood_group?: string | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  emergency_contact?: string | null;
  emergency_phone?: string | null;
  address?: string | null;
}

export interface FamilyMember {
  id: string;
  primary_patient_id: string;
  full_name: string;
  relationship: string;
  dob?: string | null;
  gender?: string | null;
  blood_group?: string | null;
  created_at?: string;
}

export type AppointmentType = "in_clinic" | "video";
export type AppointmentStatus = "booked" | "checked_in" | "in_consult" | "completed" | "cancelled" | "no_show";

export interface Appointment {
  id: string;
  appointment_number: string;
  patient_id: string;
  doctor_id: string;
  clinic_id?: string;
  for_family_member_id?: string | null;
  appointment_type: AppointmentType;
  scheduled_date: string;
  start_time: string;
  end_time: string;
  status: AppointmentStatus;
  token_number?: number | null;
  queue_status?: string | null;
  /** Rupees. The column is appointments.fee_amount. */
  fee_amount: number;
  is_paid: boolean;
  payment_method?: string | null;
  notes?: string | null;
  cancellation_reason?: string | null;
  cancelled_by?: string | null;
  cancelled_at?: string | null;
  created_at: string;
  updated_at?: string;
  // Joined fields
  doctor_name?: string;
  doctor_avatar?: string;
  qualification?: string;
  specialties?: string[];
  room_number?: string;
  license_number?: string;
  clinic_name?: string;
  clinic_address?: string;
  clinic_phone?: string;
  family_member_name?: string;
  family_member_rel?: string;
  invoice_id?: string;
  invoice_number?: string;
  net_payable?: number;
  consultation_id?: string;
  prescription_id?: string;
  prescription_number?: string;
  telehealth_room_token?: string;
  telehealth_status?: string;
}

export interface AvailableSlot {
  startTime: string;
  endTime: string;
  label: string;
  available: boolean;
}

export interface MedicalHistory {
  id?: string;
  patient_id: string;
  allergies: string[];
  chronic_conditions: string[];
  current_medications: string[];
  past_surgeries: string[];
  family_history?: string | null;
  lifestyle_notes?: string | null;
  updated_at?: string;
}

export interface VitalsRecord {
  id: string;
  patient_id: string;
  recorded_by?: string;
  recorded_by_name?: string;
  appointment_id?: string;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  heart_rate?: number | null;
  temperature_f?: number | null;
  spo2_percent?: number | null;
  blood_glucose_mg_dl?: number | null;
  notes?: string | null;
  recorded_at: string;
}

export interface Consultation {
  id: string;
  appointment_id: string;
  doctor_id: string;
  patient_id: string;
  subjective?: string | null; // Chief complaints & history
  objective?: string | null;  // Physical exam & vitals
  assessment?: string | null; // Clinical impression
  plan?: string | null;       // Treatment plan & lifestyle advice
  started_at: string;
  ended_at?: string | null;
}

export interface Diagnosis {
  id: string;
  consultation_id: string;
  icd10_code: string;
  icd10_description: string;
  is_primary: boolean;
  notes?: string | null;
}

export interface PrescriptionItem {
  id?: string;
  prescription_id?: string;
  medication_name: string;
  dosage: string;
  form: string; // tablet, syrup, injection, ointment, drops
  route: string; // oral, topical, iv, inhalation
  frequency: string; // once daily, twice daily, tds, qid, sos
  duration_days: number;
  timing: string; // before food, after food, with meals
  instructions?: string | null;
}

export interface Prescription {
  id: string;
  prescription_number: string;
  consultation_id: string;
  patient_id: string;
  doctor_id: string;
  notes?: string | null;
  is_immutable: boolean;
  digital_signature?: string | null;
  signed_at?: string | null;
  created_at: string;
  doctor_name?: string;
  qualification?: string;
  specialties?: string[];
  license_number?: string;
  clinic_name?: string;
  clinic_address?: string;
  clinic_phone?: string;
  appointment_number?: string;
  scheduled_date?: string;
  subjective?: string;
  assessment?: string;
  plan?: string;
  items?: PrescriptionItem[];
}

export interface LabTest {
  id: string;
  code: string;
  name: string;
  category: string;
  description?: string;
  standard_fee_inr: number;
  turnaround_hours: number;
  sample_type: string;
}

export interface LabOrderItem {
  id: string;
  lab_order_id: string;
  test_id: string;
  test_name?: string;
  category?: string;
  standard_fee_inr?: number;
  result_value?: string | null;
  reference_range?: string | null;
  unit?: string | null;
  flag: "normal" | "high" | "low" | "critical";
  technician_notes?: string | null;
}

export interface LabOrder {
  id: string;
  order_number: string;
  consultation_id?: string;
  patient_id: string;
  doctor_id: string;
  doctor_name?: string;
  status: "ordered" | "sample_collected" | "processing" | "completed" | "cancelled";
  created_at: string;
  completed_at?: string | null;
  items?: LabOrderItem[];
}

export interface InvoiceItem {
  id: string;
  invoice_id: string;
  item_type: "consultation_fee" | "video_fee" | "lab_test" | "procedure" | "pharmacy";
  description: string;
  quantity: number;
  unit_price: number;
  /** Rupees. The column is invoice_items.amount. */
  amount: number;
}

export type PaymentStatus = "pending" | "paid" | "refunded" | "partially_refunded";

export interface Invoice {
  id: string;
  invoice_number: string;
  patient_id: string;
  clinic_id?: string;
  appointment_id?: string;
  total_amount: number;
  discount_amount: number;
  tax_amount: number;
  net_payable: number;
  payment_status: PaymentStatus;
  payment_method?: string | null;
  transaction_ref?: string | null;
  paid_at?: string | null;
  notes?: string | null;
  created_at: string;
  appointment_number?: string;
  scheduled_date?: string;
  doctor_name?: string;
  items?: InvoiceItem[];
}

export interface TelehealthSession {
  id: string;
  appointment_id: string;
  room_token: string;
  status: "scheduled" | "active" | "completed" | "abandoned";
  doctor_joined_at?: string | null;
  patient_joined_at?: string | null;
  ended_at?: string | null;
  duration_seconds?: number;
}

export interface PatientReview {
  id: string;
  patient_id: string;
  doctor_id: string;
  appointment_id?: string | null;
  patient_name?: string;
  rating: number; // 1-5
  feedback: string;
  is_anonymous: boolean;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  link_url?: string;
  is_read: boolean;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  access_token: string;
}

// --- Clinic operations console -------------------------------------------------------------------
// The rows below come back from /api/admin/*. PostgreSQL returns COUNT() and SUM() as strings over
// the wire, so the counters are typed as strings and formatted, never arithmetic-ed, in the UI.

export interface AdminDashboard {
  metrics: {
    total_today: string;
    waiting_count: string;
    in_consult_count: string;
    completed_count: string;
    no_show_count: string;
    cancelled_count: string;
    today_revenue: string;
    onDutyDoctors: string;
    totalRegisteredPatients: string;
  };
  footfallTrend: { scheduled_date: string; visit_count: string; gmv: string }[];
}

// The admin rows are an appointment joined to its doctor, patient and invoice. They are
// intersections rather than `extends`, because the joined columns come back nullable while the
// base interface leaves them optional.
export type QueueEntry = Appointment & {
  doctor_name: string;
  specialties: string[];
  patient_name: string;
  patient_phone: string | null;
  invoice_status: PaymentStatus | null;
  invoice_id: string | null;
};

export type AdminAppointmentRow = Appointment & {
  doctor_name: string;
  specialties: string[];
  patient_name: string;
  patient_phone: string | null;
  net_payable: number | null;
  invoice_status: PaymentStatus | null;
};

export type AdminAppointmentDetail = Appointment & {
  doctor_name: string;
  qualification: string | null;
  room_number: string | null;
  patient_name: string;
  patient_email: string;
  patient_phone: string | null;
  invoice_id: string | null;
  invoice_number: string | null;
  net_payable: number | null;
  invoice_status: PaymentStatus | null;
  consultation_id: string | null;
  consult_started_at: string | null;
  consult_completed_at: string | null;
  prescription_id: string | null;
  prescription_number: string | null;
};

export interface AdminDoctorRow {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  license_number: string;
  qualification: string;
  specialties: string[];
  experience_years: number;
  consultation_fee_inr: number;
  video_fee_inr: number;
  room_number: string | null;
  rating_avg: number;
  rating_count: number;
  clinic_name: string | null;
}

export interface RoomRow {
  room_number: string | null;
  doctor_id: string;
  doctor_name: string;
  specialties: string[];
  consultation_fee_inr: number;
  on_duty: boolean;
  booked_today: string;
  waiting_now: string;
  current_token: number | null;
  current_patient: string | null;
  leave_reason: string | null;
}

export interface ScheduleOverride {
  id: string;
  doctor_id: string;
  date: string;
  is_leave: boolean;
  custom_start_time: string | null;
  custom_end_time: string | null;
  reason: string | null;
}

export interface DoctorRoster {
  doctor: AdminDoctorRow & { bio: string | null };
  shifts: DoctorShift[];
  overrides: ScheduleOverride[];
  upcoming: {
    scheduled_date: string;
    booked: string;
    video_count: string;
    first_slot: string;
    last_slot: string;
  }[];
}

export type AdminInvoiceRow = Invoice & {
  patient_name: string;
  patient_phone: string | null;
  appointment_number: string | null;
  scheduled_date: string | null;
};

export interface AdminInvoiceDetail {
  invoice: AdminInvoiceRow & {
    patient_email: string;
    dob: string | null;
    gender: string | null;
    blood_group: string | null;
    start_time?: string;
    appointment_type?: AppointmentType;
    doctor_name?: string;
    qualification?: string;
    room_number?: string;
  };
  items: InvoiceItem[];
  refunds: RefundRow[];
  clinic: Clinic | null;
}

export interface RefundRow {
  id: string;
  refund_number: string;
  invoice_id: string;
  appointment_id: string | null;
  amount: number;
  cancellation_fee: number;
  reason: string;
  refund_status: "pending" | "processed" | "failed";
  refund_method: string;
  processed_at: string;
  invoice_number?: string;
  total_amount?: number;
  patient_name?: string;
}

export type AdminLabOrderRow = LabOrder & {
  patient_name: string;
  doctor_name: string;
};

export interface AdminLabOrderDetail {
  order: AdminLabOrderRow & {
    patient_phone: string | null;
    dob: string | null;
    gender: string | null;
  };
  items: (LabOrderItem & {
    code: string;
    name: string;
    category: string;
    standard_fee_inr: number;
    turnaround_hours: number;
    sample_type: string;
  })[];
}

export interface ChartAccessLogRow {
  id: string;
  patient_id: string;
  accessed_by_user_id: string;
  access_type: string;
  resource_id: string | null;
  ip_address: string | null;
  accessed_at: string;
  actor_name: string;
  actor_role: UserRole;
  patient_name: string;
}

export interface ClinicSettings {
  clinic: Clinic | null;
  settings: {
    defaultSlotDurationMins: number;
    cancellationPolicy: string;
    mockTelehealthProvider: boolean;
    mockPaymentGateway: boolean;
    autoAssignQueueTokens: boolean;
  };
}

export interface ClinicReports {
  days: number;
  daily: {
    scheduled_date: string;
    booked: string;
    completed: string;
    no_show: string;
    cancelled: string;
    revenue: string;
  }[];
  specialties: { specialty: string; visits: string; revenue: string }[];
  doctors: {
    doctor_name: string;
    room_number: string | null;
    visits: string;
    no_show: string;
    revenue: string;
    rating_avg: number;
  }[];
  payments: { payment_method: string; invoices: string; collected: string }[];
  totals: {
    total: string;
    video: string;
    in_clinic: string;
    no_show: string;
    cancelled: string;
    unique_patients: string;
  };
}

export interface QueueDisplayEntry {
  token_number: number | null;
  queue_status: string;
  appointment_type: AppointmentType;
  doctor_name: string;
  room_number: string | null;
  specialties: string[];
  patient_name: string;
}
