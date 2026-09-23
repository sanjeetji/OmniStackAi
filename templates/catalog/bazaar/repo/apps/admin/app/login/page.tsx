"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, Store } from "lucide-react";
import { useSession } from "../../lib/session";
import { errorText } from "../../lib/use-api";
import { Button, Field, inputClass, ErrorNote } from "../../components/ui";

/** The operator the seeded marketplace ships with. Demo data only. */
const DEMO_OPERATOR = {
  email: "admin@bazaar.test",
  password: "Admin@2026",
  name: "Vikram Mehta",
  role: "Chief market operator",
};

export default function OperatorSignIn() {
  const { signIn, operator, ready } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState(DEMO_OPERATOR.email);
  const [password, setPassword] = useState(DEMO_OPERATOR.password);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && operator) router.replace("/");
  }, [ready, operator, router]);

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
    <main className="grid min-h-screen bg-[var(--background)] lg:grid-cols-[1.1fr_1fr]">
      <section className="hidden flex-col justify-between border-r border-[var(--surface-border)] bg-[var(--surface)] p-10 lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-lg bg-[var(--accent)] text-[15px] font-bold text-slate-950">
            BZ
          </span>
          <div>
            <p className="text-[14px] font-semibold text-white">Bazaar Ops</p>
            <p className="text-[11px] text-[var(--muted)]">Marketplace control</p>
          </div>
        </div>

        <div className="max-w-md">
          <h1 className="text-[29px] font-semibold leading-tight tracking-tight text-white">
            Where the whole marketplace is answerable.
          </h1>
          <p className="mt-3 text-[13px] leading-relaxed text-[var(--muted-light)]">
            Workshop onboarding and KYC, every order and the consignments it split into, the
            double-entry ledger the money actually lives in, vendor settlements, coupons, review
            moderation, and an audit trail of what operators did.
          </p>
          <ul className="mt-6 space-y-2 text-[12.5px] text-slate-300">
            {[
              "Every figure is derived from the ledger, never a stored running total",
              "A settlement batch is approved by a person, not a cron job",
              "What an operator changes is written to the audit trail",
            ].map((line) => (
              <li key={line} className="flex items-start gap-2">
                <ShieldCheck size={14} className="mt-0.5 shrink-0 text-[var(--accent-light)]" />
                {line}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[11px] text-[var(--muted)]">Operator access only.</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <h2 className="text-[21px] font-semibold tracking-tight text-slate-100">Operator sign in</h2>
          <p className="mt-1 text-[12.5px] text-[var(--muted-light)]">
            Marketplace staff only. Shopper and vendor accounts are refused here.
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
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent)] py-2.5 text-[13px] font-semibold text-slate-950 transition hover:bg-[var(--accent-light)] disabled:opacity-60"
            >
              {busy && <Loader2 size={14} className="animate-spin" />}
              {busy ? "Signing in" : "Sign in"}
            </button>
          </form>

          <div className="mt-6 rounded-lg border border-[var(--surface-border)] bg-[var(--surface)] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">
              Demo operator
            </p>
            <div className="mt-2 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-[12.5px] font-medium text-slate-200">{DEMO_OPERATOR.name}</p>
                <p className="truncate text-[11px] text-[var(--muted-light)]">{DEMO_OPERATOR.role}</p>
              </div>
              <Button size="sm" variant="quiet" onClick={() => void submit(DEMO_OPERATOR.email, DEMO_OPERATOR.password)}>
                Use
              </Button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
