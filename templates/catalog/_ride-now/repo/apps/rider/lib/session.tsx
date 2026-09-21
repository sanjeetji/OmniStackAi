"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { Session, User } from "@ridenow/shared";
import { api } from "./api";

interface SessionState {
  user: User | null;
  ready: boolean;
  signIn: (session: Session) => void;
  signOut: () => Promise<void>;
  setUser: (user: User) => void;
}

const SessionContext = createContext<SessionState>({
  user: null,
  ready: false,
  signIn: () => undefined,
  signOut: async () => undefined,
  setUser: () => undefined,
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUserState(api.session()?.user ?? null);
    setReady(true);
    const onChange = (event: Event) => setUserState((event as CustomEvent<Session | null>).detail?.user ?? null);
    window.addEventListener("ridenow:session", onChange);
    return () => window.removeEventListener("ridenow:session", onChange);
  }, []);

  return (
    <SessionContext.Provider
      value={{
        user,
        ready,
        signIn: (session) => api.signIn(session),
        signOut: () => api.signOut(),
        setUser: (next) => api.updateUser(next),
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => useContext(SessionContext);

/** Send signed-out visitors to sign-in and come back afterwards. */
export function useRequireRider(): User | null {
  const { user, ready } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (ready && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [ready, user, router, pathname]);
  return user;
}
