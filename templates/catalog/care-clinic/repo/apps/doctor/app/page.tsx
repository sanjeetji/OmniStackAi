"use client";

import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  IndianRupee,
  Play,
  Users,
  Video,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../components/shell";
import { Panel, Stat, Badge, Button, DataState, Table, Row, Cell } from "../components/ui";
import { useApi, useInterval } from "../lib/use-api";
import { useSession } from "../lib/session";
import { clock, count, minutesSince, money, num, titleCase, tone } from "../lib/format";

export default function ClinicalDashboard() {
  const { pulse, doctor } = useSession();
  const dashboard = useApi(() => defaultApiClient.getDoctorDashboard(), [pulse]);
  const queue = useApi(() => defaultApiClient.getDoctorQueue(), [pulse]);

  useInterval(() => {
    dashboard.refresh();
    queue.refresh();
  }, 20_000);

  const metrics = dashboard.data?.metrics;
  const active = dashboard.data?.activeConsultation ?? null;
  const rows = queue.data?.queue ?? [];
  const waiting = rows.filter((a) => a.status === "checked_in");
  const next = waiting[0] ?? null;
  const upcomingVideo = rows.filter((a) => a.appointment_type === "video" && a.status !== "completed");

  return (
    <Shell
      title={`Good day, ${doctor?.full_name?.split(" ").slice(0, 2).join(" ") ?? "Doctor"}`}
      subtitle="Your clinic today"
      actions={<Button href="/queue" size="sm">Open the queue</Button>}
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="On today's list" value={count(metrics?.today_total)} hint={`${count(metrics?.completed_count)} seen`} icon={<ClipboardList size={15} />} />
        <Stat
          label="Waiting for you"
          value={count(metrics?.waiting_count)}
          tone={num(metrics?.waiting_count) > 4 ? "alert" : "signal"}
          hint={`${count(metrics?.pending_count)} yet to arrive`}
          icon={<Users size={15} />}
        />
        <Stat label="Video visits" value={count(metrics?.video_count)} hint="Booked for today" icon={<Video size={15} />} />
        <Stat label="Billed today" value={money(metrics?.today_earnings)} tone="good" hint="Completed consultations" icon={<IndianRupee size={15} />} />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1.4fr_1fr]">
        <Panel
          title={active ? "In the chair" : "Nobody in the chair"}
          subtitle={active ? "The consultation you are in the middle of" : "Call the next token when you are ready"}
        >
          <DataState state={dashboard}>
            {() =>
              active ? (
                <div>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="text-[18px] font-semibold tracking-tight text-[var(--color-ink)]">
                        {active.patient_name}
                      </h3>
                      <p className="text-[12.5px] text-[var(--color-ink-muted)]">
                        Token {active.token_number ?? "—"} · {clock(active.start_time)} ·{" "}
                        {active.patient_age ? `${active.patient_age} yrs` : "age not recorded"}
                        {active.gender ? `, ${titleCase(active.gender)}` : ""}
                        {active.blood_group ? ` · ${active.blood_group}` : ""}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1.5">
                      <Badge tone="alert">In consultation</Badge>
                      {active.started_at && (
                        <span className="tabular text-[11.5px] text-[var(--color-ink-muted)]">
                          {minutesSince(active.started_at)} min so far
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button href={`/consult/${active.id}`}>
                      <Play size={13} /> Back to the consultation
                    </Button>
                    {active.appointment_type === "video" && (
                      <Button href={`/telehealth/${active.id}`} variant="quiet">
                        <Video size={13} /> Video room
                      </Button>
                    )}
                    <Button href={`/patients/${active.patient_id}`} variant="quiet">
                      Full chart
                    </Button>
                  </div>
                </div>
              ) : next ? (
                <div>
                  <p className="text-[12.5px] text-[var(--color-ink-muted)]">Next in the queue</p>
                  <h3 className="mt-1 text-[18px] font-semibold tracking-tight text-[var(--color-ink)]">
                    {next.patient_name}
                  </h3>
                  <p className="text-[12.5px] text-[var(--color-ink-muted)]">
                    Token {next.token_number ?? "—"} · {clock(next.start_time)}
                    {next.family_member_name ? ` · for ${next.family_member_name}` : ""}
                  </p>
                  <div className="mt-4">
                    <Button href={`/consult/${next.id}`}>
                      <Play size={13} /> Start the consultation
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="flex items-center gap-2 py-6 text-[13px] text-[var(--color-ink-muted)]">
                  <CheckCircle2 size={15} className="text-emerald-600" />
                  Nobody is waiting. The desk will send the next patient through.
                </p>
              )
            }
          </DataState>
        </Panel>

        <Panel title="Worth a look" subtitle="Things on today's list that need a decision" padded={false}>
          <DataState state={queue}>
            {() => {
              const notes: { text: string; href: string; tone: "alert" | "info" }[] = [];
              if (upcomingVideo.length > 0) {
                notes.push({
                  text: `${upcomingVideo.length} video visit${upcomingVideo.length > 1 ? "s" : ""} to join today`,
                  href: "/queue",
                  tone: "info",
                });
              }
              const noShows = rows.filter((a) => a.status === "no_show");
              if (noShows.length > 0) {
                notes.push({ text: `${noShows.length} patient did not arrive`, href: "/queue", tone: "alert" });
              }
              const unsigned = rows.filter((a) => a.consultation_id && !a.prescription_id && a.status === "completed");
              if (unsigned.length > 0) {
                notes.push({
                  text: `${unsigned.length} completed visit${unsigned.length > 1 ? "s" : ""} with no prescription`,
                  href: "/queue",
                  tone: "alert",
                });
              }
              if (notes.length === 0) {
                return (
                  <p className="px-4 py-8 text-center text-[12.5px] text-[var(--color-ink-muted)]">
                    Nothing needs your attention.
                  </p>
                );
              }
              return (
                <ul className="divide-y divide-[var(--color-border)]">
                  {notes.map((note) => (
                    <li key={note.text}>
                      <Link href={note.href} className="flex items-center gap-2.5 px-4 py-3 hover:bg-slate-50">
                        <AlertTriangle
                          size={14}
                          className={note.tone === "alert" ? "shrink-0 text-amber-600" : "shrink-0 text-sky-600"}
                        />
                        <span className="text-[12.5px] text-[var(--color-ink)]">{note.text}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              );
            }}
          </DataState>
        </Panel>
      </div>

      <Panel
        className="mt-3"
        title="Today's list"
        subtitle="In token order"
        padded={false}
        actions={<Button href="/queue" variant="ghost" size="sm">Open the queue</Button>}
      >
        <DataState state={queue} empty={{ title: "Nothing booked today", detail: "Your next clinic day will appear here." }}>
          {(data) => (
            <Table head={["Token", "Patient", "Time", "Type", "Status", ""]}>
              {data.queue.slice(0, 10).map((entry) => (
                <Row key={entry.id}>
                  <Cell mono>{entry.token_number ?? "—"}</Cell>
                  <Cell>
                    <p className="font-medium text-[var(--color-ink)]">{entry.patient_name}</p>
                    {entry.family_member_name && (
                      <p className="text-[11px] text-[var(--color-ink-subtle)]">
                        for {entry.family_member_name} ({entry.family_member_rel})
                      </p>
                    )}
                  </Cell>
                  <Cell mono muted>{clock(entry.start_time)}</Cell>
                  <Cell>
                    <Badge tone={entry.appointment_type === "video" ? "signal" : "neutral"}>
                      {entry.appointment_type === "video" ? "Video" : "In clinic"}
                    </Badge>
                  </Cell>
                  <Cell>
                    <Badge tone={tone.appointment(entry.status)}>{titleCase(entry.status)}</Badge>
                  </Cell>
                  <Cell align="right">
                    {(entry.status === "checked_in" || entry.status === "in_consult") && (
                      <Button size="sm" href={`/consult/${entry.id}`}>
                        {entry.status === "in_consult" ? "Resume" : "Start"}
                      </Button>
                    )}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </DataState>
      </Panel>
    </Shell>
  );
}
