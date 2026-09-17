// Typed client for the Go control-plane's auth API (R-469). Every shape here matches
// services/control-plane/internal/auth/handler.go's JSON responses exactly - this file has no
// logic of its own beyond "call the control-plane and return its shape," so there is exactly one
// place that needs updating if the control-plane's response shape ever changes.

const DEFAULT_CONTROL_PLANE_URL = "http://127.0.0.1:8080";

/** The URL the Next.js server calls the control-plane on. Server-side only - never expose this to
 * client-side JavaScript (no NEXT_PUBLIC_ prefix). */
export function controlPlaneUrl(): string {
  return process.env.OMNISTACKAI_CONTROL_PLANE_URL ?? DEFAULT_CONTROL_PLANE_URL;
}

/** A user's public profile, exactly as services/control-plane/internal/auth returns it. Never
 * carries a token or password hash. */
export interface ControlPlaneUser {
  id: string;
  email: string;
  role: string;
  plan: string;
  byok_enabled: boolean;
  credit_balance: number;
}

export interface ControlPlaneAuthResponse extends ControlPlaneUser {
  token: string;
}

export interface ControlPlaneErrorBody {
  error: string;
}

export class ControlPlaneError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ControlPlaneError";
    this.status = status;
  }
}

async function parseErrorBody(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as Partial<ControlPlaneErrorBody>;
    if (typeof body.error === "string" && body.error.length > 0) {
      return body.error;
    }
  } catch {
    // Fall through to a generic message below - the control-plane always returns a JSON error
    // body on failure, but this stays defensive against a network-level failure response.
  }
  return `control-plane request failed with status ${response.status}`;
}

async function callControlPlane<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const response = await fetch(`${controlPlaneUrl()}${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ControlPlaneError(response.status, await parseErrorBody(response));
  }
  return (await response.json()) as T;
}

export function registerAccount(
  email: string,
  password: string,
): Promise<ControlPlaneAuthResponse> {
  return callControlPlane<ControlPlaneAuthResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function login(
  email: string,
  password: string,
): Promise<ControlPlaneAuthResponse> {
  return callControlPlane<ControlPlaneAuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

/** Resolves to true if the token was accepted for logout, false if the control-plane could not be
 * reached at all. Either way, the caller (the /api/auth/logout route) clears the local cookie -
 * logout must never leave a user stuck signed in because of a network hiccup. */
export async function logout(token: string): Promise<boolean> {
  try {
    const response = await fetch(`${controlPlaneUrl()}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

/** Returns the current user for a session token, or null if the token is missing, expired, or
 * unknown. Never throws for an ordinary "not signed in" case. */
export async function currentUser(token: string): Promise<ControlPlaneUser | null> {
  try {
    const response = await fetch(`${controlPlaneUrl()}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as ControlPlaneUser;
  } catch {
    return null;
  }
}
