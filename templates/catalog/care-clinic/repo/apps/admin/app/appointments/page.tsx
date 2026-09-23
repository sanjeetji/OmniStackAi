"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Download, Search } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, inputClass } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { clock, day, money, titleCase, tone } from "../../lib/format";

const STATUSES = ["", "booked", "checked_in", "in_consult", "completed", "cancelled", "no_show"];

export default function AppointmentsMaster() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [date, setDate] = useState("");

  const doctors = useApi(() => defaultApiClient.getAdminDoctors(), []);
  const appointments = useApi(
    () => defaultApiClient.getAdminAppointments({ q: search || undefined, status: status || undefined, doctorId: doctorId || undefined, date: date || undefined }),
    [search, status, doctorId, date]
  );

  const rows = appointments.data?.appointments ?? [];

  const csv = useMemo(() => {
    const header = ["Appointment", "Date", "Time", "Patient", "Phone", "Doctor", "Type", "Status", "Fee", "Payment"];
    const lines = rows.map((row) =>
      [
        row.appointment_number,
        String(row.scheduled_date).slice(0, 10),
        row.start_time,
        row.patient_name,
        row.patient_phone ?? "",
        row.doctor_name,
        row.appointment_type,
        row.status,
        String(row.fee_amount ?? ""),
        row.invoice_status ?? "",
      ]
        .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
        .join(",")
    );
    return [header.join(","), ...lines].join("\n");
  }, [rows]);

  function exportCsv() {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `careclinic-appointments-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Shell
      title="Appointments"
      subtitle="Every appointment in the clinic, filtered and exportable"
      actions={
        <Button variant="quiet" size="sm" onClick={exportCsv} disabled={rows.length === 0}>
          <Download size={13} /> Export CSV
        </Button>
      }
    >
      <Panel padded={false}>
        <div className="grid gap-2 border-b border-[var(--color-border)] px-4 py-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="relative">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-subtle)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Patient or appointment number"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value)}>
            {STATUSES.map((option) => (
              <option key={option} value={option}>
                {option ? titleCase(option) : "Any status"}
              </option>
            ))}
          </select>
          <select className={inputClass} value={doctorId} onChange={(event) => setDoctorId(event.target.value)}>
            <option value="">Any doctor</option>
            {(doctors.data?.doctors ?? []).map((doctor) => (
              <option key={doctor.id} value={doctor.id}>
                {doctor.full_name}
              </option>
            ))}
          </select>
          <input className={inputClass} type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>

        <DataState
          state={appointments}
          empty={{ title: "No appointments match", detail: "Widen the filters or clear the date." }}
        >
          {(data) =>
            data.appointments.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                No appointments match those filters.
              </p>
            ) : (
              <>
                <Table head={["Appointment", "Date", "Time", "Patient", "Doctor", "Type", "Status", "Fee", "Payment"]}>
                  {data.appointments.map((row) => (
                    <Row key={row.id}>
                      <Cell>
                        <Link href={`/appointments/${row.id}`} className="tabular font-medium text-[var(--color-signal)] hover:underline">
                          {row.appointment_number}
                        </Link>
                      </Cell>
                      <Cell mono muted>{day(String(row.scheduled_date))}</Cell>
                      <Cell mono muted>{clock(row.start_time)}</Cell>
                      <Cell>{row.patient_name}</Cell>
                      <Cell muted>{row.doctor_name}</Cell>
                      <Cell>
                        <Badge tone={row.appointment_type === "video" ? "signal" : "neutral"}>
                          {row.appointment_type === "video" ? "Video" : "In clinic"}
                        </Badge>
                      </Cell>
                      <Cell>
                        <Badge tone={tone.appointment(row.status)}>{titleCase(row.status)}</Badge>
                      </Cell>
                      <Cell align="right">{money(row.fee_amount)}</Cell>
                      <Cell>
                        <Badge tone={tone.payment(row.invoice_status)}>{titleCase(row.invoice_status ?? "none")}</Badge>
                      </Cell>
                    </Row>
                  ))}
                </Table>
                <p className="border-t border-[var(--color-border)] px-4 py-2 text-[11.5px] text-[var(--color-ink-subtle)]">
                  Showing {data.appointments.length} appointments, newest first. The API caps a page at 100 rows.
                </p>
              </>
            )
          }
        </DataState>
      </Panel>
    </Shell>
  );
}
