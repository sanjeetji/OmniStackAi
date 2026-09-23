"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AlertTriangle, ArrowLeft, FlaskConical, Pill, Stethoscope, Video } from "lucide-react";
import type { ConsultContext } from "@careclinic/shared";
import { Panel, Badge, Button, classes } from "./ui";
import { clock, minutesSince, stamp, titleCase } from "../lib/format";

const TABS = [
  { segment: "", label: "Overview", icon: Stethoscope },
  { segment: "soap", label: "SOAP notes", icon: Stethoscope },
  { segment: "prescription", label: "Prescription", icon: Pill },
  { segment: "labs", label: "Lab orders", icon: FlaskConical },
];

/**
 * The patient banner and tab strip every consultation screen shares: who is in the chair, what
 * they are allergic to, and what the desk measured on the way in.
 */
export function ConsultFrame({
  context,
  appointmentId,
  children,
}: {
  context: ConsultContext;
  appointmentId: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const { appointment, medicalHistory, vitals, consultation } = context;
  const latest = vitals[0];
  const base = `/consult/${appointmentId}`;

  return (
    <div className="space-y-3">
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-[19px] font-semibold tracking-tight text-[var(--color-ink)]">
                {appointment.patient_name}
              </h2>
              <Badge tone={appointment.appointment_type === "video" ? "signal" : "neutral"}>
                {appointment.appointment_type === "video" ? "Video visit" : "In clinic"}
              </Badge>
              {consultation?.completed_at ? (
                <Badge tone="good">Completed</Badge>
              ) : consultation ? (
                <Badge tone="alert">In consultation</Badge>
              ) : null}
            </div>
            <p className="mt-0.5 text-[12.5px] text-[var(--color-ink-muted)]">
              {appointment.patient_age ? `${appointment.patient_age} yrs` : "Age not recorded"}
              {appointment.gender ? `, ${titleCase(appointment.gender)}` : ""}
              {appointment.blood_group ? ` · ${appointment.blood_group}` : ""} · Token{" "}
              {appointment.token_number ?? "—"} · {clock(appointment.start_time)}
              {appointment.room_number ? ` · ${appointment.room_number}` : ""}
            </p>
            {appointment.family_member_name && (
              <p className="text-[12px] text-[var(--color-ink-muted)]">
                Booked for {appointment.family_member_name} ({appointment.family_member_rel})
              </p>
            )}
            {appointment.notes && (
              <p className="mt-1.5 rounded-lg bg-slate-50 px-2.5 py-1.5 text-[12.5px] text-[var(--color-ink)]">
                <span className="font-semibold">In their words: </span>
                {appointment.notes}
              </p>
            )}
          </div>

          <div className="flex flex-col items-end gap-2">
            {consultation?.started_at && !consultation.completed_at && (
              <span className="tabular text-[11.5px] text-[var(--color-ink-muted)]">
                {minutesSince(consultation.started_at)} min in the chair
              </span>
            )}
            <div className="flex gap-1.5">
              {appointment.appointment_type === "video" && (
                <Button href={`/telehealth/${appointmentId}`} variant="quiet" size="sm">
                  <Video size={13} /> Video room
                </Button>
              )}
              <Button href={`/patients/${appointment.patient_id}`} variant="quiet" size="sm">
                Full chart
              </Button>
            </div>
          </div>
        </div>

        {medicalHistory.allergies?.length > 0 && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-red-600" />
            <p className="text-[12.5px] text-red-800">
              <span className="font-bold uppercase tracking-[0.06em]">Allergic to </span>
              {medicalHistory.allergies.join(", ")}
              {medicalHistory.chronic_conditions?.length > 0 && (
                <span className="text-red-700">
                  {" "}
                  · Known {medicalHistory.chronic_conditions.join(", ").toLowerCase()}
                </span>
              )}
            </p>
          </div>
        )}

        {latest && (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-[var(--color-border)] pt-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-slate-400">
              Desk vitals {stamp(latest.recorded_at)}
            </span>
            {[
              latest.bp_systolic ? `BP ${latest.bp_systolic}/${latest.bp_diastolic}` : null,
              latest.heart_rate ? `Pulse ${latest.heart_rate}` : null,
              latest.spo2_percent ? `SpO₂ ${latest.spo2_percent}%` : null,
              latest.temperature_f ? `Temp ${latest.temperature_f}°F` : null,
              latest.blood_glucose_mg_dl ? `Glucose ${latest.blood_glucose_mg_dl}` : null,
            ]
              .filter(Boolean)
              .map((item) => (
                <span key={item as string} className="tabular rounded bg-slate-100 px-2 py-0.5 text-[12px] text-[var(--color-ink)]">
                  {item}
                </span>
              ))}
          </div>
        )}
      </Panel>

      <nav className="flex flex-wrap gap-1.5">
        {TABS.map((tab) => {
          const href = tab.segment ? `${base}/${tab.segment}` : base;
          const active = pathname === href;
          const Icon = tab.icon;
          return (
            <Link
              key={tab.label}
              href={href}
              className={classes(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-medium transition",
                active
                  ? "bg-[var(--color-emerald-brand)] text-white"
                  : "border border-[var(--color-border)] bg-white text-[var(--color-ink-muted)] hover:bg-slate-50"
              )}
            >
              <Icon size={14} />
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}

export function BackToQueue() {
  return (
    <Button href="/queue" variant="quiet" size="sm">
      <ArrowLeft size={13} /> Queue
    </Button>
  );
}
