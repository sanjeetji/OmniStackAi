"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Activity, Banknote, ShieldCheck } from "lucide-react";
import { ApiError, type Session } from "@ridenow/shared";
import { CityMap, type MapMarker, type MapZone } from "@ridenow/shared/map";
import { Button, Field, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin } from "@/lib/session";

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

const DEMO_CARS: MapMarker[] = [
  { id: "c1", kind: "car", lat: 12.9719, lng: 77.6412, heading: 80 },
  { id: "c2", kind: "car", lat: 12.9352, lng: 77.6245, heading: 200, tone: "busy" },
  { id: "c3", kind: "car", lat: 12.9756, lng: 77.6066, heading: 140 },
  { id: "c4", kind: "car", lat: 12.9121, lng: 77.6446, heading: 20, tone: "busy" },
  { id: "c5", kind: "car", lat: 12.9569, lng: 77.7011, heading: 300 },
  { id: "c6", kind: "car", lat: 13.0035, lng: 77.5693, heading: 110 },
];
const DEMO_ZONES: MapZone[] = [{ id: "z1", lat: 12.9352, lng: 77.6245, radiusKm: 1.8, label: "Koramangala", surge: 1.4 }];

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, ready, signIn } = useAdmin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const next = safeNext(params.get("next"));

  useEffect(() => {
    if (ready && user) router.replace(next);
  }, [ready, user, router, next]);

  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(420px,1fr)_1.2fr]">
      <main className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-10 flex items-center gap-2.5">
            <span className="relative grid size-9 place-items-center rounded-lg bg-side text-base font-bold text-white">
              R
              <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full bg-brand ring-2 ring-canvas" aria-hidden="true" />
            </span>
            <div className="leading-tight">
              <p className="font-semibold">RideNow Ops</p>
              <p className="text-xs text-muted">Operations console</p>
            </div>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Sign in to run the city</h1>
          <p className="mt-1 text-[13px] text-muted">For the RideNow operations team. Rider and driver accounts use their own apps.</p>
          <form
            className="mt-7 grid gap-4"
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              setError(null);
              try {
                const session = await api.post<Session>("/auth/login", { email, password, role: "admin" });
                signIn(session);
                router.replace(next);
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Couldn't reach the RideNow API. Check that it is running.");
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field label="Work email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Field label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error ? <Notice tone="bad">{error}</Notice> : null}
            <Button type="submit" busy={busy} className="h-10">Sign in</Button>
          </form>
          <button
            type="button"
            onClick={() => {
              setEmail("admin@ridenow.test");
              setPassword("Admin@2026");
            }}
            className="mt-4 w-full rounded-box border border-dashed border-line-strong px-3.5 py-3 text-left text-[13px] text-muted hover:border-signal/60"
          >
            <span className="font-semibold text-ink">Demo operator</span> · admin@ridenow.test / Admin@2026{" "}
            <span className="font-semibold text-signal">Fill in</span>
          </button>
        </div>
      </main>
      <aside className="relative hidden overflow-hidden bg-side lg:block" aria-label="About RideNow Ops">
        <div className="absolute inset-0 opacity-90">
          <CityMap markers={DEMO_CARS} zones={DEMO_ZONES} showLabels={false} ariaLabel="Illustration: cars across Bengaluru" />
        </div>
        <div className="absolute inset-0 bg-gradient-to-t from-side via-side/70 to-side/10" aria-hidden="true" />
        <div className="absolute inset-x-10 bottom-10 grid gap-5 text-white">
          <p className="max-w-md text-2xl font-semibold leading-snug tracking-tight">Every ride, driver and rupee in one place.</p>
          <ul className="grid gap-3 text-[13px] text-side-fg">
            <li className="flex items-center gap-2.5"><Activity className="size-4 text-brand" aria-hidden="true" /> Live trips and drivers on the map as they move</li>
            <li className="flex items-center gap-2.5"><ShieldCheck className="size-4 text-brand" aria-hidden="true" /> Review driver documents before they go online</li>
            <li className="flex items-center gap-2.5"><Banknote className="size-4 text-brand" aria-hidden="true" /> Refunds, payouts and pricing with a full audit trail</li>
          </ul>
        </div>
      </aside>
    </div>
  );
}
