"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { defaultApiClient, useStream, type StreamEvent, type User } from "@careclinic/shared";

/** The console is for clinic staff. A patient or doctor account is refused by the API at sign-in. */
export const STAFF_ROLES = ["admin", "receptionist"] as const;

const USER_KEY = "careclinic_user";
const PREFS_KEY = "careclinic_admin_prefs";

export interface AdminPrefs {
  /** Chime when a token is called or a critical lab result lands. */
  sound: boolean;
  /** Seconds between fallback polls, for anything the stream does not cover. */
  refreshSeconds: number;
  /** Show the ₹ columns on shared screens. */
  showMoney: boolean;
}

export const DEFAULT_PREFS: AdminPrefs = { sound: true, refreshSeconds: 20, showMoney: true };

export function readPrefs(): AdminPrefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}

export function writePrefs(prefs: AdminPrefs): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}

export interface Toast {
  id: number;
  title: string;
  detail?: string;
  tone: "info" | "good" | "alert";
}

interface SessionValue {
  user: User | null;
  ready: boolean;
  connected: boolean;
  lastEvent: StreamEvent | null;
  /** Bumped on every stream event, so a page can put it in a dependency array and reload. */
  pulse: number;
  prefs: AdminPrefs;
  toasts: Toast[];
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  setPrefs: (prefs: AdminPrefs) => void;
  notify: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
}

const SessionContext = createContext<SessionValue | null>(null);

/** Short two-tone chime for an event the desk must not miss. No audio file to ship. */
function chime(): void {
  try {
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const context = new Ctor();
    const gain = context.createGain();
    gain.gain.value = 0.05;
    gain.connect(context.destination);
    [880, 1320].forEach((frequency, index) => {
      const osc = context.createOscillator();
      osc.type = "sine";
      osc.frequency.value = frequency;
      osc.connect(gain);
      osc.start(context.currentTime + index * 0.16);
      osc.stop(context.currentTime + index * 0.16 + 0.14);
    });
    setTimeout(() => context.close().catch(() => undefined), 900);
  } catch {
    // Autoplay policy or no Web Audio: the badge still updates.
  }
}

const NOTICE: Record<string, { title: string; tone: Toast["tone"]; loud?: boolean }> = {
  appointment_booked: { title: "New appointment booked", tone: "info" },
  appointment_cancelled: { title: "Appointment cancelled", tone: "alert" },
  queue_updated: { title: "Patient checked in", tone: "info" },
  token_called: { title: "Token called to a chamber", tone: "good", loud: true },
  consultation_started: { title: "Consultation started", tone: "info" },
  consultation_completed: { title: "Consultation completed", tone: "good" },
  lab_updated: { title: "Lab order updated", tone: "info" },
  payment_received: { title: "Payment collected", tone: "good" },
  schedule_updated: { title: "Doctor schedule changed", tone: "alert" },
};

export function AdminSessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [prefs, setPrefsState] = useState<AdminPrefs>(DEFAULT_PREFS);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);
  const [pulse, setPulse] = useState(0);
  const router = useRouter();

  useEffect(() => {
    setPrefsState(readPrefs());
    try {
      const raw = window.localStorage.getItem(USER_KEY);
      const token = defaultApiClient.getToken();
      if (raw && token) {
        const stored = JSON.parse(raw) as User;
        if ((STAFF_ROLES as readonly string[]).includes(stored.role)) setUser(stored);
      }
    } catch {
      // A corrupt entry just means signing in again.
    }
    setReady(true);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = Date.now() + Math.random();
      setToasts((current) => [{ ...toast, id }, ...current].slice(0, 4));
      setTimeout(() => dismiss(id), 6000);
    },
    [dismiss]
  );

  const onEvent = useCallback(
    (event: StreamEvent) => {
      if (event.type === "connected" || event.type === "ping") return;
      setLastEvent(event);
      setPulse((value) => value + 1);
      const notice = NOTICE[event.type];
      if (!notice) return;
      notify({ title: notice.title, detail: describe(event), tone: notice.tone });
      if (notice.loud && readPrefs().sound) chime();
    },
    [notify]
  );

  const { isConnected } = useStream({ enabled: Boolean(user), onEvent });

  const signIn = useCallback(
    async (email: string, password: string) => {
      const response = await defaultApiClient.login(email, password, "admin");
      setUser(response.user);
      router.push("/");
    },
    [router]
  );

  const signOut = useCallback(() => {
    defaultApiClient.clearSession();
    setUser(null);
    router.push("/login");
  }, [router]);

  const setPrefs = useCallback((next: AdminPrefs) => {
    setPrefsState(next);
    writePrefs(next);
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      user,
      ready,
      connected: isConnected,
      lastEvent,
      pulse,
      prefs,
      toasts,
      signIn,
      signOut,
      setPrefs,
      notify,
      dismiss,
    }),
    [user, ready, isConnected, lastEvent, pulse, prefs, toasts, signIn, signOut, setPrefs, notify, dismiss]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

function describe(event: StreamEvent): string | undefined {
  const payload = event.payload || {};
  if (payload.tokenNumber) return `Token ${payload.tokenNumber}`;
  if (payload.netPayable) return `₹${payload.netPayable}`;
  if (payload.status) return String(payload.status).replace(/_/g, " ");
  return undefined;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside AdminSessionProvider");
  return value;
}

/** Send anyone without a staff session to the sign-in page. */
export function useRequireStaff(): { user: User | null; checking: boolean } {
  const { user, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  return { user, checking: !ready || !user };
}
