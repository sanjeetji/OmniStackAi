"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import { StatCard } from "@/components/stat-card";
import {
  TrendingUp,
  Store,
  ShoppingBag,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  Truck,
  CheckCircle2,
  Clock,
  ChevronRight,
  Wallet,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

interface MetricState {
  totalGmvCents: number;
  totalOrdersCount: number;
  totalShopsCount: number;
  totalShoppersCount: number;
  pendingKycCount: number;
  pendingSettlementsCount: number;
  dailyVolume: Array<{ date: string; gmvCents: number; orderCount: number }>;
  financials: {
    platformCashBalanceCents: number;
    platformRevenueCents: number;
    totalVendorPayablesCents: number;
    totalSettlementsPaidCents: number;
  };
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<MetricState>({
    totalGmvCents: 18450000,
    totalOrdersCount: 142,
    totalShopsCount: 8,
    totalShoppersCount: 24,
    pendingKycCount: 2,
    pendingSettlementsCount: 3,
    dailyVolume: [
      { date: "2026-09-10", gmvCents: 850000, orderCount: 7 },
      { date: "2026-09-11", gmvCents: 1120000, orderCount: 9 },
      { date: "2026-09-12", gmvCents: 980000, orderCount: 8 },
      { date: "2026-09-13", gmvCents: 1450000, orderCount: 12 },
      { date: "2026-09-14", gmvCents: 1650000, orderCount: 14 },
      { date: "2026-09-15", gmvCents: 1320000, orderCount: 10 },
      { date: "2026-09-16", gmvCents: 1780000, orderCount: 15 },
      { date: "2026-09-17", gmvCents: 1420000, orderCount: 11 },
      { date: "2026-09-18", gmvCents: 1890000, orderCount: 16 },
      { date: "2026-09-19", gmvCents: 1560000, orderCount: 13 },
      { date: "2026-09-20", gmvCents: 2100000, orderCount: 18 },
      { date: "2026-09-21", gmvCents: 1940000, orderCount: 17 },
      { date: "2026-09-22", gmvCents: 2280000, orderCount: 20 },
      { date: "2026-09-23", gmvCents: 2450000, orderCount: 22 },
    ],
    financials: {
      platformCashBalanceCents: 42845000,
      platformRevenueCents: 1845000,
      totalVendorPayablesCents: 16605000,
      totalSettlementsPaidCents: 24395000,
    },
  });

  const recentOrders = [
    {
      id: "ord-8831",
      orderNumber: "BAZ-2026-8831",
      customer: "Priya Sharma",
      shops: "Jaipur Blue Pottery + Varanasi Weaves",
      totalCents: 1840000,
      shipmentsCount: 2,
      status: "processing",
      date: "2026-09-23T10:14:00Z",
    },
    {
      id: "ord-8830",
      orderNumber: "BAZ-2026-8830",
      customer: "Arjun Mehta",
      shops: "Kashmir Craftsmen Guild",
      totalCents: 3250000,
      shipmentsCount: 1,
      status: "shipped",
      date: "2026-09-23T08:30:00Z",
    },
    {
      id: "ord-8829",
      orderNumber: "BAZ-2026-8829",
      customer: "Ananya Deshmukh",
      shops: "Bastar Tribal Bell Metal",
      totalCents: 980000,
      shipmentsCount: 1,
      status: "delivered",
      date: "2026-09-22T16:45:00Z",
    },
    {
      id: "ord-8828",
      orderNumber: "BAZ-2026-8828",
      customer: "Rajesh Kannan",
      shops: "Kanchipuram Silk Loom + Jaipur Blue Pottery",
      totalCents: 2890000,
      shipmentsCount: 2,
      status: "delivered",
      date: "2026-09-22T11:20:00Z",
    },
  ];

  const pendingKycQueue = [
    {
      id: "shop-002",
      name: "Bastar Tribal Bell Metal",
      artisan: "Devnath Baghel",
      craft: "Dhokra Bell Metal Casting",
      submittedDate: "Today, 09:30 AM",
      giTag: "GI #84",
    },
    {
      id: "shop-005",
      name: "Channapatna Wooden Toys",
      artisan: "Syed Basha",
      craft: "Natural Lacquer Turned Wood",
      submittedDate: "Yesterday",
      giTag: "GI #19",
    },
  ];

  const maxVolume = Math.max(...metrics.dailyVolume.map((d) => d.gmvCents));

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Marketplace Overview"
        subtitle="High-density operator supervisor panel for multi-vendor commerce, KYC compliance, and double-entry accounting."
        badge="Supervision Active"
        actionText="Financial Ledger"
        actionHref="/finance/ledger"
        actionIcon={Wallet}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Top 4 Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Gross Merchandise Value (GMV)"
            value={formatCurrency(metrics.totalGmvCents)}
            subtitle="Platform-wide order volume"
            trend="+18.4% vs last week"
            trendPositive={true}
            icon={TrendingUp}
            tone="amber"
          />
          <StatCard
            title="Marketplace Net Revenue"
            value={formatCurrency(metrics.financials.platformRevenueCents)}
            subtitle="10.00% take-rate commissions"
            trend="100% Collected"
            trendPositive={true}
            icon={Wallet}
            tone="emerald"
          />
          <StatCard
            title="Artisan Workshops"
            value={metrics.totalShopsCount}
            subtitle="Heritage master craftspeople"
            trend="2 Pending KYC"
            trendPositive={false}
            icon={Store}
            tone="sky"
          />
          <StatCard
            title="Orders & Consignments"
            value={metrics.totalOrdersCount}
            subtitle="Split per-vendor shipments"
            trend="98.2% on-time dispatch"
            trendPositive={true}
            icon={ShoppingBag}
            tone="default"
          />
        </div>

        {/* 14-Day GMV Volume Bar Chart & Action Queues */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 14-day Chart */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-amber-400" />
                  14-Day Gross Merchandise Volume
                </h3>
                <p className="text-xs text-slate-400">
                  Daily transaction flow across all regional artisan craft ateliers
                </p>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-amber-400/10 text-amber-300 border border-amber-400/20">
                INR (₹) / Day
              </span>
            </div>

            {/* SVG Bar Chart Visualization */}
            <div className="h-44 flex items-end gap-2 pt-4 px-2 border-b border-slate-800">
              {metrics.dailyVolume.map((item, idx) => {
                const heightPercent = Math.max(15, Math.round((item.gmvCents / maxVolume) * 100));
                const dayLabel = item.date.slice(8);
                return (
                  <div key={item.date} className="flex-1 flex flex-col items-center gap-1 group relative">
                    {/* Tooltip on hover */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-8 px-2 py-1 rounded bg-slate-950 border border-slate-700 text-[10px] text-white font-mono whitespace-nowrap pointer-events-none z-10 shadow-lg">
                      {item.date}: {formatCurrency(item.gmvCents)} ({item.orderCount} orders)
                    </div>

                    <div className="w-full flex justify-center">
                      <div
                        style={{ height: `${heightPercent}%` }}
                        className={`w-full max-w-[28px] rounded-t-sm transition-all duration-300 ${
                          idx === metrics.dailyVolume.length - 1
                            ? "bg-gradient-to-t from-amber-600 to-amber-400"
                            : "bg-slate-700 hover:bg-amber-500/80"
                        }`}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">{dayLabel}</span>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-sm bg-gradient-to-t from-amber-600 to-amber-400" />
                Current Peak Day: {formatCurrency(maxVolume)}
              </span>
              <span>14 Days Total: {formatCurrency(metrics.totalGmvCents)}</span>
            </div>
          </div>

          {/* Urgent Attention / Action Queues */}
          <div className="space-y-4">
            {/* KYC Pending Alert */}
            <div className="bg-slate-900 border border-amber-500/30 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase tracking-wider">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Pending KYC Reviews ({metrics.pendingKycCount})</span>
                </div>
                <Link
                  href="/shops"
                  className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 font-medium"
                >
                  View All <ChevronRight className="w-3 h-3" />
                </Link>
              </div>

              <div className="space-y-2">
                {pendingKycQueue.map((item) => (
                  <div
                    key={item.id}
                    className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-semibold text-white">{item.name}</div>
                      <div className="text-[11px] text-slate-400">
                        {item.artisan} • <span className="text-amber-400">{item.giTag}</span>
                      </div>
                    </div>
                    <Link
                      href={`/shops/${item.id}/kyc`}
                      className="px-2 py-1 rounded bg-amber-600/30 hover:bg-amber-600 text-amber-200 hover:text-white text-[11px] font-medium transition"
                    >
                      Verify
                    </Link>
                  </div>
                ))}
              </div>
            </div>

            {/* Payout Settlements Alert */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                  <Wallet className="w-4 h-4" />
                  <span>Settlement Batches ({metrics.pendingSettlementsCount})</span>
                </div>
                <Link
                  href="/settlements"
                  className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-medium"
                >
                  Inspect <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
              <p className="text-xs text-slate-400">
                ₹1,84,500.00 ready for RTGS disbursement to 3 verified artisan workshops.
              </p>
              <Link
                href="/settlements"
                className="w-full py-2 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center justify-center gap-2 transition"
              >
                <span>Process Bank Disbursement</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Recent Global Orders Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-amber-400" />
                Recent Marketplace Split Orders
              </h3>
              <p className="text-xs text-slate-400">
                Multi-vendor carts automatically partitioned into per-vendor shipments
              </p>
            </div>
            <Link
              href="/orders"
              className="text-xs text-slate-300 hover:text-white flex items-center gap-1 font-medium"
            >
              All Orders <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Order Number</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Vendor Workshops</th>
                  <th className="px-4 py-3">Total (₹)</th>
                  <th className="px-4 py-3">Split Shipments</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {recentOrders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono font-medium text-amber-400">
                      {ord.orderNumber}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-200">
                      {ord.customer}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {ord.shops}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-white">
                      {formatCurrency(ord.totalCents)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                        {ord.shipmentsCount} consignments
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                          ord.status === "delivered"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : ord.status === "shipped"
                            ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {ord.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/orders/${ord.id}`}
                        className="text-amber-400 hover:text-amber-300 font-semibold underline underline-offset-2"
                      >
                        Investigate
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
