import { Hono } from "hono";
import { createHash, randomInt } from "node:crypto";
import { config } from "../config.ts";
import { one, query, tx } from "../db.ts";
import { hashPassword, passwordProblem, verifyPassword } from "../auth/password.ts";
import { type AppEnv, requireAuth } from "../auth/middleware.ts";
import { badRequest, conflict, forbidden, unauthorized } from "../lib/errors.ts";
import { email, oneOf, phone, str } from "../lib/validate.ts";
import { mockSms } from "../providers/sms.ts";
import { issueSession, loadSessionUser, refreshSession, revokeRefresh, type SessionUser } from "../services/sessions.ts";
import { postLedger } from "../services/wallet.ts";
import { body } from "./util.ts";

export const authRoutes = new Hono<AppEnv>();

const COLORS = ["#5B5BD6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6"];
const WELCOME_CREDIT = 100;
const USER_COLUMNS = "id, role, full_name, email, phone, avatar_color, status";

function assertActive(user: SessionUser | null): SessionUser {
  if (!user) throw unauthorized("Wrong email or password.");
  if (user.status !== "active") throw forbidden("This account is suspended. Contact support.");
  return user;
}

/** Riders sign up here and get a welcome credit. */
authRoutes.post("/register", async (c) => {
  const data = await body(c);
  const fullName = str(data, "full_name", { min: 2, max: 80 });
  const mail = email(data);
  const tel = data.phone ? phone(data) : null;
  const problem = passwordProblem(data.password);
  if (problem) throw badRequest(problem, "weak_password");
  const user = await tx(async (client) => {
    try {
      const created = await client.query<SessionUser>(
        `INSERT INTO users (role, full_name, email, phone, password_hash, avatar_color)
         VALUES ('rider', $1, $2, $3, $4, $5) RETURNING ${USER_COLUMNS}`,
        [fullName, mail, tel, hashPassword(String(data.password)), COLORS[randomInt(COLORS.length)]],
      );
      await postLedger(client, created.rows[0].id, "topup", WELCOME_CREDIT, { reference: "WELCOME", note: "Welcome credit" });
      return created.rows[0];
    } catch (error) {
      if ((error as { code?: string }).code === "23505") throw conflict("An account with that email or phone already exists.", "account_exists");
      throw error;
    }
  });
  return c.json(await issueSession(user), 201);
});

/** Drivers apply here; an admin approves them before they can go online. */
authRoutes.post("/register-driver", async (c) => {
  const data = await body(c);
  const fullName = str(data, "full_name", { min: 2, max: 80 });
  const mail = email(data);
  const tel = phone(data);
  const problem = passwordProblem(data.password);
  if (problem) throw badRequest(problem, "weak_password");
  const vehicleType = oneOf(data, "vehicle_type", ["bike", "auto", "mini", "sedan", "xl"] as const);
  const user = await tx(async (client) => {
    try {
      const created = await client.query<SessionUser>(
        `INSERT INTO users (role, full_name, email, phone, password_hash, avatar_color)
         VALUES ('driver', $1, $2, $3, $4, $5) RETURNING ${USER_COLUMNS}`,
        [fullName, mail, tel, hashPassword(String(data.password)), COLORS[randomInt(COLORS.length)]],
      );
      const id = created.rows[0].id;
      await client.query(
        `INSERT INTO drivers (user_id, vehicle_type, vehicle_make, vehicle_model, vehicle_color, plate, license_no)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [id, vehicleType, str(data, "vehicle_make", { max: 40 }), str(data, "vehicle_model", { max: 40 }),
         str(data, "vehicle_color", { max: 30 }), str(data, "plate", { max: 20 }).toUpperCase(), str(data, "license_no", { max: 30 })],
      );
      for (const kind of ["license", "registration", "insurance", "photo"]) {
        await client.query("INSERT INTO driver_documents (driver_id, kind) VALUES ($1, $2)", [id, kind]);
      }
      await postLedger(client, id, "adjustment", 0, { note: "Wallet opened" });
      return created.rows[0];
    } catch (error) {
      if ((error as { code?: string }).code === "23505") throw conflict("That email, phone or plate is already registered.", "account_exists");
      throw error;
    }
  });
  return c.json(await issueSession(user), 201);
});

authRoutes.post("/login", async (c) => {
  const data = await body(c);
  const row = await one<SessionUser & { password_hash: string | null }>(
    `SELECT ${USER_COLUMNS}, password_hash FROM users WHERE email = $1`,
    [email(data)],
  );
  const password = typeof data.password === "string" ? data.password : "";
  if (!row || !verifyPassword(password, row.password_hash)) throw unauthorized("Wrong email or password.");
  const role = typeof data.role === "string" ? data.role : null;
  if (role && role !== row.role) throw forbidden(`This is a ${row.role} account. Use the ${row.role} app to sign in.`);
  const { password_hash: _ignored, ...user } = row;
  return c.json(await issueSession(assertActive(user)));
});

const hashCode = (phoneNumber: string, code: string) => createHash("sha256").update(`${phoneNumber}:${code}`).digest("hex");

authRoutes.post("/otp/request", async (c) => {
  const tel = phone(await body(c));
  const code = String(randomInt(100000, 1000000));
  await query(
    `INSERT INTO otp_codes (phone, code_hash, expires_at, attempts) VALUES ($1, $2, now() + interval '5 minutes', 0)
     ON CONFLICT (phone) DO UPDATE SET code_hash = EXCLUDED.code_hash, expires_at = EXCLUDED.expires_at, attempts = 0`,
    [tel, hashCode(tel, code)],
  );
  await mockSms.send(tel, `Your RideNow code is ${code}. It expires in 5 minutes.`);
  return c.json({ sent: true, phone: tel, demo_hint: config.preview ? "In the preview, 123456 also works." : undefined });
});

authRoutes.post("/otp/verify", async (c) => {
  const data = await body(c);
  const tel = phone(data);
  const code = str(data, "code", { min: 6, max: 6 });
  const row = await one<{ code_hash: string; expired: boolean; attempts: number }>(
    "SELECT code_hash, expires_at < now() AS expired, attempts FROM otp_codes WHERE phone = $1",
    [tel],
  );
  const demoOk = config.preview && code === "123456";
  if (!demoOk) {
    if (!row || row.expired) throw badRequest("The code has expired. Request a new one.", "otp_expired");
    if (row.attempts >= 5) throw badRequest("Too many attempts. Request a new code.", "otp_locked");
    if (row.code_hash !== hashCode(tel, code)) {
      await query("UPDATE otp_codes SET attempts = attempts + 1 WHERE phone = $1", [tel]);
      throw badRequest("That code is not right.", "otp_wrong");
    }
  }
  await query("DELETE FROM otp_codes WHERE phone = $1", [tel]);
  let user = await one<SessionUser>(`SELECT ${USER_COLUMNS} FROM users WHERE phone = $1`, [tel]);
  if (!user) {
    // First sign-in by phone creates a rider account.
    user = await tx(async (client) => {
      const created = await client.query<SessionUser>(
        `INSERT INTO users (role, full_name, phone, avatar_color) VALUES ('rider', $1, $2, $3) RETURNING ${USER_COLUMNS}`,
        [typeof data.full_name === "string" && data.full_name.trim() ? data.full_name.trim().slice(0, 80) : "RideNow rider", tel, COLORS[randomInt(COLORS.length)]],
      );
      await postLedger(client, created.rows[0].id, "topup", WELCOME_CREDIT, { reference: "WELCOME", note: "Welcome credit" });
      return created.rows[0];
    });
  }
  return c.json(await issueSession(assertActive(user)));
});

authRoutes.post("/refresh", async (c) => {
  const token = str(await body(c), "refresh_token", { max: 200 });
  return c.json(await refreshSession(token));
});

authRoutes.post("/logout", async (c) => {
  const data = await body(c);
  if (typeof data.refresh_token === "string") await revokeRefresh(data.refresh_token);
  return c.body(null, 204);
});

authRoutes.get("/me", requireAuth(), async (c) => {
  const user = await loadSessionUser(c.get("user").sub);
  if (!user) throw unauthorized();
  return c.json(user);
});

authRoutes.patch("/me", requireAuth(), async (c) => {
  const data = await body(c);
  const updates: string[] = [];
  const values: unknown[] = [c.get("user").sub];
  if (data.full_name !== undefined) {
    values.push(str(data, "full_name", { min: 2, max: 80 }));
    updates.push(`full_name = $${values.length}`);
  }
  if (data.phone !== undefined) {
    values.push(phone(data));
    updates.push(`phone = $${values.length}`);
  }
  if (data.password !== undefined) {
    const problem = passwordProblem(data.password);
    if (problem) throw badRequest(problem, "weak_password");
    values.push(hashPassword(String(data.password)));
    updates.push(`password_hash = $${values.length}`);
  }
  if (updates.length === 0) throw badRequest("Nothing to update.");
  try {
    const user = await one<SessionUser>(`UPDATE users SET ${updates.join(", ")} WHERE id = $1 RETURNING ${USER_COLUMNS}`, values);
    return c.json(user);
  } catch (error) {
    if ((error as { code?: string }).code === "23505") throw conflict("That phone number is already used by another account.");
    throw error;
  }
});
