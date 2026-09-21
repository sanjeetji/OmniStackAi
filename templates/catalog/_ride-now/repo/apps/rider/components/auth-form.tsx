"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Mail, Phone } from "lucide-react";
import { ApiError, type Session } from "@ridenow/shared";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Alert, Button, Input, cx } from "./ui";
import { Logo } from "./logo";

/** Only same-app paths are allowed as a post-login destination. */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/ride";
}

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const params = useSearchParams();
  const { signIn } = useSession();
  const [method, setMethod] = useState<"email" | "phone">("email");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", phone: "", code: "" });
  const [otpSent, setOtpSent] = useState(false);
  const [demoHint, setDemoHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: event.target.value });

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const finish = (session: Session) => {
    if (session.user.role !== "rider") {
      setError(`This is a ${session.user.role} account. Use the RideNow ${session.user.role === "driver" ? "Driver" : "Ops"} app.`);
      return;
    }
    signIn(session);
    router.replace(safeNext(params.get("next")));
  };

  const submitEmail = (event: React.FormEvent) => {
    event.preventDefault();
    void run(async () => {
      const session =
        mode === "signup"
          ? await api.post<Session>("/auth/register", { full_name: form.full_name, email: form.email, password: form.password })
          : await api.post<Session>("/auth/login", { email: form.email, password: form.password, role: "rider" });
      finish(session);
    });
  };

  const submitPhone = (event: React.FormEvent) => {
    event.preventDefault();
    void run(async () => {
      if (!otpSent) {
        const result = await api.post<{ demo_hint?: string }>("/auth/otp/request", { phone: form.phone });
        setOtpSent(true);
        setDemoHint(result.demo_hint ?? null);
        return;
      }
      finish(await api.post<Session>("/auth/otp/verify", { phone: form.phone, code: form.code, full_name: form.full_name || undefined }));
    });
  };

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <div className="my-auto w-full max-w-sm py-10">
          <h1 className="text-3xl font-extrabold tracking-tight">{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
          <p className="mt-2 text-muted">{mode === "signup" ? "₹100 ride credit on us when you join." : "Sign in to book your next ride."}</p>

          <div role="tablist" aria-label="Sign-in method" className="mt-8 grid grid-cols-2 rounded-full bg-black/5 p-1">
            {(["email", "phone"] as const).map((value) => (
              <button
                key={value}
                role="tab"
                type="button"
                aria-selected={method === value}
                onClick={() => {
                  setMethod(value);
                  setError(null);
                }}
                className={cx("flex h-10 items-center justify-center gap-2 rounded-full text-sm font-semibold transition", method === value ? "bg-white shadow-sm" : "text-muted")}
              >
                {value === "email" ? <Mail className="size-4" aria-hidden="true" /> : <Phone className="size-4" aria-hidden="true" />}
                {value === "email" ? "Email" : "Phone"}
              </button>
            ))}
          </div>

          {method === "email" ? (
            <form onSubmit={submitEmail} className="mt-6 grid gap-4" noValidate>
              {mode === "signup" ? <Input label="Full name" value={form.full_name} onChange={set("full_name")} autoComplete="name" required minLength={2} /> : null}
              <Input label="Email" type="email" value={form.email} onChange={set("email")} autoComplete="email" required />
              <Input
                label="Password"
                type="password"
                value={form.password}
                onChange={set("password")}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                hint={mode === "signup" ? "At least 8 characters, with letters and numbers." : undefined}
                required
              />
              {error ? <Alert>{error}</Alert> : null}
              <Button type="submit" size="lg" busy={busy}>{mode === "signup" ? "Create account" : "Sign in"}</Button>
            </form>
          ) : (
            <form onSubmit={submitPhone} className="mt-6 grid gap-4" noValidate>
              <Input label="Mobile number" type="tel" inputMode="tel" value={form.phone} onChange={set("phone")} placeholder="98765 43210" leading={<span className="text-sm font-semibold text-muted">+91</span>} autoComplete="tel-national" disabled={otpSent} />
              {otpSent ? (
                <>
                  {mode === "signup" ? <Input label="Full name" value={form.full_name} onChange={set("full_name")} autoComplete="name" /> : null}
                  <Input label="6-digit code" inputMode="numeric" value={form.code} onChange={set("code")} maxLength={6} autoComplete="one-time-code" hint={demoHint ?? "We sent it by SMS. It expires in 5 minutes."} />
                </>
              ) : null}
              {error ? <Alert>{error}</Alert> : null}
              <Button type="submit" size="lg" busy={busy}>{otpSent ? "Verify and continue" : "Send code"}</Button>
              {otpSent ? (
                <button type="button" className="text-sm font-semibold text-teal hover:underline" onClick={() => { setOtpSent(false); setForm({ ...form, code: "" }); }}>
                  Use a different number
                </button>
              ) : null}
            </form>
          )}

          <p className="mt-8 text-center text-sm text-muted">
            {mode === "signup" ? "Already have an account? " : "New to RideNow? "}
            <Link href={mode === "signup" ? "/login" : "/signup"} className="font-semibold text-ink hover:underline">
              {mode === "signup" ? "Sign in" : "Create an account"}
            </Link>
          </p>
          {mode === "login" ? (
            <p className="mt-4 rounded-2xl bg-amber-soft px-4 py-3 text-center text-xs text-amber-deep">
              Demo: <b>asha@ridenow.test</b> / <b>Rider@2026</b>
            </p>
          ) : null}
        </div>
      </div>
      <div className="relative hidden overflow-hidden bg-ink lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgb(255_176_32/0.35),transparent_45%),radial-gradient(circle_at_80%_80%,rgb(15_118_110/0.35),transparent_40%)]" />
        <div className="relative flex h-full flex-col justify-end p-12 text-white">
          <p className="max-w-md text-balance text-4xl font-extrabold leading-tight">Upfront fares. Live tracking. Drivers you can trust.</p>
          <p className="mt-4 max-w-sm text-white/70">Every ride starts with your PIN and ends with a receipt in your inbox.</p>
        </div>
      </div>
    </div>
  );
}
