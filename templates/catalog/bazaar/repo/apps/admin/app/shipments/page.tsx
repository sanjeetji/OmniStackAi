"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search, Truck } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, DataState, Stat, inputClass } from "../../components/ui";
import { useApi, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, inr, stamp, titleCase, tone } from "../../lib/format";

// migrations/003_orders.sql
const STAGES = ["placed", "accepted", "packed", "shipped", "delivered"];
const FILTERS = [{ id: "", label: "Everything" }, ...STAGES.map((s) => ({ id: s, label: titleCase(s) }))];

export default function Consignments() {
  const { pulse } = useSession();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const shipments = useApi(() => api.getAdminShipments(status || undefined), [status, pulse]);

  useInterval(shipments.refresh, 20_000);

  const rows = useMemo(() => {
    const list = shipments.data?.shipments ?? [];
    const term = search.trim().toLowerCase();
    if (!term) return list;
    return list.filter(
      (s: any) =>
        (s.shop_name ?? "").toLowerCase().includes(term) ||
        (s.order_number ?? "").toLowerCase().includes(term) ||
        (s.tracking_number ?? "").toLowerCase().includes(term)
    );
  }, [shipments.data, search]);

  const all = shipments.data?.shipments ?? [];
  const inFlight = all.filter((s: any) => ["accepted", "packed", "shipped"].includes(s.status)).length;

  return (
    <Shell title="Consignments" subtitle="Every workshop's half of an order, from acceptance to doorstep">
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="In this view" value={count(rows.length)} icon={<Truck size={15} />} />
        <Stat label="On the move" value={count(inFlight)} tone="signal" hint="Accepted, packed or shipped" />
        <Stat label="Delivered" value={count(all.filter((s: any) => s.status === "delivered").length)} tone="good" />
        <Stat
          label="Not yet accepted"
          value={count(all.filter((s: any) => s.status === "placed").length)}
          tone={all.some((s: any) => s.status === "placed") ? "alert" : "plain"}
          hint="Waiting on the workshop"
        />
      </div>

      <Panel className="mt-3" padded={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--surface-border)] px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id || "all"}
                onClick={() => setStatus(option.id)}
                className={
                  status === option.id
                    ? "rounded-lg bg-[var(--accent)] px-2.5 py-1 text-[12px] font-semibold text-slate-950"
                    : "rounded-lg border border-[var(--surface-border)] bg-[var(--surface-elevated)] px-2.5 py-1 text-[12px] font-medium text-[var(--muted-light)] hover:bg-slate-700"
                }
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Workshop, order or AWB"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <DataState state={shipments}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                No consignment matches that filter.
              </p>
            ) : (
              <Table head={["Consignment", "Order", "Workshop", "Carrier", "Value", "Stage", "Updated"]}>
                {rows.map((shipment: any) => (
                  <Row key={shipment.id}>
                    <Cell mono>{shipment.shipment_number ?? shipment.id.slice(0, 8)}</Cell>
                    <Cell>
                      {shipment.order_id ? (
                        <Link href={`/orders/${shipment.order_id}`} className="tabular text-[var(--accent-light)] hover:underline">
                          {shipment.order_number ?? "Open"}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </Cell>
                    <Cell>{shipment.shop_name ?? "—"}</Cell>
                    <Cell muted>
                      {shipment.carrier ?? "—"}
                      {shipment.tracking_number && (
                        <span className="tabular block text-[11px] text-[var(--muted)]">{shipment.tracking_number}</span>
                      )}
                    </Cell>
                    <Cell align="right">{inr(shipment.subtotal_cents ?? shipment.total_cents)}</Cell>
                    <Cell>
                      <Badge tone={tone.shipment(shipment.status)}>{titleCase(shipment.status)}</Badge>
                    </Cell>
                    <Cell mono muted>{stamp(shipment.updated_at ?? shipment.created_at)}</Cell>
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
