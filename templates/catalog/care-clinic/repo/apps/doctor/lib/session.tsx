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

/** The workstation is for physicians. Any other account is refused by the API at sign-in. */
const USER_KEY = "careclinic_user";

export interface Toast {
  id: number;
  title: string;
  detail?: string;
  tone: "info" | "good" | "alert";
}

interface SessionValue {
  doctor: User | null;
  ready: boolean;
  connected: boolean;
  /** Bumped on every clinic event, so a screen can put it in a dependency array and reload. */
  pulse: number;
  toasts: Toast[];
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  notify: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
}

const SessionContext = createContext<SessionValue | null>(null);

const NOTICE: Record<string, { title: string; tone: Toast["tone"] }> = {
  queue_updated: { title: "A patient has checked in", tone: "info" },
  token_called: { title: "Token called", tone: "info" },
  appointment_booked: { title: "New appointment booked", tone: "info" },
  appointment_cancelled: { title: "Appointment cancelled", tone: "alert" },
  lab_updated: { title: "Lab order updated", tone: "info" },
  telehealth_participant_joined: { title: "Patient joined the video room", tone: "good" },
};

export function DoctorSessionProvider({ children }: { children: ReactNode }) {
  const [doctor, setDoctor] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [pulse, setPulse] = useState(0);
  const router = useRouter();

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(USER_KEY);
      const token = defaultApiClient.getToken();
      if (raw && token) {
        const stored = JSON.parse(raw) as User;
        if (stored.role === "doctor") setDoctor(stored);
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
      setPulse((value) => value + 1);
      const notice = NOTICE[event.type];
      if (notice) notify({ title: notice.title, tone: notice.tone });
    },
    [notify]
  );

  const { isConnected } = useStream({ enabled: Boolean(doctor), onEvent });

  const signIn = useCallback(
    async (email: string, password: string) => {
      const response = await defaultApiClient.login(email, password, "doctor");
      setDoctor(response.user);
      router.push("/");
    },
    [router]
  );

  const signOut = useCallback(() => {
    defaultApiClient.clearSession();
    setDoctor(null);
    router.push("/login");
  }, [router]);

  const value = useMemo<SessionValue>(
    () => ({ doctor, ready, connected: isConnected, pulse, toasts, signIn, signOut, notify, dismiss }),
    [doctor, ready, isConnected, pulse, toasts, signIn, signOut, notify, dismiss]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside DoctorSessionProvider");
  return value;
}

/** Send anyone without a doctor session to the sign-in page. */
export function useRequireDoctor(): { doctor: User | null; checking: boolean } {
  const { doctor, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (ready && !doctor) router.replace("/login");
  }, [ready, doctor, router]);

  return { doctor, checking: !ready || !doctor };
}
