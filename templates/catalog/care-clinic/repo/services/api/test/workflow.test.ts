/**
 * End-to-end workflow against a running API with the demo seed loaded:
 *
 *   API_BASE=http://127.0.0.1:4000 node --test test/workflow.test.ts
 *
 * Skipped when API_BASE is not set (the unit tests run without a database). It walks one patient
 * through the whole clinic: booking, the front desk, the consultation, the prescription, the
 * cashier and the refund policy, and checks that each app sees the others' work.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

const BASE = process.env.API_BASE;
const skip = BASE ? false : "set API_BASE to run the live workflow";

async function call(
  path: string,
  init: { method?: string; token?: string; body?: unknown } = {}
): Promise<{ status: number; data: any }> {
  const response = await fetch(`${BASE}${path}`, {
    method: init.method ?? (init.body === undefined ? "GET" : "POST"),
    headers: {
      "Content-Type": "application/json",
      ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}),
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const text = await response.text();
  return { status: response.status, data: text ? JSON.parse(text) : null };
}

async function login(email: string, password: string, role?: string) {
  const { status, data } = await call("/auth/login", { body: { email, password, role } });
  assert.equal(status, 200, `login ${email}: ${JSON.stringify(data)}`);
  return data.token as string;
}

const PATIENT = { email: "ananya@careclinic.test", password: "Patient@2026" };
const DOCTOR = { email: "dr.rajesh@careclinic.test", password: "Doctor@2026" };
const STAFF = { email: "admin@careclinic.test", password: "Admin@2026" };

test("each app only admits its own kind of account", { skip }, async () => {
  const refused = await call("/auth/login", {
    body: { ...PATIENT, role: "admin" },
  });
  assert.equal(refused.status, 403);
  assert.match(refused.data.error, /admin or receptionist/);

  const staffOnDoctorApp = await call("/auth/login", { body: { ...STAFF, role: "doctor" } });
  assert.equal(staffOnDoctorApp.status, 403);

  const patientToken = await login(PATIENT.email, PATIENT.password, "patient");
  const forbidden = await call("/api/admin/dashboard", { token: patientToken });
  assert.equal(forbidden.status, 403, "a patient token must not read the clinic dashboard");
});

test("a patient books a free slot and the desk sees it", { skip }, async () => {
  const patient = await login(PATIENT.email, PATIENT.password, "patient");
  const staff = await login(STAFF.email, STAFF.password, "admin");

  const doctors = await call("/api/public/doctors", {});
  assert.equal(doctors.status, 200);
  const doctor = doctors.data.doctors[0];

  const date = new Date();
  date.setDate(date.getDate() + 3);
  const on = date.toISOString().slice(0, 10);

  const slots = await call(`/api/patient/doctors/${doctor.id}/slots?date=${on}`, { token: patient });
  assert.equal(slots.status, 200);
  const free = (slots.data.slots ?? []).filter((s: any) => s.available);
  if (free.length === 0) return; // the doctor is fully booked that day; nothing to assert

  const booked = await call("/api/patient/book", {
    token: patient,
    body: {
      doctorId: doctor.id,
      appointmentType: "in_clinic",
      scheduledDate: on,
      startTime: free[0].start_time,
      notes: "Workflow test booking",
    },
  });
  assert.equal(booked.status, 201, JSON.stringify(booked.data));
  const appointment = booked.data.appointment;

  const again = await call("/api/patient/book", {
    token: patient,
    body: {
      doctorId: doctor.id,
      appointmentType: "in_clinic",
      scheduledDate: on,
      startTime: free[0].start_time,
    },
  });
  assert.equal(again.status, 409, "the same slot must not be bookable twice");

  const master = await call(`/api/admin/appointments?date=${on}`, { token: staff });
  assert.equal(master.status, 200);
  assert.ok(
    master.data.appointments.some((a: any) => a.id === appointment.id),
    "the clinic console should list the appointment the patient just made"
  );

  const cancelled = await call(`/api/patient/appointments/${appointment.id}/cancel`, {
    token: patient,
    body: { reason: "Workflow test cleanup" },
  });
  assert.equal(cancelled.status, 200);
  assert.equal(cancelled.data.refund.refundPercentage, 100, "three days' notice is a full refund");
});

test("the front desk checks a patient in and calls the token", { skip }, async () => {
  const staff = await login(STAFF.email, STAFF.password, "admin");

  const desk = await call("/api/admin/front-desk", { token: staff });
  assert.equal(desk.status, 200);
  const waiting = desk.data.queue.find((a: any) => a.status === "booked");
  if (!waiting) return; // everyone on today's list has already arrived

  const arrived = await call("/api/admin/check-in", { token: staff, body: { appointmentId: waiting.id } });
  assert.equal(arrived.status, 200, JSON.stringify(arrived.data));
  assert.equal(arrived.data.appointment.status, "checked_in");
  assert.ok(arrived.data.appointment.token_number > 0, "check-in must issue a token");

  const called = await call(`/api/admin/queue/${waiting.id}/call`, { token: staff, method: "POST" });
  assert.equal(called.status, 200);
  assert.equal(called.data.appointment.queue_status, "called");

  const board = await call("/api/admin/queue-display", {});
  assert.equal(board.status, 200, "the waiting-room board is public");
  assert.ok(Array.isArray(board.data.activeQueue));
});

test("a doctor's consultation produces a prescription the patient can read", { skip }, async () => {
  const doctor = await login(DOCTOR.email, DOCTOR.password, "doctor");
  const patient = await login(PATIENT.email, PATIENT.password, "patient");

  const queue = await call("/api/doctor/queue", { token: doctor });
  assert.equal(queue.status, 200);
  const waiting = queue.data.queue.find((a: any) => a.status === "checked_in");
  if (!waiting) return; // nobody is waiting in this run

  const started = await call(`/api/doctor/consult/${waiting.id}/start`, { token: doctor, method: "POST" });
  assert.equal(started.status, 200, JSON.stringify(started.data));
  const consultationId = started.data.consultation.id;

  const soap = await call(`/api/doctor/consult/${waiting.id}/soap`, {
    token: doctor,
    body: {
      subjective: "Workflow test: routine review, no new complaints.",
      objective: "BP 124/80 mmHg, pulse 72/min, chest clear.",
      assessment: "Stable.",
      plan: "Continue current therapy; review in three months.",
      diagnoses: [{ icd10Code: "I10", conditionName: "Essential (primary) hypertension", isPrimary: true }],
    },
  });
  assert.equal(soap.status, 200, JSON.stringify(soap.data));

  const prescribed = await call(`/api/doctor/consult/${waiting.id}/prescribe`, {
    token: doctor,
    body: {
      diagnosisSummary: "Essential hypertension, controlled",
      items: [
        {
          medicineName: "Telmisartan",
          dosageForm: "tablet",
          strength: "40mg",
          frequency: "1-0-0",
          timing: "before_food",
          durationDays: 30,
        },
      ],
    },
  });
  assert.equal(prescribed.status, 201, JSON.stringify(prescribed.data));
  const prescriptionId = prescribed.data.prescription.id;

  const tamper = await call(`/api/doctor/consult/${waiting.id}/prescribe`, {
    token: doctor,
    body: { diagnosisSummary: "Changed after signing", items: [{ medicineName: "X", dosageForm: "tablet", strength: "1mg", frequency: "1-0-0", timing: "after_food" }] },
  });
  assert.ok(tamper.status >= 400, "a signed prescription must not be rewritten");

  const done = await call(`/api/doctor/consult/${waiting.id}/complete`, { token: doctor, method: "POST" });
  assert.equal(done.status, 200, JSON.stringify(done.data));

  const mine = await call("/api/patient/prescriptions", { token: patient });
  assert.equal(mine.status, 200);
  if (waiting.patient_id === mine.data.prescriptions[0]?.patient_id) {
    assert.ok(
      mine.data.prescriptions.some((p: any) => p.id === prescriptionId),
      "the patient should see the prescription the doctor just signed"
    );
  }

  const audit = await call("/api/admin/audit-logs", { token: await login(STAFF.email, STAFF.password, "admin") });
  assert.equal(audit.status, 200);
  assert.ok(
    audit.data.auditLogs.some((row: any) => row.resource_id === prescriptionId || row.resource_id === consultationId),
    "issuing a prescription must appear in the chart access audit"
  );
});

test("the cashier collects an outstanding invoice", { skip }, async () => {
  const staff = await login(STAFF.email, STAFF.password, "admin");

  const pending = await call("/api/admin/billing?status=pending", { token: staff });
  assert.equal(pending.status, 200);
  const invoice = pending.data.invoices[0];
  if (!invoice) return; // nothing outstanding in this run

  const collected = await call(`/api/admin/invoices/${invoice.id}/collect`, {
    token: staff,
    body: { paymentMethod: "cash" },
  });
  assert.equal(collected.status, 200, JSON.stringify(collected.data));
  assert.equal(collected.data.invoice.payment_status, "paid");

  const receipt = await call(`/api/admin/invoices/${invoice.id}`, { token: staff });
  assert.equal(receipt.status, 200);
  assert.equal(receipt.data.invoice.payment_method, "cash");
  assert.ok(receipt.data.items.length > 0, "a receipt needs line items");
});

test("the clinic's reports add up", { skip }, async () => {
  const staff = await login(STAFF.email, STAFF.password, "admin");

  const reports = await call("/api/admin/reports?days=30", { token: staff });
  assert.equal(reports.status, 200);
  assert.ok(reports.data.daily.length > 0, "30 days of a seeded clinic should have footfall");
  assert.ok(reports.data.specialties.length >= 5, "twelve doctors cover several specialties");

  const booked = reports.data.daily.reduce((sum: number, row: any) => sum + Number(row.booked), 0);
  assert.equal(
    booked,
    Number(reports.data.totals.total),
    "the daily rows must add up to the headline count"
  );

  const rooms = await call("/api/admin/rooms", { token: staff });
  assert.equal(rooms.status, 200);
  assert.equal(rooms.data.rooms.length, 12, "every doctor has a chamber row");
});
