// CareClinic screenshot plan for scripts/capture-template-screens.mjs (R-538).
// Captures all 48 screens across the patient portal, the doctor's clinical workstation and the
// clinic operations console, plus a composed cover image.
//
// Every route that takes an id resolves it from the running API first, so the shots are of real
// records in the seeded clinic rather than placeholders.

export const users = {
  patient: { email: "ananya@careclinic.test", password: "Patient@2026", role: "patient" },
  doctor: { email: "dr.rajesh@careclinic.test", password: "Doctor@2026", role: "doctor" },
  admin: { email: "admin@careclinic.test", password: "Admin@2026", role: "admin" },
};

/**
 * The apps keep the bearer token under `careclinic_token` (and a per-role copy), with the signed-in
 * user beside it, which is what packages/shared/src/api.ts reads on start-up.
 */
export function storage(_app, session) {
  const token = session.token ?? session.access_token;
  return [
    ["careclinic_token", token],
    [`careclinic_${session.user.role}_token`, token],
    ["careclinic_user", JSON.stringify(session.user)],
  ];
}

export default async function capture({ api, shot: rawShot, render, image }) {
  // Every screen is captured as that app's demo user. The two sign-in pages and the waiting-room
  // board are the exceptions: they are what a signed-out visitor sees.
  const SIGNED_OUT = new Set(["login", "live-queue-board"]);
  const shot = (options) => rawShot({ as: SIGNED_OUT.has(options.name) ? null : options.app, ...options });

  // Real records from the seeded clinic, so no screen shows a placeholder id.
  const [patientAppointments, prescriptions, patientLabs, doctors, doctorQueue, adminInvoices] =
    await Promise.all([
      api("patient", "GET", "/api/patient/appointments"),
      api("patient", "GET", "/api/patient/prescriptions"),
      api("patient", "GET", "/api/patient/labs"),
      api(null, "GET", "/api/public/doctors"),
      api("doctor", "GET", "/api/doctor/queue"),
      api("admin", "GET", "/api/admin/billing"),
    ]);

  const upcoming =
    patientAppointments.appointments.find((a) => a.status === "booked") ??
    patientAppointments.appointments[0];
  const completedVisit =
    patientAppointments.appointments.find((a) => a.status === "completed") ?? upcoming;
  const videoVisit =
    patientAppointments.appointments.find((a) => a.appointment_type === "video") ?? completedVisit;
  const rajesh = doctors.doctors.find((d) => d.email === users.doctor.email) ?? doctors.doctors[0];
  const inConsult = doctorQueue.queue.find((a) => a.status === "in_consult") ?? doctorQueue.queue[0];
  const paidInvoice =
    adminInvoices.invoices.find((i) => i.payment_status === "paid") ?? adminInvoices.invoices[0];
  const reportedLab =
    patientLabs.orders.find((o) => o.status === "completed") ?? patientLabs.orders[0];

  const id = {
    doctor: rajesh.doctor_id ?? rajesh.id,
    upcomingVisit: upcoming.id,
    completedVisit: completedVisit.id,
    videoVisit: videoVisit.id,
    prescription: prescriptions.prescriptions[0].id,
    labOrder: reportedLab.id,
    consult: inConsult.id,
    chartPatient: inConsult.patient_id,
    invoice: paidInvoice.id,
  };

  // --- Patient Web App (16 screens) --------------------------------------------------------------
  await shot({
    app: "patient",
    name: "home",
    route: "/",
    title: "Patient Home",
    description: "Personalized clinical landing with active appointment banner, queue token countdown, and doctor specialties.",
    highlight: true,
  });

  await shot({
    app: "patient",
    name: "doctors",
    route: "/doctors",
    title: "Doctor Directory",
    description: "Searchable specialist directory filtered by department, consultation mode, and consultation tariffs.",
    highlight: true,
  });

  await shot({
    app: "patient",
    name: "doctor-profile",
    route: `/doctors/${id.doctor}`,
    displayRoute: "/doctors/[id]",
    title: "Doctor Profile",
    description: "Physician credentials, medical council registration, OPD shift timetable, and verified patient reviews.",
  });

  await shot({
    app: "patient",
    name: "booking",
    route: `/book/${id.doctor}`,
    displayRoute: "/book/[doctorId]",
    title: "Book Appointment",
    description: "7-day calendar view with dynamic 20-minute slot matrix, family dependent selector, and intake notes.",
    highlight: true,
  });

  await shot({
    app: "patient",
    name: "payment",
    route: `/checkout/${id.upcomingVisit}`,
    displayRoute: "/checkout/[appointmentId]",
    title: "Consultation Fee Payment",
    description: "Checkout summary with instant UPI QR, card processing, and clinic desk payment alternatives.",
  });

  await shot({
    app: "patient",
    name: "booking-confirmation",
    route: `/appointments/${id.upcomingVisit}/confirmation`,
    displayRoute: "/appointments/[id]/confirmation",
    title: "Booking Confirmation",
    description: "Downloadable booking receipt with sequential token number, clinic chamber location, and arrival rules.",
  });

  await shot({
    app: "patient",
    name: "appointments",
    route: "/appointments",
    title: "My Appointments",
    description: "Upcoming and past appointment tracking with real-time status badges and 1-click video join.",
    highlight: true,
  });

  await shot({
    app: "patient",
    name: "appointment-detail",
    route: `/appointments/${id.completedVisit}`,
    displayRoute: "/appointments/[id]",
    title: "Appointment Detail",
    description: "Detailed consultation tracker with 4-stage milestone stepper and tiered cancellation refund calculator.",
  });

  await shot({
    app: "patient",
    name: "telehealth-room",
    route: `/telehealth/${id.videoVisit}`,
    displayRoute: "/telehealth/[appointmentId]",
    title: "Telehealth Video Room",
    description: "WebRTC peer consultation with physician video feed, patient self-view PIP, and encrypted in-call chat.",
    highlight: true,
  });

  await shot({
    app: "patient",
    name: "prescriptions",
    route: "/prescriptions",
    title: "Digital Prescriptions",
    description: "Searchable medication history with cryptographic verification badges and dosage guidelines.",
    highlight: true,
  });

  await shot({
    app: "patient",
    name: "prescription-detail",
    route: `/prescriptions/${id.prescription}`,
    displayRoute: "/prescriptions/[id]",
    title: "Prescription View",
    description: "NABH-compliant printable clinical prescription slip with ICD-10 diagnosis, dosage, and doctor sign-off.",
  });

  await shot({
    app: "patient",
    name: "lab-reports",
    route: "/lab-reports",
    title: "Diagnostic Lab Reports",
    description: "Diagnostic pathology reports archive with reference intervals, abnormal flags, and laboratory pathologist verification.",
  });

  await shot({
    app: "patient",
    name: "medical-records",
    route: "/records",
    title: "Medical Records & Vitals",
    description: "Personal health record tracking blood pressure, pulse, glucose levels, drug allergies, and immunization history.",
  });

  await shot({
    app: "patient",
    name: "family-members",
    route: "/family",
    title: "Family Members",
    description: "Household dependents directory enabling unified appointment booking and pediatric records management.",
  });

  await shot({
    app: "patient",
    name: "invoices",
    route: "/invoices",
    title: "Billing Invoices",
    description: "Itemized consultation receipts, diagnostic test charges, and tax invoice downloads.",
  });

  await shot({
    app: "patient",
    name: "login",
    route: "/login",
    title: "Patient Sign In",
    description: "Patient authentication with 1-click Ananya Deshmukh demo credentials and new patient onboarding.",
  });

  // --- Doctor Clinical Workstation (14 screens) ---------------------------------------------------
  await shot({
    app: "doctor",
    name: "login",
    route: "/login",
    title: "Doctor Sign In",
    description: "Physician authentication with 1-click Dr. Rajesh Varma (Cardiology) demo credentials.",
  });

  await shot({
    app: "doctor",
    name: "dashboard",
    route: "/",
    title: "Physician Dashboard",
    description: "Clinical command center with daily appointment metrics, active patient spotlight, and urgent diagnostic alerts.",
    highlight: true,
  });

  await shot({
    app: "doctor",
    name: "queue",
    route: "/queue",
    title: "Today's Patient Queue",
    description: "Live outpatient queue with token numbers, arrival status, wait timers, and 1-click consultation initiation.",
    highlight: true,
  });

  await shot({
    app: "doctor",
    name: "consultation",
    route: `/consult/${id.consult}`,
    displayRoute: "/consult/[appointmentId]",
    title: "Clinical Consultation Screen",
    description: "Active consultation workspace integrating patient demographics, vital signs, allergy warnings, and action tabs.",
    highlight: true,
  });

  await shot({
    app: "doctor",
    name: "soap-notes",
    route: `/consult/${id.consult}/soap`,
    displayRoute: "/consult/[appointmentId]/soap",
    title: "SOAP Clinical Notes",
    description: "Structured medical documentation (Subjective, Objective, Assessment, Plan) with ICD-10 diagnostic coding.",
  });

  await shot({
    app: "doctor",
    name: "prescription-builder",
    route: `/consult/${id.consult}/prescription`,
    displayRoute: "/consult/[appointmentId]/prescription",
    title: "E-Prescription Builder",
    description: "Multi-item digital prescription generator with dosage, frequency, food timing, and cryptographic signature.",
    highlight: true,
  });

  await shot({
    app: "doctor",
    name: "lab-order",
    route: `/consult/${id.consult}/labs`,
    displayRoute: "/consult/[appointmentId]/labs",
    title: "Diagnostic Lab Order",
    description: "Pathology and radiology test ordering console with clinical indications and urgent turnaround prioritization.",
  });

  await shot({
    app: "doctor",
    name: "patient-chart",
    route: `/patients/${id.chartPatient}`,
    displayRoute: "/patients/[id]",
    title: "Patient Medical Chart",
    description: "Longitudinal health record displaying historical encounters, vital sign trajectories, and HIPAA audit badge.",
  });

  await shot({
    app: "doctor",
    name: "patient-history",
    route: "/patients",
    displayRoute: "/patients",
    title: "Patient List",
    description: "Comprehensive medical directory with chronic condition filters, last consultation dates, and panel indicators.",
  });

  await shot({
    app: "doctor",
    name: "schedule-settings",
    route: "/schedule",
    title: "Schedule Configuration",
    description: "Weekly consultation availability schedule, slot duration controls, and session capacity quotas.",
  });

  await shot({
    app: "doctor",
    name: "availability-rules",
    route: "/schedule/rules",
    title: "Availability Rules",
    description: "Physician leave requests, emergency slot blocking, and holiday schedule overrides.",
  });

  await shot({
    app: "doctor",
    name: "earnings",
    route: "/earnings",
    title: "Doctor Earnings & Payouts",
    description: "Consultation revenue breakdown by in-clinic vs video consults, cashier settlements, and payout statements.",
  });

  await shot({
    app: "doctor",
    name: "reviews",
    route: "/reviews",
    title: "Patient Reviews",
    description: "Patient feedback and clinical rating aggregation with department benchmark comparison.",
  });

  await shot({
    app: "doctor",
    name: "telehealth-call",
    route: `/telehealth/${id.videoVisit}`,
    displayRoute: "/telehealth/[appointmentId]",
    title: "Doctor Telehealth Interface",
    description: "Physician video consultation console with floating patient chart and concurrent prescription draft.",
    highlight: true,
  });

  // --- Clinic Operations Console (18 screens) ----------------------------------------------------
  await shot({
    app: "admin",
    name: "login",
    route: "/login",
    title: "Staff Sign In",
    description: "Clinic staff sign-in. Patient and doctor accounts are refused by the API with a 403.",
  });

  await shot({
    app: "admin",
    name: "dashboard",
    route: "/",
    title: "Clinic Operations Dashboard",
    description: "Comprehensive clinic KPI overview: daily footfall, active consults, revenue, and queue health.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "front-desk",
    route: "/front-desk",
    title: "Front Desk Reception",
    description: "Primary reception console: token queue advancement, patient lookups, and room allocations.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "check-in",
    route: "/check-in",
    title: "Patient Check-In",
    description: "One-click arrival check-in issuing sequential physical queue token number and SMS notice.",
  });

  await shot({
    app: "admin",
    name: "walk-in",
    route: "/walk-in",
    title: "Walk-In Appointment Booking",
    description: "Rapid walk-in scheduling assigning immediate next-available slot with on-duty physician.",
  });

  await shot({
    app: "admin",
    name: "appointments",
    route: "/appointments",
    title: "Global Appointments Master",
    description: "Complete clinic appointments directory with date range picker, specialty filters, and CSV export.",
  });

  await shot({
    app: "admin",
    name: "appointment-detail",
    route: `/appointments/${id.completedVisit}`,
    displayRoute: "/appointments/[id]",
    title: "Appointment Investigation",
    description: "Deep appointment audit showing timeline, vitals records, billing status, and cancellation trail.",
  });

  await shot({
    app: "admin",
    name: "doctors",
    route: "/doctors",
    title: "Doctor Staff Directory",
    description: "Physician credentialing management, license verification, specialty tagging, and room mapping.",
  });

  await shot({
    app: "admin",
    name: "doctor-schedule",
    route: `/doctors/${id.doctor}/schedule`,
    displayRoute: "/doctors/[id]/schedule",
    title: "Doctor Rostering & Schedules",
    description: "Clinic-wide doctor schedule calendar monitoring on-duty hours and planned physician leaves.",
  });

  await shot({
    app: "admin",
    name: "rooms",
    route: "/rooms",
    title: "Consultation Room Allocation",
    description: "Physical OPD examination room roster assigning active doctors to physical chambers.",
  });

  await shot({
    app: "admin",
    name: "billing",
    route: "/billing",
    title: "Clinic Billing & Cashier",
    description: "Front desk billing desk handling cash, card, and UPI collections for consultations and tests.",
  });

  await shot({
    app: "admin",
    name: "invoice-detail",
    route: `/billing/${id.invoice}`,
    displayRoute: "/billing/[id]",
    title: "Invoice Details & Receipts",
    description: "Itemized official medical receipt with GST compliance, clinic letterhead, and payment proof.",
  });

  await shot({
    app: "admin",
    name: "refunds",
    route: "/refunds",
    title: "Cancellation & Refunds",
    description: "Dispute and cancellation policy settlement processing automatic partial or full refunds.",
  });

  await shot({
    app: "admin",
    name: "lab-management",
    route: "/labs",
    title: "Diagnostic Lab Management",
    description: "Lab test catalog pricing, order processing queue, and technician report upload portal.",
  });

  await shot({
    app: "admin",
    name: "reports",
    route: "/reports",
    title: "Clinical Analytics & Footfall",
    description: "Multi-dimensional reports on daily patient footfall, specialty distribution, and no-show rates.",
  });

  await shot({
    app: "admin",
    name: "audit-logs",
    route: "/audit",
    title: "Security & Chart Access Audit",
    description: "HIPAA-compliant immutable audit log recording every electronic health record query by staff.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "settings",
    route: "/settings",
    title: "Clinic System Settings",
    description: "Default consultation slot duration, cancellation refund policies, and mock provider toggles.",
  });

  await shot({
    app: "admin",
    name: "live-queue-board",
    route: "/queue-display",
    title: "Live OPD Queue Display Board",
    description: "Waiting room TV monitor display board broadcasting live token numbers calling patients to OPD rooms.",
    highlight: true,
  });

  // --- Composed Marketing Cover Image (media/cover.jpg) -------------------------------------------
  const [adminShot, patientShot, doctorShot] = await Promise.all([
    image("media/admin/dashboard.jpg"),
    image("media/patient/home.jpg"),
    image("media/doctor/dashboard.jpg"),
  ]);

  await render(composeCoverHtml({ adminShot, patientShot, doctorShot }), {
    file: "cover.jpg",
    width: 1600,
    height: 1000,
  });
}

function composeCoverHtml({ adminShot, patientShot, doctorShot }) {
  return `<!doctype html><html><head><meta charset="utf-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      width: 1600px;
      height: 1000px;
      background: radial-gradient(circle at 15% 15%, #0d9488 0%, #0f172a 55%, #020617 100%);
      position: relative;
      overflow: hidden;
      color: #fff;
    }
    .title {
      position: absolute;
      top: 50px;
      left: 80px;
      z-index: 10;
    }
    .title h1 {
      font-size: 50px;
      font-weight: 900;
      letter-spacing: -1.5px;
      color: #ffffff;
      line-height: 1.1;
    }
    .title h1 span {
      background: linear-gradient(135deg, #2dd4bf 0%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .title p {
      font-size: 19px;
      color: #94a3b8;
      margin-top: 10px;
      max-width: 720px;
      line-height: 1.4;
    }
    .chips {
      position: absolute;
      top: 205px;
      left: 80px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      max-width: 900px;
      z-index: 10;
    }
    .chips b {
      font-size: 13px;
      font-weight: 700;
      padding: 8px 16px;
      border-radius: 999px;
      background: rgba(13, 148, 136, 0.2);
      border: 1px solid rgba(45, 212, 191, 0.4);
      color: #e2e8f0;
      letter-spacing: 0.3px;
    }
    .win {
      position: absolute;
      border-radius: 14px;
      overflow: hidden;
      background: #0f172a;
      box-shadow: 0 40px 90px -20px rgba(0,0,0,0.85);
      border: 1px solid rgba(255,255,255,0.12);
    }
    .win .bar {
      height: 30px;
      background: #1e293b;
      display: flex;
      align-items: center;
      gap: 7px;
      padding-left: 14px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .win .bar i { width: 11px; height: 11px; border-radius: 50%; background: #475569; }
    .win img { display: block; width: 100%; height: calc(100% - 30px); object-fit: cover; object-position: top; }
    .admin { left: 480px; top: 300px; width: 1040px; height: 660px; z-index: 1; }
    .patient { left: 70px; top: 400px; width: 580px; height: 520px; z-index: 2; }
    .doctor { left: 1120px; top: 120px; width: 400px; height: 320px; z-index: 3; }
    .label {
      position: absolute;
      font-size: 13px;
      font-weight: 700;
      color: #042f2e;
      background: #2dd4bf;
      padding: 6px 14px;
      border-radius: 8px;
      box-shadow: 0 4px 14px rgba(0,0,0,0.4);
      letter-spacing: 0.2px;
    }
  </style></head><body>
    <div class="title">
      <h1>CareClinic <span>Healthcare Platform</span></h1>
      <p>Clinical care, appointment scheduling, telemedicine video visits, electronic health records, and practice management for modern clinics.</p>
    </div>
    <div class="chips">
      <b>20-Min Slot Generator</b>
      <b>Tamper-Proof Digital Rx</b>
      <b>HIPAA Audit Ledger</b>
      <b>WebRTC Video Telehealth</b>
    </div>
    <div class="win admin"><div class="bar"><i></i><i></i><i></i></div><img src="${adminShot}"></div>
    <div class="win patient"><div class="bar"><i></i><i></i><i></i></div><img src="${patientShot}"></div>
    <div class="win doctor"><div class="bar"><i></i><i></i><i></i></div><img src="${doctorShot}"></div>
    <div class="label" style="left:86px;top:372px;z-index:10;">Patient Web App</div>
    <div class="label" style="left:496px;top:270px;z-index:10;">Clinic Operations Command Console</div>
    <div class="label" style="left:1136px;top:92px;z-index:10;">Physician Clinical Workstation</div>
  </body></html>`;
}
