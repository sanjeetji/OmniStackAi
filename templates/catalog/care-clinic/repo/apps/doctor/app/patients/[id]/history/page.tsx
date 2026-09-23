"use client";

import { use } from "react";
import { ArrowLeft, FlaskConical, Pill, Stethoscope } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../../components/shell";
import { Panel, Badge, Button, DataState } from "../../../../components/ui";
import { TrendChart } from "../../../../components/charts";
import { useApi } from "../../../../lib/use-api";
import { dayShort, day, stamp, titleCase, tone } from "../../../../lib/format";

type Entry =
  | { kind: "consultation"; at: string; title: string; detail: string; sub: string }
  | { kind: "prescription"; at: string; title: string; detail: string; sub: string }
  | { kind: "lab"; at: string; title: string; detail: string; sub: string; status: string };

export default function PatientHistory({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const chart = useApi(() => defaultApiClient.getPatientChart(id), [id]);

  return (
    <Shell
      title="Longitudinal history"
      subtitle="Every encounter on record, newest first"
      actions={
        <Button href={`/patients/${id}`} variant="quiet" size="sm">
          <ArrowLeft size={13} /> Chart
        </Button>
      }
    >
      <DataState state={chart}>
        {(data) => {
          const entries: Entry[] = [
            ...data.consultations.map((c) => ({
              kind: "consultation" as const,
              at: String(c.completed_at ?? c.scheduled_date),
              title: c.assessment ?? "Consultation",
              detail: c.plan ?? "",
              sub: `${c.doctor_name} · ${c.appointment_number}`,
            })),
            ...data.prescriptions.map((rx) => ({
              kind: "prescription" as const,
              at: String(rx.signed_at ?? rx.created_at),
              title: rx.diagnosis_summary,
              detail: `Prescription ${rx.prescription_number}`,
              sub: rx.doctor_name,
            })),
            ...data.labOrders.map((order) => ({
              kind: "lab" as const,
              at: String(order.completed_at ?? order.created_at),
              title: `Lab order ${order.order_number}`,
              detail: "",
              sub: order.doctor_name,
              status: order.status,
            })),
          ].sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());

          const bp = [...data.vitals]
            .filter((v) => v.bp_systolic)
            .reverse()
            .map((v) => ({
              label: dayShort(v.recorded_at),
              value: Number(v.bp_systolic),
              secondary: Number(v.bp_diastolic),
            }));

          return (
            <div className="grid gap-3 lg:grid-cols-[1.5fr_1fr]">
              <Panel title="Timeline" subtitle={`${entries.length} entries`} padded={false}>
                {entries.length === 0 ? (
                  <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                    Nothing on record for this patient yet.
                  </p>
                ) : (
                  <ol className="divide-y divide-[var(--color-border)]">
                    {entries.map((entry, index) => (
                      <li key={`${entry.kind}-${index}`} className="flex gap-3 px-4 py-3">
                        <span className="mt-0.5 shrink-0 text-slate-400">
                          {entry.kind === "consultation" ? (
                            <Stethoscope size={15} />
                          ) : entry.kind === "prescription" ? (
                            <Pill size={15} />
                          ) : (
                            <FlaskConical size={15} />
                          )}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <p className="text-[13px] font-semibold text-[var(--color-ink)]">{entry.title}</p>
                            <span className="tabular shrink-0 text-[11.5px] text-[var(--color-ink-subtle)]">
                              {stamp(entry.at)}
                            </span>
                          </div>
                          {entry.detail && (
                            <p className="mt-0.5 text-[12.5px] leading-relaxed text-[var(--color-ink-muted)]">
                              {entry.detail}
                            </p>
                          )}
                          <div className="mt-1 flex items-center gap-2">
                            <span className="text-[11.5px] text-[var(--color-ink-subtle)]">{entry.sub}</span>
                            {entry.kind === "lab" && (
                              <Badge tone={tone.lab(entry.status)}>{titleCase(entry.status)}</Badge>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </Panel>

              <div className="space-y-3">
                <Panel title="Blood pressure" subtitle="Bars are systolic; the amber tick is diastolic">
                  {bp.length === 0 ? (
                    <p className="py-8 text-center text-[12.5px] text-[var(--color-ink-muted)]">
                      No blood-pressure readings on record.
                    </p>
                  ) : (
                    <TrendChart series={bp} height={150} />
                  )}
                </Panel>

                <Panel title="Recorded vitals" padded={false}>
                  {data.vitals.length === 0 ? (
                    <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-ink-muted)]">None.</p>
                  ) : (
                    <ul className="divide-y divide-[var(--color-border)]">
                      {data.vitals.map((vital) => (
                        <li key={vital.id} className="px-4 py-2.5">
                          <p className="tabular text-[12.5px] text-[var(--color-ink)]">
                            {vital.bp_systolic ? `${vital.bp_systolic}/${vital.bp_diastolic} mmHg` : "—"}
                            {vital.heart_rate ? ` · ${vital.heart_rate} bpm` : ""}
                            {vital.spo2_percent ? ` · SpO₂ ${vital.spo2_percent}%` : ""}
                          </p>
                          <p className="text-[11px] text-[var(--color-ink-subtle)]">
                            {stamp(vital.recorded_at)}
                            {vital.notes ? ` · ${vital.notes}` : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </Panel>
              </div>
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
