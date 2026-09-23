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
import { api, useStream, type User } from "@bazaar/shared";

/** The operations console is for marketplace staff. Any other account is refused at sign-in. */
const STAFF_ROLES = ["admin"] as const;
const USER_KEY = "bazaar_user";

export interface Toast {
  id: number;
  title: string;
  detail?: string;
  tone: "info" | "good" | "alert";
}

interface SessionValue {
  operator: User | null;
  ready: boolean;
  connected: boolean;
  /** Bumped on every marketplace event, so a screen can put it in a dependency array. */
  pulse: number;
  toasts: Toast[];
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  notify: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
}

const SessionContext = createContext<SessionValue | null>(null);

const NOTICE: Record<string, { title: string; tone: Toast["tone"] }> = {
  order_placed: { title: "New order", tone: "good" },
  shipment_updated: { title: "A consignment moved", tone: "info" },
  shipment_delivered: { title: "Consignment delivered", tone: "good" },
  settlement_requested: { title: "A vendor asked for a payout", tone: "alert" },
  kyc_submitted: { title: "New KYC to review", tone: "alert" },
  review_posted: { title: "New review", tone: "info" },
};

export function OperatorSessionProvider({ children }: { children: ReactNode }) {
  const [operator, setOperator] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [pulse, setPulse] = useState(0);
  const router = useRouter();

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(USER_KEY);
      const token = window.localStorage.getItem("bazaar_token");
      if (raw && token) {
        const stored = JSON.parse(raw) as User;
        if ((STAFF_ROLES as readonly string[]).includes(stored.role)) setOperator(stored);
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
    (event: { type: string }) => {
      if (event.type === "connected" || event.type === "ping") return;
      setPulse((value) => value + 1);
      const notice = NOTICE[event.type];
      if (notice) notify({ title: notice.title, tone: notice.tone });
    },
    [notify]
  );

  const { isConnected } = useStream({ enabled: Boolean(operator), onEvent });

  const signIn = useCallback(
    async (email: string, password: string) => {
      const response = await api.login(email, password);
      if (!(STAFF_ROLES as readonly string[]).includes(response.user.role)) {
        api.logout();
        throw new Error(
          `This sign-in is for marketplace operators. ${response.user.email} is a ${response.user.role} account.`
        );
      }
      setOperator(response.user);
      router.push("/");
    },
    [router]
  );

  const signOut = useCallback(() => {
    api.logout();
    setOperator(null);
    router.push("/login");
  }, [router]);

  const value = useMemo<SessionValue>(
    () => ({ operator, ready, connected: isConnected, pulse, toasts, signIn, signOut, notify, dismiss }),
    [operator, ready, isConnected, pulse, toasts, signIn, signOut, notify, dismiss]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside OperatorSessionProvider");
  return value;
}

/** Send anyone without an operator session to the sign-in page. */
export function useRequireOperator(): { operator: User | null; checking: boolean } {
  const { operator, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (ready && !operator) router.replace("/login");
  }, [ready, operator, router]);

  return { operator, checking: !ready || !operator };
}
