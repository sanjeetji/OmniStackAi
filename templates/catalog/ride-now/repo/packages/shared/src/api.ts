import type { Session, User } from "./types.ts";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  put<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body?: unknown): Promise<T>;
  del<T>(path: string): Promise<T>;
  session(): Session | null;
  signIn(session: Session): void;
  signOut(): Promise<void>;
  updateUser(user: User): void;
  streamUrl(): string | null;
  baseUrl: string;
}

/**
 * The RideNow API client. The session lives in localStorage under `storageKey` (each app has its
 * own). A 401 triggers one refresh; if that fails, `onSignedOut` runs.
 */
export function createApi(options: { baseUrl: string; storageKey: string; onSignedOut?: () => void }): ApiClient {
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  let cached: Session | null | undefined;
  let refreshing: Promise<boolean> | null = null;

  const read = (): Session | null => {
    if (cached !== undefined) return cached;
    if (typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem(options.storageKey);
      cached = raw ? (JSON.parse(raw) as Session) : null;
    } catch {
      cached = null;
    }
    return cached;
  };
  const write = (session: Session | null) => {
    cached = session;
    if (typeof window === "undefined") return;
    try {
      if (session) window.localStorage.setItem(options.storageKey, JSON.stringify(session));
      else window.localStorage.removeItem(options.storageKey);
    } catch {
      // Private mode or blocked storage: the session lasts for this page only.
    }
    window.dispatchEvent(new CustomEvent("ridenow:session", { detail: session }));
  };

  async function refresh(): Promise<boolean> {
    const current = read();
    if (!current) return false;
    refreshing ??= (async () => {
      try {
        const response = await fetch(`${baseUrl}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: current.refresh_token }),
        });
        if (!response.ok) return false;
        write((await response.json()) as Session);
        return true;
      } catch {
        return false;
      } finally {
        setTimeout(() => (refreshing = null), 0);
      }
    })();
    return refreshing;
  }

  async function request<T>(method: string, path: string, body?: unknown, retry = true): Promise<T> {
    const session = read();
    let response: Response;
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method,
        headers: {
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
          ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, "network", "Couldn't reach RideNow. Check your connection and try again.");
    }
    if (response.status === 401 && retry && session && !path.startsWith("/auth/")) {
      if (await refresh()) return request<T>(method, path, body, false);
      write(null);
      options.onSignedOut?.();
    }
    if (response.status === 204) return undefined as T;
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new ApiError(response.status, data?.code ?? "error", data?.error ?? "Something went wrong. Please try again.");
    }
    return data as T;
  }

  return {
    baseUrl,
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body ?? {}),
    put: (path, body) => request("PUT", path, body ?? {}),
    patch: (path, body) => request("PATCH", path, body ?? {}),
    del: (path) => request("DELETE", path),
    session: read,
    signIn: (session) => write(session),
    updateUser: (user) => {
      const current = read();
      if (current) write({ ...current, user });
    },
    async signOut() {
      const current = read();
      write(null);
      if (current) {
        await fetch(`${baseUrl}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: current.refresh_token }),
        }).catch(() => undefined);
      }
    },
    streamUrl() {
      const current = read();
      return current ? `${baseUrl}/stream?token=${encodeURIComponent(current.access_token)}` : null;
    },
  };
}
