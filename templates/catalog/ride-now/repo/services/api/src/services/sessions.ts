import { config } from "../config.ts";
import { one, query } from "../db.ts";
import { unauthorized } from "../lib/errors.ts";
import { hashToken, newRefreshToken, signJwt } from "../auth/tokens.ts";

export interface SessionUser {
  id: string;
  role: "rider" | "driver" | "admin";
  full_name: string;
  email: string | null;
  phone: string | null;
  avatar_color: string;
  status: string;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: SessionUser;
}

export async function issueSession(user: SessionUser): Promise<Session> {
  const refresh = newRefreshToken();
  await query(
    `INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, now() + ($3 || ' days')::interval)`,
    [user.id, refresh.hash, String(config.refreshTtlDays)],
  );
  await query("UPDATE users SET last_login_at = now() WHERE id = $1", [user.id]);
  return {
    access_token: signJwt({ sub: user.id, role: user.role, name: user.full_name }, config.jwtSecret, config.accessTtlSeconds),
    refresh_token: refresh.token,
    expires_in: config.accessTtlSeconds,
    user,
  };
}

/** Rotate a refresh token: the old one is revoked; a reused revoked token revokes the whole family. */
export async function refreshSession(token: string): Promise<Session> {
  const row = await one<{ id: string; user_id: string; revoked_at: Date | null; expired: boolean }>(
    "SELECT id, user_id, revoked_at, expires_at < now() AS expired FROM refresh_tokens WHERE token_hash = $1",
    [hashToken(token)],
  );
  if (!row || row.expired) throw unauthorized("Your session has ended. Please sign in again.");
  if (row.revoked_at) {
    await query("UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = $1 AND revoked_at IS NULL", [row.user_id]);
    throw unauthorized("Your session has ended. Please sign in again.");
  }
  await query("UPDATE refresh_tokens SET revoked_at = now() WHERE id = $1", [row.id]);
  const user = await loadSessionUser(row.user_id);
  if (!user || user.status !== "active") throw unauthorized("This account is not active.");
  return issueSession(user);
}

export async function revokeRefresh(token: string): Promise<void> {
  await query("UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = $1 AND revoked_at IS NULL", [hashToken(token)]);
}

export async function loadSessionUser(id: string): Promise<SessionUser | null> {
  return one<SessionUser>(
    "SELECT id, role, full_name, email, phone, avatar_color, status FROM users WHERE id = $1",
    [id],
  );
}
