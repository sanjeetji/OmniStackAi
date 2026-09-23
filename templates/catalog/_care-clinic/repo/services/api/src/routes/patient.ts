/** Patient portal routes for CareClinic: appointments, prescriptions, records, and telehealth. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { requireAuth, requireRole } from "../auth/middleware.ts";
import { SchedulingService } from "../services/scheduling.ts";
import { ClinicalService } from "../services/clinical.ts";
import { BillingService } from "../services/billing.ts";
import { TelehealthService } from "../services/telehealth.ts";
import { BadRequestError, NotFoundError, ForbiddenError } from "../lib/errors.ts";

export const patientRoutes = new Hono();

patientRoutes.use("/api/patient/*", requireAuth);
patientRoutes.use("/api/patient/*", requireRole("patient", "admin"));

// Patient Profile & Dependents
patientRoutes.get("/api/patient/me", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT u.id, u.email, u.full_name, u.phone, u.avatar_url,
            p.dob, p.gender, p.blood_group, p.height_cm, p.weight_kg,
            p.emergency_contact, p.emergency_phone, p.address
     FROM users u
     LEFT JOIN patient_profiles p ON p.patient_id = u.id
     WHERE u.id = $1`,
    [user.userId]
  );

  const familyRes = await query(
    `SELECT * FROM family_members WHERE primary_patient_id = $1 ORDER BY full_name ASC`,
    [user.userId]
  );

  return c.json({
    patient: res.rows[0],
    familyMembers: familyRes.rows,
  });
});

// Update Profile
patientRoutes.put("/api/patient/me", async (c) => {
  const user = c.get("user");
  const body = await c.req.json().catch(() => ({}));
  const { fullName, phone, dob, gender, bloodGroup, heightCm, weightKg, emergencyContact, emergencyPhone, address } = body;

  if (fullName) {
    await query(`UPDATE users SET full_name = $1, phone = $2, updated_at = NOW() WHERE id = $3`, [
      fullName,
      phone || null,
      user.userId,
    ]);
  }

  await query(
    `UPDATE patient_profiles
     SET dob = COALESCE($1, dob), gender = COALESCE($2, gender), blood_group = COALESCE($3, blood_group),
         height_cm = COALESCE($4, height_cm), weight_kg = COALESCE($5, weight_kg),
         emergency_contact = COALESCE($6, emergency_contact), emergency_phone = COALESCE($7, emergency_phone),
         address = COALESCE($8, address)
     WHERE patient_id = $9`,
    [dob || null, gender || null, bloodGroup || null, heightCm || null, weightKg || null, emergencyContact || null, emergencyPhone || null, address || null, user.userId]
  );

  return c.json({ success: true });
});

// Available Slots Query
patientRoutes.get("/api/patient/doctors/:id/slots", async (c) => {
  const doctorId = c.req.param("id");
  const date = c.req.query("date") || new Date().toISOString().slice(0, 10);

  const slots = await SchedulingService.getDoctorAvailableSlots(doctorId, date);
  return c.json({ doctorId, date, slots });
});

// Book Appointment
patientRoutes.post("/api/patient/book", async (c) => {
  const user = c.get("user");
  const body = await c.req.json().catch(() => ({}));
  const { doctorId, clinicId, forFamilyMemberId, appointmentType, scheduledDate, startTime, notes, paymentMethod } = body;

  if (!doctorId || !appointmentType || !scheduledDate || !startTime) {
    throw new BadRequestError("doctorId, appointmentType, scheduledDate, and startTime are required");
  }

  const appointment = await SchedulingService.bookAppointment({
    patientId: user.userId,
    doctorId,
    clinicId,
    forFamilyMemberId,
    appointmentType,
    scheduledDate,
    startTime,
    notes,
    paymentMethod,
  });

  return c.json({ appointment }, 201);
});

// Patient Appointments List
patientRoutes.get("/api/patient/appointments", async (c) => {
  const user = c.get("user");
  const filter = c.req.query("filter"); // upcoming, past

  let sql = `
    SELECT a.*, u.full_name as doctor_name, dp.qualification, dp.specialties, dp.room_number,
           c.name as clinic_name, c.address as clinic_address,
           fm.full_name as family_member_name, fm.relationship as family_member_rel,
           p.id as prescription_id
    FROM appointments a
    JOIN users u ON u.id = a.doctor_id
    JOIN doctor_profiles dp ON dp.doctor_id = u.id
    LEFT JOIN clinics c ON c.id = a.clinic_id
    LEFT JOIN family_members fm ON fm.id = a.for_family_member_id
    LEFT JOIN consultations con ON con.appointment_id = a.id
    LEFT JOIN prescriptions p ON p.consultation_id = con.id
    WHERE a.patient_id = $1
  `;
  const params: any[] = [user.userId];

  if (filter === "upcoming") {
    sql += ` AND a.status IN ('booked', 'checked_in', 'in_consult') AND (a.scheduled_date >= CURRENT_DATE)`;
    sql += ` ORDER BY a.scheduled_date ASC, a.start_time ASC`;
  } else if (filter === "past") {
    sql += ` AND (a.status IN ('completed', 'cancelled', 'no_show') OR a.scheduled_date < CURRENT_DATE)`;
    sql += ` ORDER BY a.scheduled_date DESC, a.start_time DESC`;
  } else {
    sql += ` ORDER BY a.scheduled_date DESC, a.start_time DESC`;
  }

  const res = await query(sql, params);
  return c.json({ appointments: res.rows });
});

// Single Appointment Detail
patientRoutes.get("/api/patient/appointments/:id", async (c) => {
  const user = c.get("user");
  const aptId = c.req.param("id");

  const res = await query(
    `SELECT a.*, u.full_name as doctor_name, u.avatar_url as doctor_avatar,
            dp.qualification, dp.specialties, dp.room_number, dp.license_number,
            c.name as clinic_name, c.address as clinic_address, c.phone as clinic_phone,
            inv.id as invoice_id, inv.invoice_number, inv.net_payable, inv.payment_status,
            con.id as consultation_id, p.id as prescription_id, p.prescription_number,
            ts.room_token as telehealth_room_token, ts.status as telehealth_status
     FROM appointments a
     JOIN users u ON u.id = a.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     LEFT JOIN clinics c ON c.id = a.clinic_id
     LEFT JOIN invoices inv ON inv.appointment_id = a.id
     LEFT JOIN consultations con ON con.appointment_id = a.id
     LEFT JOIN prescriptions p ON p.consultation_id = con.id
     LEFT JOIN telehealth_sessions ts ON ts.appointment_id = a.id
     WHERE a.id = $1 AND (a.patient_id = $2 OR $3 = 'admin')`,
    [aptId, user.userId, user.role]
  );

  if (res.rows.length === 0) {
    throw new NotFoundError("Appointment not found");
  }

  return c.json({ appointment: res.rows[0] });
});

// Cancel Appointment
patientRoutes.post("/api/patient/appointments/:id/cancel", async (c) => {
  const user = c.get("user");
  const aptId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { reason = "Patient requested cancellation" } = body;

  // Verify ownership
  const check = await query(`SELECT patient_id FROM appointments WHERE id = $1`, [aptId]);
  if (check.rows.length === 0) throw new NotFoundError("Appointment not found");
  if (check.rows[0].patient_id !== user.userId && user.role !== "admin") {
    throw new ForbiddenError("You can only cancel your own appointments");
  }

  const result = await SchedulingService.cancelAppointment(aptId, user.userId, reason);
  return c.json(result);
});

// Patient Digital Prescriptions
patientRoutes.get("/api/patient/prescriptions", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT p.*, u.full_name as doctor_name, dp.qualification, dp.specialties,
            a.appointment_number, a.scheduled_date
     FROM prescriptions p
     JOIN users u ON u.id = p.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     JOIN consultations c ON c.id = p.consultation_id
     JOIN appointments a ON a.id = c.appointment_id
     WHERE p.patient_id = $1
     ORDER BY p.signed_at DESC NULLS LAST, p.created_at DESC`,
    [user.userId]
  );
  return c.json({ prescriptions: res.rows });
});

// Single Prescription View
patientRoutes.get("/api/patient/prescriptions/:id", async (c) => {
  const user = c.get("user");
  const rxId = c.req.param("id");

  const rxRes = await query(
    `SELECT p.*, u.full_name as doctor_name, dp.qualification, dp.specialties, dp.license_number,
            c_clinic.name as clinic_name, c_clinic.address as clinic_address, c_clinic.phone as clinic_phone,
            a.appointment_number, a.scheduled_date, con.subjective, con.assessment, con.plan
     FROM prescriptions p
     JOIN users u ON u.id = p.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     JOIN consultations con ON con.id = p.consultation_id
     JOIN appointments a ON a.id = con.appointment_id
     LEFT JOIN clinics c_clinic ON c_clinic.id = a.clinic_id
     WHERE p.id = $1 AND (p.patient_id = $2 OR $3 = 'admin')`,
    [rxId, user.userId, user.role]
  );

  if (rxRes.rows.length === 0) {
    throw new NotFoundError("Prescription not found");
  }

  const itemsRes = await query(
    `SELECT * FROM prescription_items WHERE prescription_id = $1 ORDER BY id ASC`,
    [rxId]
  );

  return c.json({
    prescription: rxRes.rows[0],
    items: itemsRes.rows,
  });
});

// Lab Reports List
patientRoutes.get("/api/patient/labs", async (c) => {
  const user = c.get("user");
  const ordersRes = await query(
    `SELECT lo.*, u.full_name as doctor_name
     FROM lab_orders lo
     JOIN users u ON u.id = lo.doctor_id
     WHERE lo.patient_id = $1
     ORDER BY lo.created_at DESC`,
    [user.userId]
  );

  const orderIds = ordersRes.rows.map((o: { id: string }) => o.id);
  let items: any[] = [];
  if (orderIds.length > 0) {
    const itemsRes = await query(
      `SELECT loi.*, ltc.name as test_name, ltc.category, ltc.standard_fee_inr
       FROM lab_order_items loi
       JOIN lab_test_catalog ltc ON ltc.id = loi.test_id
       WHERE loi.lab_order_id = ANY($1)`,
      [orderIds]
    );
    items = itemsRes.rows;
  }

  return c.json({ orders: ordersRes.rows, items });
});

// Medical History & Longitudinal Vitals
patientRoutes.get("/api/patient/records", async (c) => {
  const user = c.get("user");
  const historyRes = await query(
    `SELECT * FROM medical_histories WHERE patient_id = $1`,
    [user.userId]
  );

  const vitalsRes = await query(
    `SELECT vr.*, u.full_name as recorded_by_name
     FROM vitals_records vr
     LEFT JOIN users u ON u.id = vr.recorded_by
     WHERE vr.patient_id = $1
     ORDER BY vr.recorded_at DESC LIMIT 20`,
    [user.userId]
  );

  return c.json({
    medicalHistory: historyRes.rows[0] || {
      allergies: [],
      chronic_conditions: [],
      current_medications: [],
      past_surgeries: [],
    },
    vitals: vitalsRes.rows,
  });
});

// Record Vitals (Patient self-log)
patientRoutes.post("/api/patient/records/vitals", async (c) => {
  const user = c.get("user");
  const body = await c.req.json().catch(() => ({}));
  const { bpSystolic, bpDiastolic, heartRate, temperatureF, spo2Percent, bloodGlucoseMgDl, notes } = body;

  const res = await query(
    `INSERT INTO vitals_records (
      patient_id, recorded_by, bp_systolic, bp_diastolic, heart_rate,
      temperature_f, spo2_percent, blood_glucose_mg_dl, notes
    ) VALUES ($1, $1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING *`,
    [user.userId, bpSystolic || null, bpDiastolic || null, heartRate || null, temperatureF || null, spo2Percent || null, bloodGlucoseMgDl || null, notes || "Patient logged"]
  );

  return c.json({ vitals: res.rows[0] }, 201);
});

// Family Members
patientRoutes.get("/api/patient/family", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT * FROM family_members WHERE primary_patient_id = $1 ORDER BY created_at ASC`,
    [user.userId]
  );
  return c.json({ familyMembers: res.rows });
});

patientRoutes.post("/api/patient/family", async (c) => {
  const user = c.get("user");
  const body = await c.req.json().catch(() => ({}));
  const { fullName, relationship, dob, gender, bloodGroup } = body;

  if (!fullName || !relationship) {
    throw new BadRequestError("Full name and relationship are required");
  }

  const res = await query(
    `INSERT INTO family_members (primary_patient_id, full_name, relationship, dob, gender, blood_group)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING *`,
    [user.userId, fullName.trim(), relationship, dob || null, gender || null, bloodGroup || null]
  );

  return c.json({ member: res.rows[0] }, 201);
});

// Patient Invoices
patientRoutes.get("/api/patient/invoices", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT inv.*, a.appointment_number, a.scheduled_date, u.full_name as doctor_name
     FROM invoices inv
     LEFT JOIN appointments a ON a.id = inv.appointment_id
     LEFT JOIN users u ON u.id = a.doctor_id
     WHERE inv.patient_id = $1
     ORDER BY inv.created_at DESC`,
    [user.userId]
  );
  return c.json({ invoices: res.rows });
});

patientRoutes.post("/api/patient/invoices/:id/pay", async (c) => {
  const user = c.get("user");
  const invoiceId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { paymentMethod = "upi", transactionRef } = body;

  const invRes = await query(`SELECT patient_id FROM invoices WHERE id = $1`, [invoiceId]);
  if (invRes.rows.length === 0) throw new NotFoundError("Invoice not found");
  if (invRes.rows[0].patient_id !== user.userId && user.role !== "admin") {
    throw new ForbiddenError("You can only pay your own invoices");
  }

  const invoice = await BillingService.payInvoice(invoiceId, paymentMethod, transactionRef);
  return c.json({ invoice });
});

// Telehealth Video Session
patientRoutes.get("/api/patient/telehealth/:appointmentId", async (c) => {
  const user = c.get("user");
  const aptId = c.req.param("appointmentId");

  const room = await TelehealthService.getOrCreateRoom(aptId);
  return c.json({ session: room });
});

patientRoutes.post("/api/patient/telehealth/:appointmentId/join", async (c) => {
  const user = c.get("user");
  const aptId = c.req.param("appointmentId");

  const room = await TelehealthService.joinRoom(aptId, "patient");
  return c.json({ session: room });
});

// Patient Review
patientRoutes.post("/api/patient/reviews", async (c) => {
  const user = c.get("user");
  const body = await c.req.json().catch(() => ({}));
  const { doctorId, appointmentId, rating, feedback, isAnonymous } = body;

  if (!doctorId || !rating || !feedback) {
    throw new BadRequestError("doctorId, rating (1-5), and feedback are required");
  }

  const res = await query(
    `INSERT INTO patient_reviews (patient_id, doctor_id, appointment_id, rating, feedback, is_anonymous)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING *`,
    [user.userId, doctorId, appointmentId || null, rating, feedback, isAnonymous || false]
  );

  // Recalculate doctor rating
  await query(
    `UPDATE doctor_profiles
     SET rating_avg = (SELECT COALESCE(AVG(rating), 5.0) FROM patient_reviews WHERE doctor_id = $1),
         rating_count = (SELECT COUNT(*) FROM patient_reviews WHERE doctor_id = $1)
     WHERE doctor_id = $1`,
    [doctorId]
  );

  return c.json({ review: res.rows[0] }, 201);
});
