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

/** Starts a streaming build via the control-plane's `POST /jobs/build/stream` (R-484) - returns
 * the raw upstream `Response`, unlike every other function in this file (which awaits and returns
 * parsed JSON via `callControlPlane`), so the proxy route can pipe its body straight through
 * unbuffered. Never throws for a non-2xx response - the caller (`app/api/jobs/build/stream/
 * route.ts`) relays whatever status/body the control-plane returns rather than inspecting it. */
export function streamBuildApp(token: string, prompt: string): Promise<Response> {
  return fetch(`${controlPlaneUrl()}/jobs/build/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt }),
    cache: "no-store",
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

/** One chat turn, exactly as studio/session.py's `StudioSessionStore.turns_view` (R-468, extended
 * R-476 so a build's own first turn is included too) reports it. `created_at` is a `time.time()`
 * float - seconds since the epoch, not milliseconds. */
export interface ChatTurn {
  role: string;
  text: string;
  created_at: number;
}

/** The control-plane's `GET /jobs/build/{id}/turns` (R-476) response - proxied verbatim from the
 * agent-engine. Empty for an unknown or evicted build id (not an error - see studio-chat.tsx for
 * why this means turns-hydration can't itself detect a stale build id). */
export interface BuildTurnsResponse {
  turns: ChatTurn[];
}

/** The control-plane's `POST /jobs/build/{id}/edit` response (R-476): the agent-engine's real
 * `_edit()` payload - deliberately narrower than `BuildJobResponse` (no `name`/`description`/
 * `files` - an edit never re-lists the whole file tree) - augmented with
 * `credits_spent`/`credit_balance`. */
export interface BuildEditResponse {
  id?: string;
  diff?: {
    added: string[];
    modified: string[];
    deleted: string[];
    summary: string;
  };
  entities?: string[];
  file_count?: number;
  commit_sha?: string;
  rationale?: string;
  usage?: BuildJobUsage;
  turns?: ChatTurn[];
  credits_spent: number;
  credit_balance: number;
  [key: string]: unknown;
}

/** Applies one follow-up prompt to an existing build via the control-plane's
 * `POST /jobs/build/{id}/edit` (R-476). Same "can take real minutes" shape as `buildApp`. */
export function editBuild(
  token: string,
  buildId: string,
  prompt: string,
): Promise<BuildEditResponse> {
  return callControlPlane<BuildEditResponse>(`/jobs/build/${encodeURIComponent(buildId)}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt }),
  });
}

/** Lists a build's chat turns via the control-plane's `GET /jobs/build/{id}/turns` (R-476) -
 * read-only, no credit debit. */
export function getBuildTurns(token: string, buildId: string): Promise<BuildTurnsResponse> {
  return callControlPlane<BuildTurnsResponse>(`/jobs/build/${encodeURIComponent(buildId)}/turns`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** The trusted-local preview's current state, exactly as studio/preview.py's
 * `StudioPreviewManager` reports it (R-478) - every shape verified by reading the source rather
 * than assumed: `"idle"`/`"stopped"` (never started, stopped, or exited on its own), `"error"`
 * (start failed, or - for the build-scoped route only - the build itself is no longer available),
 * `"unavailable"` (the generated project has no web target), `"ready"` (`web_url` always present,
 * `api_url` only when the generated project also has a backend). */
export interface PreviewStatus {
  status: "idle" | "stopped" | "error" | "unavailable" | "ready";
  message: string;
  web_url?: string;
  api_url?: string;
}

/** Reads the singleton preview's current status via `GET /jobs/preview` (R-478) - read-only, no
 * credit debit. */
export function getPreviewStatus(token: string): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>("/jobs/preview", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Stops the singleton preview via `POST /jobs/preview/stop` (R-478). */
export function stopPreview(token: string): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>("/jobs/preview/stop", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Restarts the singleton preview via `POST /jobs/preview/restart` (R-478) - can take as long as a
 * real cold start (up to ~45s, confirmed live during R-478's own smoke test). */
export function restartPreview(token: string): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>("/jobs/preview/restart", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Starts (or re-starts) the preview for one specific build via
 * `POST /jobs/build/{id}/preview` (R-478) - the primitive a chat-per-build UI needs to answer
 * "show me *this* build's preview." An unknown/evicted build id resolves successfully with a real
 * `{"status": "error", ...}` body (verified live during R-478), not a thrown `ControlPlaneError` -
 * only a non-2xx HTTP status throws. */
export function previewBuild(token: string, buildId: string): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>(`/jobs/build/${encodeURIComponent(buildId)}/preview`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** A real TypeScript compile report, exactly as `verify/compile.py`'s `CompileReport.to_dict()`
 * (R-480) reports it. `files` maps a path to its already-rendered diagnostic lines (`"L12:5
 * TS2339: ..."`) - ready to show as-is, no client-side re-formatting needed. */
export interface ProblemsReport {
  ok: boolean;
  returncode: number;
  error_count: number;
  files: Record<string, string[]>;
  output_tail: string;
}

/** Triggers a fresh problems check via `POST /jobs/build/{id}/problems` (R-480) - a real local
 * `tsc` run, can take real time on a larger app. Not automatic; only ever called from an explicit
 * user action ("Check for problems"). */
export function checkBuildProblems(token: string, buildId: string): Promise<ProblemsReport> {
  return callControlPlane<ProblemsReport>(`/jobs/build/${encodeURIComponent(buildId)}/problems`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Reads the last stored problems report via `GET /jobs/build/{id}/problems` (R-480) - read-only,
 * no credit debit. Throws a `ControlPlaneError` with `status: 404` when no check has been run yet. */
export function getBuildProblems(token: string, buildId: string): Promise<ProblemsReport> {
  return callControlPlane<ProblemsReport>(`/jobs/build/${encodeURIComponent(buildId)}/problems`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** One provider's status, exactly as `model_gateway/overview.py`'s `platform_overview()` (R-482)
 * reports it - `active` reflects only whether an API key is configured, never the key itself. */
export interface ProviderInfo {
  providerId: string;
  tier: "local" | "cloud";
  kind: string;
  defaultModel: string;
  active: boolean;
  keyEnv: string | null;
}

/** A live status view of the model fabric via `GET /jobs/providers` (R-482) - which providers have
 * a key configured, plus `activeNow`: the exact provider/model that would run the *next* real
 * build/edit, resolved live (never a guess). `activeNow` is `null` only if resolving it raised a
 * genuinely unexpected error (never for "nothing configured" - a real deployment always has at
 * least local Ollama to fall back to), in which case `activeNowError` carries the real message. */
export interface ProviderStatus {
  note: string;
  routingMode: string;
  cloudTierSelected: string | null;
  providers: ProviderInfo[];
  activeNow: { providerId: string; modelId: string } | null;
  activeNowError: string | null;
}

/** Reads the live provider status via `GET /jobs/providers` (R-482) - read-only, no credit debit. */
export function getProviderStatus(token: string): Promise<ProviderStatus> {
  return callControlPlane<ProviderStatus>("/jobs/providers", {
    headers: { Authorization: `Bearer ${token}` },
  });
}
