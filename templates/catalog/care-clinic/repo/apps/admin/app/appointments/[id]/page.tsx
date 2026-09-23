"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Ban, FileText, Receipt, Stethoscope } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote, Field, inputClass } from "../../../components/ui";
import { useApi, useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { clock, day, money, stamp, titleCase, tone } from "../../../lib/format";

const TIMELINE: { status: string; label: string; detail: string }[] = [
  { status: "booked", label: "Booked", detail: "Slot reserved and the invoice raised" },
  { status: "checked_in", label: "Checked in", detail: "Arrived at the desk and given a token" },
  { status: "in_consult", label: "In consultation", detail: "Called into the chamber" },
  { status: "completed", label: "Completed", detail: "SOAP note signed and prescription issued" },
];

export default function AppointmentInvestigation({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { notify } = useSession();
  const detail = useApi(() => defaultApiClient.getAdminAppointment(id), [id]);
  const { run, busy, error } = useAction();
  const [reason, setReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  async function cancel() {
    const ok = await run(async () => {
      const result = await defaultApiClient.cancelAppointmentAtDesk(id, reason.trim());
      notify({
        title: "Appointment cancelled",
        detail: `${result.refund.refundPercentage}% refunded (${money(result.refund.refundAmount)})`,
        tone: "alert",
      });
    });
    if (ok) {
      setCancelling(false);
      setReason("");
      detail.refresh();
    }
  }

  return (
    <Shell
      title="Appointment"
      subtitle="The whole trail: booking, arrival, consultation, prescription and money"
      actions={
        <Button href="/appointments" variant="quiet" size="sm">
          <ArrowLeft size={13} /> All appointments
        </Button>
      }
    >
      <DataState state={detail}>
        {(data) => {
          const appointment = data.appointment;
          const reached = TIMELINE.findIndex((step) => step.status === appointment.status);
          const cancelled = appointment.status === "cancelled" || appointment.status === "no_show";

          return (
            <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
              <div className="space-y-3">
                <Panel>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="tabular text-[12px] text-[var(--color-ink-subtle)]">{appointment.appointment_number}</p>
                      <h2 className="mt-0.5 text-[18px] font-semibold tracking-tight text-[var(--color-ink)]">
                        {appointment.patient_name}
                      </h2>
                      <p className="text-[12.5px] text-[var(--color-ink-muted)]">
                        {appointment.patient_email}
                        {appointment.patient_phone ? ` · ${appointment.patient_phone}` : ""}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1.5">
                      <Badge tone={tone.appointment(appointment.status)}>{titleCase(appointment.status)}</Badge>
                      <Badge tone={appointment.appointment_type === "video" ? "signal" : "neutral"}>
                        {appointment.appointment_type === "video" ? "Video visit" : "In clinic"}
                      </Badge>
                    </div>
                  </div>

                  <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                    {[
                      { label: "Date", value: day(String(appointment.scheduled_date)) },
                      { label: "Slot", value: `${clock(appointment.start_time)} – ${clock(appointment.end_time)}` },
                      { label: "Token", value: appointment.token_number ?? "Not issued" },
                      { label: "Doctor", value: appointment.doctor_name },
                      { label: "Qualification", value: appointment.qualification ?? "—" },
                      { label: "Room", value: appointment.room_number ?? "Unassigned" },
                    ].map((item) => (
                      <div key={item.label}>
                        <dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">
                          {item.label}
                        </dt>
                        <dd className="tabular mt-0.5 text-[13px] text-[var(--color-ink)]">{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                </Panel>

                <Panel title="What happened" subtitle="Each step of the visit, in order">
                  <ol className="space-y-3">
                    {TIMELINE.map((step, index) => {
                      const done = !cancelled && reached >= index;
                      const current = !cancelled && reached === index;
                      return (
                        <li key={step.status} className="flex gap-3">
                          <span
                            className={
                              done
                                ? "mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--color-good)]"
                                : "mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full bg-slate-300"
                            }
                          />
                          <div>
                            <p className={done ? "text-[13px] font-semibold text-[var(--color-ink)]" : "text-[13px] text-[var(--color-ink-muted)]"}>
                              {step.label}
                              {current && <span className="ml-2 text-[11px] font-semibold text-[var(--color-signal)]">now</span>}
                            </p>
                            <p className="text-[12px] text-[var(--color-ink-muted)]">{step.detail}</p>
                          </div>
                        </li>
                      );
                    })}
                    {cancelled && (
                      <li className="flex gap-3">
                        <span className="mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--color-danger)]" />
                        <div>
                          <p className="text-[13px] font-semibold text-[var(--color-danger)]">{titleCase(appointment.status)}</p>
                          <p className="text-[12px] text-[var(--color-ink-muted)]">
                            {appointment.cancellation_reason ?? "No reason recorded"}
                            {appointment.cancelled_at ? ` · ${stamp(appointment.cancelled_at)}` : ""}
                          </p>
                        </div>
                      </li>
                    )}
                  </ol>
                </Panel>
              </div>

              <div className="space-y-3">
                <Panel title="Money">
                  <dl className="space-y-2 text-[13px]">
                    <div className="flex items-center justify-between">
                      <dt className="text-[var(--color-ink-muted)]">Consultation fee</dt>
                      <dd className="tabular font-semibold">{money(appointment.fee_amount)}</dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-[var(--color-ink-muted)]">Invoice</dt>
                      <dd>
                        {appointment.invoice_id ? (
                          <Link href={`/billing/${appointment.invoice_id}`} className="tabular font-medium text-[var(--color-signal)] hover:underline">
                            {appointment.invoice_number}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-[var(--color-ink-muted)]">Status</dt>
                      <dd><Badge tone={tone.payment(appointment.invoice_status)}>{titleCase(appointment.invoice_status ?? "none")}</Badge></dd>
                    </div>
                  </dl>
                  {appointment.invoice_id && (
                    <div className="mt-3">
                      <Button href={`/billing/${appointment.invoice_id}`} variant="quiet" size="sm">
                        <Receipt size={13} /> Open the receipt
                      </Button>
                    </div>
                  )}
                </Panel>

                <Panel title="Clinical record">
                  <ul className="space-y-2 text-[12.5px]">
                    <li className="flex items-start gap-2">
                      <Stethoscope size={14} className="mt-0.5 shrink-0 text-[var(--color-ink-subtle)]" />
                      <span>
                        {appointment.consultation_id
                          ? `Consultation started ${stamp(appointment.consult_started_at)}${
                              appointment.consult_completed_at ? `, completed ${stamp(appointment.consult_completed_at)}` : ""
                            }`
                          : "No consultation was started for this appointment."}
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <FileText size={14} className="mt-0.5 shrink-0 text-[var(--color-ink-subtle)]" />
                      <span className="tabular">
                        {appointment.prescription_number
                          ? `Prescription ${appointment.prescription_number} signed and locked`
                          : "No prescription issued."}
                      </span>
                    </li>
                  </ul>
                  <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-ink-subtle)]">
                    The console does not open clinical notes. Only the treating doctor can read the chart, and
                    every access is written to the audit log.
                  </p>
                </Panel>

                {!cancelled && appointment.status !== "completed" && (
                  <Panel title="Cancel this appointment" subtitle="The clinic refund policy is applied automatically">
                    {error && <div className="mb-2"><ErrorNote message={error} /></div>}
                    {cancelling ? (
                      <div className="space-y-2">
                        <Field label="Reason">
                          <textarea
                            className={`${inputClass} min-h-16`}
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            placeholder="Why is the visit being cancelled?"
                          />
                        </Field>
                        <div className="flex gap-2">
                          <Button variant="danger" size="sm" disabled={busy || !reason.trim()} onClick={() => void cancel()}>
                            Confirm cancellation
                          </Button>
                          <Button variant="quiet" size="sm" onClick={() => setCancelling(false)}>
                            Keep it
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button variant="quiet" size="sm" onClick={() => setCancelling(true)}>
                        <Ban size={13} /> Cancel and refund
                      </Button>
                    )}
                  </Panel>
                )}
              </div>
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
