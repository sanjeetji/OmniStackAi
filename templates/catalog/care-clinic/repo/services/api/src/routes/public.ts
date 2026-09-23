/** Public routes for CareClinic: health, authentication, doctor directory, and clinic catalog. */

import { Hono } from "hono";
import type { AppEnv } from "../auth/middleware.ts";
import { query } from "../db.ts";
import { verifyPassword, hashPassword } from "../auth/password.ts";
import { generateToken } from "../auth/tokens.ts";
import { BadRequestError, UnauthorizedError, ForbiddenError, ConflictError } from "../lib/errors.ts";

export const publicRoutes = new Hono<AppEnv>();

// Healthcheck
publicRoutes.get("/health", (c) => {
  return c.json({ status: "ok", service: "CareClinic API", version: "1.0.0" });
});

// User Authentication (Login)
// Each app sends the role it is for. A patient account signing in to the clinic console, or a
// receptionist signing in to the doctor workstation, is refused here rather than half-working.
const ROLE_GROUPS: Record<string, string[]> = {
  patient: ["patient"],
  doctor: ["doctor"],
  admin: ["admin", "receptionist"],
  receptionist: ["admin", "receptionist"],
};

publicRoutes.post("/auth/login", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const { email, password, role } = body;

  if (!email || !password) {
    throw new BadRequestError("Email and password are required");
  }

  const res = await query(
    `SELECT u.*, dp.clinic_id
     FROM users u
     LEFT JOIN doctor_profiles dp ON dp.doctor_id = u.id
     WHERE u.email = $1`,
    [email.toLowerCase().trim()]
  );

  if (res.rows.length === 0) {
    throw new UnauthorizedError("Invalid email or password");
  }

  const user = res.rows[0];
  const isValid = await verifyPassword(password, user.password_hash);
  if (!isValid) {
    throw new UnauthorizedError("Invalid email or password");
  }

  if (role) {
    const allowed = ROLE_GROUPS[role];
    if (!allowed) {
      throw new BadRequestError(`Unknown role: ${role}`);
    }
    if (!allowed.includes(user.role)) {
      throw new ForbiddenError(
        `This sign-in is for ${allowed.join(" or ")} accounts. ${user.email} is a ${user.role} account.`
      );
    }
  }

  const token = generateToken({
    userId: user.id,
    email: user.email,
    role: user.role,
    clinicId: user.clinic_id,
    doctorId: user.role === "doctor" ? user.id : undefined,
  });

  const { password_hash, ...safeUser } = user;

  return c.json({
    user: safeUser,
    token,
    access_token: token, // Compatible with runner auth standard
  });
});

// Patient Self-Registration
publicRoutes.post("/auth/register", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const { email, password, fullName, phone, bloodGroup, gender, dob } = body;

  if (!email || !password || !fullName) {
    throw new BadRequestError("Email, password, and full name are required");
  }

  const existing = await query(`SELECT id FROM users WHERE email = $1`, [
    email.toLowerCase().trim(),
  ]);
  if (existing.rows.length > 0) {
    throw new ConflictError("Account with this email already exists");
  }

  const passwordHash = await hashPassword(password);

  const userRes = await query(
    `INSERT INTO users (email, password_hash, full_name, phone, role)
     VALUES ($1, $2, $3, $4, 'patient')
     RETURNING id, email, full_name, phone, role, created_at`,
    [email.toLowerCase().trim(), passwordHash, fullName.trim(), phone || null]
  );

  const newUser = userRes.rows[0];

  // Initialize patient profile
  await query(
    `INSERT INTO patient_profiles (patient_id, dob, gender, blood_group)
     VALUES ($1, $2, $3, $4)`,
    [newUser.id, dob || null, gender || null, bloodGroup || null]
  );

  // Initialize empty medical history
  await query(`INSERT INTO medical_histories (patient_id) VALUES ($1)`, [newUser.id]);

  const token = generateToken({
    userId: newUser.id,
    email: newUser.email,
    role: "patient",
  });

  return c.json(
    {
      user: newUser,
      token,
      access_token: token,
    },
    201
  );
});

// Clinics List
publicRoutes.get("/api/public/clinics", async (c) => {
  const res = await query(
    `SELECT * FROM clinics WHERE is_active = TRUE ORDER BY name ASC`
  );
  return c.json({ clinics: res.rows });
});

// Specialties Catalog
publicRoutes.get("/api/public/specialties", async (c) => {
  const res = await query(`
    SELECT unnest(specialties) as specialty, COUNT(doctor_id) as doctor_count
    FROM doctor_profiles
    GROUP BY specialty
    ORDER BY doctor_count DESC, specialty ASC
  `);
  return c.json({ specialties: res.rows });
});

// Doctor Directory
publicRoutes.get("/api/public/doctors", async (c) => {
  const q = c.req.query("q")?.toLowerCase();
  const specialty = c.req.query("specialty");
  const clinicId = c.req.query("clinicId");

  let sql = `
    SELECT u.id, u.full_name, u.email, u.phone, u.avatar_url,
           dp.license_number, dp.qualification, dp.specialties, dp.experience_years,
           dp.consultation_fee_inr, dp.video_fee_inr, dp.bio, dp.room_number,
           dp.rating_avg, dp.rating_count, dp.is_accepting_patients,
           c.name as clinic_name, c.address as clinic_address, c.city as clinic_city
    FROM users u
    JOIN doctor_profiles dp ON dp.doctor_id = u.id
    LEFT JOIN clinics c ON c.id = dp.clinic_id
    WHERE u.role = 'doctor'
  `;
  const params: any[] = [];

  if (q) {
    params.push(`%${q}%`);
    sql += ` AND (LOWER(u.full_name) LIKE $${params.length} OR LOWER(dp.qualification) LIKE $${params.length})`;
  }

  if (specialty) {
    params.push(specialty);
    sql += ` AND $${params.length} = ANY(dp.specialties)`;
  }

  if (clinicId) {
    params.push(clinicId);
    sql += ` AND dp.clinic_id = $${params.length}`;
  }

  sql += ` ORDER BY dp.rating_avg DESC, dp.experience_years DESC`;

  const res = await query(sql, params);
  return c.json({ doctors: res.rows });
});

// Doctor Profile with Availability Shifts & Reviews
publicRoutes.get("/api/public/doctors/:id", async (c) => {
  const doctorId = c.req.param("id");

  const docRes = await query(
    `SELECT u.id, u.full_name, u.email, u.phone, u.avatar_url,
            dp.license_number, dp.qualification, dp.specialties, dp.experience_years,
            dp.consultation_fee_inr, dp.video_fee_inr, dp.bio, dp.room_number,
            dp.rating_avg, dp.rating_count, dp.is_accepting_patients,
            c.name as clinic_name, c.address as clinic_address, c.phone as clinic_phone
     FROM users u
     JOIN doctor_profiles dp ON dp.doctor_id = u.id
     LEFT JOIN clinics c ON c.id = dp.clinic_id
     WHERE u.id = $1 AND u.role = 'doctor'`,
    [doctorId]
  );

  if (docRes.rows.length === 0) {
    return c.json({ error: "Doctor not found" }, 404);
  }

  const shiftsRes = await query(
    `SELECT day_of_week, start_time, end_time, slot_duration_mins, is_available
     FROM doctor_availability
     WHERE doctor_id = $1
     ORDER BY day_of_week ASC`,
    [doctorId]
  );

  const reviewsRes = await query(
    `SELECT r.*, u.full_name as patient_name
     FROM patient_reviews r
     JOIN users u ON u.id = r.patient_id
     WHERE r.doctor_id = $1
     ORDER BY r.created_at DESC
     LIMIT 15`,
    [doctorId]
  );

  return c.json({
    doctor: docRes.rows[0],
    availability: shiftsRes.rows,
    reviews: reviewsRes.rows,
  });
});

// Lab Test Catalog
publicRoutes.get("/api/public/lab-tests", async (c) => {
  const res = await query(
    `SELECT * FROM lab_test_catalog ORDER BY category ASC, name ASC`
  );
  return c.json({ tests: res.rows });
});
