"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CalendarDays, FileText, Play, Search, Video } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, Stat, inputClass } from "../../components/ui";
import { useApi, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { clock, titleCase, tone } from "../../lib/format";

const FILTERS = [
  { id: "all", label: "Everyone" },
  { id: "checked_in", label: "Waiting" },
  { id: "in_consult", label: "In consult" },
  { id: "booked", label: "Not arrived" },
  { id: "completed", label: "Seen" },
] as const;

export default function TodaysQueue() {
  const { pulse } = useSession();
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [search, setSearch] = useState("");
  const queue = useApi(() => defaultApiClient.getDoctorQueue(date), [date, pulse]);

  useInterval(queue.refresh, 20_000);

  const rows = queue.data?.queue ?? [];
  const shown = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rows.filter((entry) => {
      if (filter !== "all" && entry.status !== filter) return false;
      if (!term) return true;
      return (
        entry.patient_name.toLowerCase().includes(term) ||
        entry.appointment_number.toLowerCase().includes(term) ||
        (entry.patient_phone ?? "").includes(term)
      );
    });
  }, [rows, filter, search]);

  const counts = useMemo(() => {
    const map: Record<string, number> = { all: rows.length };
    for (const entry of rows) map[entry.status] = (map[entry.status] ?? 0) + 1;
    return map;
  }, [rows]);

  const isToday = date === new Date().toISOString().slice(0, 10);

  return (
    <Shell
      title="Today's queue"
      subtitle={isToday ? "Live from the front desk" : `Clinic list for ${date}`}
      actions={
        <input
          className={`${inputClass} w-auto py-1`}
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
      }
    >
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="On the list" value={counts.all ?? 0} icon={<CalendarDays size={15} />} />
        <Stat label="Waiting" value={counts.checked_in ?? 0} tone={(counts.checked_in ?? 0) > 4 ? "alert" : "signal"} />
        <Stat label="In consult" value={counts.in_consult ?? 0} tone="alert" />
        <Stat label="Seen" value={counts.completed ?? 0} tone="good" />
      </div>

      <Panel className="mt-3" padded={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id}
                onClick={() => setFilter(option.id)}
                className={
                  filter === option.id
                    ? "rounded-lg bg-[var(--color-emerald-brand)] px-2.5 py-1 text-[12px] font-semibold text-white"
                    : "rounded-lg border border-[var(--color-border)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)] hover:bg-slate-50"
                }
              >
                {option.label}
                <span className="tabular ml-1.5 text-[11px] opacity-70">{counts[option.id] ?? 0}</span>
              </button>
            ))}
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Patient, phone or appointment number"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <DataState state={queue}>
          {() =>
            shown.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                {rows.length === 0 ? "Nothing booked for this day." : "Nobody matches that filter."}
              </p>
            ) : (
              <Table head={["Token", "Patient", "Slot", "Type", "Status", "Record", ""]}>
                {shown.map((entry) => (
                  <Row key={entry.id}>
                    <Cell mono>{entry.token_number ?? "—"}</Cell>
                    <Cell>
                      <Link
                        href={`/patients/${entry.patient_id}`}
                        className="font-medium text-[var(--color-ink)] hover:text-[var(--color-emerald-brand)]"
                      >
                        {entry.patient_name}
                      </Link>
                      <p className="text-[11px] text-[var(--color-ink-subtle)]">
                        {entry.family_member_name
                          ? `for ${entry.family_member_name} (${entry.family_member_rel})`
                          : `${entry.patient_age ? `${entry.patient_age} yrs` : "age not recorded"}${
                              entry.gender ? `, ${titleCase(entry.gender)}` : ""
                            }${entry.blood_group ? ` · ${entry.blood_group}` : ""}`}
                      </p>
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
                    <Cell muted>
                      {entry.prescription_id ? (
                        <span className="inline-flex items-center gap-1 text-[12px] text-emerald-700">
                          <FileText size={12} /> Signed
                        </span>
                      ) : entry.consultation_id ? (
                        "Notes started"
                      ) : (
                        "—"
                      )}
                    </Cell>
                    <Cell align="right">
                      <div className="flex justify-end gap-1.5">
                        {entry.appointment_type === "video" && entry.status !== "completed" && (
                          <Button size="sm" variant="quiet" href={`/telehealth/${entry.id}`}>
                            <Video size={13} /> Join
                          </Button>
                        )}
                        {(entry.status === "checked_in" || entry.status === "in_consult") && (
                          <Button size="sm" href={`/consult/${entry.id}`}>
                            <Play size={13} /> {entry.status === "in_consult" ? "Resume" : "Start"}
                          </Button>
                        )}
                        {entry.status === "completed" && entry.consultation_id && (
                          <Button size="sm" variant="quiet" href={`/consult/${entry.id}`}>
                            Review
                          </Button>
                        )}
                      </div>
                    </Cell>
                  </Row>
                ))}
              </Table>
            )
          }
        </DataState>
      </Panel>
    </Shell>
  );
}
