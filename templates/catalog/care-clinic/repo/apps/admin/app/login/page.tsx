"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";
import { useSession } from "../../lib/session";
import { errorText } from "../../lib/use-api";
import { Button, Field, inputClass, ErrorNote } from "../../components/ui";

/** The accounts the seeded clinic ships with. Demo data only; no real credential is in the repo. */
const DEMO_STAFF = [
  {
    email: "admin@careclinic.test",
    password: "Admin@2026",
    name: "Kavita Nair",
    role: "Operations lead",
  },
  {
    email: "suresh.gowda@careclinic.test",
    password: "Admin@2026",
    name: "Suresh Gowda",
    role: "Front desk",
  },
];

export default function StaffSignIn() {
  const { signIn, user, ready } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_STAFF[0].email);
  const [password, setPassword] = useState(DEMO_STAFF[0].password);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace("/");
  }, [ready, user, router]);

  async function submit(nextEmail = email, nextPassword = password) {
    setBusy(true);
    setError(null);
    try {
      await signIn(nextEmail, nextPassword);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="hidden flex-col justify-between bg-[var(--color-rail)] p-10 lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-md bg-[var(--color-signal-bright)] text-[14px] font-bold text-[#04232b]">
            CC
          </span>
          <div>
            <p className="text-[14px] font-semibold text-white">CareClinic Ops</p>
            <p className="text-[11px] text-slate-400">Indiranagar branch · Bengaluru</p>
          </div>
        </div>

        <div className="max-w-md">
          <h1 className="text-[28px] font-semibold leading-tight tracking-tight text-white">
            The desk that runs the clinic day.
          </h1>
          <p className="mt-3 text-[13px] leading-relaxed text-slate-400">
            Token queues and check-in, walk-in booking, doctor rosters and room allocation, the
            cashier counter, the diagnostics bench, and an audit trail of every chart opened.
          </p>
          <ul className="mt-6 space-y-2 text-[12.5px] text-slate-300">
            {[
              "Live OPD queue with tokens called to chambers",
              "Cashier collection across cash, card, UPI and insurance",
              "HIPAA-style log of every electronic record access",
            ].map((line) => (
              <li key={line} className="flex items-start gap-2">
                <ShieldCheck size={14} className="mt-0.5 shrink-0 text-[var(--color-signal-bright)]" />
                {line}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[11px] text-slate-500">Staff access only. Every chart opened here is recorded.</p>
      </section>

      <section className="flex items-center justify-center bg-[var(--color-canvas)] p-6">
        <div className="w-full max-w-sm">
          <h2 className="text-[20px] font-semibold tracking-tight text-[var(--color-ink)]">Staff sign in</h2>
          <p className="mt-1 text-[12.5px] text-[var(--color-ink-muted)]">
            Clinic operations and front desk accounts. Patient and doctor accounts are refused here.
          </p>

          <form
            className="mt-6 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            <Field label="Work email">
              <input
                className={inputClass}
                type="email"
                value={email}
                autoComplete="username"
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </Field>
            <Field label="Password">
              <input
                className={inputClass}
                type="password"
                value={password}
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>

            {error && <ErrorNote message={error} />}

            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-[var(--color-signal)] py-2 text-[13px] font-semibold text-white transition hover:bg-[#0c6178] disabled:opacity-60"
            >
              {busy && <Loader2 size={14} className="animate-spin" />}
              {busy ? "Signing in" : "Sign in"}
            </button>
          </form>

          <div className="mt-6 rounded-lg border border-[var(--color-border)] bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">
              Demo staff accounts
            </p>
            <div className="mt-2 space-y-1.5">
              {DEMO_STAFF.map((staff) => (
                <div key={staff.email} className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-[12.5px] font-medium text-[var(--color-ink)]">
                      {staff.name} <span className="text-[var(--color-ink-subtle)]">· {staff.role}</span>
                    </p>
                    <p className="truncate text-[11px] text-[var(--color-ink-muted)]">{staff.email}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="quiet"
                    onClick={() => {
                      setEmail(staff.email);
                      setPassword(staff.password);
                      void submit(staff.email, staff.password);
                    }}
                  >
                    Use
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
