"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Mic,
  MicOff,
  MonitorUp,
  PhoneOff,
  Pill,
  Stethoscope,
  Video,
  VideoOff,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote, classes } from "../../../components/ui";
import { useApi, useAction, useInterval } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { clock, stamp, titleCase } from "../../../lib/format";

function duration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function TelehealthRoom({ params }: { params: Promise<{ appointmentId: string }> }) {
  const { appointmentId } = use(params);
  const router = useRouter();
  const { notify, pulse } = useSession();
  const context = useApi(() => defaultApiClient.getConsultContext(appointmentId), [appointmentId]);
  const session = useApi(() => defaultApiClient.getDoctorTelehealth(appointmentId), [appointmentId, pulse]);
  const { run, busy, error } = useAction();

  const [micOff, setMicOff] = useState(false);
  const [cameraOff, setCameraOff] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const room = session.data?.session ?? null;
  const live = room?.status === "active";

  useInterval(() => setElapsed((value) => value + 1), live ? 1000 : null);
  useInterval(session.refresh, 15_000);

  useEffect(() => {
    if (room?.doctor_joined_at) {
      setElapsed(Math.max(0, Math.round((Date.now() - new Date(room.doctor_joined_at).getTime()) / 1000)));
    }
  }, [room?.doctor_joined_at]);

  async function join() {
    const ok = await run(async () => {
      await defaultApiClient.joinDoctorTelehealth(appointmentId);
      session.refresh();
    });
    if (ok) notify({ title: "You are in the room", tone: "good" });
  }

  async function end() {
    const ok = await run(async () => {
      await defaultApiClient.endDoctorTelehealth(appointmentId);
      session.refresh();
    });
    if (ok) {
      notify({ title: "Call ended", tone: "info" });
      router.push(`/consult/${appointmentId}`);
    }
  }

  return (
    <Shell
      title="Video consultation"
      subtitle="The room is simulated in this deployment; swap the provider in services/api/src/services/telehealth.ts"
      wide
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={context}>
        {(data) => {
          const { appointment, medicalHistory, vitals } = data;
          const latest = vitals[0];

          return (
            <div className="grid gap-3 xl:grid-cols-[1.6fr_1fr]">
              <div className="space-y-3">
                <div className="relative overflow-hidden rounded-2xl bg-slate-900 ring-1 ring-slate-800">
                  <div className="flex aspect-video items-center justify-center">
                    {live ? (
                      <div className="text-center">
                        <div className="mx-auto grid h-24 w-24 place-items-center rounded-full bg-slate-800 text-[30px] font-semibold text-slate-300">
                          {appointment.patient_name
                            .split(" ")
                            .map((part) => part[0])
                            .slice(0, 2)
                            .join("")}
                        </div>
                        <p className="mt-3 text-[16px] font-semibold text-white">{appointment.patient_name}</p>
                        <p className="text-[12.5px] text-slate-400">
                          {room?.patient_joined_at ? "Connected" : "Waiting for the patient to join"}
                          {room?.connection_quality ? ` · ${titleCase(room.connection_quality)} connection` : ""}
                        </p>
                      </div>
                    ) : (
                      <div className="text-center">
                        <Video size={34} className="mx-auto text-slate-600" />
                        <p className="mt-3 text-[15px] font-semibold text-white">
                          {room?.status === "ended" ? "The call has ended" : "You are not in the room yet"}
                        </p>
                        <p className="text-[12.5px] text-slate-400">
                          {room?.status === "ended"
                            ? `Lasted ${duration(room.call_duration_seconds ?? 0)}`
                            : "Join when you are ready to see the patient"}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* The doctor's own picture-in-picture preview. */}
                  <div className="absolute bottom-3 right-3 grid h-24 w-36 place-items-center rounded-xl bg-slate-800 ring-1 ring-slate-700">
                    {cameraOff ? (
                      <VideoOff size={18} className="text-slate-500" />
                    ) : (
                      <span className="text-[11px] font-medium text-slate-400">You</span>
                    )}
                  </div>

                  {live && (
                    <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
                      <span className="tabular text-[12px] font-semibold text-white">{duration(elapsed)}</span>
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap items-center justify-center gap-2 rounded-2xl border border-[var(--color-border)] bg-white p-3">
                  <button
                    onClick={() => setMicOff((value) => !value)}
                    disabled={!live}
                    className={classes(
                      "grid h-11 w-11 place-items-center rounded-full transition disabled:opacity-40",
                      micOff ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    )}
                    aria-label={micOff ? "Unmute" : "Mute"}
                  >
                    {micOff ? <MicOff size={18} /> : <Mic size={18} />}
                  </button>
                  <button
                    onClick={() => setCameraOff((value) => !value)}
                    disabled={!live}
                    className={classes(
                      "grid h-11 w-11 place-items-center rounded-full transition disabled:opacity-40",
                      cameraOff ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    )}
                    aria-label={cameraOff ? "Turn the camera on" : "Turn the camera off"}
                  >
                    {cameraOff ? <VideoOff size={18} /> : <Video size={18} />}
                  </button>
                  <button
                    onClick={() => setSharing((value) => !value)}
                    disabled={!live}
                    className={classes(
                      "grid h-11 w-11 place-items-center rounded-full transition disabled:opacity-40",
                      sharing ? "bg-sky-100 text-sky-700" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    )}
                    aria-label="Share a report"
                  >
                    <MonitorUp size={18} />
                  </button>

                  <div className="mx-2 h-8 w-px bg-[var(--color-border)]" />

                  {live ? (
                    <Button variant="danger" disabled={busy} onClick={() => void end()}>
                      <PhoneOff size={14} /> End the call
                    </Button>
                  ) : room?.status === "ended" ? (
                    <Button href={`/consult/${appointmentId}`} variant="quiet">
                      Back to the consultation
                    </Button>
                  ) : (
                    <Button disabled={busy} onClick={() => void join()}>
                      <Video size={14} /> Join the room
                    </Button>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <Panel title="Who you are seeing">
                  <p className="text-[16px] font-semibold tracking-tight text-[var(--color-ink)]">
                    {appointment.patient_name}
                  </p>
                  <p className="text-[12.5px] text-[var(--color-ink-muted)]">
                    {appointment.patient_age ? `${appointment.patient_age} yrs` : "Age not recorded"}
                    {appointment.gender ? `, ${titleCase(appointment.gender)}` : ""}
                    {appointment.blood_group ? ` · ${appointment.blood_group}` : ""} · {clock(appointment.start_time)}
                  </p>

                  {appointment.notes && (
                    <p className="mt-2 rounded-lg bg-slate-50 px-2.5 py-1.5 text-[12.5px] text-[var(--color-ink)]">
                      <span className="font-semibold">In their words: </span>
                      {appointment.notes}
                    </p>
                  )}

                  {medicalHistory.allergies?.length > 0 && (
                    <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[12px] text-red-800">
                      <AlertTriangle size={13} className="mt-0.5 shrink-0" />
                      Allergic to {medicalHistory.allergies.join(", ")}
                    </p>
                  )}

                  {latest && (
                    <div className="mt-3 flex flex-wrap gap-1.5 border-t border-[var(--color-border)] pt-2.5">
                      {[
                        latest.bp_systolic ? `BP ${latest.bp_systolic}/${latest.bp_diastolic}` : null,
                        latest.heart_rate ? `Pulse ${latest.heart_rate}` : null,
                        latest.spo2_percent ? `SpO₂ ${latest.spo2_percent}%` : null,
                      ]
                        .filter(Boolean)
                        .map((item) => (
                          <span key={item as string} className="tabular rounded bg-slate-100 px-2 py-0.5 text-[12px]">
                            {item}
                          </span>
                        ))}
                    </div>
                  )}
                </Panel>

                <Panel title="While you talk">
                  <div className="flex flex-col gap-2">
                    <Button href={`/consult/${appointmentId}/soap`} variant="quiet">
                      <Stethoscope size={13} /> Write the notes
                    </Button>
                    <Button href={`/consult/${appointmentId}/prescription`} variant="quiet">
                      <Pill size={13} /> Prescribe
                    </Button>
                    <Button href={`/patients/${appointment.patient_id}`} variant="quiet">
                      Open the full chart
                    </Button>
                  </div>
                </Panel>

                <Panel title="This room">
                  <DataState state={session}>
                    {(data) => (
                      <dl className="space-y-1.5 text-[12.5px]">
                        {[
                          ["Status", data.session ? titleCase(data.session.status) : "—"],
                          ["You joined", data.session?.doctor_joined_at ? stamp(data.session.doctor_joined_at) : "Not yet"],
                          ["Patient joined", data.session?.patient_joined_at ? stamp(data.session.patient_joined_at) : "Not yet"],
                          ["Quality", data.session?.connection_quality ? titleCase(data.session.connection_quality) : "—"],
                        ].map(([label, value]) => (
                          <div key={label} className="flex justify-between gap-4">
                            <dt className="text-[var(--color-ink-muted)]">{label}</dt>
                            <dd className="text-right text-[var(--color-ink)]">{value}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </DataState>
                  <p className="mt-2.5 border-t border-[var(--color-border)] pt-2 text-[11px] leading-relaxed text-[var(--color-ink-muted)]">
                    The media layer is a mock: the room, its token and its state are real rows, but no peer
                    connection is opened. Replace the service to use a real provider.
                  </p>
                </Panel>
              </div>
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
