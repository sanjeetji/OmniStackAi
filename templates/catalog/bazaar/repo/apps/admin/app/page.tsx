"use client";

import Link from "next/link";
import { IndianRupee, PackageCheck, ShieldAlert, ShoppingBag, Store, Users, Wallet } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../components/shell";
import { Panel, Stat, Badge, Button, DataState, Table, Row, Cell } from "../components/ui";
import { TrendChart } from "../components/charts";
import { useApi, useInterval } from "../lib/use-api";
import { useSession } from "../lib/session";
import { count, dayShort, inr, inrShort, num, stamp, titleCase, tone } from "../lib/format";

export default function MarketplaceDashboard() {
  const { pulse } = useSession();
  const metrics = useApi(() => api.getAdminMetrics(), [pulse]);
  const orders = useApi(() => api.getAdminOrders({ limit: 8 }), [pulse]);
  const settlements = useApi(() => api.getAdminSettlements(), [pulse]);

  useInterval(() => {
    metrics.refresh();
    orders.refresh();
    settlements.refresh();
  }, 20_000);

  const m = metrics.data?.metrics;
  const pendingKyc = num(m?.pendingKycCount);
  const pendingSettlements = num(m?.pendingSettlementsCount);

  return (
    <Shell
      title="Marketplace dashboard"
      subtitle="Every workshop, order and rupee moving through Bazaar"
      actions={
        <>
          {pendingKyc > 0 && (
            <Button href="/shops" variant="quiet" size="sm">
              {pendingKyc} KYC to review
            </Button>
          )}
          <Button href="/settlements" size="sm">
            Settlements
          </Button>
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Gross merchandise value" value={inr(m?.totalGmvCents)} tone="good" hint={`${count(m?.totalOrdersCount)} orders`} icon={<IndianRupee size={15} />} />
        <Stat label="Workshops" value={count(m?.totalShopsCount)} hint={pendingKyc > 0 ? `${pendingKyc} awaiting KYC` : "All verified"} tone={pendingKyc > 0 ? "alert" : "plain"} icon={<Store size={15} />} />
        <Stat label="Shoppers" value={count(m?.totalShoppersCount)} hint="Registered buyers" icon={<Users size={15} />} />
        <Stat
          label="Owed to vendors"
          value={inr(m?.financials?.totalVendorPayablesCents)}
          tone={pendingSettlements > 0 ? "alert" : "plain"}
          hint={`${pendingSettlements} payout${pendingSettlements === 1 ? "" : "s"} waiting`}
          icon={<Wallet size={15} />}
        />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1.6fr_1fr]">
        <Panel
          title="Volume over the last 14 days"
          subtitle="Bars are orders; the blue tick is the value they carried"
          actions={<Button href="/finance" variant="ghost" size="sm">Financials</Button>}
        >
          <DataState state={metrics}>
            {(data) => (
              <TrendChart
                series={(data.metrics.dailyVolume ?? []).map((point) => ({
                  label: dayShort(point.date),
                  value: point.orderCount,
                  secondary: point.gmvCents / 100000,
                }))}
                format={(value) => String(Math.round(value))}
              />
            )}
          </DataState>
        </Panel>

        <div className="space-y-3">
          <Panel title="The platform's own books">
            <DataState state={metrics}>
              {(data) => (
                <dl className="space-y-2.5 text-[13px]">
                  {[
                    ["Cash the platform holds", inr(data.metrics.financials?.platformCashBalanceCents)],
                    ["Commission earned", inr(data.metrics.financials?.platformRevenueCents)],
                    ["Owed out to vendors", inr(data.metrics.financials?.totalVendorPayablesCents)],
                    ["Settled to date", inr(data.metrics.financials?.totalSettlementsPaidCents)],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between gap-3">
                      <dt className="text-[var(--muted-light)]">{label}</dt>
                      <dd className="tabular font-semibold text-slate-100">{value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </DataState>
            <p className="mt-3 border-t border-[var(--surface-border)] pt-2 text-[11px] leading-relaxed text-[var(--muted)]">
              Every figure is derived from the double-entry ledger, never stored as a running total.
            </p>
          </Panel>

          <Panel
            title="Needs an operator"
            subtitle={pendingKyc + pendingSettlements === 0 ? "Nothing waiting" : undefined}
            padded={false}
          >
            {pendingKyc + pendingSettlements === 0 ? (
              <p className="px-4 py-6 text-center text-[12.5px] text-[var(--muted-light)]">
                No KYC or payout is waiting on you.
              </p>
            ) : (
              <ul className="divide-y divide-[var(--surface-border)]">
                {pendingKyc > 0 && (
                  <li>
                    <Link href="/shops" className="flex items-center gap-2.5 px-4 py-3 hover:bg-slate-800/50">
                      <ShieldAlert size={15} className="shrink-0 text-amber-400" />
                      <span className="text-[12.5px] text-slate-200">
                        {pendingKyc} workshop{pendingKyc === 1 ? "" : "s"} awaiting KYC verification
                      </span>
                    </Link>
                  </li>
                )}
                {pendingSettlements > 0 && (
                  <li>
                    <Link href="/settlements" className="flex items-center gap-2.5 px-4 py-3 hover:bg-slate-800/50">
                      <PackageCheck size={15} className="shrink-0 text-sky-400" />
                      <span className="text-[12.5px] text-slate-200">
                        {pendingSettlements} settlement batch{pendingSettlements === 1 ? "" : "es"} to approve
                      </span>
                    </Link>
                  </li>
                )}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <Panel
        className="mt-3"
        title="Recent orders"
        subtitle="Newest first, across every workshop"
        padded={false}
        actions={<Button href="/orders" variant="ghost" size="sm">All orders</Button>}
      >
        <DataState state={orders} empty={{ title: "No orders yet", detail: "They will appear here as shoppers check out." }}>
          {(data) => (
            <Table head={["Order", "Shopper", "Workshops", "Value", "Status", "Placed"]}>
              {(data.orders ?? []).map((order) => (
                <Row key={order.id}>
                  <Cell>
                    <Link href={`/orders/${order.id}`} className="tabular font-medium text-[var(--accent-light)] hover:underline">
                      {order.order_number}
                    </Link>
                  </Cell>
                  <Cell>{order.shopper_name ?? order.shopper_email ?? "—"}</Cell>
                  <Cell muted>{order.shipment_count ?? "—"}</Cell>
                  <Cell align="right">{inr(order.total_cents)}</Cell>
                  <Cell>
                    <Badge tone={tone.order(order.status)}>{titleCase(order.status)}</Badge>
                  </Cell>
                  <Cell mono muted>{stamp(order.created_at)}</Cell>
                </Row>
              ))}
            </Table>
          )}
        </DataState>
      </Panel>
    </Shell>
  );
}
