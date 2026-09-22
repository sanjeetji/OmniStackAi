"use client";

import Link from "next/link";
import { Landmark } from "lucide-react";
import { inr, signedInr } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { LEDGER_KIND } from "@/components/status";
import { ErrorState, LoadingPage, PageHeader, Panel, Stat, Table, td, th } from "@/components/ui";
import type { Finance } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function FinancePage() {
  return (
    <Shell>
      <FinanceView />
    </Shell>
  );
}

// The platform account is credited commission on every completed trip (wallet or cash), net of the
// promo discount it funds, and debited for refunds (services/api/src/services/trips.ts).
const EXPLAIN: Record<string, string> = {
  commission: "Commission on completed trips, after the promo discounts the platform funds",
  refund: "Fares refunded to riders by operators",
};

function FinanceView() {
  const { data, error, reload } = useApi<Finance>("/admin/finance");
  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <LoadingPage label="Loading finance" />;

  const entries = Object.entries(data.last_30_days).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const net = entries.reduce((sum, [, amount]) => sum + amount, 0);

  return (
    <>
      <PageHeader
        title="Finance"
        description="The platform account in the RideNow ledger. Every trip books the rider, the driver and the platform, so the books always balance."
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Platform balance" value={inr(data.platform_balance)} hint="All-time commission less refunds and promos" icon={<Landmark className="size-4" aria-hidden="true" />} />
        <Stat label="Net, last 30 days" value={signedInr(net)} />
        <Stat label="Owed to drivers" value={inr(data.owed_to_drivers)} hint={<Link href="/payouts" className="text-signal hover:underline">Wallet balances not yet withdrawn</Link>} />
        <Stat label="Rider wallet float" value={inr(data.rider_wallet_float)} hint="Money riders hold in their wallets" />
      </div>
      <Panel className="mt-5" title="Platform account, last 30 days" description="Movements by kind">
        <Table label="Platform account movements, last 30 days">
          <thead>
            <tr>
              <th className={th}>Kind</th>
              <th className={th}>What it is</th>
              <th className={`${th} text-right`}>Amount</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr><td className={`${td} text-muted`} colSpan={3}>No movements in the last 30 days.</td></tr>
            ) : (
              entries.map(([kind, amount]) => (
                <tr key={kind}>
                  <td className={`${td} font-medium`}>{LEDGER_KIND[kind] ?? kind}</td>
                  <td className={`${td} text-ink-2`}>{EXPLAIN[kind] ?? "Other platform movements"}</td>
                  <td className={`${td} num text-right font-semibold ${amount < 0 ? "text-bad" : "text-ok"}`}>{signedInr(amount)}</td>
                </tr>
              ))
            )}
          </tbody>
          <tfoot>
            <tr>
              <td className={`${td} font-semibold`} colSpan={2}>Net</td>
              <td className={`${td} num text-right font-semibold`}>{signedInr(net)}</td>
            </tr>
          </tfoot>
        </Table>
      </Panel>
    </>
  );
}
