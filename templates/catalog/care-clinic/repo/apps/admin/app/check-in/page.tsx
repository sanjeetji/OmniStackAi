"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Search, Ticket } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Stat, inputClass } from "../../components/ui";
import { useApi, useAction, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { clock, money, titleCase, tone } from "../../lib/format";

export default function CheckIn() {
  const { pulse, prefs, notify } = useSession();
  const [search, setSearch] = useState("");
  const [issued, setIssued] = useState<{ name: string; token: number | null; room: string | null } | null>(null);
  const desk = useApi(() => defaultApiClient.getFrontDesk(), [pulse]);
  const { run, busy, error } = useAction();

  useInterval(desk.refresh, prefs.refreshSeconds * 1000);

  const queue = desk.data?.queue ?? [];
  const arriving = useMemo(() => {
    const term = search.trim().toLowerCase();
    return queue
      .filter((entry) => entry.status === "booked")
      .filter((entry) =>
        !term
          ? true
          : entry.patient_name.toLowerCase().includes(term) ||
            entry.appointment_number.toLowerCase().includes(term) ||
            (entry.patient_phone ?? "").includes(term)
      );
  }, [queue, search]);

  const waiting = queue.filter((entry) => entry.status === "checked_in");
  const lastToken = queue.reduce((highest, entry) => Math.max(highest, entry.token_number ?? 0), 0);

  async function arrive(appointmentId: string, name: string, room: string | null) {
    const ok = await run(async () => {
      const result = await defaultApiClient.checkInPatient(appointmentId);
      setIssued({ name, token: result.appointment.token_number ?? null, room });
    });
    if (ok) {
      notify({ title: `${name} checked in`, detail: "An SMS with the token has been queued", tone: "good" });
      desk.refresh();
    }
  }

  return (
    <Shell title="Patient check-in" subtitle="Mark an arrival and issue the next queue token">
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Still to arrive" value={arriving.length} hint="Booked but not checked in" icon={<Search size={15} />} />
        <Stat label="Waiting now" value={waiting.length} tone="signal" hint="Token issued, waiting for a chamber" icon={<Ticket size={15} />} />
        <Stat label="Last token issued" value={lastToken || "—"} hint="Tokens run per doctor per day" tone="plain" />
      </div>

      {issued && (
        <div className="rise-in mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-[var(--color-good-soft)] px-4 py-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 size={18} className="text-[var(--color-good)]" />
            <div>
              <p className="text-[13px] font-semibold text-[var(--color-ink)]">{issued.name} is checked in</p>
              <p className="text-[12px] text-[var(--color-ink-muted)]">
                Token {issued.token ?? "—"} · {issued.room ?? "Room not yet assigned"} · SMS queued to the patient
              </p>
            </div>
          </div>
          <span className="tabular rounded-md bg-white px-3 py-1.5 text-[22px] font-bold text-[var(--color-good)] ring-1 ring-emerald-200">
            {issued.token ?? "—"}
          </span>
        </div>
      )}

      <Panel
        className="mt-3"
        title="Expected today"
        subtitle="Search by name, phone or appointment number, then check the patient in"
        padded={false}
        actions={
          <div className="relative w-64">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-subtle)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Find a patient"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        }
      >
        <DataState state={desk}>
          {() =>
            arriving.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                Everyone booked for today has already arrived.
              </p>
            ) : (
              <Table head={["Slot", "Patient", "Doctor", "Room", "Type", "Fee", ""]}>
                {arriving.map((entry) => (
                  <Row key={entry.id}>
                    <Cell mono>{clock(entry.start_time)}</Cell>
                    <Cell>
                      <p className="font-medium text-[var(--color-ink)]">{entry.patient_name}</p>
                      <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">{entry.appointment_number}</p>
                    </Cell>
                    <Cell muted>{entry.doctor_name}</Cell>
                    <Cell muted>{entry.room_number ?? "—"}</Cell>
                    <Cell>
                      <Badge tone={entry.appointment_type === "video" ? "signal" : "neutral"}>
                        {entry.appointment_type === "video" ? "Video" : "In clinic"}
                      </Badge>
                    </Cell>
                    <Cell align="right">
                      <Badge tone={tone.payment(entry.invoice_status)}>
                        {entry.invoice_status === "pending" ? money(entry.fee_amount) : titleCase(entry.invoice_status ?? "none")}
                      </Badge>
                    </Cell>
                    <Cell align="right">
                      <Button size="sm" disabled={busy} onClick={() => void arrive(entry.id, entry.patient_name, entry.room_number ?? null)}>
                        <CheckCircle2 size={13} /> Check in
                      </Button>
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
