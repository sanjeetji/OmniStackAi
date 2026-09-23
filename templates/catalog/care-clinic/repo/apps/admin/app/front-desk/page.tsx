"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BellRing, CheckCircle2, IndianRupee, Search } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, inputClass } from "../../components/ui";
import { useApi, useAction, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { clock, money, titleCase, tone } from "../../lib/format";

const FILTERS = [
  { id: "all", label: "Everyone" },
  { id: "booked", label: "Not arrived" },
  { id: "checked_in", label: "Waiting" },
  { id: "in_consult", label: "With a doctor" },
  { id: "completed", label: "Seen" },
] as const;

export default function FrontDesk() {
  const { pulse, prefs, notify } = useSession();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [search, setSearch] = useState("");
  const desk = useApi(() => defaultApiClient.getFrontDesk(), [pulse]);
  const { run, busy, error } = useAction();

  useInterval(desk.refresh, prefs.refreshSeconds * 1000);

  const rows = useMemo(() => {
    const queue = desk.data?.queue ?? [];
    const term = search.trim().toLowerCase();
    return queue.filter((entry) => {
      if (filter !== "all" && entry.status !== filter) return false;
      if (!term) return true;
      return (
        entry.patient_name.toLowerCase().includes(term) ||
        entry.appointment_number.toLowerCase().includes(term) ||
        (entry.patient_phone ?? "").includes(term)
      );
    });
  }, [desk.data, filter, search]);

  const counts = useMemo(() => {
    const queue = desk.data?.queue ?? [];
    return {
      all: queue.length,
      booked: queue.filter((entry) => entry.status === "booked").length,
      checked_in: queue.filter((entry) => entry.status === "checked_in").length,
      in_consult: queue.filter((entry) => entry.status === "in_consult").length,
      completed: queue.filter((entry) => entry.status === "completed").length,
    } as Record<string, number>;
  }, [desk.data]);

  async function checkIn(appointmentId: string, name: string) {
    const ok = await run(() => defaultApiClient.checkInPatient(appointmentId));
    if (ok) {
      notify({ title: `${name} checked in`, detail: "A token has been issued", tone: "good" });
      desk.refresh();
    }
  }

  async function call(appointmentId: string, token: number | null) {
    const ok = await run(() => defaultApiClient.callToken(appointmentId));
    if (ok) {
      notify({ title: `Token ${token ?? ""} called`, detail: "Shown on the waiting-room board", tone: "good" });
      desk.refresh();
    }
  }

  async function collect(invoiceId: string) {
    const ok = await run(() => defaultApiClient.collectPayment(invoiceId, "cash"));
    if (ok) {
      notify({ title: "Payment collected", detail: "Cash taken at the counter", tone: "good" });
      desk.refresh();
    }
  }

  return (
    <Shell
      title="Front desk"
      subtitle="Today's reception: arrivals, tokens and counter payments"
      actions={<Button href="/queue-display" variant="quiet" size="sm">Waiting-room board</Button>}
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <Panel padded={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id}
                onClick={() => setFilter(option.id)}
                className={
                  filter === option.id
                    ? "rounded-md bg-[var(--color-signal)] px-2.5 py-1 text-[12px] font-semibold text-white"
                    : "rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)] hover:bg-slate-50"
                }
              >
                {option.label}
                <span className="tabular ml-1.5 text-[11px] opacity-70">{counts[option.id] ?? 0}</span>
              </button>
            ))}
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-subtle)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Patient, phone or appointment number"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <DataState state={desk}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                Nobody matches that filter right now.
              </p>
            ) : (
              <Table head={["Token", "Patient", "Doctor", "Room", "Slot", "Status", "Payment", ""]}>
                {rows.map((entry) => (
                  <Row key={entry.id}>
                    <Cell mono>{entry.token_number ?? "—"}</Cell>
                    <Cell>
                      <Link href={`/appointments/${entry.id}`} className="font-medium text-[var(--color-ink)] hover:text-[var(--color-signal)]">
                        {entry.patient_name}
                      </Link>
                      <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">{entry.patient_phone ?? "No phone on file"}</p>
                    </Cell>
                    <Cell muted>{entry.doctor_name}</Cell>
                    <Cell muted>{entry.room_number ?? "—"}</Cell>
                    <Cell mono muted>{clock(entry.start_time)}</Cell>
                    <Cell>
                      <Badge tone={tone.appointment(entry.status)}>{titleCase(entry.status)}</Badge>
                    </Cell>
                    <Cell>
                      <Badge tone={tone.payment(entry.invoice_status)}>
                        {entry.invoice_status === "pending" ? money(entry.fee_amount) : titleCase(entry.invoice_status ?? "none")}
                      </Badge>
                    </Cell>
                    <Cell align="right">
                      <div className="flex justify-end gap-1.5">
                        {entry.status === "booked" && (
                          <Button size="sm" disabled={busy} onClick={() => void checkIn(entry.id, entry.patient_name)}>
                            <CheckCircle2 size={13} /> Check in
                          </Button>
                        )}
                        {entry.status === "checked_in" && entry.queue_status !== "called" && (
                          <Button size="sm" variant="quiet" disabled={busy} onClick={() => void call(entry.id, entry.token_number ?? null)}>
                            <BellRing size={13} /> Call
                          </Button>
                        )}
                        {entry.invoice_status === "pending" && entry.invoice_id && (
                          <Button size="sm" variant="quiet" disabled={busy} onClick={() => void collect(entry.invoice_id as string)}>
                            <IndianRupee size={13} /> Take cash
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
