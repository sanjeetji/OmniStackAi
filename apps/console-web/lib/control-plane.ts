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
  status: "idle" | "starting" | "stopped" | "error" | "unavailable" | "ready";
  message: string;
  phase?: "idle" | "install" | "migrate" | "start" | "ready" | "stopped" | "error";
  elapsed_ms?: number;
  web_url?: string;
  api_url?: string;
  web_port?: number;
  api_port?: number;
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

// ---------------------------------------------------------------------------
// Projects & Workspaces (F-01 / R-499)
// ---------------------------------------------------------------------------

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string;
  status: "active" | "archived" | "deleted";
  last_prompt: string;
  entities: string[];
  file_count: number;
  commit_sha: string;
  credits_spent: number;
  created_at: string;
  updated_at: string;
  last_opened_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  prompt?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

export function listProjects(
  token: string,
  options?: { status?: string; sort?: string; limit?: number; offset?: number }
): Promise<ProjectListResponse> {
  const params = new URLSearchParams();
  if (options?.status) params.set("status", options.status);
  if (options?.sort) params.set("sort", options.sort);
  if (options?.limit) params.set("limit", options.limit.toString());
  if (options?.offset) params.set("offset", options.offset.toString());
  const qs = params.toString() ? `?${params.toString()}` : "";
  return callControlPlane<ProjectListResponse>(`/projects${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createProject(
  token: string,
  req: CreateProjectRequest
): Promise<Project> {
  return callControlPlane<Project>("/projects", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });
}

export function getProject(token: string, projectId: string): Promise<Project> {
  return callControlPlane<Project>(`/projects/${encodeURIComponent(projectId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function updateProject(
  token: string,
  projectId: string,
  req: UpdateProjectRequest
): Promise<Project> {
  return callControlPlane<Project>(`/projects/${encodeURIComponent(projectId)}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });
}

export function deleteProject(
  token: string,
  projectId: string,
  purge: boolean = false
): Promise<{ status: string }> {
  const qs = purge ? "?purge=true" : "";
  return callControlPlane<{ status: string }>(
    `/projects/${encodeURIComponent(projectId)}${qs}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function touchProjectOpened(
  token: string,
  projectId: string
): Promise<void> {
  return callControlPlane<void>(
    `/projects/${encodeURIComponent(projectId)}/opened`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function streamProjectBuild(
  token: string,
  projectId: string,
  prompt: string
): Promise<Response> {
  return fetch(`${controlPlaneUrl()}/projects/${encodeURIComponent(projectId)}/build/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt }),
    cache: "no-store",
  });
}

export function getProjectTurns(
  token: string,
  projectId: string
): Promise<BuildTurnsResponse> {
  return callControlPlane<BuildTurnsResponse>(
    `/projects/${encodeURIComponent(projectId)}/turns`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectFiles(
  token: string,
  projectId: string
): Promise<BuildFileTreeResponse> {
  return callControlPlane<BuildFileTreeResponse>(
    `/projects/${encodeURIComponent(projectId)}/files`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectFile(
  token: string,
  projectId: string,
  filePath: string
): Promise<BuildFileContentResponse> {
  const qs = `?path=${encodeURIComponent(filePath)}`;
  return callControlPlane<BuildFileContentResponse>(
    `/projects/${encodeURIComponent(projectId)}/file${qs}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function editProject(
  token: string,
  projectId: string,
  prompt: string
): Promise<BuildEditResponse> {
  return callControlPlane<BuildEditResponse>(
    `/projects/${encodeURIComponent(projectId)}/edit`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    }
  );
}

export function getProjectPreview(
  token: string,
  projectId: string
): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>(
    `/projects/${encodeURIComponent(projectId)}/preview`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function previewProject(
  token: string,
  projectId: string
): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>(
    `/projects/${encodeURIComponent(projectId)}/preview`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function stopProjectPreview(
  token: string,
  projectId: string
): Promise<PreviewStatus> {
  return callControlPlane<PreviewStatus>(
    `/projects/${encodeURIComponent(projectId)}/preview/stop`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function checkProjectProblems(
  token: string,
  projectId: string
): Promise<ProblemsReport> {
  return callControlPlane<ProblemsReport>(
    `/projects/${encodeURIComponent(projectId)}/problems`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectProblems(
  token: string,
  projectId: string
): Promise<ProblemsReport> {
  return callControlPlane<ProblemsReport>(
    `/projects/${encodeURIComponent(projectId)}/problems`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export interface GitConnectionStatus {
  connected: boolean;
  provider?: string;
  external_login?: string;
  installation_id?: string;
  connected_at?: string;
}

export interface ProjectGitStatus {
  connected: boolean;
  external_login?: string;
  repo_full_name?: string;
  repo_url?: string;
  repo_private?: boolean;
  last_pushed_sha?: string;
  last_pushed_at?: string;
  commit_sha?: string;
  branch?: string;
  dirty?: boolean;
  ahead_by?: number;
}

export interface CreateRepoParams {
  name: string;
  description?: string;
  private: boolean;
}

export interface PushResult {
  commit_sha: string;
  pushed_at: string;
}

export function getGitStatus(token: string): Promise<GitConnectionStatus> {
  return callControlPlane<GitConnectionStatus>("/git/status", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function disconnectGit(token: string): Promise<{ disconnected: boolean }> {
  return callControlPlane<{ disconnected: boolean }>("/git/connection", {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getProjectGit(
  token: string,
  projectId: string,
): Promise<ProjectGitStatus> {
  return callControlPlane<ProjectGitStatus>(
    `/projects/${encodeURIComponent(projectId)}/git`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
}

export function createProjectRepo(
  token: string,
  projectId: string,
  params: CreateRepoParams,
): Promise<ProjectGitStatus> {
  return callControlPlane<ProjectGitStatus>(
    `/projects/${encodeURIComponent(projectId)}/git/repo`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(params),
    },
  );
}

export function pushProjectGit(
  token: string,
  projectId: string,
): Promise<PushResult> {
  return callControlPlane<PushResult>(
    `/projects/${encodeURIComponent(projectId)}/git/push`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    },
  );
}

// ----------------------------------------------------------------------------
// F-04 / R-502: Knowledge & Skills
// ----------------------------------------------------------------------------

export interface Skill {
  id: string;
  user_id: string;
  name: string;
  title: string;
  description: string;
  body: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectKnowledge {
  knowledge: string;
  updated_at: string;
}

export interface CreateSkillParams {
  name: string;
  title: string;
  description?: string;
  body: string;
  is_default?: boolean;
}

export interface UpdateSkillParams {
  title?: string;
  description?: string;
  body?: string;
  is_default?: boolean;
}

export function listSkills(token: string): Promise<Skill[]> {
  return callControlPlane<{ skills: Skill[] }>("/skills", {
    headers: { Authorization: `Bearer ${token}` },
  }).then((res) => res.skills ?? []);
}

export function createSkill(token: string, params: CreateSkillParams): Promise<Skill> {
  return callControlPlane<Skill>("/skills", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(params),
  });
}

export function getSkill(token: string, skillId: string): Promise<Skill> {
  return callControlPlane<Skill>(`/skills/${encodeURIComponent(skillId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function updateSkill(
  token: string,
  skillId: string,
  params: UpdateSkillParams
): Promise<Skill> {
  return callControlPlane<Skill>(`/skills/${encodeURIComponent(skillId)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(params),
  });
}

export function deleteSkill(token: string, skillId: string): Promise<{ deleted: boolean }> {
  return callControlPlane<{ deleted: boolean }>(`/skills/${encodeURIComponent(skillId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getProjectKnowledge(
  token: string,
  projectId: string
): Promise<ProjectKnowledge> {
  return callControlPlane<ProjectKnowledge>(
    `/projects/${encodeURIComponent(projectId)}/knowledge`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function updateProjectKnowledge(
  token: string,
  projectId: string,
  knowledge: string
): Promise<ProjectKnowledge> {
  return callControlPlane<ProjectKnowledge>(
    `/projects/${encodeURIComponent(projectId)}/knowledge`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ knowledge }),
    }
  );
}

export function listProjectSkills(
  token: string,
  projectId: string
): Promise<Skill[]> {
  return callControlPlane<{ skills: Skill[] }>(
    `/projects/${encodeURIComponent(projectId)}/skills`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  ).then((res) => res.skills ?? []);
}

export function attachProjectSkill(
  token: string,
  projectId: string,
  skillId: string
): Promise<{ attached: boolean }> {
  return callControlPlane<{ attached: boolean }>(
    `/projects/${encodeURIComponent(projectId)}/skills/${encodeURIComponent(skillId)}`,
    {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function detachProjectSkill(
  token: string,
  projectId: string,
  skillId: string
): Promise<{ detached: boolean }> {
  return callControlPlane<{ detached: boolean }>(
    `/projects/${encodeURIComponent(projectId)}/skills/${encodeURIComponent(skillId)}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

// ---------------------------------------------------------------------------
// Secrets (F-05)
// ---------------------------------------------------------------------------

export interface SecretMetadata {
  key: string;
  description: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

export interface SetSecretParams {
  value: string;
  description?: string;
}

export interface SecretRevealResponse {
  key: string;
  value: string;
}

export function getProjectSecrets(
  token: string,
  projectId: string
): Promise<SecretMetadata[]> {
  return callControlPlane<SecretMetadata[]>(
    `/projects/${encodeURIComponent(projectId)}/secrets`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function setProjectSecret(
  token: string,
  projectId: string,
  key: string,
  params: SetSecretParams
): Promise<SecretMetadata> {
  return callControlPlane<SecretMetadata>(
    `/projects/${encodeURIComponent(projectId)}/secrets/${encodeURIComponent(key)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(params),
    }
  );
}

export function deleteProjectSecret(
  token: string,
  projectId: string,
  key: string
): Promise<void> {
  return callControlPlane<void>(
    `/projects/${encodeURIComponent(projectId)}/secrets/${encodeURIComponent(key)}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function revealProjectSecret(
  token: string,
  projectId: string,
  key: string
): Promise<SecretRevealResponse> {
  return callControlPlane<SecretRevealResponse>(
    `/projects/${encodeURIComponent(projectId)}/secrets/reveal/${encodeURIComponent(key)}`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

// ---------------------------------------------------------------------------
// AI & Usage Management (R-504)
// ---------------------------------------------------------------------------

export interface KeyMetadata {
  provider_id: string;
  label: string;
  created_at: string;
  last_used_at?: string;
}

export interface ModelCall {
  id?: number;
  user_id: string;
  project_id?: string;
  provider_id: string;
  model_id: string;
  tier: string;
  purpose: string;
  input_tokens: number;
  output_tokens: number;
  cost_micros_usd: number;
  credits_spent: number;
  billed_to: string;
  success: boolean;
  error_code: string;
  latency_ms: number;
  created_at: string;
}

export interface UsageTotals {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_micros_usd: number;
  credits_spent: number;
  unpriced_calls: number;
}

export interface DailyUsage {
  date: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_micros_usd: number;
  credits_spent: number;
}

export interface PurposeUsage {
  purpose: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_micros_usd: number;
  credits_spent: number;
}

export interface ProjectUsageReport {
  project_id: string;
  range_days: number;
  totals: UsageTotals;
  by_day: DailyUsage[];
  by_purpose: Record<string, PurposeUsage>;
}

export interface ProjectSummaryUsage {
  project_id: string;
  project_name: string;
  calls: number;
  cost_micros_usd: number;
  credits_spent: number;
}

export interface AccountUsageReport {
  range_days: number;
  totals: UsageTotals;
  by_day: DailyUsage[];
  by_project: ProjectSummaryUsage[];
  credit_balance: number;
}

export interface ProjectModelConfig {
  project_id: string;
  model_provider_id: string;
  model_id: string;
}

export interface ProviderCatalogItem {
  id: string;
  name: string;
  kind: string;
  configured: boolean;
  default_model: string;
  supported_models: string[];
}

export function getAIProviders(token: string): Promise<{ providers: ProviderCatalogItem[] }> {
  return callControlPlane<{ providers: ProviderCatalogItem[] }>("/ai/providers", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getUserKeys(token: string): Promise<KeyMetadata[]> {
  return callControlPlane<KeyMetadata[]>("/ai/keys", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getUserKey(token: string, providerId: string): Promise<KeyMetadata> {
  return callControlPlane<KeyMetadata>(`/ai/keys/${encodeURIComponent(providerId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function setUserKey(
  token: string,
  providerId: string,
  apiKey: string,
  label: string
): Promise<{ status: string; key: KeyMetadata }> {
  return callControlPlane<{ status: string; key: KeyMetadata }>(
    `/ai/keys/${encodeURIComponent(providerId)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ api_key: apiKey, label }),
    }
  );
}

export function deleteUserKey(token: string, providerId: string): Promise<{ status: string }> {
  return callControlPlane<{ status: string }>(`/ai/keys/${encodeURIComponent(providerId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function testUserKey(
  token: string,
  providerId: string,
  apiKey?: string
): Promise<{ success: boolean; latency_ms?: number; message?: string; error?: string }> {
  return callControlPlane<{ success: boolean; latency_ms?: number; message?: string; error?: string }>(
    `/ai/keys/${encodeURIComponent(providerId)}/test`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ api_key: apiKey }),
    }
  );
}

export function getProjectModel(token: string, projectId: string): Promise<ProjectModelConfig> {
  return callControlPlane<ProjectModelConfig>(
    `/projects/${encodeURIComponent(projectId)}/model`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function setProjectModel(
  token: string,
  projectId: string,
  providerId: string,
  modelId: string
): Promise<ProjectModelConfig> {
  return callControlPlane<ProjectModelConfig>(
    `/projects/${encodeURIComponent(projectId)}/model`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ model_provider_id: providerId, model_id: modelId }),
    }
  );
}

export function getProjectUsage(
  token: string,
  projectId: string,
  days: number = 30
): Promise<ProjectUsageReport> {
  return callControlPlane<ProjectUsageReport>(
    `/projects/${encodeURIComponent(projectId)}/usage?days=${days}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getAccountUsage(token: string, days: number = 30): Promise<AccountUsageReport> {
  return callControlPlane<AccountUsageReport>(`/usage?days=${days}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export interface ProjectSEO {
  project_id: string;
  site_name: string;
  default_title: string;
  description: string;
  canonical_host: string;
  discourage: boolean;
  updated_at: string;
}

export interface ProjectPageSEO {
  id?: string;
  project_id: string;
  route: string;
  title: string;
  description: string;
  noindex: boolean;
  updated_at?: string;
}

export interface SEOFinding {
  id: string;
  severity: "error" | "warning" | "info";
  category?: "meta" | "content" | "technical" | "ai-readiness";
  route?: string;
  file: string;
  line?: number;
  message?: string;
  title?: string;
  description?: string;
  suggestion?: string;
  fix_prompt?: string;
}

export interface SEOPageMetadata {
  route: string;
  title: string;
  description: string;
  has_h1: boolean;
  og_title: string;
  og_description: string;
  canonical: string;
  noindex: boolean;
}

export interface SEOAuditReport {
  score: number;
  passed?: number;
  total?: number;
  counts?: {
    total: number;
    errors: number;
    warnings: number;
    info: number;
  };
  findings: SEOFinding[];
  pages?: SEOPageMetadata[];
  files_present?: {
    sitemap: boolean;
    robots: boolean;
    llms_txt: boolean;
    og_image: boolean;
  };
}

export interface SEOSuggestion {
  suggested_title: string;
  suggested_description: string;
}

export function getProjectSEO(token: string, projectId: string): Promise<ProjectSEO> {
  return callControlPlane<ProjectSEO>(`/projects/${encodeURIComponent(projectId)}/seo`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function setProjectSEO(
  token: string,
  projectId: string,
  seo: Partial<ProjectSEO>
): Promise<ProjectSEO> {
  return callControlPlane<ProjectSEO>(`/projects/${encodeURIComponent(projectId)}/seo`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(seo),
  });
}

export function getProjectPageSEOs(token: string, projectId: string): Promise<ProjectPageSEO[]> {
  return callControlPlane<ProjectPageSEO[]>(`/projects/${encodeURIComponent(projectId)}/seo/pages`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function setProjectPageSEO(
  token: string,
  projectId: string,
  route: string,
  page: Partial<ProjectPageSEO>
): Promise<ProjectPageSEO> {
  const normalizedRoute = route.startsWith("/") ? route.slice(1) : route;
  const pathSuffix = normalizedRoute ? `/${encodeURIComponent(normalizedRoute)}` : "";
  return callControlPlane<ProjectPageSEO>(
    `/projects/${encodeURIComponent(projectId)}/seo/pages${pathSuffix}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...page, route: route || "/" }),
    }
  );
}

export function auditProjectSEO(token: string, projectId: string): Promise<SEOAuditReport> {
  return callControlPlane<SEOAuditReport>(
    `/projects/${encodeURIComponent(projectId)}/seo/audit`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function suggestProjectSEOCopy(
  token: string,
  projectId: string,
  route: string,
  pageName?: string
): Promise<SEOSuggestion> {
  return callControlPlane<SEOSuggestion>(
    `/projects/${encodeURIComponent(projectId)}/seo/suggest`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ route, page_name: pageName }),
    }
  );
}

// Aliases for compatibility with any existing calls
export const getProjectSEOAudit = auditProjectSEO;
export const updateProjectPageSEO = (
  token: string,
  projectId: string,
  data: { route: string; title: string; description: string; noindex?: boolean }
) => setProjectPageSEO(token, projectId, data.route, data);
export const suggestProjectPageSEO = (
  token: string,
  projectId: string,
  data: { route: string; page_name?: string }
) => suggestProjectSEOCopy(token, projectId, data.route, data.page_name);

// F-08: Logs and Chat Controls
export interface BuildLogEntry {
  ts: number;
  level: "info" | "warn" | "error";
  phase: string;
  message: string;
}

export interface ProjectLogsResponse {
  source: "build" | "app";
  lines: (BuildLogEntry | string)[];
  next_cursor: number;
  total: number;
}

export function getProjectLogs(
  token: string,
  projectId: string,
  source: "build" | "app" = "build",
  since?: number,
  limit?: number
): Promise<ProjectLogsResponse> {
  const params = new URLSearchParams();
  params.set("source", source);
  if (since !== undefined && since !== null) {
    params.set("since", String(since));
  }
  if (limit !== undefined && limit !== null) {
    params.set("limit", String(limit));
  }
  return callControlPlane<ProjectLogsResponse>(
    `/projects/${encodeURIComponent(projectId)}/logs?${params.toString()}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function clearProjectLogs(
  token: string,
  projectId: string,
  source?: "build" | "app"
): Promise<{ status: string }> {
  const query = source ? `?source=${encodeURIComponent(source)}` : "";
  return callControlPlane<{ status: string }>(
    `/projects/${encodeURIComponent(projectId)}/logs${query}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function cancelProjectBuild(
  token: string,
  projectId: string
): Promise<{ status: string }> {
  return callControlPlane<{ status: string }>(
    `/projects/${encodeURIComponent(projectId)}/build/cancel`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function streamProjectLogs(
  token: string,
  projectId: string,
  source: "build" | "app" = "build"
): Promise<Response> {
  return fetch(
    `${controlPlaneUrl()}/projects/${encodeURIComponent(projectId)}/logs/stream?source=${encodeURIComponent(source)}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }
  );
}

// ---------------------------------------------------------------------------
// Database Explorer & SQL Editor (F-09 / R-507)
// ---------------------------------------------------------------------------

export interface DBTable {
  schema: string;
  name: string;
  row_count: number;
  column_count: number;
}

export interface DBTablesResponse {
  db_name: string;
  tables: DBTable[];
}

export interface DBColumnMeta {
  column: string;
  type: string;
  nullable: boolean;
  default: string | null;
}

export interface DBTableRowsResponse {
  db_name: string;
  table: string;
  schema: string;
  columns_meta: DBColumnMeta[];
  columns: string[];
  rows: Record<string, any>[];
  total: number;
  limit: number;
  offset: number;
}

export interface DBQueryResult {
  db_name: string;
  rows: Record<string, any>[];
  columns: string[];
  rowcount: number;
  duration_ms: number;
  write_mode: boolean;
  notice: string;
}

export interface DBSchemaResponse {
  db_name: string;
  schema_sql: string;
}

export function getProjectDBTables(
  token: string,
  projectId: string
): Promise<DBTablesResponse> {
  return callControlPlane<DBTablesResponse>(
    `/projects/${encodeURIComponent(projectId)}/db/tables`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectDBTableRows(
  token: string,
  projectId: string,
  table: string,
  options?: {
    schema?: string;
    limit?: number;
    offset?: number;
    orderBy?: string;
    direction?: "ASC" | "DESC";
  }
): Promise<DBTableRowsResponse> {
  const params = new URLSearchParams();
  if (options?.schema) params.set("schema", options.schema);
  if (options?.limit !== undefined) params.set("limit", String(options.limit));
  if (options?.offset !== undefined) params.set("offset", String(options.offset));
  if (options?.orderBy) params.set("order_by", options.orderBy);
  if (options?.direction) params.set("direction", options.direction);
  const q = params.toString();
  return callControlPlane<DBTableRowsResponse>(
    `/projects/${encodeURIComponent(projectId)}/db/tables/${encodeURIComponent(table)}${q ? `?${q}` : ""}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function executeProjectDBQuery(
  token: string,
  projectId: string,
  sql: string,
  write?: boolean
): Promise<DBQueryResult> {
  return callControlPlane<DBQueryResult>(
    `/projects/${encodeURIComponent(projectId)}/db/query`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ sql, write: !!write }),
    }
  );
}

export function getProjectDBSchema(
  token: string,
  projectId: string
): Promise<DBSchemaResponse> {
  return callControlPlane<DBSchemaResponse>(
    `/projects/${encodeURIComponent(projectId)}/db/schema`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

// ---------------------------------------------------------------------------
// Security scan & Tests (F-10 / R-508)
// ---------------------------------------------------------------------------

export interface SecurityFinding {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  rule: string;
  file?: string;
  line?: number;
  message: string;
  fix?: string;
}

export interface SecurityCheck {
  name: string;
  status: "passed" | "failed" | "skipped";
  note?: string;
}

export interface ProjectSecurityReport {
  findings: SecurityFinding[];
  checks: SecurityCheck[];
  summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
    total_issues: number;
  };
  scanned_at: string;
}

export interface TestCaseResult {
  name: string;
  status: "passed" | "failed" | "skipped";
  duration_ms: number;
  message?: string;
}

export interface TestSuiteResult {
  name: string;
  passed: number;
  failed: number;
  skipped: number;
  duration_ms: number;
  status: "passed" | "failed" | "skipped";
  tests: TestCaseResult[];
  raw_output?: string;
  message?: string;
}

export interface ProjectTestReport {
  suites: TestSuiteResult[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    duration_ms: number;
  };
  raw_output: string;
  message?: string | null;
  ran_at: string;
}

export function runProjectSecurityScan(
  token: string,
  projectId: string
): Promise<ProjectSecurityReport> {
  return callControlPlane<ProjectSecurityReport>(
    `/projects/${encodeURIComponent(projectId)}/security/scan`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectSecurityReport(
  token: string,
  projectId: string
): Promise<ProjectSecurityReport> {
  return callControlPlane<ProjectSecurityReport>(
    `/projects/${encodeURIComponent(projectId)}/security`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function runProjectTests(
  token: string,
  projectId: string
): Promise<ProjectTestReport> {
  return callControlPlane<ProjectTestReport>(
    `/projects/${encodeURIComponent(projectId)}/tests/run`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectTestReport(
  token: string,
  projectId: string
): Promise<ProjectTestReport> {
  return callControlPlane<ProjectTestReport>(
    `/projects/${encodeURIComponent(projectId)}/tests`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

// --- G-01 Publish v1 / R-509 Deployments & Connections ---

export interface DeployConnectionStatus {
  provider: "vercel" | "netlify";
  connected: boolean;
  account_label?: string;
  connected_at?: string;
}

export interface DeploymentRecord {
  id: string;
  project_id: string;
  user_id: string;
  provider: "vercel" | "netlify";
  external_id?: string;
  status: "queued" | "building" | "ready" | "error" | "canceled";
  url?: string;
  commit_sha?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface PublishReadiness {
  path: 1 | 2 | 3;
  path_description: string;
  has_backend: boolean;
  has_db: boolean;
  render_yaml?: string;
  fly_toml?: string;
  git_connected: boolean;
  repo_name: string;
  provider_connected: boolean;
  provider: string;
  account_label?: string;
  secrets_count: number;
  missing_secrets: string[];
  latest_deployment?: DeploymentRecord;
  live_url?: string;
}

export interface TriggerPublishResponse {
  deployment: DeploymentRecord;
  live_url: string;
}

export function getDeployConnection(
  token: string,
  provider: "vercel" | "netlify"
): Promise<DeployConnectionStatus> {
  return callControlPlane<DeployConnectionStatus>(
    `/deploy/connections/${encodeURIComponent(provider)}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function saveDeployConnection(
  token: string,
  provider: "vercel" | "netlify",
  apiKey: string,
  accountLabel?: string
): Promise<DeployConnectionStatus> {
  return callControlPlane<DeployConnectionStatus>(
    `/deploy/connections/${encodeURIComponent(provider)}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api_key: apiKey,
        account_label: accountLabel ?? "",
      }),
    }
  );
}

export function deleteDeployConnection(
  token: string,
  provider: "vercel" | "netlify"
): Promise<{ ok: boolean }> {
  return callControlPlane<{ ok: boolean }>(
    `/deploy/connections/${encodeURIComponent(provider)}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getPublishReadiness(
  token: string,
  projectId: string
): Promise<PublishReadiness> {
  return callControlPlane<PublishReadiness>(
    `/projects/${encodeURIComponent(projectId)}/publish`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function triggerPublish(
  token: string,
  projectId: string,
  provider?: "vercel" | "netlify"
): Promise<TriggerPublishResponse> {
  return callControlPlane<TriggerPublishResponse>(
    `/projects/${encodeURIComponent(projectId)}/publish`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(provider ? { provider } : {}),
    }
  );
}

export function getProjectDeployments(
  token: string,
  projectId: string
): Promise<{ deployments: DeploymentRecord[] }> {
  return callControlPlane<{ deployments: DeploymentRecord[] }>(
    `/projects/${encodeURIComponent(projectId)}/deployments`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function getProjectDeployment(
  token: string,
  projectId: string,
  deploymentId: string
): Promise<{ deployment: DeploymentRecord }> {
  return callControlPlane<{ deployment: DeploymentRecord }>(
    `/projects/${encodeURIComponent(projectId)}/deployments/${encodeURIComponent(deploymentId)}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

// R-510 (G-02 Custom Domains)
export interface ProjectDomain {
  id: string;
  project_id: string;
  hostname: string;
  provider: string;
  record_type: string;
  record_name: string;
  record_value: string;
  status: "pending" | "verifying" | "verified" | "failed" | "removed";
  tls_status: "pending" | "issued" | "failed";
  is_primary: boolean;
  last_checked_at?: string;
  verified_at?: string;
  error?: string;
  created_at: string;
}

export function listProjectDomains(
  token: string,
  projectId: string
): Promise<{ domains: ProjectDomain[] }> {
  return callControlPlane<{ domains: ProjectDomain[] }>(
    `/projects/${encodeURIComponent(projectId)}/domains`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function addProjectDomain(
  token: string,
  projectId: string,
  hostname: string,
  provider?: string
): Promise<ProjectDomain> {
  return callControlPlane<ProjectDomain>(
    `/projects/${encodeURIComponent(projectId)}/domains`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ hostname, provider }),
    }
  );
}

export function verifyProjectDomain(
  token: string,
  projectId: string,
  domainId: string
): Promise<ProjectDomain> {
  return callControlPlane<ProjectDomain>(
    `/projects/${encodeURIComponent(projectId)}/domains/${encodeURIComponent(domainId)}/verify`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function setPrimaryDomain(
  token: string,
  projectId: string,
  domainId: string
): Promise<ProjectDomain> {
  return callControlPlane<ProjectDomain>(
    `/projects/${encodeURIComponent(projectId)}/domains/${encodeURIComponent(domainId)}/primary`,
    {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}

export function deleteProjectDomain(
  token: string,
  projectId: string,
  domainId: string
): Promise<{ deleted: boolean }> {
  return callControlPlane<{ deleted: boolean }>(
    `/projects/${encodeURIComponent(projectId)}/domains/${encodeURIComponent(domainId)}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }
  );
}



