"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useStream, type Session, type User } from "@ridenow/shared";
import { api } from "./api";
import type { Dashboard } from "./types";

/** Events the API sends on the admin channel (services/api, hub.publish("admin", …)). */
export const ADMIN_EVENTS = [
  "trip.updated",
  "driver.status",
  "driver.location",
  "ticket.created",
  "ticket.updated",
  "payout.requested",
  "zone.updated",
] as const;
export type AdminEvent = (typeof ADMIN_EVENTS)[number];

/** Counts shown in the sidebar and the top bar. */
export interface Queues {
  driversPending: number;
  openTickets: number;
  payoutsDue: number;
  driversOnline: number;
  activeTrips: number;
}

export interface Toast {
  id: number;
  tone: "ok" | "bad" | "info";
  text: string;
}

interface AdminState {
  user: User | null;
  ready: boolean;
  queues: Queues | null;
  refreshQueues: () => void;
  signIn: (session: Session) => void;
  signOut: () => Promise<void>;
  on: (type: AdminEvent, handler: (data: any) => void) => () => void;
  toast: (text: string, tone?: Toast["tone"]) => void;
  toasts: Toast[];
  dismissToast: (id: number) => void;
}

const Ctx = createContext<AdminState | null>(null);

// --- device preferences (Settings → This device) -------------------------------------------------

export interface Prefs {
  sound: boolean;
  compact: boolean;
}
const PREF_KEY = "ridenow.admin.prefs";
let memoryPrefs: Prefs = { sound: false, compact: false };

export function readPrefs(): Prefs {
  try {
    const saved = JSON.parse(window.localStorage.getItem(PREF_KEY) ?? "{}") as Partial<Prefs>;
    return { sound: Boolean(saved.sound), compact: Boolean(saved.compact) };
  } catch {
    return memoryPrefs;
  }
}

/** Save and apply at once; returns false when the browser blocks storage (kept for this visit). */
export function writePrefs(prefs: Prefs): boolean {
  memoryPrefs = prefs;
  applyPrefs(prefs);
  try {
    window.localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
    return true;
  } catch {
    return false;
  }
}

function applyPrefs(prefs: Prefs): void {
  if (prefs.compact) document.documentElement.dataset.density = "compact";
  else delete document.documentElement.dataset.density;
}

/** A short two-tone chime from the Web Audio API (no sound file to ship). */
function chime(): void {
  try {
    const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    [880, 1320].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime + i * 0.18);
      gain.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + i * 0.18 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + i * 0.18 + 0.3);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime + i * 0.18);
      osc.stop(ctx.currentTime + i * 0.18 + 0.32);
    });
    setTimeout(() => void ctx.close(), 1000);
  } catch {
    // Audio is blocked until the operator has interacted with the page; the toast still shows.
  }
}

// Events that change a sidebar count. Driver locations only move cars on the live map.
const QUEUE_EVENTS: AdminEvent[] = ["trip.updated", "driver.status", "ticket.created", "ticket.updated", "payout.requested"];

export function AdminProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [queues, setQueues] = useState<Queues | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const listeners = useRef(new Map<AdminEvent, Set<(data: any) => void>>());
  const queueTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastId = useRef(0);

  useEffect(() => {
    const session = api.session();
    // Only operations accounts may use this app; drop any other session found in storage.
    if (session && session.user.role !== "admin") {
      void api.signOut();
      setUser(null);
    } else {
      setUser(session?.user ?? null);
    }
    applyPrefs(readPrefs());
    setReady(true);
    const onChange = (event: Event) => setUser((event as CustomEvent<Session | null>).detail?.user ?? null);
    window.addEventListener("ridenow:session", onChange);
    return () => window.removeEventListener("ridenow:session", onChange);
  }, []);

  const loadQueues = useCallback(async () => {
    if (!api.session()) return;
    try {
      const d = await api.get<Dashboard>("/admin/dashboard");
      setQueues({
        driversPending: d.kpis.drivers_pending,
        openTickets: d.kpis.open_tickets,
        payoutsDue: d.kpis.payouts_due.count,
        driversOnline: d.kpis.drivers_online,
        activeTrips: d.kpis.active_trips,
      });
    } catch {
      // Counts are a convenience; each page shows its own errors.
    }
  }, []);

  const refreshQueues = useCallback(() => {
    if (queueTimer.current) clearTimeout(queueTimer.current);
    queueTimer.current = setTimeout(() => void loadQueues(), 1500);
  }, [loadQueues]);

  useEffect(() => {
    if (!user) {
      setQueues(null);
      return;
    }
    void loadQueues();
    const timer = setInterval(() => void loadQueues(), 60_000);
    return () => clearInterval(timer);
  }, [user, loadQueues]);

  const emit = (type: AdminEvent, data: unknown) => {
    listeners.current.get(type)?.forEach((handler) => handler(data));
    if (QUEUE_EVENTS.includes(type)) refreshQueues();
    // Safety tickets are always urgent: tell the operator wherever they are in the app.
    if (type === "ticket.created" && (data as { category?: string } | null)?.category === "safety") {
      toast(`Urgent safety ticket ${(data as { code?: string }).code ?? ""}`.trim(), "bad");
      if (readPrefs().sound) chime();
    }
  };

  useStream(
    api,
    Object.fromEntries(ADMIN_EVENTS.map((type) => [type, (data: unknown) => emit(type, data)])),
    Boolean(user),
  );

  const on = useCallback((type: AdminEvent, handler: (data: any) => void) => {
    const set = listeners.current.get(type) ?? new Set();
    set.add(handler);
    listeners.current.set(type, set);
    return () => {
      set.delete(handler);
    };
  }, []);

  const dismissToast = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), []);
  const toast = useCallback(
    (text: string, tone: Toast["tone"] = "ok") => {
      const id = ++toastId.current;
      setToasts((all) => [...all.slice(-2), { id, tone, text }]);
      setTimeout(() => dismissToast(id), 4500);
    },
    [dismissToast],
  );

  const value: AdminState = {
    user,
    ready,
    queues,
    refreshQueues,
    on,
    toast,
    toasts,
    dismissToast,
    signIn: (session) => api.signIn(session),
    signOut: () => api.signOut(),
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAdmin(): AdminState {
  const value = useContext(Ctx);
  if (!value) throw new Error("useAdmin must be used inside AdminProvider");
  return value;
}

/** Redirects to sign-in when there is no operations session. */
export function useRequireAdmin(): AdminState {
  const state = useAdmin();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (state.ready && !state.user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [state.ready, state.user, router, pathname]);
  return state;
}

/** Run `handler` for the given realtime events while the component is mounted. */
export function useAdminEvent(types: AdminEvent[], handler: (type: AdminEvent, data: any) => void): void {
  const { on } = useAdmin();
  const latest = useRef(handler);
  latest.current = handler;
  const key = types.join(",");
  useEffect(() => {
    const offs = key.split(",").map((type) => on(type as AdminEvent, (data) => latest.current(type as AdminEvent, data)));
    return () => offs.forEach((off) => off());
  }, [on, key]);
}
