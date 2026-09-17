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
  name: string;
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
  name: string,
  password: string,
): Promise<ControlPlaneAuthResponse> {
  return callControlPlane<ControlPlaneAuthResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password }),
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

/** Real per-request cost/usage, exactly as studio/live_serve.py's `_usage_summary_to_dict` (R-472)
 * reports it. `cost_micros_usd` is USD * 1,000,000 (an integer, never a float/decimal string). */
export interface BuildJobUsage {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  input_tokens: number;
  output_tokens: number;
  unpriced_calls: number;
  cost_micros_usd: number;
}

/** The control-plane's `POST /jobs/build` response (R-472): the agent-engine's own build payload -
 * whose exact shape varies by build kind (plain prompt vs. Solution Pack vs. Ecosystem) and this
 * client does not fully enumerate - augmented with `credits_spent`/`credit_balance`. Only the
 * fields this console actually renders are typed; everything else still round-trips via the index
 * signature rather than being silently dropped. */
export interface BuildJobResponse {
  id?: string;
  name?: string;
  description?: string;
  entities?: string[];
  file_count?: number;
  commit_sha?: string;
  files?: string[];
  usage?: BuildJobUsage;
  credits_spent: number;
  credit_balance: number;
  [key: string]: unknown;
}

/** Builds an app for `prompt` via the control-plane's Job API. `token` is the caller's session
 * token - it is only ever handled server-side (see app/api/jobs/build/route.ts), never sent to
 * client-side JavaScript. Can take real minutes for a real model call; this makes no attempt to
 * time it out early - the control-plane's own R-472 write-deadline fix is what makes waiting
 * possible in the first place. */
export function buildApp(token: string, prompt: string): Promise<BuildJobResponse> {
  return callControlPlane<BuildJobResponse>("/jobs/build", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt }),
  });
}

/** A sorted, flat, secret-free file list for a build, exactly as studio/files.py's
 * `list_build_files` (R-467) reports it. */
export interface BuildFileTreeResponse {
  files: string[];
  truncated: boolean;
}

/** One file's content, exactly as studio/files.py's `read_build_file` (R-467) reports it. A binary
 * file has `binary: true` and empty `content` - never garbled raw bytes. */
export interface BuildFileContentResponse {
  path: string;
  content: string;
  truncated: boolean;
  binary: boolean;
  size: number;
}

/** Lists a build's files via the control-plane's `GET /jobs/build/{id}/files` (R-474) - read-only,
 * no credit debit. */
export function listBuildFiles(token: string, buildId: string): Promise<BuildFileTreeResponse> {
  return callControlPlane<BuildFileTreeResponse>(`/jobs/build/${encodeURIComponent(buildId)}/files`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Reads one file's content via the control-plane's `GET /jobs/build/{id}/file?path=...` (R-474). */
export function readBuildFile(
  token: string,
  buildId: string,
  path: string,
): Promise<BuildFileContentResponse> {
  const query = new URLSearchParams({ path });
  return callControlPlane<BuildFileContentResponse>(
    `/jobs/build/${encodeURIComponent(buildId)}/file?${query.toString()}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
}
