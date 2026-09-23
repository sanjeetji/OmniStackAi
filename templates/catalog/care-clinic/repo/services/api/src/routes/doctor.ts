/** Doctor clinical workstation routes for CareClinic: queue, SOAP, prescriptions, chart, and schedule. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { requireAuth, requireRole, type AppEnv, type AuthContext } from "../auth/middleware.ts";
import { ClinicalService } from "../services/clinical.ts";
import { TelehealthService } from "../services/telehealth.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";
import { nextDocumentNumber } from "../lib/document-number.ts";

export const doctorRoutes = new Hono<AppEnv>();

doctorRoutes.use("/api/doctor/*", requireAuth);
doctorRoutes.use("/api/doctor/*", requireRole("doctor", "admin"));

// Helper to resolve doctor ID from user context
function getDoctorId(c: AuthContext): string {
  const user = c.get("user");
  return user.doctorId || user.userId;
}

// Doctor Dashboard Overview
doctorRoutes.get("/api/doctor/dashboard", async (c) => {
  const doctorId = getDoctorId(c);
  const today = new Date().toISOString().slice(0, 10);

  const statsRes = await query(
    `SELECT
       COUNT(*) as today_total,
       COUNT(*) FILTER (WHERE status = 'booked') as pending_count,
       COUNT(*) FILTER (WHERE status = 'checked_in') as waiting_count,
       COUNT(*) FILTER (WHERE status = 'in_consult') as in_consult_count,
       COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
       COUNT(*) FILTER (WHERE appointment_type = 'video') as video_count,
       COALESCE(SUM(fee_amount) FILTER (WHERE status = 'completed'), 0) as today_earnings
     FROM appointments
     WHERE doctor_id = $1 AND scheduled_date = $2`,
    [doctorId, today]
  );

  const activeRes = await query(
    `SELECT a.*, u.full_name as patient_name, u.avatar_url as patient_avatar,
            p.gender, p.blood_group, EXTRACT(YEAR FROM AGE(p.dob)) as patient_age,
            c.id as consultation_id
     FROM appointments a
     JOIN users u ON u.id = a.patient_id
     LEFT JOIN patient_profiles p ON p.patient_id = u.id
     LEFT JOIN consultations c ON c.appointment_id = a.id
     WHERE a.doctor_id = $1 AND a.scheduled_date = $2 AND a.status = 'in_consult'
     LIMIT 1`,
    [doctorId, today]
  );

  return c.json({
    metrics: statsRes.rows[0],
    activeConsultation: activeRes.rows[0] || null,
  });
});

// Today's Waiting Queue
doctorRoutes.get("/api/doctor/queue", async (c) => {
  const doctorId = getDoctorId(c);
  const date = c.req.query("date") || new Date().toISOString().slice(0, 10);

  const res = await query(
    `SELECT a.*, u.full_name as patient_name, u.phone as patient_phone,
            p.gender, p.blood_group, EXTRACT(YEAR FROM AGE(p.dob)) as patient_age,
            fm.full_name as family_member_name, fm.relationship as family_member_rel,
            c.id as consultation_id, rx.id as prescription_id
     FROM appointments a
     JOIN users u ON u.id = a.patient_id
     LEFT JOIN patient_profiles p ON p.patient_id = u.id
     LEFT JOIN family_members fm ON fm.id = a.for_family_member_id
     LEFT JOIN consultations c ON c.appointment_id = a.id
     LEFT JOIN prescriptions rx ON rx.consultation_id = c.id
     WHERE a.doctor_id = $1 AND a.scheduled_date = $2
     ORDER BY a.token_number ASC NULLS LAST, a.start_time ASC`,
    [doctorId, date]
  );

  return c.json({ queue: res.rows });
});

// Patient Directory under this Doctor's Care
doctorRoutes.get("/api/doctor/patients", async (c) => {
  const doctorId = getDoctorId(c);
  const q = c.req.query("q")?.toLowerCase();

  let sql = `
    SELECT u.id, u.full_name, u.email, u.phone,
           p.gender, p.blood_group, EXTRACT(YEAR FROM AGE(p.dob)) as age,
           COUNT(a.id) as visit_count,
           MAX(a.scheduled_date) as last_visit_date
    FROM users u
    JOIN appointments a ON a.patient_id = u.id
    LEFT JOIN patient_profiles p ON p.patient_id = u.id
    WHERE a.doctor_id = $1
  `;
  const params: any[] = [doctorId];

  if (q) {
    params.push(`%${q}%`);
    sql += ` AND (LOWER(u.full_name) LIKE $${params.length} OR LOWER(u.email) LIKE $${params.length})`;
  }

  sql += ` GROUP BY u.id, u.full_name, u.email, u.phone, p.gender, p.blood_group, p.dob
           ORDER BY last_visit_date DESC`;

  const res = await query(sql, params);
  return c.json({ patients: res.rows });
});

// Full Longitudinal Patient Chart (Audited)
doctorRoutes.get("/api/doctor/patients/:id/chart", async (c) => {
  const doctorId = getDoctorId(c);
  const patientId = c.req.param("id");
  const ip = c.req.header("x-forwarded-for") || "127.0.0.1";

  const chart = await ClinicalService.getPatientChart(patientId, doctorId, ip);
  return c.json(chart);
});

// Start Consultation
doctorRoutes.post("/api/doctor/consult/:appointmentId/start", async (c) => {
  const doctorId = getDoctorId(c);
  const aptId = c.req.param("appointmentId");

  const consult = await ClinicalService.startConsultation(aptId, doctorId);
  return c.json({ consultation: consult });
});

// Save SOAP Clinical Notes & Diagnoses
doctorRoutes.post("/api/doctor/consult/:appointmentId/soap", async (c) => {
  const doctorId = getDoctorId(c);
  const aptId = c.req.param("appointmentId");
  const body = await c.req.json().catch(() => ({}));
  const ip = c.req.header("x-forwarded-for") || "127.0.0.1";

  // Find consultation ID
  const cRes = await query(`SELECT id FROM consultations WHERE appointment_id = $1`, [aptId]);
  if (cRes.rows.length === 0) {
    throw new NotFoundError("Consultation not found. Start consultation first.");
  }

  const updated = await ClinicalService.saveSoapNotes(
    cRes.rows[0].id,
    doctorId,
    body,
    ip
  );
  return c.json({ consultation: updated });
});

// Issue Immutable E-Prescription
doctorRoutes.post("/api/doctor/consult/:appointmentId/prescribe", async (c) => {
  const doctorId = getDoctorId(c);
  const aptId = c.req.param("appointmentId");
  const body = await c.req.json().catch(() => ({}));
  const { diagnosisSummary, items } = body;
  const ip = c.req.header("x-forwarded-for") || "127.0.0.1";

  if (!diagnosisSummary || !items || !Array.isArray(items)) {
    throw new BadRequestError("diagnosisSummary and items array are required");
  }

  const cRes = await query(`SELECT id FROM consultations WHERE appointment_id = $1`, [aptId]);
  if (cRes.rows.length === 0) {
    throw new NotFoundError("Consultation not found. Start consultation first.");
  }

  const prescription = await ClinicalService.issuePrescription(
    cRes.rows[0].id,
    doctorId,
    diagnosisSummary,
    items,
    ip
  );

  return c.json({ prescription }, 201);
});

// Order Diagnostic Labs
doctorRoutes.post("/api/doctor/consult/:appointmentId/labs", async (c) => {
  const doctorId = getDoctorId(c);
  const aptId = c.req.param("appointmentId");
  const body = await c.req.json().catch(() => ({}));
  const { testCodes } = body;

  if (!testCodes || !Array.isArray(testCodes) || testCodes.length === 0) {
    throw new BadRequestError("testCodes array is required");
  }

  const cRes = await query(
    `SELECT c.id, c.patient_id FROM consultations c WHERE c.appointment_id = $1`,
    [aptId]
  );
  if (cRes.rows.length === 0) throw new NotFoundError("Consultation not found");

  const consult = cRes.rows[0];

  const orderNumber = await nextDocumentNumber({ query }, "lab_orders");

  const orderRes = await query(
    `INSERT INTO lab_orders (order_number, consultation_id, patient_id, doctor_id, status)
     VALUES ($1, $2, $3, $4, 'ordered')
     RETURNING *`,
    [orderNumber, consult.id, consult.patient_id, doctorId]
  );
  const order = orderRes.rows[0];

  const testsRes = await query(
    `SELECT id, code, standard_fee_inr FROM lab_test_catalog WHERE code = ANY($1)`,
    [testCodes]
  );

  for (const t of testsRes.rows) {
    await query(
      `INSERT INTO lab_order_items (lab_order_id, test_id) VALUES ($1, $2)`,
      [order.id, t.id]
    );
  }

  return c.json({ order, tests: testsRes.rows }, 201);
});

// Complete Consultation Visit
doctorRoutes.post("/api/doctor/consult/:appointmentId/complete", async (c) => {
  const doctorId = getDoctorId(c);
  const aptId = c.req.param("appointmentId");

  const cRes = await query(`SELECT id FROM consultations WHERE appointment_id = $1`, [aptId]);
  if (cRes.rows.length === 0) throw new NotFoundError("Consultation not found");

  const result = await ClinicalService.completeConsultation(cRes.rows[0].id, doctorId);
  return c.json(result);
});

// Doctor Schedule & Availability Rules
doctorRoutes.get("/api/doctor/schedule", async (c) => {
  const doctorId = getDoctorId(c);

  const availRes = await query(
    `SELECT * FROM doctor_availability WHERE doctor_id = $1 ORDER BY day_of_week ASC`,
    [doctorId]
  );

  const overrideRes = await query(
    `SELECT * FROM schedule_overrides WHERE doctor_id = $1 AND date >= CURRENT_DATE ORDER BY date ASC`,
    [doctorId]
  );

  return c.json({
    shifts: availRes.rows,
    overrides: overrideRes.rows,
  });
});

doctorRoutes.put("/api/doctor/schedule", async (c) => {
  const doctorId = getDoctorId(c);
  const body = await c.req.json().catch(() => ({}));
  const { shifts } = body;

  if (!shifts || !Array.isArray(shifts)) {
    throw new BadRequestError("shifts array is required");
  }

  // Clear existing and replace
  await query(`DELETE FROM doctor_availability WHERE doctor_id = $1`, [doctorId]);

  for (const s of shifts) {
    await query(
      `INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time, slot_duration_mins, is_available)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [doctorId, s.dayOfWeek, s.startTime, s.endTime, s.slotDurationMins || 20, s.isAvailable ?? true]
    );
  }

  return c.json({ success: true, count: shifts.length });
});

// Doctor Reviews
doctorRoutes.get("/api/doctor/reviews", async (c) => {
  const doctorId = getDoctorId(c);
  const res = await query(
    `SELECT pr.*, u.full_name as patient_name
     FROM patient_reviews pr
     JOIN users u ON u.id = pr.patient_id
     WHERE pr.doctor_id = $1
     ORDER BY pr.created_at DESC`,
    [doctorId]
  );
  return c.json({ reviews: res.rows });
});

// Telehealth Video Call Controls
doctorRoutes.get("/api/doctor/telehealth/:appointmentId", async (c) => {
  const aptId = c.req.param("appointmentId");
  const session = await TelehealthService.getOrCreateRoom(aptId);
  return c.json({ session });
});

doctorRoutes.post("/api/doctor/telehealth/:appointmentId/join", async (c) => {
  const aptId = c.req.param("appointmentId");
  const session = await TelehealthService.joinRoom(aptId, "doctor");
  return c.json({ session });
});

doctorRoutes.post("/api/doctor/telehealth/:appointmentId/end", async (c) => {
  const aptId = c.req.param("appointmentId");
  const session = await TelehealthService.endRoom(aptId);
  return c.json({ session });
});
