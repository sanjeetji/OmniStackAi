"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, Download, Scale } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, Stat } from "../../../components/ui";
import { useApi } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { count, inr, num, stamp, titleCase } from "../../../lib/format";

// migrations/004_ledger.sql
const TYPES = [
  { id: "", label: "Every entry" },
  { id: "order_payment", label: "Order payment" },
  { id: "commission_fee", label: "Commission" },
  { id: "vendor_credit", label: "Vendor credit" },
  { id: "shopper_refund", label: "Refund" },
  { id: "payout_settlement", label: "Settlement" },
];

export default function Ledger() {
  const { pulse } = useSession();
  const [entryType, setEntryType] = useState("");
  const ledger = useApi(() => api.getAdminLedger(entryType || undefined), [entryType, pulse]);

  const rows = ledger.data?.entries ?? [];
  const total = useMemo(() => rows.reduce((sum: number, row: any) => sum + num(row.amount_cents), 0), [rows]);

  function exportCsv() {
    const header = "Entry,Type,From,To,Amount (paise),Reference,When";
    const body = rows
      .map((row: any) =>
        [row.journal_id ?? row.id, row.entry_type, row.debit_holder, row.credit_holder, row.amount_cents, row.reference_id ?? "", row.created_at]
          .map((cell: any) => `"${String(cell).replace(/"/g, '""')}"`)
          .join(",")
      )
      .join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `bazaar-ledger-${entryType || "all"}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Shell
      title="Double-entry ledger"
      subtitle="Every posting the marketplace has made, both sides of each one"
      actions={
        <>
          <Button href="/finance" variant="quiet" size="sm">
            <ArrowLeft size={13} /> Financials
          </Button>
          <Button variant="quiet" size="sm" onClick={exportCsv} disabled={rows.length === 0}>
            <Download size={13} /> CSV
          </Button>
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Entries shown" value={count(rows.length)} icon={<Scale size={15} />} />
        <Stat label="Value moved" value={inr(total)} tone="signal" />
        <Stat
          label="Distinct journals"
          value={count(new Set(rows.map((row: any) => row.journal_id ?? row.id)).size)}
          hint="Each journal is one balanced transaction"
        />
      </div>

      <Panel className="mt-3" padded={false}>
        <div className="flex flex-wrap gap-1.5 border-b border-[var(--surface-border)] px-4 py-3">
          {TYPES.map((option) => (
            <button
              key={option.id || "all"}
              onClick={() => setEntryType(option.id)}
              className={
                entryType === option.id
                  ? "rounded-lg bg-[var(--accent)] px-2.5 py-1 text-[12px] font-semibold text-slate-950"
                  : "rounded-lg border border-[var(--surface-border)] bg-[var(--surface-elevated)] px-2.5 py-1 text-[12px] font-medium text-[var(--muted-light)] hover:bg-slate-700"
              }
            >
              {option.label}
            </button>
          ))}
        </div>

        <DataState state={ledger}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                No entry of that kind.
              </p>
            ) : (
              <Table head={["Type", "Debited", "Credited", "Amount", "Against", "When"]}>
                {rows.map((entry: any) => (
                  <Row key={entry.id}>
                    <Cell>
                      <Badge
                        tone={
                          entry.entry_type === "commission_fee"
                            ? "good"
                            : entry.entry_type === "shopper_refund"
                              ? "danger"
                              : entry.entry_type === "payout_settlement"
                                ? "alert"
                                : "signal"
                        }
                      >
                        {titleCase(entry.entry_type)}
                      </Badge>
                    </Cell>
                    <Cell muted>{titleCase(entry.debit_holder)}</Cell>
                    <Cell muted>{titleCase(entry.credit_holder)}</Cell>
                    <Cell align="right">{inr(entry.amount_cents)}</Cell>
                    <Cell mono muted>
                      {entry.reference_type ? `${entry.reference_type} ${String(entry.reference_id ?? "").slice(0, 8)}` : "—"}
                    </Cell>
                    <Cell mono muted>{stamp(entry.created_at)}</Cell>
                  </Row>
                ))}
              </Table>
            )
          }
        </DataState>
      </Panel>

      <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--muted)]">
        Every transaction is two postings: one account is debited and another credited by the same
        amount, so the sum across all accounts is always zero. Balances on every other screen are
        derived from these rows.
      </p>
    </Shell>
  );
}
