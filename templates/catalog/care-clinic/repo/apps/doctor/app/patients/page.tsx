"use client";

import { useState } from "react";
import Link from "next/link";
import { History, Search, Users } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, DataState, Stat, inputClass } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { count, day, titleCase } from "../../lib/format";

export default function MyPatients() {
  const [search, setSearch] = useState("");
  const patients = useApi(() => defaultApiClient.getDoctorPatients(search || undefined), [search]);

  const rows = patients.data?.patients ?? [];
  const returning = rows.filter((p) => Number(p.visit_count) > 1).length;

  return (
    <Shell title="My patients" subtitle="Everyone who has been on your list, most recent first">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Patients seen" value={count(rows.length)} icon={<Users size={15} />} />
        <Stat label="Returning" value={count(returning)} tone="good" hint="More than one visit with you" />
        <Stat
          label="Seen this month"
          value={count(
            rows.filter((p) => {
              if (!p.last_visit_date) return false;
              const last = new Date(p.last_visit_date);
              const now = new Date();
              return last.getMonth() === now.getMonth() && last.getFullYear() === now.getFullYear();
            }).length
          )}
        />
      </div>

      <Panel
        className="mt-3"
        padded={false}
        title="Patient directory"
        subtitle="Only patients who have had an appointment with you"
        actions={
          <div className="relative w-64">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Name or email"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        }
      >
        <DataState state={patients}>
          {(data) =>
            data.patients.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                No patient matches that search.
              </p>
            ) : (
              <Table head={["Patient", "Age", "Sex", "Blood group", "Visits", "Last seen", ""]}>
                {data.patients.map((patient) => (
                  <Row key={patient.id}>
                    <Cell>
                      <Link
                        href={`/patients/${patient.id}`}
                        className="font-medium text-[var(--color-ink)] hover:text-[var(--color-emerald-brand)]"
                      >
                        {patient.full_name}
                      </Link>
                      <p className="text-[11px] text-[var(--color-ink-subtle)]">{patient.email}</p>
                    </Cell>
                    <Cell align="right" muted>{patient.age ?? "—"}</Cell>
                    <Cell muted>{patient.gender ? titleCase(patient.gender) : "—"}</Cell>
                    <Cell muted>{patient.blood_group ?? "—"}</Cell>
                    <Cell align="right">{count(patient.visit_count)}</Cell>
                    <Cell mono muted>{day(patient.last_visit_date)}</Cell>
                    <Cell align="right">
                      <Link
                        href={`/patients/${patient.id}/history`}
                        className="inline-flex items-center gap-1 text-[12px] font-semibold text-[var(--color-emerald-brand)] hover:underline"
                      >
                        <History size={13} /> History
                      </Link>
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
