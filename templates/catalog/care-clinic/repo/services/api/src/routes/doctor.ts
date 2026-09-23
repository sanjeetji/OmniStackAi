/** Doctor clinical workstation routes for CareClinic: queue, SOAP, prescriptions, chart, and schedule. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { requireAuth, requireRole, type AppEnv, type AuthContext } from "../auth/middleware.ts";
import { ClinicalService } from "../services/clinical.ts";
import { TelehealthService } from "../services/telehealth.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";
import { nextDocumentNumber } from "../lib/document-number.ts";
import { broadcastEvent } from "./stream.ts";

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

// Everything the consultation screens need in one read: the patient in the chair, what the desk
// recorded, and whatever this consultation has produced so far.
doctorRoutes.get("/api/doctor/consult/:appointmentId", async (c) => {
  const doctorId = getDoctorId(c);
  const appointmentId = c.req.param("appointmentId");

  const aptRes = await query(
    `SELECT a.*, u.full_name as patient_name, u.email as patient_email, u.phone as patient_phone,
            u.avatar_url as patient_avatar,
            p.dob, p.gender, p.blood_group, p.height_cm, p.weight_kg,
            p.emergency_contact, p.emergency_phone,
            EXTRACT(YEAR FROM AGE(p.dob)) as patient_age,
            fm.full_name as family_member_name, fm.relationship as family_member_rel,
            dp.room_number
     FROM appointments a
     JOIN users u ON u.id = a.patient_id
     LEFT JOIN patient_profiles p ON p.patient_id = u.id
     LEFT JOIN family_members fm ON fm.id = a.for_family_member_id
     LEFT JOIN doctor_profiles dp ON dp.doctor_id = a.doctor_id
     WHERE a.id = $1 AND a.doctor_id = $2`,
    [appointmentId, doctorId]
  );
  if (aptRes.rows.length === 0) {
    throw new NotFoundError("Appointment not found, or it belongs to another doctor");
  }
  const appointment = aptRes.rows[0];

  const [history, vitals, consultation] = await Promise.all([
    query(
      `SELECT allergies, chronic_conditions, current_medications, past_surgeries,
              family_history, lifestyle_notes
       FROM medical_histories WHERE patient_id = $1`,
      [appointment.patient_id]
    ),
    query(
      `SELECT * FROM vitals_records WHERE patient_id = $1 ORDER BY recorded_at DESC LIMIT 5`,
      [appointment.patient_id]
    ),
    query(`SELECT * FROM consultations WHERE appointment_id = $1`, [appointmentId]),
  ]);

  const current = consultation.rows[0] ?? null;
  let diagnoses: any[] = [];
  let prescription: any = null;
  let prescriptionItems: any[] = [];
  let labOrders: any[] = [];

  if (current) {
    const [diagRes, rxRes, labRes] = await Promise.all([
      query(`SELECT * FROM diagnoses WHERE consultation_id = $1 ORDER BY is_primary DESC`, [current.id]),
      query(`SELECT * FROM prescriptions WHERE consultation_id = $1`, [current.id]),
      query(
        `SELECT lo.*, COUNT(loi.id) AS test_count
         FROM lab_orders lo
         LEFT JOIN lab_order_items loi ON loi.lab_order_id = lo.id
         WHERE lo.consultation_id = $1
         GROUP BY lo.id
         ORDER BY lo.created_at DESC`,
        [current.id]
      ),
    ]);
    diagnoses = diagRes.rows;
    prescription = rxRes.rows[0] ?? null;
    labOrders = labRes.rows;
    if (prescription) {
      const itemsRes = await query(
        `SELECT * FROM prescription_items WHERE prescription_id = $1 ORDER BY id ASC`,
        [prescription.id]
      );
      prescriptionItems = itemsRes.rows;
    }
  }

  // Previous visits with this patient, so the doctor can see what was done last time.
  const priorRes = await query(
    `SELECT c.id, c.assessment, c.plan, c.completed_at, a.scheduled_date, u.full_name as doctor_name
     FROM consultations c
     JOIN appointments a ON a.id = c.appointment_id
     JOIN users u ON u.id = c.doctor_id
     WHERE c.patient_id = $1 AND c.appointment_id <> $2 AND c.completed_at IS NOT NULL
     ORDER BY a.scheduled_date DESC LIMIT 5`,
    [appointment.patient_id, appointmentId]
  );

  await ClinicalService.logChartAccess(appointment.patient_id, doctorId, "view_chart", appointmentId);

  return c.json({
    appointment,
    medicalHistory: history.rows[0] ?? {
      allergies: [],
      chronic_conditions: [],
      current_medications: [],
      past_surgeries: [],
    },
    vitals: vitals.rows,
    consultation: current,
    diagnoses,
    prescription,
    prescriptionItems,
    labOrders,
    previousVisits: priorRes.rows,
  });
});

// What the doctor has earned, and how the clinic settled it.
doctorRoutes.get("/api/doctor/earnings", async (c) => {
  const doctorId = getDoctorId(c);
  const days = Math.min(Math.max(parseInt(c.req.query("days") || "30", 10) || 30, 7), 180);

  const [totals, daily, byType, recent] = await Promise.all([
    query(
      // A visit can have more than one invoice (the consultation, then the diagnostics), so the
      // invoice is picked with a LATERAL rather than joined: a plain join would count the
      // consultation fee once per invoice.
      `SELECT
         COUNT(*) FILTER (WHERE a.status = 'completed') AS consultations,
         COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed'), 0) AS gross,
         COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed' AND inv.payment_status = 'paid'), 0) AS settled,
         COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed' AND inv.payment_status = 'pending'), 0) AS outstanding,
         COUNT(*) FILTER (WHERE a.status = 'no_show') AS no_show,
         COUNT(*) FILTER (WHERE a.status = 'cancelled') AS cancelled
       FROM appointments a
       LEFT JOIN LATERAL (
         SELECT i.payment_status FROM invoices i
          WHERE i.appointment_id = a.id
          ORDER BY i.created_at ASC
          LIMIT 1
       ) inv ON TRUE
       WHERE a.doctor_id = $1
         AND a.scheduled_date > CURRENT_DATE - ($2::int || ' days')::interval
         AND a.scheduled_date <= CURRENT_DATE`,
      [doctorId, days]
    ),
    query(
      `SELECT a.scheduled_date,
              COUNT(*) FILTER (WHERE a.status = 'completed') AS consultations,
              COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed'), 0) AS earned
       FROM appointments a
       WHERE a.doctor_id = $1
         AND a.scheduled_date > CURRENT_DATE - ($2::int || ' days')::interval
         AND a.scheduled_date <= CURRENT_DATE
       GROUP BY a.scheduled_date
       ORDER BY a.scheduled_date ASC`,
      [doctorId, days]
    ),
    query(
      `SELECT a.appointment_type,
              COUNT(*) FILTER (WHERE a.status = 'completed') AS consultations,
              COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed'), 0) AS earned
       FROM appointments a
       WHERE a.doctor_id = $1
         AND a.scheduled_date > CURRENT_DATE - ($2::int || ' days')::interval
         AND a.scheduled_date <= CURRENT_DATE
       GROUP BY a.appointment_type`,
      [doctorId, days]
    ),
    query(
      `SELECT a.id, a.appointment_number, a.scheduled_date, a.start_time, a.appointment_type,
              a.fee_amount, a.status, u.full_name AS patient_name,
              inv.invoice_number, inv.payment_status, inv.payment_method, inv.paid_at
       FROM appointments a
       JOIN users u ON u.id = a.patient_id
       LEFT JOIN LATERAL (
         SELECT i.invoice_number, i.payment_status, i.payment_method, i.paid_at
           FROM invoices i
          WHERE i.appointment_id = a.id
          ORDER BY i.created_at ASC
          LIMIT 1
       ) inv ON TRUE
       WHERE a.doctor_id = $1 AND a.status = 'completed'
       ORDER BY a.scheduled_date DESC, a.start_time DESC
       LIMIT 40`,
      [doctorId]
    ),
  ]);

  return c.json({
    days,
    totals: totals.rows[0],
    daily: daily.rows,
    byType: byType.rows,
    recent: recent.rows,
  });
});

// Planned absences and altered hours the doctor records for themselves.
doctorRoutes.post("/api/doctor/schedule/overrides", async (c) => {
  const doctorId = getDoctorId(c);
  const body = await c.req.json().catch(() => ({}));
  const { date, isLeave = true, customStartTime, customEndTime, reason } = body;

  if (!date) throw new BadRequestError("date is required");
  if (!isLeave && (!customStartTime || !customEndTime)) {
    throw new BadRequestError("customStartTime and customEndTime are required for altered hours");
  }

  const res = await query(
    `INSERT INTO schedule_overrides (doctor_id, date, is_leave, custom_start_time, custom_end_time, reason)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING *`,
    [doctorId, date, isLeave, customStartTime || null, customEndTime || null, reason || null]
  );

  broadcastEvent("schedule_updated", { doctorId, date, isLeave });
  return c.json({ override: res.rows[0] }, 201);
});

doctorRoutes.delete("/api/doctor/schedule/overrides/:id", async (c) => {
  const doctorId = getDoctorId(c);
  const res = await query(
    `DELETE FROM schedule_overrides WHERE id = $1 AND doctor_id = $2 RETURNING id`,
    [c.req.param("id"), doctorId]
  );
  if (res.rows.length === 0) throw new NotFoundError("Override not found");

  broadcastEvent("schedule_updated", { doctorId });
  return c.json({ deleted: res.rows[0].id });
});
