"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BadgeCheck, CalendarDays, Search, Star } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, inputClass } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { money } from "../../lib/format";

export default function DoctorDirectory() {
  const [search, setSearch] = useState("");
  const [specialty, setSpecialty] = useState("");
  const doctors = useApi(() => defaultApiClient.getAdminDoctors(), []);

  const specialties = useMemo(() => {
    const all = new Set<string>();
    for (const doctor of doctors.data?.doctors ?? []) {
      for (const item of doctor.specialties) all.add(item);
    }
    return [...all].sort();
  }, [doctors.data]);

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (doctors.data?.doctors ?? []).filter((doctor) => {
      if (specialty && !doctor.specialties.includes(specialty)) return false;
      if (!term) return true;
      return (
        doctor.full_name.toLowerCase().includes(term) ||
        doctor.license_number.toLowerCase().includes(term) ||
        doctor.specialties.join(" ").toLowerCase().includes(term)
      );
    });
  }, [doctors.data, search, specialty]);

  return (
    <Shell
      title="Doctors"
      subtitle="Credentials, council registration, fees and chamber allocation"
      actions={<Button href="/rooms" variant="quiet" size="sm">Room board</Button>}
    >
      <Panel padded={false}>
        <div className="flex flex-wrap items-center gap-2 border-b border-[var(--color-border)] px-4 py-3">
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-subtle)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Name, licence or specialty"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <select className={`${inputClass} w-auto`} value={specialty} onChange={(event) => setSpecialty(event.target.value)}>
            <option value="">Every specialty</option>
            {specialties.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <span className="tabular ml-auto text-[12px] text-[var(--color-ink-muted)]">{rows.length} doctors</span>
        </div>

        <DataState state={doctors}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">No doctor matches that search.</p>
            ) : (
              <Table head={["Doctor", "Specialties", "Council registration", "Experience", "Room", "OPD fee", "Video fee", "Rating", ""]}>
                {rows.map((doctor) => (
                  <Row key={doctor.id}>
                    <Cell>
                      <p className="font-medium text-[var(--color-ink)]">{doctor.full_name}</p>
                      <p className="text-[11px] text-[var(--color-ink-subtle)]">{doctor.qualification}</p>
                    </Cell>
                    <Cell>
                      <div className="flex flex-wrap gap-1">
                        {doctor.specialties.map((item) => (
                          <Badge key={item}>{item}</Badge>
                        ))}
                      </div>
                    </Cell>
                    <Cell mono muted>
                      <span className="inline-flex items-center gap-1">
                        <BadgeCheck size={13} className="text-[var(--color-good)]" />
                        {doctor.license_number}
                      </span>
                    </Cell>
                    <Cell align="right" muted>{doctor.experience_years} yrs</Cell>
                    <Cell muted>{doctor.room_number ?? "Unassigned"}</Cell>
                    <Cell align="right">{money(doctor.consultation_fee_inr)}</Cell>
                    <Cell align="right" muted>{money(doctor.video_fee_inr)}</Cell>
                    <Cell align="right">
                      <span className="inline-flex items-center gap-1 tabular">
                        <Star size={12} className="fill-amber-400 text-amber-400" />
                        {Number(doctor.rating_avg).toFixed(2)}
                        <span className="text-[11px] text-[var(--color-ink-subtle)]">({doctor.rating_count})</span>
                      </span>
                    </Cell>
                    <Cell align="right">
                      <Link
                        href={`/doctors/${doctor.id}/schedule`}
                        className="inline-flex items-center gap-1 text-[12px] font-semibold text-[var(--color-signal)] hover:underline"
                      >
                        <CalendarDays size={13} /> Roster
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
