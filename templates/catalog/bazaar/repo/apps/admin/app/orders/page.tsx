"use client";

import { useState } from "react";
import Link from "next/link";
import { Download, ShoppingBag } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, Stat } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, inr, num, stamp, titleCase, tone } from "../../lib/format";

const PAGE = 50;
const FILTERS = [
  { id: "", label: "Every order" },
  { id: "pending_payment", label: "Awaiting payment" },
  { id: "processing", label: "Processing" },
  { id: "partially_shipped", label: "Partly shipped" },
  { id: "completed", label: "Completed" },
  { id: "cancelled", label: "Cancelled" },
];

export default function Orders() {
  const { pulse } = useSession();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const orders = useApi(
    () => api.getAdminOrders({ status: status || undefined, limit: PAGE, offset: page * PAGE }),
    [status, page, pulse]
  );

  const rows = orders.data?.orders ?? [];
  const gmv = rows.reduce((sum, row) => sum + num(row.total_cents), 0);

  function exportCsv() {
    const header = "Order,Placed,Shopper,Value,Status";
    const body = rows
      .map((row) =>
        [row.order_number, String(row.created_at).slice(0, 10), row.shopper_name ?? "", row.total_cents, row.status]
          .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
          .join(",")
      )
      .join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `bazaar-orders-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Shell
      title="Orders"
      subtitle="Every order, and the consignments each one split into"
      actions={
        <Button variant="quiet" size="sm" onClick={exportCsv} disabled={rows.length === 0}>
          <Download size={13} /> Export CSV
        </Button>
      }
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Orders in this view" value={count(rows.length)} icon={<ShoppingBag size={15} />} />
        <Stat label="Value in this view" value={inr(gmv)} tone="good" />
        <Stat
          label="Average order"
          value={rows.length ? inr(Math.round(gmv / rows.length)) : "—"}
          hint="Across the rows shown"
        />
      </div>

      <Panel className="mt-3" padded={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--surface-border)] px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id || "all"}
                onClick={() => {
                  setStatus(option.id);
                  setPage(0);
                }}
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
          <div className="flex items-center gap-2">
            <Button size="sm" variant="quiet" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
              Previous
            </Button>
            <span className="tabular text-[12px] text-[var(--muted-light)]">Page {page + 1}</span>
            <Button size="sm" variant="quiet" disabled={rows.length < PAGE} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>

        <DataState state={orders}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                No order matches that filter.
              </p>
            ) : (
              <Table head={["Order", "Placed", "Shopper", "Consignments", "Value", "Status"]}>
                {rows.map((order) => (
                  <Row key={order.id}>
                    <Cell>
                      <Link href={`/orders/${order.id}`} className="tabular font-medium text-[var(--accent-light)] hover:underline">
                        {order.order_number}
                      </Link>
                    </Cell>
                    <Cell mono muted>{stamp(order.created_at)}</Cell>
                    <Cell>
                      <p className="text-slate-200">{order.shopper_name ?? "—"}</p>
                      <p className="text-[11px] text-[var(--muted)]">{order.shopper_email ?? ""}</p>
                    </Cell>
                    <Cell align="right" muted>{order.shipment_count ?? "—"}</Cell>
                    <Cell align="right">{inr(order.total_cents)}</Cell>
                    <Cell>
                      <Badge tone={tone.order(order.status)}>{titleCase(order.status)}</Badge>
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
