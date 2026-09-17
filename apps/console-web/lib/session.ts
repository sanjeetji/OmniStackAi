import type { NextRequest } from "next/server";
import { cookies } from "next/headers";
import { currentUser, type ControlPlaneUser } from "./control-plane";

/** The only place the session cookie's name and lifetime are defined. The cookie holds the raw
 * control-plane session token but is httpOnly - client-side JavaScript can never read it. */
export const SESSION_COOKIE_NAME = "omnistackai_session";

/** 30 days, matching the control-plane's own default OMNISTACKAI_SESSION_TTL (720h). If the
 * control-plane session expires first, /auth/me simply starts returning 401 and the cookie stops
 * being useful until the next login - this is just an outer bound on the cookie's own lifetime. */
export const SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

/** Server-only. Reads the session cookie (if any) and resolves the current user against the
 * control-plane. Returns null for "not signed in" - callers decide whether that means a redirect
 * to /login or just rendering a signed-out view; this never throws for that ordinary case. */
export async function getCurrentUser(): Promise<ControlPlaneUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }
  return currentUser(token);
}

/** Server-only. Reads the raw session token, if any - only ever passed straight to the
 * control-plane (e.g. for logout), never rendered or sent anywhere else. */
export async function getSessionToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(SESSION_COOKIE_NAME)?.value ?? null;
}

/** Whether the *current request* actually arrived over HTTPS - checked per-request rather than
 * from NODE_ENV, because `next start` always sets NODE_ENV=production regardless of the real
 * protocol. Getting this wrong the other way (marking a cookie Secure on a plain-HTTP local dev
 * server) silently breaks login in a real browser, which enforces the Secure attribute even
 * though curl does not - confirmed by hand while testing this app. Checks
 * `x-forwarded-proto` first for the common case of running behind a reverse proxy/load balancer
 * that terminates TLS. */
export function isSecureRequest(request: NextRequest): boolean {
  const forwardedProto = request.headers.get("x-forwarded-proto");
  if (forwardedProto) {
    return forwardedProto.split(",")[0]?.trim() === "https";
  }
  return request.nextUrl.protocol === "https:";
}
