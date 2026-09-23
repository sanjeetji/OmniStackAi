"use client";

import Link from "next/link";
import {
  Activity,
  CalendarCheck,
  CheckCircle2,
  DoorOpen,
  IndianRupee,
  Stethoscope,
  UserMinus,
  Users,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../components/shell";
import { Panel, Stat, Table, Row, Cell, Badge, Button, DataState } from "../components/ui";
import { TrendChart } from "../components/charts";
import { useApi, useInterval } from "../lib/use-api";
import { useSession } from "../lib/session";
import { clock, count, dayShort, money, num, percent, tone, titleCase } from "../lib/format";

export default function OperationsDashboard() {
  const { pulse, prefs } = useSession();
  const dashboard = useApi(() => defaultApiClient.getAdminDashboard(), [pulse]);
  const desk = useApi(() => defaultApiClient.getFrontDesk(), [pulse]);
  const rooms = useApi(() => defaultApiClient.getRooms(), [pulse]);

  useInterval(() => {
    dashboard.refresh();
    desk.refresh();
    rooms.refresh();
  }, prefs.refreshSeconds * 1000);

  const metrics = dashboard.data?.metrics;
  const booked = num(metrics?.total_today);
  const waiting = num(metrics?.waiting_count);
  const queue = desk.data?.queue ?? [];
  const unpaid = queue.filter((entry) => entry.invoice_status === "pending");
  const occupied = (rooms.data?.rooms ?? []).filter((room) => room.current_token !== null);

  return (
    <Shell
      title="Operations dashboard"
      subtitle="Today at CareClinic Indiranagar"
      actions={
        <>
          <Button href="/check-in" variant="quiet" size="sm">
            Check in a patient
          </Button>
          <Button href="/walk-in" size="sm">
            Walk-in booking
          </Button>
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Booked today" value={count(metrics?.total_today)} hint={`${count(metrics?.completed_count)} seen so far`} icon={<CalendarCheck size={15} />} />
        <Stat
          label="Waiting now"
          value={count(metrics?.waiting_count)}
          hint={`${count(metrics?.in_consult_count)} in consultation`}
          tone={waiting > 6 ? "alert" : "signal"}
          icon={<Users size={15} />}
        />
        <Stat
          label="Collected today"
          value={prefs.showMoney ? money(metrics?.today_revenue) : "—"}
          hint={`${unpaid.length} still to settle at the desk`}
          tone="good"
          icon={<IndianRupee size={15} />}
        />
        <Stat
          label="Did not arrive"
          value={count(metrics?.no_show_count)}
          hint={booked > 0 ? `${percent(num(metrics?.no_show_count), booked)} of today's list` : "No list yet"}
          tone={num(metrics?.no_show_count) > 0 ? "danger" : "plain"}
          icon={<UserMinus size={15} />}
        />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1.6fr_1fr]">
        <Panel
          title="Footfall over the last 14 days"
          subtitle="Bars are visits; the amber tick is the money billed that day"
          actions={<Button href="/reports" variant="ghost" size="sm">Full reports</Button>}
        >
          <DataState state={dashboard}>
            {(data) => (
              <TrendChart
                series={data.footfallTrend.map((point) => ({
                  label: dayShort(point.scheduled_date),
                  value: num(point.visit_count),
                  secondary: num(point.gmv) / 1000,
                }))}
              />
            )}
          </DataState>
        </Panel>

        <div className="space-y-3">
          <Panel title="Clinic at a glance">
            <dl className="space-y-2.5 text-[13px]">
              {[
                { label: "Doctors on duty", value: count(metrics?.onDutyDoctors), icon: <Stethoscope size={14} /> },
                { label: "Chambers in use", value: `${occupied.length} of ${rooms.data?.rooms.length ?? 0}`, icon: <DoorOpen size={14} /> },
                { label: "Registered patients", value: count(metrics?.totalRegisteredPatients), icon: <Users size={14} /> },
                { label: "Cancelled today", value: count(metrics?.cancelled_count), icon: <Activity size={14} /> },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between gap-3">
                  <dt className="flex items-center gap-2 text-[var(--color-ink-muted)]">
                    <span className="text-[var(--color-ink-subtle)]">{item.icon}</span>
                    {item.label}
                  </dt>
                  <dd className="tabular font-semibold text-[var(--color-ink)]">{item.value}</dd>
                </div>
              ))}
            </dl>
          </Panel>

          <Panel
            title="Needs the desk"
            subtitle={unpaid.length === 0 ? "Nothing outstanding" : `${unpaid.length} unpaid consultations today`}
            padded={false}
          >
            <DataState state={desk}>
              {() =>
                unpaid.length === 0 ? (
                  <p className="flex items-center gap-2 px-4 py-6 text-[12.5px] text-[var(--color-ink-muted)]">
                    <CheckCircle2 size={14} className="text-[var(--color-good)]" />
                    Every patient on today's list has settled.
                  </p>
                ) : (
                  <ul className="divide-y divide-[var(--color-border)]">
                    {unpaid.slice(0, 6).map((entry) => (
                      <li key={entry.id} className="flex items-center justify-between gap-2 px-4 py-2">
                        <div className="min-w-0">
                          <p className="truncate text-[12.5px] font-medium text-[var(--color-ink)]">{entry.patient_name}</p>
                          <p className="truncate text-[11px] text-[var(--color-ink-muted)]">
                            {clock(entry.start_time)} · {entry.doctor_name}
                          </p>
                        </div>
                        <Link
                          href={entry.invoice_id ? `/billing/${entry.invoice_id}` : "/billing"}
                          className="tabular shrink-0 text-[12px] font-semibold text-[var(--color-signal)] hover:underline"
                        >
                          {money(entry.fee_amount)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )
              }
            </DataState>
          </Panel>
        </div>
      </div>

      <Panel
        className="mt-3"
        title="Today's list"
        subtitle="Every appointment booked for today, in token order"
        padded={false}
        actions={<Button href="/front-desk" variant="ghost" size="sm">Open the front desk</Button>}
      >
        <DataState state={desk} empty={{ title: "No appointments today", detail: "Book a walk-in to start the day." }}>
          {(data) => (
            <Table head={["Token", "Patient", "Doctor", "Room", "Time", "Status", "Payment"]}>
              {data.queue.slice(0, 12).map((entry) => (
                <Row key={entry.id}>
                  <Cell mono>{entry.token_number ?? "—"}</Cell>
                  <Cell>
                    <Link href={`/appointments/${entry.id}`} className="font-medium text-[var(--color-ink)] hover:text-[var(--color-signal)]">
                      {entry.patient_name}
                    </Link>
                  </Cell>
                  <Cell muted>{entry.doctor_name}</Cell>
                  <Cell muted>{entry.room_number ?? "Unassigned"}</Cell>
                  <Cell mono muted>{clock(entry.start_time)}</Cell>
                  <Cell>
                    <Badge tone={tone.appointment(entry.status)}>{titleCase(entry.status)}</Badge>
                  </Cell>
                  <Cell>
                    <Badge tone={tone.payment(entry.invoice_status)}>{titleCase(entry.invoice_status ?? "none")}</Badge>
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
