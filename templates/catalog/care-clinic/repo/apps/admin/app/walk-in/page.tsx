"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, UserPlus } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Field, Button, DataState, ErrorNote, inputClass, Badge } from "../../components/ui";
import { useApi, useAction } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { money } from "../../lib/format";

const PAYMENT_METHODS = ["cash", "card", "upi", "insurance"] as const;

export default function WalkIn() {
  const router = useRouter();
  const { notify } = useSession();
  const doctors = useApi(() => defaultApiClient.getAdminDoctors(), []);
  const { run, busy, error } = useAction();

  const [patientName, setPatientName] = useState("");
  const [phone, setPhone] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [notes, setNotes] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<(typeof PAYMENT_METHODS)[number]>("cash");
  const [booked, setBooked] = useState<{ name: string; token: number | null; number: string } | null>(null);

  const selected = doctors.data?.doctors.find((doctor) => doctor.id === doctorId);

  async function submit() {
    const ok = await run(async () => {
      const result = await defaultApiClient.bookWalkIn({
        patientName: patientName.trim(),
        phone: phone.trim() || undefined,
        doctorId,
        notes: notes.trim() || undefined,
        paymentMethod,
      });
      setBooked({
        name: result.patient.full_name,
        token: result.appointment.token_number ?? null,
        number: result.appointment.appointment_number,
      });
      setPatientName("");
      setPhone("");
      setNotes("");
    });
    if (ok) notify({ title: "Walk-in booked", detail: "The patient is in today's queue", tone: "good" });
  }

  return (
    <Shell
      title="Walk-in booking"
      subtitle="Register someone at the counter and put them straight into today's queue"
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      {booked && (
        <div className="rise-in mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-[var(--color-good-soft)] px-4 py-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 size={18} className="text-[var(--color-good)]" />
            <div>
              <p className="text-[13px] font-semibold text-[var(--color-ink)]">{booked.name} is booked and checked in</p>
              <p className="tabular text-[12px] text-[var(--color-ink-muted)]">{booked.number}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="tabular rounded-md bg-white px-3 py-1.5 text-[22px] font-bold text-[var(--color-good)] ring-1 ring-emerald-200">
              {booked.token ?? "—"}
            </span>
            <Button variant="quiet" size="sm" onClick={() => router.push("/front-desk")}>
              Open the desk
            </Button>
          </div>
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
        <Panel title="Patient" subtitle="A counter registration; the full record can be completed later">
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            <Field label="Full name">
              <input
                className={inputClass}
                value={patientName}
                onChange={(event) => setPatientName(event.target.value)}
                placeholder="As written on the ID"
                required
              />
            </Field>
            <Field label="Mobile" hint="Used for the token SMS and the receipt">
              <input
                className={inputClass}
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="+91 "
              />
            </Field>
            <Field label="Reason for the visit">
              <textarea
                className={`${inputClass} min-h-20`}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Presenting complaint in the patient's own words"
              />
            </Field>
            <Field label="Payment at the counter">
              <div className="flex flex-wrap gap-1.5">
                {PAYMENT_METHODS.map((method) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => setPaymentMethod(method)}
                    className={
                      paymentMethod === method
                        ? "rounded-md bg-[var(--color-signal)] px-2.5 py-1 text-[12px] font-semibold capitalize text-white"
                        : "rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1 text-[12px] font-medium capitalize text-[var(--color-ink-muted)] hover:bg-slate-50"
                    }
                  >
                    {method}
                  </button>
                ))}
              </div>
            </Field>

            <Button type="submit" disabled={busy || !patientName.trim() || !doctorId}>
              <UserPlus size={14} /> {busy ? "Booking" : "Book and issue a token"}
            </Button>
          </form>
        </Panel>

        <Panel title="Who is free now" subtitle="The walk-in takes the next 20-minute slot with this doctor" padded={false}>
          <DataState state={doctors}>
            {(data) => (
              <ul className="max-h-[520px] divide-y divide-[var(--color-border)] overflow-y-auto">
                {data.doctors.map((doctor) => (
                  <li key={doctor.id}>
                    <button
                      onClick={() => setDoctorId(doctor.id)}
                      className={
                        doctorId === doctor.id
                          ? "flex w-full items-center justify-between gap-3 bg-[var(--color-signal-soft)] px-4 py-2.5 text-left"
                          : "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-slate-50"
                      }
                    >
                      <div className="min-w-0">
                        <p className="truncate text-[12.5px] font-medium text-[var(--color-ink)]">{doctor.full_name}</p>
                        <p className="truncate text-[11px] text-[var(--color-ink-muted)]">
                          {doctor.specialties.join(", ")} · {doctor.room_number ?? "No room"}
                        </p>
                      </div>
                      <span className="tabular shrink-0 text-[12px] font-semibold text-[var(--color-ink)]">
                        {money(doctor.consultation_fee_inr)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </DataState>
          {selected && (
            <div className="border-t border-[var(--color-border)] px-4 py-3">
              <Badge tone="signal">Selected</Badge>
              <p className="mt-1.5 text-[12.5px] font-medium text-[var(--color-ink)]">{selected.full_name}</p>
              <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                {selected.qualification} · {money(selected.consultation_fee_inr)} consultation
              </p>
            </div>
          )}
        </Panel>
      </div>
    </Shell>
  );
}
