"use client";

import Link from "next/link";
import { Receipt, Scale, TrendingUp, Wallet } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Button, DataState, Stat, Badge } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { inr, num, stamp, titleCase } from "../../lib/format";

export default function Financials() {
  const { pulse } = useSession();
  const finance = useApi(() => api.getAdminFinance(), [pulse]);

  return (
    <Shell
      title="Financials"
      subtitle="What the platform holds, what it earned, and what it owes"
      actions={
        <Button href="/finance/ledger" variant="quiet" size="sm">
          <Receipt size={13} /> Full ledger
        </Button>
      }
    >
      <DataState state={finance}>
        {(data) => {
          const s = data.summary;
          const owed = num(s.totalVendorPayablesCents);
          const cash = num(s.platformCashBalanceCents);

          return (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Stat label="Cash held" value={inr(cash)} hint="In the platform's own accounts" icon={<Wallet size={15} />} />
                <Stat label="Commission earned" value={inr(s.platformRevenueCents)} tone="good" icon={<TrendingUp size={15} />} />
                <Stat
                  label="Owed to vendors"
                  value={inr(owed)}
                  tone={owed > cash ? "danger" : "alert"}
                  hint={owed > cash ? "More owed than held — investigate" : "Covered by cash held"}
                />
                <Stat label="Settled to date" value={inr(s.totalSettlementsPaidCents)} hint="Paid out in batches" />
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1.6fr]">
                <Panel title="Is the book balanced?" subtitle="Derived, never stored">
                  <div className="space-y-3 text-[13px]">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[var(--muted-light)]">Escrow held for vendors</span>
                      <span className="tabular font-semibold text-slate-100">{inr(owed)}</span>
                    </div>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[var(--muted-light)]">Platform cash</span>
                      <span className="tabular font-semibold text-slate-100">{inr(cash)}</span>
                    </div>
                    <div className="flex items-baseline justify-between gap-3 border-t border-[var(--surface-border)] pt-2">
                      <span className="text-[var(--muted-light)]">Cover</span>
                      <span
                        className={
                          owed <= cash
                            ? "tabular font-semibold text-[var(--emerald)]"
                            : "tabular font-semibold text-[var(--rose)]"
                        }
                      >
                        {cash > 0 ? `${Math.round((cash / Math.max(owed, 1)) * 100)}%` : "—"}
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 flex items-start gap-1.5 border-t border-[var(--surface-border)] pt-2.5 text-[11.5px] leading-relaxed text-[var(--muted)]">
                    <Scale size={12} className="mt-0.5 shrink-0" />
                    Every figure here is summed from the accounts the double-entry ledger maintains.
                    Nothing on this page is a running total kept by hand.
                  </p>
                </Panel>

                <Panel title="Latest postings" subtitle="The twenty most recent ledger entries" padded={false}>
                  {data.recentEntries.length === 0 ? (
                    <p className="px-4 py-10 text-center text-[13px] text-[var(--muted-light)]">
                      No posting yet.
                    </p>
                  ) : (
                    <Table head={["Entry", "From", "To", "Amount", "When"]}>
                      {data.recentEntries.map((entry) => (
                        <Row key={entry.id}>
                          <Cell>
                            <Badge tone={entry.entry_type === "commission_fee" ? "good" : entry.entry_type === "shopper_refund" ? "danger" : "signal"}>
                              {titleCase(entry.entry_type)}
                            </Badge>
                          </Cell>
                          <Cell muted>{titleCase(entry.debit_holder)}</Cell>
                          <Cell muted>{titleCase(entry.credit_holder)}</Cell>
                          <Cell align="right">{inr(entry.amount_cents)}</Cell>
                          <Cell mono muted>{stamp(entry.created_at)}</Cell>
                        </Row>
                      ))}
                    </Table>
                  )}
                  <div className="border-t border-[var(--surface-border)] px-4 py-2.5">
                    <Link href="/finance/ledger" className="text-[12px] font-semibold text-[var(--accent-light)] hover:underline">
                      Open the full ledger
                    </Link>
                  </div>
                </Panel>
              </div>
            </>
          );
        }}
      </DataState>
    </Shell>
  );
}
