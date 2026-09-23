"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, Stethoscope } from "lucide-react";
import { useSession } from "../../lib/session";
import { errorText } from "../../lib/use-api";
import { Button, Field, inputClass, ErrorNote } from "../../components/ui";

/** The physician the seeded clinic ships with. Demo data only; no real credential is in the repo. */
const DEMO_DOCTOR = {
  email: "dr.rajesh@careclinic.test",
  password: "Doctor@2026",
  name: "Dr. Rajesh Varma, MD, DM",
  role: "Cardiology and internal medicine",
};

export default function DoctorSignIn() {
  const { signIn, doctor, ready } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_DOCTOR.email);
  const [password, setPassword] = useState(DEMO_DOCTOR.password);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && doctor) router.replace("/");
  }, [ready, doctor, router]);

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
      <section className="hidden flex-col justify-between bg-[var(--color-sidebar)] p-10 lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--color-emerald-brand)] text-white">
            <Stethoscope size={19} />
          </span>
          <div>
            <p className="text-[14px] font-semibold text-white">CareClinic Workstation</p>
            <p className="text-[11px] text-slate-400">Indiranagar branch · Bengaluru</p>
          </div>
        </div>

        <div className="max-w-md">
          <h1 className="text-[30px] font-semibold leading-tight tracking-tight text-white">
            Your clinic day, in one screen.
          </h1>
          <p className="mt-3 text-[13px] leading-relaxed text-slate-400">
            Today's token queue, the patient in the chair with their allergies and vitals in front of
            you, SOAP notes and ICD-10 coding, a prescription that is signed and then locked, lab
            orders, and the whole chart a click away.
          </p>
          <ul className="mt-6 space-y-2 text-[12.5px] text-slate-300">
            {[
              "Consultations move one way: checked in, in consult, completed",
              "A signed prescription can never be edited, only replaced",
              "Every chart you open is written to the clinic's audit log",
            ].map((line) => (
              <li key={line} className="flex items-start gap-2">
                <ShieldCheck size={14} className="mt-0.5 shrink-0 text-emerald-400" />
                {line}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[11px] text-slate-500">Physician access only. Every record you open is recorded.</p>
      </section>

      <section className="flex items-center justify-center bg-[var(--color-canvas)] p-6">
        <div className="w-full max-w-sm">
          <h2 className="text-[21px] font-semibold tracking-tight text-[var(--color-ink)]">Doctor sign in</h2>
          <p className="mt-1 text-[12.5px] text-[var(--color-ink-muted)]">
            Physician accounts only. Patient and front-desk accounts are refused here.
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
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--color-emerald-brand)] py-2.5 text-[13px] font-semibold text-white transition hover:bg-[var(--color-emerald-dark)] disabled:opacity-60"
            >
              {busy && <Loader2 size={14} className="animate-spin" />}
              {busy ? "Signing in" : "Sign in"}
            </button>
          </form>

          <div className="mt-6 rounded-xl border border-[var(--color-border)] bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
              Demo physician
            </p>
            <div className="mt-2 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-[12.5px] font-medium text-[var(--color-ink)]">{DEMO_DOCTOR.name}</p>
                <p className="truncate text-[11px] text-[var(--color-ink-muted)]">{DEMO_DOCTOR.role}</p>
              </div>
              <Button size="sm" variant="quiet" onClick={() => void submit(DEMO_DOCTOR.email, DEMO_DOCTOR.password)}>
                Use
              </Button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
