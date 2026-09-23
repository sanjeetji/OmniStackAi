"use client";

import { use, useEffect, useRef } from "react";
import { CheckCircle2, FlaskConical, Pill, Play, Stethoscope } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../components/shell";
import { ConsultFrame, BackToQueue } from "../../../components/consult-frame";
import { Panel, Badge, Button, DataState, ErrorNote } from "../../../components/ui";
import { useApi, useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { day, stamp, titleCase, tone } from "../../../lib/format";

export default function Consultation({ params }: { params: Promise<{ appointmentId: string }> }) {
  const { appointmentId } = use(params);
  const { notify } = useSession();
  const context = useApi(() => defaultApiClient.getConsultContext(appointmentId), [appointmentId]);
  const { run, busy, error } = useAction();
  const startedOnce = useRef(false);

  // A checked-in patient moves to "in consult" the moment the doctor opens this screen. The API
  // refuses the transition from any other state, so a completed visit just opens read-only.
  useEffect(() => {
    const appointment = context.data?.appointment;
    if (!appointment || startedOnce.current) return;
    if (appointment.status !== "checked_in") return;
    startedOnce.current = true;
    void run(async () => {
      await defaultApiClient.startConsultation(appointmentId);
      context.refresh();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [context.data?.appointment?.status]);

  async function complete() {
    const ok = await run(async () => {
      await defaultApiClient.completeConsultation(appointmentId);
      context.refresh();
    });
    if (ok) notify({ title: "Consultation completed", detail: "The desk can settle the bill", tone: "good" });
  }

  return (
    <Shell title="Consultation" subtitle="The patient in front of you" actions={<BackToQueue />}>
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={context}>
        {(data) => {
          const { consultation, diagnoses, prescription, prescriptionItems, labOrders, previousVisits } = data;
          const finished = Boolean(consultation?.completed_at);
          const hasNotes = Boolean(consultation?.subjective || consultation?.assessment);

          return (
            <ConsultFrame context={data} appointmentId={appointmentId}>
              <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
                <div className="space-y-3">
                  <Panel
                    title="This visit"
                    subtitle={
                      consultation
                        ? `Started ${stamp(consultation.started_at)}${
                            consultation.completed_at ? `, completed ${stamp(consultation.completed_at)}` : ""
                          }`
                        : "Not started yet"
                    }
                  >
                    {consultation ? (
                      <dl className="space-y-3">
                        {[
                          ["Subjective", consultation.subjective],
                          ["Objective", consultation.objective],
                          ["Assessment", consultation.assessment],
                          ["Plan", consultation.plan],
                        ].map(([label, value]) => (
                          <div key={label as string}>
                            <dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                              {label}
                            </dt>
                            <dd className="mt-0.5 text-[13px] leading-relaxed text-[var(--color-ink)]">
                              {(value as string) || <span className="text-[var(--color-ink-subtle)]">Not written yet</span>}
                            </dd>
                          </div>
                        ))}
                        {consultation.follow_up_date && (
                          <div>
                            <dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                              Follow-up
                            </dt>
                            <dd className="tabular mt-0.5 text-[13px] text-[var(--color-ink)]">
                              {day(String(consultation.follow_up_date))}
                            </dd>
                          </div>
                        )}
                      </dl>
                    ) : (
                      <p className="py-6 text-center text-[13px] text-[var(--color-ink-muted)]">
                        Opening this screen starts the consultation once the patient has checked in.
                      </p>
                    )}

                    <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--color-border)] pt-3">
                      <Button href={`/consult/${appointmentId}/soap`} variant={hasNotes ? "quiet" : "primary"}>
                        <Stethoscope size={13} /> {hasNotes ? "Edit the notes" : "Write the notes"}
                      </Button>
                      <Button href={`/consult/${appointmentId}/prescription`} variant="quiet">
                        <Pill size={13} /> {prescription ? "View the prescription" : "Prescribe"}
                      </Button>
                      <Button href={`/consult/${appointmentId}/labs`} variant="quiet">
                        <FlaskConical size={13} /> Order tests
                      </Button>
                    </div>
                  </Panel>

                  {diagnoses.length > 0 && (
                    <Panel title="Diagnoses" padded={false}>
                      <ul className="divide-y divide-[var(--color-border)]">
                        {diagnoses.map((diagnosis) => (
                          <li key={diagnosis.id} className="flex items-start justify-between gap-3 px-4 py-2.5">
                            <div>
                              <p className="text-[13px] font-medium text-[var(--color-ink)]">
                                {diagnosis.condition_name}
                              </p>
                              {diagnosis.notes && (
                                <p className="text-[11.5px] text-[var(--color-ink-muted)]">{diagnosis.notes}</p>
                              )}
                            </div>
                            <div className="flex shrink-0 items-center gap-1.5">
                              <span className="tabular rounded bg-slate-100 px-1.5 py-0.5 text-[11.5px] font-semibold text-[var(--color-ink)]">
                                {diagnosis.icd10_code}
                              </span>
                              {diagnosis.is_primary && <Badge tone="signal">Primary</Badge>}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </Panel>
                  )}
                </div>

                <div className="space-y-3">
                  <Panel title="Finish the visit">
                    {finished ? (
                      <p className="flex items-center gap-2 text-[13px] text-emerald-700">
                        <CheckCircle2 size={15} /> Completed {stamp(consultation!.completed_at)}
                      </p>
                    ) : (
                      <>
                        <ul className="space-y-1.5 text-[12.5px]">
                          {[
                            { label: "SOAP notes written", done: hasNotes },
                            { label: "Diagnosis coded", done: diagnoses.length > 0 },
                            { label: "Prescription signed", done: Boolean(prescription) },
                          ].map((step) => (
                            <li key={step.label} className="flex items-center gap-2">
                              <span
                                className={
                                  step.done
                                    ? "h-2 w-2 shrink-0 rounded-full bg-emerald-500"
                                    : "h-2 w-2 shrink-0 rounded-full bg-slate-300"
                                }
                              />
                              <span className={step.done ? "text-[var(--color-ink)]" : "text-[var(--color-ink-muted)]"}>
                                {step.label}
                              </span>
                            </li>
                          ))}
                        </ul>
                        <div className="mt-3">
                          <Button disabled={busy || !consultation} onClick={() => void complete()}>
                            <CheckCircle2 size={13} /> Complete the consultation
                          </Button>
                        </div>
                        <p className="mt-1.5 text-[11.5px] text-[var(--color-ink-muted)]">
                          Completing releases the patient to the desk and closes this record.
                        </p>
                      </>
                    )}
                  </Panel>

                  <Panel title="Orders from this visit" padded={false}>
                    {prescription || labOrders.length > 0 ? (
                      <ul className="divide-y divide-[var(--color-border)]">
                        {prescription && (
                          <li className="flex items-start gap-2 px-4 py-2.5">
                            <Pill size={14} className="mt-0.5 shrink-0 text-slate-400" />
                            <div className="min-w-0">
                              <p className="tabular text-[12.5px] font-medium text-[var(--color-ink)]">
                                {prescription.prescription_number}
                              </p>
                              <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                                {prescriptionItems.length} medicine{prescriptionItems.length === 1 ? "" : "s"} ·{" "}
                                {prescription.is_immutable ? "signed and locked" : "draft"}
                              </p>
                            </div>
                          </li>
                        )}
                        {labOrders.map((order) => (
                          <li key={order.id} className="flex items-center justify-between gap-2 px-4 py-2.5">
                            <div className="min-w-0">
                              <p className="tabular text-[12.5px] font-medium text-[var(--color-ink)]">
                                {order.order_number}
                              </p>
                              <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                                {order.test_count} test{Number(order.test_count) === 1 ? "" : "s"}
                              </p>
                            </div>
                            <Badge tone={tone.lab(order.status)}>{titleCase(order.status)}</Badge>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-ink-muted)]">
                        Nothing ordered yet.
                      </p>
                    )}
                  </Panel>

                  <Panel title="Last time" subtitle="Previous completed visits" padded={false}>
                    {previousVisits.length === 0 ? (
                      <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-ink-muted)]">
                        This is their first consultation on record.
                      </p>
                    ) : (
                      <ul className="divide-y divide-[var(--color-border)]">
                        {previousVisits.map((visit) => (
                          <li key={visit.id} className="px-4 py-2.5">
                            <div className="flex items-baseline justify-between gap-2">
                              <p className="text-[12.5px] font-medium text-[var(--color-ink)]">
                                {visit.assessment ?? "Consultation"}
                              </p>
                              <span className="tabular shrink-0 text-[11px] text-[var(--color-ink-subtle)]">
                                {day(String(visit.scheduled_date))}
                              </span>
                            </div>
                            {visit.plan && (
                              <p className="mt-0.5 text-[11.5px] leading-relaxed text-[var(--color-ink-muted)]">
                                {visit.plan}
                              </p>
                            )}
                            <p className="text-[11px] text-[var(--color-ink-subtle)]">{visit.doctor_name}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Panel>
                </div>
              </div>
            </ConsultFrame>
          );
        }}
      </DataState>
    </Shell>
  );
}
