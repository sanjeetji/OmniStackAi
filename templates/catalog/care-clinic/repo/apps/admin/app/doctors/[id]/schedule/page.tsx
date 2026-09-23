"use client";

import { use, useState } from "react";
import { ArrowLeft, CalendarOff, Clock } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Field, inputClass, Stat } from "../../../../components/ui";
import { useApi, useAction } from "../../../../lib/use-api";
import { useSession } from "../../../../lib/session";
import { clock, count, day, money, num } from "../../../../lib/format";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function DoctorRoster({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { notify } = useSession();
  const roster = useApi(() => defaultApiClient.getDoctorRoster(id), [id]);
  const { run, busy, error } = useAction();

  const [date, setDate] = useState("");
  const [isLeave, setIsLeave] = useState(true);
  const [startTime, setStartTime] = useState("11:00");
  const [endTime, setEndTime] = useState("15:00");
  const [reason, setReason] = useState("");

  async function addOverride() {
    const ok = await run(() =>
      defaultApiClient.addScheduleOverride(id, {
        date,
        isLeave,
        customStartTime: isLeave ? undefined : `${startTime}:00`,
        customEndTime: isLeave ? undefined : `${endTime}:00`,
        reason: reason.trim() || undefined,
      })
    );
    if (ok) {
      notify({ title: isLeave ? "Leave recorded" : "OPD hours changed", detail: day(date), tone: "alert" });
      setDate("");
      setReason("");
      roster.refresh();
    }
  }

  return (
    <Shell
      title="Doctor roster"
      subtitle="Weekly OPD hours, planned absences and what is booked against them"
      actions={
        <Button href="/doctors" variant="quiet" size="sm">
          <ArrowLeft size={13} /> Doctors
        </Button>
      }
    >
      <DataState state={roster}>
        {(data) => {
          const bookedTotal = data.upcoming.reduce((sum, row) => sum + num(row.booked), 0);
          const weeklyHours = data.shifts.reduce((sum, shift) => {
            const [sh, sm] = shift.start_time.split(":").map(Number);
            const [eh, em] = shift.end_time.split(":").map(Number);
            return sum + (eh * 60 + em - (sh * 60 + sm)) / 60;
          }, 0);

          return (
            <>
              <Panel className="mb-3">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-[18px] font-semibold tracking-tight text-[var(--color-ink)]">{data.doctor.full_name}</h2>
                    <p className="text-[12.5px] text-[var(--color-ink-muted)]">{data.doctor.qualification}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {data.doctor.specialties.map((item) => (
                        <Badge key={item} tone="signal">{item}</Badge>
                      ))}
                    </div>
                  </div>
                  <dl className="grid gap-x-8 gap-y-1 text-[12.5px] sm:grid-cols-2">
                    {[
                      ["Council registration", data.doctor.license_number],
                      ["Room", data.doctor.room_number ?? "Unassigned"],
                      ["OPD fee", money(data.doctor.consultation_fee_inr)],
                      ["Video fee", money(data.doctor.video_fee_inr)],
                    ].map(([label, value]) => (
                      <div key={label} className="flex justify-between gap-6">
                        <dt className="text-[var(--color-ink-muted)]">{label}</dt>
                        <dd className="tabular font-medium text-[var(--color-ink)]">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </Panel>

              <div className="mb-3 grid gap-3 sm:grid-cols-3">
                <Stat label="OPD hours a week" value={`${weeklyHours.toFixed(0)}h`} hint={`${data.shifts.length} shifts`} icon={<Clock size={15} />} />
                <Stat label="Booked in 14 days" value={count(bookedTotal)} tone="signal" hint={`${data.upcoming.length} clinic days`} />
                <Stat
                  label="Planned absences"
                  value={data.overrides.filter((item) => item.is_leave).length}
                  tone={data.overrides.some((item) => item.is_leave) ? "alert" : "plain"}
                  hint="From a week ago onwards"
                  icon={<CalendarOff size={15} />}
                />
              </div>

              <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
                <Panel title="Weekly OPD rule" subtitle="Slots are generated from these shifts" padded={false}>
                  <Table head={["Day", "From", "To", "Slot", "Open"]}>
                    {data.shifts.map((shift) => (
                      <Row key={shift.id}>
                        <Cell>{DAY_NAMES[shift.day_of_week]}</Cell>
                        <Cell mono muted>{clock(shift.start_time)}</Cell>
                        <Cell mono muted>{clock(shift.end_time)}</Cell>
                        <Cell mono muted>{shift.slot_duration_mins} min</Cell>
                        <Cell>
                          <Badge tone={shift.is_available ? "good" : "danger"}>{shift.is_available ? "Open" : "Closed"}</Badge>
                        </Cell>
                      </Row>
                    ))}
                  </Table>
                </Panel>

                <Panel title="Next 14 days" subtitle="What is already booked against the rule" padded={false}>
                  {data.upcoming.length === 0 ? (
                    <p className="px-4 py-10 text-center text-[13px] text-[var(--color-ink-muted)]">Nothing booked yet.</p>
                  ) : (
                    <Table head={["Date", "Booked", "Video", "First", "Last"]}>
                      {data.upcoming.map((row) => (
                        <Row key={String(row.scheduled_date)}>
                          <Cell mono>{day(String(row.scheduled_date))}</Cell>
                          <Cell align="right">{count(row.booked)}</Cell>
                          <Cell align="right" muted>{count(row.video_count)}</Cell>
                          <Cell mono muted>{clock(row.first_slot)}</Cell>
                          <Cell mono muted>{clock(row.last_slot)}</Cell>
                        </Row>
                      ))}
                    </Table>
                  )}
                </Panel>
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr]">
                <Panel title="Absences and altered hours" padded={false}>
                  {data.overrides.length === 0 ? (
                    <p className="px-4 py-10 text-center text-[13px] text-[var(--color-ink-muted)]">
                      No absence recorded for this doctor.
                    </p>
                  ) : (
                    <Table head={["Date", "Kind", "Hours", "Reason"]}>
                      {data.overrides.map((item) => (
                        <Row key={item.id}>
                          <Cell mono>{day(String(item.date))}</Cell>
                          <Cell>
                            <Badge tone={item.is_leave ? "danger" : "alert"}>{item.is_leave ? "On leave" : "Altered hours"}</Badge>
                          </Cell>
                          <Cell mono muted>
                            {item.custom_start_time ? `${clock(item.custom_start_time)} – ${clock(item.custom_end_time)}` : "—"}
                          </Cell>
                          <Cell muted>{item.reason ?? "—"}</Cell>
                        </Row>
                      ))}
                    </Table>
                  )}
                </Panel>

                <Panel title="Record an absence" subtitle="Slots stop being offered for that day">
                  {error && <div className="mb-2"><ErrorNote message={error} /></div>}
                  <form
                    className="space-y-3"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void addOverride();
                    }}
                  >
                    <Field label="Date">
                      <input className={inputClass} type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
                    </Field>
                    <div className="flex gap-1.5">
                      {[
                        { value: true, label: "Full day off" },
                        { value: false, label: "Different hours" },
                      ].map((option) => (
                        <button
                          key={String(option.value)}
                          type="button"
                          onClick={() => setIsLeave(option.value)}
                          className={
                            isLeave === option.value
                              ? "rounded-md bg-[var(--color-signal)] px-2.5 py-1 text-[12px] font-semibold text-white"
                              : "rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)]"
                          }
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                    {!isLeave && (
                      <div className="grid grid-cols-2 gap-2">
                        <Field label="From">
                          <input className={inputClass} type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} />
                        </Field>
                        <Field label="To">
                          <input className={inputClass} type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
                        </Field>
                      </div>
                    )}
                    <Field label="Reason">
                      <input
                        className={inputClass}
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder="Conference, leave, theatre list…"
                      />
                    </Field>
                    <Button type="submit" disabled={busy || !date}>
                      {busy ? "Saving" : "Record it"}
                    </Button>
                  </form>
                </Panel>
              </div>
            </>
          );
        }}
      </DataState>
    </Shell>
  );
}
