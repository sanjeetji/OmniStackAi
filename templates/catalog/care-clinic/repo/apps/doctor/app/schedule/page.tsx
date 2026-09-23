"use client";

import { useEffect, useState } from "react";
import { Clock, Save, SlidersHorizontal } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Button, DataState, ErrorNote, Stat, inputClass } from "../../components/ui";
import { useApi, useAction } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { clock } from "../../lib/format";

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

interface ShiftDraft {
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_mins: number;
  is_available: boolean;
}

/** "09:00:00" and "09:00" both come back from the API and the input; normalise to HH:MM. */
function hhmm(value: string): string {
  return value.slice(0, 5);
}

export default function OpdHours() {
  const { notify } = useSession();
  const schedule = useApi(() => defaultApiClient.getDoctorSchedule(), []);
  const { run, busy, error } = useAction();
  const [shifts, setShifts] = useState<ShiftDraft[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!schedule.data || loaded) return;
    setShifts(
      schedule.data.shifts.map((shift) => ({
        day_of_week: shift.day_of_week,
        start_time: hhmm(shift.start_time),
        end_time: hhmm(shift.end_time),
        slot_duration_mins: shift.slot_duration_mins,
        is_available: shift.is_available,
      }))
    );
    setLoaded(true);
  }, [schedule.data, loaded]);

  function update(index: number, patch: Partial<ShiftDraft>) {
    setShifts((current) => current.map((shift, i) => (i === index ? { ...shift, ...patch } : shift)));
  }

  function addShift(day: number) {
    setShifts((current) => [
      ...current,
      { day_of_week: day, start_time: "09:00", end_time: "13:00", slot_duration_mins: 20, is_available: true },
    ]);
  }

  async function save() {
    const ok = await run(async () => {
      await defaultApiClient.updateDoctorSchedule(
        shifts.map((shift) => ({
          dayOfWeek: shift.day_of_week,
          startTime: `${shift.start_time}:00`,
          endTime: `${shift.end_time}:00`,
          slotDurationMins: shift.slot_duration_mins,
          isAvailable: shift.is_available,
        }))
      );
      schedule.refresh();
    });
    if (ok) notify({ title: "OPD hours saved", detail: "New slots follow this rule", tone: "good" });
  }

  const weeklyHours = shifts
    .filter((shift) => shift.is_available)
    .reduce((sum, shift) => {
      const [sh, sm] = shift.start_time.split(":").map(Number);
      const [eh, em] = shift.end_time.split(":").map(Number);
      return sum + Math.max(0, eh * 60 + em - (sh * 60 + sm)) / 60;
    }, 0);
  const slotsPerWeek = shifts
    .filter((shift) => shift.is_available)
    .reduce((sum, shift) => {
      const [sh, sm] = shift.start_time.split(":").map(Number);
      const [eh, em] = shift.end_time.split(":").map(Number);
      return sum + Math.floor(Math.max(0, eh * 60 + em - (sh * 60 + sm)) / shift.slot_duration_mins);
    }, 0);

  return (
    <Shell
      title="OPD hours"
      subtitle="The rule your appointment slots are generated from"
      actions={
        <Button href="/schedule/rules" variant="quiet" size="sm">
          <SlidersHorizontal size={13} /> Leave and changes
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Clinic hours a week" value={`${weeklyHours.toFixed(0)}h`} icon={<Clock size={15} />} />
        <Stat label="Slots a week" value={slotsPerWeek} tone="signal" hint="At the durations below" />
        <Stat label="Days you sit" value={new Set(shifts.filter((s) => s.is_available).map((s) => s.day_of_week)).size} />
      </div>

      <Panel className="mt-3" title="Weekly rule" subtitle="Each row is one sitting; a day can have more than one">
        <DataState state={schedule}>
          {() => (
            <div className="space-y-4">
              {DAYS.map((name, day) => {
                const rows = shifts
                  .map((shift, index) => ({ shift, index }))
                  .filter(({ shift }) => shift.day_of_week === day);

                return (
                  <div key={name} className="rounded-xl border border-[var(--color-border)] p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-[13px] font-semibold text-[var(--color-ink)]">{name}</p>
                      <Button size="sm" variant="ghost" onClick={() => addShift(day)}>
                        Add a sitting
                      </Button>
                    </div>

                    {rows.length === 0 ? (
                      <p className="text-[12.5px] text-[var(--color-ink-muted)]">No clinic on this day.</p>
                    ) : (
                      <div className="space-y-2">
                        {rows.map(({ shift, index }) => (
                          <div key={index} className="flex flex-wrap items-center gap-2">
                            <input
                              className={`${inputClass} w-28`}
                              type="time"
                              value={shift.start_time}
                              onChange={(event) => update(index, { start_time: event.target.value })}
                            />
                            <span className="text-[12px] text-[var(--color-ink-muted)]">to</span>
                            <input
                              className={`${inputClass} w-28`}
                              type="time"
                              value={shift.end_time}
                              onChange={(event) => update(index, { end_time: event.target.value })}
                            />
                            <select
                              className={`${inputClass} w-28`}
                              value={shift.slot_duration_mins}
                              onChange={(event) => update(index, { slot_duration_mins: Number(event.target.value) })}
                            >
                              {[10, 15, 20, 30, 45].map((mins) => (
                                <option key={mins} value={mins}>
                                  {mins} min slots
                                </option>
                              ))}
                            </select>
                            <label className="flex items-center gap-1.5 text-[12.5px] text-[var(--color-ink-muted)]">
                              <input
                                type="checkbox"
                                className="h-4 w-4 accent-[var(--color-emerald-brand)]"
                                checked={shift.is_available}
                                onChange={(event) => update(index, { is_available: event.target.checked })}
                              />
                              Open
                            </label>
                            <button
                              onClick={() => setShifts((current) => current.filter((_, i) => i !== index))}
                              className="text-[12px] text-slate-400 hover:text-red-600"
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              <Button disabled={busy} onClick={() => void save()}>
                <Save size={13} /> {busy ? "Saving" : "Save the weekly rule"}
              </Button>
              <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                Saving replaces your whole rule. Appointments already booked are not moved.
              </p>
            </div>
          )}
        </DataState>
      </Panel>
    </Shell>
  );
}
