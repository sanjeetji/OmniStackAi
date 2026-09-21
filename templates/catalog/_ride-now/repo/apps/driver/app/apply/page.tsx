"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, type Session } from "@ridenow/shared";
import { AuthFrame } from "@/components/auth-frame";
import { Button, Field, Notice, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useDriver } from "@/lib/driver";

const VEHICLES = [
  { id: "bike", label: "Bike" },
  { id: "auto", label: "Auto" },
  { id: "mini", label: "Mini" },
  { id: "sedan", label: "Sedan" },
  { id: "xl", label: "XL" },
] as const;

type Form = Record<"full_name" | "email" | "phone" | "password" | "vehicle_make" | "vehicle_model" | "vehicle_color" | "plate" | "license_no", string>;

const EMPTY: Form = { full_name: "", email: "", phone: "", password: "", vehicle_make: "", vehicle_model: "", vehicle_color: "", plate: "", license_no: "" };

export default function ApplyPage() {
  const router = useRouter();
  const { signIn } = useDriver();
  const [step, setStep] = useState<1 | 2>(1);
  const [form, setForm] = useState<Form>(EMPTY);
  const [vehicle, setVehicle] = useState<(typeof VEHICLES)[number]["id"]>("mini");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof Form) => (event: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: event.target.value });

  return (
    <AuthFrame
      title={step === 1 ? "Drive with RideNow" : "Your vehicle"}
      subtitle={step === 1 ? "Keep 80% of every fare, get paid out any day, choose your own hours." : "We'll check your documents before your first ride."}
      footer={<>Already driving with us? <Link href="/login" className="font-bold text-go">Sign in</Link></>}
    >
      <ol className="grid grid-cols-2 gap-2" aria-label="Steps">
        {["About you", "Vehicle"].map((label, index) => (
          <li key={label} aria-current={step === index + 1 ? "step" : undefined} className={cx("h-1.5 rounded-full", step > index ? "bg-go" : "bg-line")}>
            <span className="sr-only">{label}</span>
          </li>
        ))}
      </ol>
      <form
        className="grid gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          if (step === 1) {
            setStep(2);
            return;
          }
          setBusy(true);
          setError(null);
          try {
            const session = await api.post<Session>("/auth/register-driver", { ...form, vehicle_type: vehicle });
            signIn(session);
            router.replace("/account?welcome=1");
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Couldn't send your application.");
            if (err instanceof ApiError && err.code === "account_exists") setStep(1);
          } finally {
            setBusy(false);
          }
        }}
      >
        {step === 1 ? (
          <>
            <Field label="Full name" autoComplete="name" value={form.full_name} onChange={set("full_name")} minLength={2} maxLength={80} required />
            <Field label="Email" type="email" autoComplete="email" value={form.email} onChange={set("email")} required />
            <Field label="Mobile number" type="tel" autoComplete="tel" value={form.phone} onChange={set("phone")} placeholder="+91 98450 12345" required />
            <Field label="Password" type="password" autoComplete="new-password" value={form.password} onChange={set("password")} minLength={8} hint="At least 8 characters, with a letter and a number." required />
            <Button type="submit" size="xl">Continue</Button>
          </>
        ) : (
          <>
            <div className="grid gap-1.5">
              <span className="text-sm font-semibold text-fg-muted" id="vehicle-type">Vehicle type</span>
              <div className="grid grid-cols-5 gap-2" role="radiogroup" aria-labelledby="vehicle-type">
                {VEHICLES.map((v) => (
                  <button key={v.id} type="button" role="radio" aria-checked={vehicle === v.id} onClick={() => setVehicle(v.id)} className={cx("h-12 rounded-2xl border text-sm font-bold", vehicle === v.id ? "border-go bg-go-soft text-go" : "border-line text-fg-muted")}>{v.label}</button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Make" value={form.vehicle_make} onChange={set("vehicle_make")} placeholder="Maruti" required />
              <Field label="Model" value={form.vehicle_model} onChange={set("vehicle_model")} placeholder="Dzire" required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Colour" value={form.vehicle_color} onChange={set("vehicle_color")} placeholder="White" required />
              <Field label="Number plate" value={form.plate} onChange={set("plate")} placeholder="KA 05 MX 4417" required />
            </div>
            <Field label="Driving licence number" value={form.license_no} onChange={set("license_no")} placeholder="KA0520190012345" required />
            {error ? <Notice>{error}</Notice> : null}
            <div className="grid grid-cols-[auto_1fr] gap-2">
              <Button type="button" variant="outline" size="xl" onClick={() => setStep(1)}>Back</Button>
              <Button type="submit" size="xl" busy={busy}>Submit application</Button>
            </div>
          </>
        )}
        {step === 1 && error ? <Notice>{error}</Notice> : null}
      </form>
    </AuthFrame>
  );
}
