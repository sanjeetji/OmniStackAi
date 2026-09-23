"use client";

import { useState } from "react";
import { CalendarOff, Clock, Plus, Trash2 } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote, Field, Stat, Table, Row, Cell, inputClass } from "../../../components/ui";
import { useApi, useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { clock, day } from "../../../lib/format";

export default function LeaveAndChanges() {
  const { notify } = useSession();
  const schedule = useApi(() => defaultApiClient.getDoctorSchedule(), []);
  const { run, busy, error } = useAction();

  const [date, setDate] = useState("");
  const [isLeave, setIsLeave] = useState(true);
  const [startTime, setStartTime] = useState("11:00");
  const [endTime, setEndTime] = useState("15:00");
  const [reason, setReason] = useState("");

  async function add() {
    const ok = await run(async () => {
      await defaultApiClient.addDoctorScheduleOverride({
        date,
        isLeave,
        customStartTime: isLeave ? undefined : `${startTime}:00`,
        customEndTime: isLeave ? undefined : `${endTime}:00`,
        reason: reason.trim() || undefined,
      });
      schedule.refresh();
    });
    if (ok) {
      notify({ title: isLeave ? "Leave recorded" : "Hours changed", detail: day(date), tone: "good" });
      setDate("");
      setReason("");
    }
  }

  async function remove(id: string) {
    const ok = await run(async () => {
      await defaultApiClient.removeDoctorScheduleOverride(id);
      schedule.refresh();
    });
    if (ok) notify({ title: "Removed", detail: "Slots are offered again for that day", tone: "info" });
  }

  const overrides = schedule.data?.overrides ?? [];
  const leaves = overrides.filter((o) => o.is_leave);

  return (
    <Shell
      title="Leave and changes"
      subtitle="Days you are away, and days you sit at different hours"
      actions={
        <Button href="/schedule" variant="quiet" size="sm">
          <Clock size={13} /> Weekly rule
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Days away" value={leaves.length} tone={leaves.length ? "alert" : "plain"} icon={<CalendarOff size={15} />} />
        <Stat label="Altered days" value={overrides.length - leaves.length} hint="Different hours, still sitting" />
        <Stat
          label="Next absence"
          value={leaves[0] ? day(String(leaves[0].date)) : "—"}
          hint={leaves[0]?.reason ?? "Nothing planned"}
        />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Planned" subtitle="From today onwards" padded={false}>
          <DataState state={schedule}>
            {() =>
              overrides.length === 0 ? (
                <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                  Nothing recorded. Your weekly rule applies every day.
                </p>
              ) : (
                <Table head={["Date", "Kind", "Hours", "Reason", ""]}>
                  {overrides.map((override) => (
                    <Row key={override.id}>
                      <Cell mono>{day(String(override.date))}</Cell>
                      <Cell>
                        <Badge tone={override.is_leave ? "danger" : "alert"}>
                          {override.is_leave ? "Away" : "Altered hours"}
                        </Badge>
                      </Cell>
                      <Cell mono muted>
                        {override.custom_start_time
                          ? `${clock(override.custom_start_time)} – ${clock(override.custom_end_time)}`
                          : "—"}
                      </Cell>
                      <Cell muted>{override.reason ?? "—"}</Cell>
                      <Cell align="right">
                        <button
                          onClick={() => void remove(override.id)}
                          disabled={busy}
                          aria-label="Remove"
                          className="text-slate-400 hover:text-red-600 disabled:opacity-50"
                        >
                          <Trash2 size={14} />
                        </button>
                      </Cell>
                    </Row>
                  ))}
                </Table>
              )
            }
          </DataState>
        </Panel>

        <Panel title="Record a change" subtitle="No slot is offered for a day you are away">
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void add();
            }}
          >
            <Field label="Date">
              <input className={inputClass} type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
            </Field>

            <div className="flex gap-1.5">
              {[
                { value: true, label: "Away all day" },
                { value: false, label: "Different hours" },
              ].map((option) => (
                <button
                  key={String(option.value)}
                  type="button"
                  onClick={() => setIsLeave(option.value)}
                  className={
                    isLeave === option.value
                      ? "rounded-lg bg-[var(--color-emerald-brand)] px-2.5 py-1 text-[12px] font-semibold text-white"
                      : "rounded-lg border border-[var(--color-border)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)]"
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

            <Field label="Reason" hint="The front desk sees this when they reschedule.">
              <input
                className={inputClass}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Conference, leave, theatre list…"
              />
            </Field>

            <Button type="submit" disabled={busy || !date}>
              <Plus size={13} /> {busy ? "Saving" : "Record it"}
            </Button>
          </form>
        </Panel>
      </div>
    </Shell>
  );
}
