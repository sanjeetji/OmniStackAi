"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ApiError, type Session } from "@ridenow/shared";
import { AuthFrame } from "@/components/auth-frame";
import { Button, Field, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import { useDriver } from "@/lib/driver";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

/** Only follow in-app paths after sign-in, never another origin. */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, ready, signIn } = useDriver();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const next = safeNext(params.get("next"));

  useEffect(() => {
    if (ready && user) router.replace(next);
  }, [ready, user, router, next]);

  return (
    <AuthFrame
      title="Welcome back"
      subtitle="Sign in to go online and start taking rides."
      footer={<>New to RideNow? <Link href="/apply" className="font-bold text-go">Apply to drive</Link></>}
    >
      <form
        className="grid gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          try {
            const session = await api.post<Session>("/auth/login", { email, password, role: "driver" });
            signIn(session);
            router.replace(next);
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Couldn't reach RideNow. Check your connection.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Field label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error ? <Notice>{error}</Notice> : null}
        <Button type="submit" size="xl" busy={busy}>Sign in</Button>
      </form>
      <button
        type="button"
        onClick={() => {
          setEmail("ravi@ridenow.test");
          setPassword("Driver@2026");
        }}
        className="rounded-2xl border border-dashed border-line px-4 py-3 text-left text-sm text-fg-muted hover:border-go/60"
      >
        <span className="font-bold text-fg">Demo driver</span> · ravi@ridenow.test / Driver@2026 <span className="text-go">Fill in</span>
      </button>
    </AuthFrame>
  );
}
