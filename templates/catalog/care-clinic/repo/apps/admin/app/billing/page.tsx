"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { IndianRupee, Search } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Stat, inputClass } from "../../components/ui";
import { useApi, useAction } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { day, money, num, stamp, titleCase, tone } from "../../lib/format";

const TABS = [
  { id: "", label: "All invoices" },
  { id: "pending", label: "To collect" },
  { id: "paid", label: "Settled" },
  { id: "refunded", label: "Refunded" },
];

const METHODS = ["cash", "card", "upi", "insurance"] as const;

export default function Cashier() {
  const { notify } = useSession();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [method, setMethod] = useState<(typeof METHODS)[number]>("cash");
  const invoices = useApi(
    () => defaultApiClient.getAdminInvoices({ status: status || undefined, q: search || undefined }),
    [status, search]
  );
  const { run, busy, error } = useAction();

  const rows = invoices.data?.invoices ?? [];
  const totals = useMemo(
    () => ({
      collected: rows.filter((row) => row.payment_status === "paid").reduce((sum, row) => sum + num(row.net_payable), 0),
      outstanding: rows.filter((row) => row.payment_status === "pending").reduce((sum, row) => sum + num(row.net_payable), 0),
      pendingCount: rows.filter((row) => row.payment_status === "pending").length,
    }),
    [rows]
  );

  async function collect(invoiceId: string, patient: string) {
    const ok = await run(() => defaultApiClient.collectPayment(invoiceId, method));
    if (ok) {
      notify({ title: `Collected from ${patient}`, detail: `Paid by ${method}`, tone: "good" });
      invoices.refresh();
    }
  }

  return (
    <Shell
      title="Cashier"
      subtitle="Consultation and diagnostic invoices, and the counter that settles them"
      actions={
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">Take payment as</span>
          <select className={`${inputClass} w-auto py-1`} value={method} onChange={(event) => setMethod(event.target.value as typeof method)}>
            {METHODS.map((item) => (
              <option key={item} value={item}>
                {titleCase(item)}
              </option>
            ))}
          </select>
        </div>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Collected in this view" value={money(totals.collected)} tone="good" icon={<IndianRupee size={15} />} />
        <Stat label="Still to collect" value={money(totals.outstanding)} tone={totals.outstanding > 0 ? "alert" : "plain"} hint={`${totals.pendingCount} invoices`} />
        <Stat label="Invoices listed" value={rows.length} hint="Newest first, capped at 100" />
      </div>

      <Panel className="mt-3" padded={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatus(tab.id)}
                className={
                  status === tab.id
                    ? "rounded-md bg-[var(--color-signal)] px-2.5 py-1 text-[12px] font-semibold text-white"
                    : "rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)] hover:bg-slate-50"
                }
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-subtle)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Patient or invoice number"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <DataState state={invoices}>
          {(data) =>
            data.invoices.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">Nothing in this list.</p>
            ) : (
              <Table head={["Invoice", "Patient", "Visit", "Raised", "Amount", "Status", "Method", ""]}>
                {data.invoices.map((invoice) => (
                  <Row key={invoice.id}>
                    <Cell>
                      <Link href={`/billing/${invoice.id}`} className="tabular font-medium text-[var(--color-signal)] hover:underline">
                        {invoice.invoice_number}
                      </Link>
                    </Cell>
                    <Cell>
                      <p className="font-medium text-[var(--color-ink)]">{invoice.patient_name}</p>
                      <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">{invoice.patient_phone ?? "—"}</p>
                    </Cell>
                    <Cell mono muted>{invoice.scheduled_date ? day(String(invoice.scheduled_date)) : "—"}</Cell>
                    <Cell mono muted>{stamp(invoice.created_at)}</Cell>
                    <Cell align="right">{money(invoice.net_payable)}</Cell>
                    <Cell>
                      <Badge tone={tone.payment(invoice.payment_status)}>{titleCase(invoice.payment_status)}</Badge>
                    </Cell>
                    <Cell muted>{invoice.payment_method ? titleCase(invoice.payment_method) : "—"}</Cell>
                    <Cell align="right">
                      {invoice.payment_status === "pending" && (
                        <Button size="sm" disabled={busy} onClick={() => void collect(invoice.id, invoice.patient_name)}>
                          Collect {money(invoice.net_payable)}
                        </Button>
                      )}
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
