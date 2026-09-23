"use client";

import { use } from "react";
import Link from "next/link";
import { Activity, AlertTriangle, ArrowLeft, FileText, FlaskConical, History, Pill } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../components/shell";
import { Panel, Badge, Button, DataState, Table, Row, Cell } from "../../../components/ui";
import { useApi } from "../../../lib/use-api";
import { ageFrom, day, stamp, titleCase, tone } from "../../../lib/format";

export default function PatientChart({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const chart = useApi(() => defaultApiClient.getPatientChart(id), [id]);

  return (
    <Shell
      title="Patient chart"
      subtitle="Opening this chart is recorded in the clinic's audit log"
      actions={
        <Button href="/patients" variant="quiet" size="sm">
          <ArrowLeft size={13} /> Patients
        </Button>
      }
    >
      <DataState state={chart}>
        {(data) => {
          const { profile, medicalHistory, vitals, consultations, prescriptions, labOrders } = data;
          const latest = vitals[0];
          const age = profile.dob ? ageFrom(profile.dob) : null;

          return (
            <div className="grid gap-3 lg:grid-cols-[1fr_1.6fr]">
              <div className="space-y-3">
                <Panel>
                  <h2 className="text-[19px] font-semibold tracking-tight text-[var(--color-ink)]">
                    {profile.full_name}
                  </h2>
                  <p className="text-[12.5px] text-[var(--color-ink-muted)]">
                    {age !== null ? `${age} years` : "Age not recorded"}
                    {profile.gender ? `, ${titleCase(profile.gender)}` : ""}
                    {profile.blood_group ? ` · Blood group ${profile.blood_group}` : ""}
                  </p>

                  <dl className="mt-4 space-y-2 text-[12.5px]">
                    {[
                      ["Email", profile.email],
                      ["Phone", profile.phone ?? "—"],
                      ["Date of birth", profile.dob ? day(profile.dob) : "—"],
                      ["Height", profile.height_cm ? `${profile.height_cm} cm` : "—"],
                      ["Weight", profile.weight_kg ? `${profile.weight_kg} kg` : "—"],
                      ["In an emergency", profile.emergency_contact ? `${profile.emergency_contact} · ${profile.emergency_phone ?? ""}` : "—"],
                    ].map(([label, value]) => (
                      <div key={label} className="flex justify-between gap-4">
                        <dt className="shrink-0 text-[var(--color-ink-muted)]">{label}</dt>
                        <dd className="text-right text-[var(--color-ink)]">{value}</dd>
                      </div>
                    ))}
                  </dl>

                  <div className="mt-3">
                    <Button href={`/patients/${id}/history`} variant="quiet" size="sm">
                      <History size={13} /> Full history
                    </Button>
                  </div>
                </Panel>

                {medicalHistory.allergies?.length > 0 && (
                  <div className="rounded-xl border border-red-200 bg-red-50 p-3.5">
                    <p className="flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-[0.08em] text-red-700">
                      <AlertTriangle size={14} /> Allergies
                    </p>
                    <ul className="mt-1.5 space-y-0.5 text-[13px] font-medium text-red-800">
                      {medicalHistory.allergies.map((allergy) => (
                        <li key={allergy}>{allergy}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <Panel title="Standing problems">
                  {[
                    ["Chronic conditions", medicalHistory.chronic_conditions],
                    ["Current medication", medicalHistory.current_medications],
                    ["Past surgery", medicalHistory.past_surgeries],
                  ].map(([label, items]) => (
                    <div key={label as string} className="mb-3 last:mb-0">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">{label}</p>
                      {(items as string[])?.length ? (
                        <ul className="mt-1 flex flex-wrap gap-1">
                          {(items as string[]).map((item) => (
                            <li key={item}>
                              <Badge>{item}</Badge>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-0.5 text-[12.5px] text-[var(--color-ink-muted)]">Nothing recorded</p>
                      )}
                    </div>
                  ))}
                  {medicalHistory.family_history && (
                    <p className="mt-2 border-t border-[var(--color-border)] pt-2 text-[12px] text-[var(--color-ink-muted)]">
                      <span className="font-semibold text-[var(--color-ink)]">Family history: </span>
                      {medicalHistory.family_history}
                    </p>
                  )}
                </Panel>
              </div>

              <div className="space-y-3">
                <Panel title="Latest vitals" subtitle={latest ? `Recorded ${stamp(latest.recorded_at)}` : undefined}>
                  {latest ? (
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      {[
                        { label: "Blood pressure", value: latest.bp_systolic ? `${latest.bp_systolic}/${latest.bp_diastolic}` : "—", unit: "mmHg" },
                        { label: "Pulse", value: latest.heart_rate ?? "—", unit: "bpm" },
                        { label: "SpO₂", value: latest.spo2_percent ?? "—", unit: "%" },
                        { label: "Temperature", value: latest.temperature_f ?? "—", unit: "°F" },
                        { label: "Respiratory", value: latest.respiratory_rate ?? "—", unit: "/min" },
                        { label: "Glucose", value: latest.blood_glucose_mg_dl ?? "—", unit: "mg/dL" },
                      ].map((vital) => (
                        <div key={vital.label} className="rounded-lg border border-[var(--color-border)] p-2.5">
                          <p className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-slate-400">{vital.label}</p>
                          <p className="tabular text-[17px] font-semibold text-[var(--color-ink)]">{vital.value}</p>
                          <p className="text-[10.5px] text-[var(--color-ink-subtle)]">{vital.unit}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="py-6 text-center text-[13px] text-[var(--color-ink-muted)]">
                      No vitals have been recorded for this patient.
                    </p>
                  )}
                </Panel>

                <Panel title="Consultations" subtitle={`${consultations.length} on record`} padded={false}>
                  {consultations.length === 0 ? (
                    <p className="px-4 py-8 text-center text-[13px] text-[var(--color-ink-muted)]">No consultation yet.</p>
                  ) : (
                    <Table head={["Date", "Doctor", "Assessment", "Follow-up"]}>
                      {consultations.slice(0, 8).map((consultation) => (
                        <Row key={consultation.id}>
                          <Cell mono>{day(String(consultation.scheduled_date))}</Cell>
                          <Cell muted>{consultation.doctor_name}</Cell>
                          <Cell>{consultation.assessment ?? "—"}</Cell>
                          <Cell mono muted>{consultation.follow_up_date ? day(String(consultation.follow_up_date)) : "—"}</Cell>
                        </Row>
                      ))}
                    </Table>
                  )}
                </Panel>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Panel title="Prescriptions" padded={false}>
                    {prescriptions.length === 0 ? (
                      <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-ink-muted)]">None.</p>
                    ) : (
                      <ul className="divide-y divide-[var(--color-border)]">
                        {prescriptions.slice(0, 5).map((rx) => (
                          <li key={rx.id} className="flex items-start gap-2 px-4 py-2.5">
                            <Pill size={14} className="mt-0.5 shrink-0 text-slate-400" />
                            <div className="min-w-0">
                              <p className="tabular text-[12.5px] font-medium text-[var(--color-ink)]">
                                {rx.prescription_number}
                              </p>
                              <p className="truncate text-[11.5px] text-[var(--color-ink-muted)]">
                                {rx.diagnosis_summary}
                              </p>
                              <p className="text-[11px] text-[var(--color-ink-subtle)]">
                                {rx.doctor_name} · {stamp(rx.signed_at)}
                              </p>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Panel>

                  <Panel title="Lab orders" padded={false}>
                    {labOrders.length === 0 ? (
                      <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-ink-muted)]">None.</p>
                    ) : (
                      <ul className="divide-y divide-[var(--color-border)]">
                        {labOrders.slice(0, 5).map((order) => (
                          <li key={order.id} className="flex items-center justify-between gap-2 px-4 py-2.5">
                            <div className="min-w-0">
                              <p className="tabular text-[12.5px] font-medium text-[var(--color-ink)]">
                                {order.order_number}
                              </p>
                              <p className="text-[11px] text-[var(--color-ink-subtle)]">{stamp(order.created_at)}</p>
                            </div>
                            <Badge tone={tone.lab(order.status)}>{titleCase(order.status)}</Badge>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Panel>
                </div>
              </div>
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
