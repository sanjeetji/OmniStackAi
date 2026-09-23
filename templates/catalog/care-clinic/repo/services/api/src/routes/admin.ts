/** Front desk, clinic operations, and administrator routes for CareClinic. */

import { Hono } from "hono";
import { query, withTransaction } from "../db.ts";
import { requireAuth, requireRole, type AppEnv } from "../auth/middleware.ts";
import { SchedulingService } from "../services/scheduling.ts";
import { BillingService } from "../services/billing.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";
import { broadcastEvent } from "./stream.ts";

export const adminRoutes = new Hono<AppEnv>();

// Queue display endpoint is public so waiting-room TV monitors can stream it
adminRoutes.get("/api/admin/queue-display", async (c) => {
  const today = new Date().toISOString().slice(0, 10);

  const res = await query(
    `SELECT a.token_number, a.queue_status, a.appointment_type,
            u_doc.full_name as doctor_name, dp.room_number, dp.specialties,
            u_pat.full_name as patient_name
     FROM appointments a
     JOIN users u_doc ON u_doc.id = a.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u_doc.id
     JOIN users u_pat ON u_pat.id = a.patient_id
     WHERE a.scheduled_date = $1 AND a.status IN ('checked_in', 'in_consult')
     ORDER BY a.status DESC, a.token_number ASC`,
    [today]
  );

  return c.json({ activeQueue: res.rows });
});

// Protect all other admin endpoints
adminRoutes.use("/api/admin/*", requireAuth);
adminRoutes.use("/api/admin/*", requireRole("admin", "receptionist"));

// Clinic Operations Dashboard Overview
adminRoutes.get("/api/admin/dashboard", async (c) => {
  const today = new Date().toISOString().slice(0, 10);

  const statsRes = await query(
    `SELECT
       COUNT(*) as total_today,
       COUNT(*) FILTER (WHERE status = 'checked_in') as waiting_count,
       COUNT(*) FILTER (WHERE status = 'in_consult') as in_consult_count,
       COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
       COUNT(*) FILTER (WHERE status = 'no_show') as no_show_count,
       COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_count,
       COALESCE(SUM(fee_amount) FILTER (WHERE status = 'completed'), 0) as today_revenue
     FROM appointments
     WHERE scheduled_date = $1`,
    [today]
  );

  const doctorsRes = await query(
    `SELECT COUNT(DISTINCT doctor_id) as on_duty_doctors
     FROM doctor_availability
     WHERE day_of_week = EXTRACT(DOW FROM CURRENT_DATE) AND is_available = TRUE`
  );

  const totalPatientsRes = await query(`SELECT COUNT(*) as total_patients FROM users WHERE role = 'patient'`);

  // 14-day footfall trend
  const footfallRes = await query(
    `SELECT scheduled_date, COUNT(*) as visit_count, SUM(fee_amount) as gmv
     FROM appointments
     WHERE scheduled_date >= CURRENT_DATE - INTERVAL '14 days' AND scheduled_date <= CURRENT_DATE
     GROUP BY scheduled_date
     ORDER BY scheduled_date ASC`
  );

  return c.json({
    metrics: {
      ...statsRes.rows[0],
      onDutyDoctors: doctorsRes.rows[0]?.on_duty_doctors || 0,
      totalRegisteredPatients: totalPatientsRes.rows[0]?.total_patients || 0,
    },
    footfallTrend: footfallRes.rows,
  });
});

// Front Desk Operations Console
adminRoutes.get("/api/admin/front-desk", async (c) => {
  const today = new Date().toISOString().slice(0, 10);

  const queueRes = await query(
    `SELECT a.*, u_doc.full_name as doctor_name, dp.room_number, dp.specialties,
            u_pat.full_name as patient_name, u_pat.phone as patient_phone,
            inv.payment_status as invoice_status, inv.id as invoice_id
     FROM appointments a
     JOIN users u_doc ON u_doc.id = a.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u_doc.id
     JOIN users u_pat ON u_pat.id = a.patient_id
     LEFT JOIN invoices inv ON inv.appointment_id = a.id
     WHERE a.scheduled_date = $1
     ORDER BY a.token_number ASC NULLS LAST, a.start_time ASC`,
    [today]
  );

  return c.json({ queue: queueRes.rows });
});

// Front Desk Patient Check-In
adminRoutes.post("/api/admin/check-in", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const { appointmentId } = body;

  if (!appointmentId) throw new BadRequestError("appointmentId is required");

  const user = c.get("user");
  const appointment = await SchedulingService.checkIn(appointmentId, user.userId);
  return c.json({ appointment });
});

// Front Desk Walk-In Booking
adminRoutes.post("/api/admin/walk-in", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const { patientName, phone, doctorId, notes, paymentMethod = "cash" } = body;

  if (!patientName || !doctorId) {
    throw new BadRequestError("patientName and doctorId are required for walk-in");
  }

  const today = new Date().toISOString().slice(0, 10);
  const now = new Date();
  const currentHour = now.getHours().toString().padStart(2, "0");
  const currentMin = (Math.floor(now.getMinutes() / 20) * 20).toString().padStart(2, "0");
  const startTime = `${currentHour}:${currentMin}:00`;

  return withTransaction(async (client) => {
    // 1. Find or create guest patient
    const email = `walkin_${Date.now()}@careclinic.test`;
    const userRes = await client.query(
      `INSERT INTO users (email, password_hash, full_name, phone, role)
       VALUES ($1, 'walkin_nopass', $2, $3, 'patient')
       RETURNING id, full_name`,
      [email, patientName.trim(), phone || null]
    );
    const patient = userRes.rows[0];

    await client.query(`INSERT INTO patient_profiles (patient_id) VALUES ($1)`, [patient.id]);
    await client.query(`INSERT INTO medical_histories (patient_id) VALUES ($1)`, [patient.id]);

    // 2. Book appointment
    const appointment = await SchedulingService.bookAppointment({
      patientId: patient.id,
      doctorId,
      appointmentType: "in_clinic",
      scheduledDate: today,
      startTime,
      notes: notes || "Front desk walk-in appointment",
      paymentMethod,
    });

    // 3. Immediately check in to allocate token
    const checkedIn = await SchedulingService.checkIn(appointment.id);

    return c.json({ patient, appointment: checkedIn }, 201);
  });
});

// Global Appointments Master
adminRoutes.get("/api/admin/appointments", async (c) => {
  const q = c.req.query("q")?.toLowerCase();
  const status = c.req.query("status");
  const doctorId = c.req.query("doctorId");
  const date = c.req.query("date");

  let sql = `
    SELECT a.*, u_doc.full_name as doctor_name, dp.room_number, dp.specialties,
            u_pat.full_name as patient_name, u_pat.phone as patient_phone,
            inv.net_payable, inv.payment_status as invoice_status
     FROM appointments a
     JOIN users u_doc ON u_doc.id = a.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u_doc.id
     JOIN users u_pat ON u_pat.id = a.patient_id
     LEFT JOIN invoices inv ON inv.appointment_id = a.id
     WHERE 1=1
  `;
  const params: any[] = [];

  if (q) {
    params.push(`%${q}%`);
    sql += ` AND (LOWER(u_pat.full_name) LIKE $${params.length} OR LOWER(a.appointment_number) LIKE $${params.length})`;
  }

  if (status) {
    params.push(status);
    sql += ` AND a.status = $${params.length}`;
  }

  if (doctorId) {
    params.push(doctorId);
    sql += ` AND a.doctor_id = $${params.length}`;
  }

  if (date) {
    params.push(date);
    sql += ` AND a.scheduled_date = $${params.length}`;
  }

  sql += ` ORDER BY a.scheduled_date DESC, a.start_time DESC LIMIT 100`;

  const res = await query(sql, params);
  return c.json({ appointments: res.rows });
});

// Single Appointment Investigation
adminRoutes.get("/api/admin/appointments/:id", async (c) => {
  const aptId = c.req.param("id");

  const res = await query(
    `SELECT a.*, u_doc.full_name as doctor_name, dp.qualification, dp.room_number,
            u_pat.full_name as patient_name, u_pat.email as patient_email, u_pat.phone as patient_phone,
            inv.id as invoice_id, inv.invoice_number, inv.net_payable, inv.payment_status as invoice_status,
            c.id as consultation_id, c.started_at as consult_started_at, c.completed_at as consult_completed_at,
            rx.id as prescription_id, rx.prescription_number
     FROM appointments a
     JOIN users u_doc ON u_doc.id = a.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u_doc.id
     JOIN users u_pat ON u_pat.id = a.patient_id
     LEFT JOIN invoices inv ON inv.appointment_id = a.id
     LEFT JOIN consultations c ON c.appointment_id = a.id
     LEFT JOIN prescriptions rx ON rx.consultation_id = c.id
     WHERE a.id = $1`,
    [aptId]
  );

  if (res.rows.length === 0) throw new NotFoundError("Appointment not found");
  return c.json({ appointment: res.rows[0] });
});

// Doctors Roster & Room Assignments
adminRoutes.get("/api/admin/doctors", async (c) => {
  const res = await query(
    `SELECT u.id, u.full_name, u.email, u.phone,
            dp.license_number, dp.qualification, dp.specialties, dp.experience_years,
            dp.consultation_fee_inr, dp.video_fee_inr, dp.room_number, dp.rating_avg, dp.rating_count,
            c.name as clinic_name
     FROM users u
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     LEFT JOIN clinics c ON c.id = dp.clinic_id
     WHERE u.role = 'doctor'
     ORDER BY u.full_name ASC`
  );
  return c.json({ doctors: res.rows });
});

adminRoutes.put("/api/admin/doctors/:id/room", async (c) => {
  const doctorId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { roomNumber } = body;

  await query(
    `UPDATE doctor_profiles SET room_number = $1 WHERE doctor_id = $2`,
    [roomNumber || null, doctorId]
  );

  return c.json({ success: true, roomNumber });
});

// Clinic Invoices Master
adminRoutes.get("/api/admin/billing", async (c) => {
  const status = c.req.query("status");
  const q = c.req.query("q")?.toLowerCase();

  let sql = `
    SELECT inv.*, u.full_name as patient_name, u.phone as patient_phone,
           a.appointment_number, a.scheduled_date
    FROM invoices inv
    JOIN users u ON u.id = inv.patient_id
    LEFT JOIN appointments a ON a.id = inv.appointment_id
    WHERE 1=1
  `;
  const params: any[] = [];

  if (status) {
    params.push(status);
    sql += ` AND inv.payment_status = $${params.length}`;
  }

  if (q) {
    params.push(`%${q}%`);
    sql += ` AND (LOWER(u.full_name) LIKE $${params.length} OR LOWER(inv.invoice_number) LIKE $${params.length})`;
  }

  sql += ` ORDER BY inv.created_at DESC LIMIT 100`;

  const res = await query(sql, params);
  return c.json({ invoices: res.rows });
});

// Diagnostic Lab Management Queue
adminRoutes.get("/api/admin/labs", async (c) => {
  const status = c.req.query("status");

  let sql = `
    SELECT lo.*, u_pat.full_name as patient_name, u_doc.full_name as doctor_name
    FROM lab_orders lo
    JOIN users u_pat ON u_pat.id = lo.patient_id
    JOIN users u_doc ON u_doc.id = lo.doctor_id
    WHERE 1=1
  `;
  const params: any[] = [];

  if (status) {
    params.push(status);
    sql += ` AND lo.status = $${params.length}`;
  }

  sql += ` ORDER BY lo.created_at DESC LIMIT 50`;

  const ordersRes = await query(sql, params);
  return c.json({ orders: ordersRes.rows });
});

// Upload Lab Results
adminRoutes.post("/api/admin/labs/:id/results", async (c) => {
  const orderId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { items } = body; // array of { itemId, resultValue, flag, technicianNotes }

  if (!items || !Array.isArray(items)) {
    throw new BadRequestError("items array is required");
  }

  return withTransaction(async (client) => {
    for (const item of items) {
      await client.query(
        `UPDATE lab_order_items
         SET result_value = $1, flag = $2, technician_notes = $3
         WHERE id = $4`,
        [item.resultValue, item.flag || "normal", item.technicianNotes || null, item.itemId]
      );
    }

    const updatedOrder = await client.query(
      `UPDATE lab_orders
       SET status = 'completed', completed_at = NOW()
       WHERE id = $1
       RETURNING *`,
      [orderId]
    );

    return c.json({ order: updatedOrder.rows[0] });
  });
});

// Refunds Log
adminRoutes.get("/api/admin/refunds", async (c) => {
  const res = await query(
    `SELECT ref.*, inv.invoice_number, inv.total_amount, u.full_name as patient_name
     FROM refunds ref
     JOIN invoices inv ON inv.id = ref.invoice_id
     JOIN users u ON u.id = inv.patient_id
     ORDER BY ref.processed_at DESC LIMIT 50`
  );
  return c.json({ refunds: res.rows });
});

// HIPAA Chart Access Audit Logs
adminRoutes.get("/api/admin/audit-logs", async (c) => {
  const q = c.req.query("q")?.toLowerCase();

  let sql = `
    SELECT cal.*, u_actor.full_name as actor_name, u_actor.role as actor_role,
           u_pat.full_name as patient_name
    FROM chart_access_logs cal
    JOIN users u_actor ON u_actor.id = cal.accessed_by_user_id
    JOIN users u_pat ON u_pat.id = cal.patient_id
    WHERE 1=1
  `;
  const params: any[] = [];

  if (q) {
    params.push(`%${q}%`);
    sql += ` AND (LOWER(u_actor.full_name) LIKE $${params.length} OR LOWER(u_pat.full_name) LIKE $${params.length})`;
  }

  sql += ` ORDER BY cal.accessed_at DESC LIMIT 100`;

  const res = await query(sql, params);
  return c.json({ auditLogs: res.rows });
});

// Clinic System Settings
adminRoutes.get("/api/admin/settings", async (c) => {
  const clinicRes = await query(`SELECT * FROM clinics LIMIT 1`);
  return c.json({
    clinic: clinicRes.rows[0] || null,
    settings: {
      defaultSlotDurationMins: 20,
      cancellationPolicy: "Full refund >24h, 70% refund 4-24h, 0% refund <4h",
      mockTelehealthProvider: true,
      mockPaymentGateway: true,
      autoAssignQueueTokens: true,
    },
  });
});

// Consultation Room Board: every chamber, who is in it and which token is being seen
adminRoutes.get("/api/admin/rooms", async (c) => {
  const today = new Date().toISOString().slice(0, 10);

  const res = await query(
    `SELECT dp.room_number, u.id as doctor_id, u.full_name as doctor_name,
            dp.specialties, dp.consultation_fee_inr,
            EXISTS (
              SELECT 1 FROM doctor_availability da
              WHERE da.doctor_id = u.id
                AND da.day_of_week = EXTRACT(DOW FROM CURRENT_DATE)
                AND da.is_available = TRUE
            ) AS on_duty,
            (SELECT COUNT(*) FROM appointments a
              WHERE a.doctor_id = u.id AND a.scheduled_date = $1) AS booked_today,
            (SELECT COUNT(*) FROM appointments a
              WHERE a.doctor_id = u.id AND a.scheduled_date = $1 AND a.status = 'checked_in') AS waiting_now,
            (SELECT a.token_number FROM appointments a
              WHERE a.doctor_id = u.id AND a.scheduled_date = $1 AND a.status = 'in_consult'
              ORDER BY a.token_number ASC LIMIT 1) AS current_token,
            (SELECT p.full_name FROM appointments a
              JOIN users p ON p.id = a.patient_id
              WHERE a.doctor_id = u.id AND a.scheduled_date = $1 AND a.status = 'in_consult'
              ORDER BY a.token_number ASC LIMIT 1) AS current_patient,
            (SELECT so.reason FROM schedule_overrides so
              WHERE so.doctor_id = u.id AND so.date = CURRENT_DATE AND so.is_leave = TRUE
              LIMIT 1) AS leave_reason
     FROM users u
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     WHERE u.role = 'doctor'
     ORDER BY dp.room_number ASC NULLS LAST`,
    [today]
  );

  return c.json({ rooms: res.rows });
});

// Doctor Rostering: the weekly OPD rule, planned absences and what is booked against them
adminRoutes.get("/api/admin/doctors/:id/schedule", async (c) => {
  const doctorId = c.req.param("id");

  const doctorRes = await query(
    `SELECT u.id, u.full_name, u.email, u.phone, dp.license_number, dp.qualification,
            dp.specialties, dp.experience_years, dp.consultation_fee_inr, dp.video_fee_inr,
            dp.room_number, dp.rating_avg, dp.rating_count, dp.bio
     FROM users u
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     WHERE u.id = $1 AND u.role = 'doctor'`,
    [doctorId]
  );
  if (doctorRes.rows.length === 0) throw new NotFoundError("Doctor not found");

  const shiftsRes = await query(
    `SELECT * FROM doctor_availability WHERE doctor_id = $1 ORDER BY day_of_week ASC, start_time ASC`,
    [doctorId]
  );

  const overridesRes = await query(
    `SELECT * FROM schedule_overrides
     WHERE doctor_id = $1 AND date >= CURRENT_DATE - INTERVAL '7 days'
     ORDER BY date ASC`,
    [doctorId]
  );

  const upcomingRes = await query(
    `SELECT a.scheduled_date, COUNT(*) AS booked,
            COUNT(*) FILTER (WHERE a.appointment_type = 'video') AS video_count,
            MIN(a.start_time) AS first_slot, MAX(a.end_time) AS last_slot
     FROM appointments a
     WHERE a.doctor_id = $1 AND a.scheduled_date >= CURRENT_DATE
       AND a.scheduled_date <= CURRENT_DATE + INTERVAL '14 days'
       AND a.status NOT IN ('cancelled')
     GROUP BY a.scheduled_date
     ORDER BY a.scheduled_date ASC`,
    [doctorId]
  );

  return c.json({
    doctor: doctorRes.rows[0],
    shifts: shiftsRes.rows,
    overrides: overridesRes.rows,
    upcoming: upcomingRes.rows,
  });
});

// Record a planned absence or a one-off change of OPD hours
adminRoutes.post("/api/admin/doctors/:id/schedule-override", async (c) => {
  const doctorId = c.req.param("id");
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

// Itemised receipt for one invoice
adminRoutes.get("/api/admin/invoices/:id", async (c) => {
  const invoiceId = c.req.param("id");

  const invRes = await query(
    `SELECT inv.*, u.full_name as patient_name, u.email as patient_email, u.phone as patient_phone,
            pp.dob, pp.gender, pp.blood_group,
            a.appointment_number, a.scheduled_date, a.start_time, a.appointment_type,
            doc.full_name as doctor_name, dp.qualification, dp.room_number
     FROM invoices inv
     JOIN users u ON u.id = inv.patient_id
     LEFT JOIN patient_profiles pp ON pp.patient_id = u.id
     LEFT JOIN appointments a ON a.id = inv.appointment_id
     LEFT JOIN users doc ON doc.id = a.doctor_id
     LEFT JOIN doctor_profiles dp ON dp.doctor_id = doc.id
     WHERE inv.id = $1`,
    [invoiceId]
  );
  if (invRes.rows.length === 0) throw new NotFoundError("Invoice not found");

  const itemsRes = await query(
    `SELECT * FROM invoice_items WHERE invoice_id = $1 ORDER BY id ASC`,
    [invoiceId]
  );
  const refundsRes = await query(
    `SELECT * FROM refunds WHERE invoice_id = $1 ORDER BY processed_at DESC`,
    [invoiceId]
  );
  const clinicRes = await query(`SELECT * FROM clinics LIMIT 1`);

  return c.json({
    invoice: invRes.rows[0],
    items: itemsRes.rows,
    refunds: refundsRes.rows,
    clinic: clinicRes.rows[0] || null,
  });
});

// Cashier: take payment at the front desk
adminRoutes.post("/api/admin/invoices/:id/collect", async (c) => {
  const invoiceId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { paymentMethod = "cash" } = body;

  const allowed = ["card", "upi", "cash", "insurance", "netbanking"];
  if (!allowed.includes(paymentMethod)) {
    throw new BadRequestError(`paymentMethod must be one of ${allowed.join(", ")}`);
  }

  const invoice = await BillingService.payInvoice(invoiceId, paymentMethod);
  return c.json({ invoice });
});

// Cancel an appointment from the desk and settle the refund under the clinic policy
adminRoutes.post("/api/admin/appointments/:id/cancel", async (c) => {
  const appointmentId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { reason } = body;

  if (!reason) throw new BadRequestError("reason is required");

  const user = c.get("user");
  const result = await SchedulingService.cancelAppointment(appointmentId, user.userId, reason);
  return c.json(result);
});

// One lab order with its tests, for the technician's result entry
adminRoutes.get("/api/admin/labs/:id", async (c) => {
  const orderId = c.req.param("id");

  const orderRes = await query(
    `SELECT lo.*, u_pat.full_name as patient_name, u_pat.phone as patient_phone,
            pp.dob, pp.gender, u_doc.full_name as doctor_name
     FROM lab_orders lo
     JOIN users u_pat ON u_pat.id = lo.patient_id
     LEFT JOIN patient_profiles pp ON pp.patient_id = u_pat.id
     JOIN users u_doc ON u_doc.id = lo.doctor_id
     WHERE lo.id = $1`,
    [orderId]
  );
  if (orderRes.rows.length === 0) throw new NotFoundError("Lab order not found");

  const itemsRes = await query(
    `SELECT loi.*, lt.code, lt.name, lt.category, lt.standard_fee_inr, lt.turnaround_hours, lt.sample_type
     FROM lab_order_items loi
     JOIN lab_test_catalog lt ON lt.id = loi.test_id
     WHERE loi.lab_order_id = $1
     ORDER BY lt.name ASC`,
    [orderId]
  );

  return c.json({ order: orderRes.rows[0], items: itemsRes.rows });
});

// Move a lab order along the bench without entering results yet
adminRoutes.put("/api/admin/labs/:id/status", async (c) => {
  const orderId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const { status } = body;

  const allowed = ["ordered", "sample_collected", "processing", "completed", "cancelled"];
  if (!allowed.includes(status)) {
    throw new BadRequestError(`status must be one of ${allowed.join(", ")}`);
  }

  const res = await query(
    `UPDATE lab_orders
     SET status = $1, completed_at = CASE WHEN $1 = 'completed' THEN NOW() ELSE completed_at END
     WHERE id = $2
     RETURNING *`,
    [status, orderId]
  );
  if (res.rows.length === 0) throw new NotFoundError("Lab order not found");

  broadcastEvent("lab_updated", { orderId, status });
  return c.json({ order: res.rows[0] });
});

// Call the next token to a chamber, which the waiting-room board picks up over SSE
adminRoutes.post("/api/admin/queue/:id/call", async (c) => {
  const appointmentId = c.req.param("id");

  const res = await query(
    `UPDATE appointments
     SET queue_status = 'called', updated_at = NOW()
     WHERE id = $1 AND status = 'checked_in'
     RETURNING *`,
    [appointmentId]
  );
  if (res.rows.length === 0) {
    throw new BadRequestError("Only a checked-in patient can be called to a chamber");
  }

  const apt = res.rows[0];
  await query(
    `INSERT INTO notifications (user_id, title, message, type, link)
     VALUES ($1, $2, $3, 'token_called', '/appointments')`,
    [
      apt.patient_id,
      `Token ${apt.token_number} called`,
      "Please proceed to the consultation room.",
    ]
  );

  broadcastEvent("token_called", {
    appointmentId,
    doctorId: apt.doctor_id,
    tokenNumber: apt.token_number,
  });

  return c.json({ appointment: apt });
});

// Clinical analytics: footfall, specialty mix, no-shows and how the money came in
adminRoutes.get("/api/admin/reports", async (c) => {
  const days = Math.min(Math.max(parseInt(c.req.query("days") || "30", 10) || 30, 7), 90);

  const dailyRes = await query(
    `SELECT a.scheduled_date,
            COUNT(*) AS booked,
            COUNT(*) FILTER (WHERE a.status = 'completed') AS completed,
            COUNT(*) FILTER (WHERE a.status = 'no_show') AS no_show,
            COUNT(*) FILTER (WHERE a.status = 'cancelled') AS cancelled,
            COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed'), 0) AS revenue
     FROM appointments a
     WHERE a.scheduled_date > CURRENT_DATE - ($1::int || ' days')::interval
       AND a.scheduled_date <= CURRENT_DATE
     GROUP BY a.scheduled_date
     ORDER BY a.scheduled_date ASC`,
    [days]
  );

  const specialtyRes = await query(
    `SELECT s.specialty, COUNT(*) AS visits,
            COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed'), 0) AS revenue
     FROM appointments a
     JOIN doctor_profiles dp ON dp.doctor_id = a.doctor_id
     CROSS JOIN LATERAL unnest(dp.specialties) AS s(specialty)
     WHERE a.scheduled_date > CURRENT_DATE - ($1::int || ' days')::interval
       AND a.scheduled_date <= CURRENT_DATE
     GROUP BY s.specialty
     ORDER BY visits DESC`,
    [days]
  );

  const doctorRes = await query(
    `SELECT u.full_name AS doctor_name, dp.room_number,
            COUNT(*) AS visits,
            COUNT(*) FILTER (WHERE a.status = 'no_show') AS no_show,
            COALESCE(SUM(a.fee_amount) FILTER (WHERE a.status = 'completed'), 0) AS revenue,
            dp.rating_avg
     FROM appointments a
     JOIN users u ON u.id = a.doctor_id
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     WHERE a.scheduled_date > CURRENT_DATE - ($1::int || ' days')::interval
       AND a.scheduled_date <= CURRENT_DATE
     GROUP BY u.full_name, dp.room_number, dp.rating_avg
     ORDER BY visits DESC
     LIMIT 12`,
    [days]
  );

  const paymentRes = await query(
    `SELECT COALESCE(payment_method, 'unpaid') AS payment_method,
            COUNT(*) AS invoices, COALESCE(SUM(net_payable), 0) AS collected
     FROM invoices
     WHERE created_at > NOW() - ($1::int || ' days')::interval
     GROUP BY COALESCE(payment_method, 'unpaid')
     ORDER BY collected DESC`,
    [days]
  );

  const mixRes = await query(
    `SELECT
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE appointment_type = 'video') AS video,
       COUNT(*) FILTER (WHERE appointment_type = 'in_clinic') AS in_clinic,
       COUNT(*) FILTER (WHERE status = 'no_show') AS no_show,
       COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
       COUNT(DISTINCT patient_id) AS unique_patients
     FROM appointments
     WHERE scheduled_date > CURRENT_DATE - ($1::int || ' days')::interval
       AND scheduled_date <= CURRENT_DATE`,
    [days]
  );

  return c.json({
    days,
    daily: dailyRes.rows,
    specialties: specialtyRes.rows,
    doctors: doctorRes.rows,
    payments: paymentRes.rows,
    totals: mixRes.rows[0],
  });
});
