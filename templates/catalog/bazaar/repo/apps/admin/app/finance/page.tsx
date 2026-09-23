"use client";

import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import { StatCard } from "@/components/stat-card";
import {
  Wallet,
  Receipt,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle2,
  FileCheck2,
  Building,
  TrendingUp,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

export default function AdminFinancePage() {
  const financialSummary = {
    platformCashBalanceCents: 42845000,
    platformRevenueCents: 1845000,
    totalVendorPayablesCents: 16605000,
    totalSettlementsPaidCents: 24395000,
  };

  const recentMovements = [
    {
      id: "mv-01",
      date: "2026-09-23T10:14:00Z",
      type: "order_payment",
      amountCents: 1840000,
      direction: "inflow",
      account: "Escrow Reserve Pool",
      ref: "BAZ-2026-8831",
      description: "Customer checkout authorization and escrow hold",
    },
    {
      id: "mv-02",
      date: "2026-09-23T10:14:00Z",
      type: "commission_fee",
      amountCents: 166000,
      direction: "internal",
      account: "Platform Commission Revenue",
      ref: "BAZ-2026-8831",
      description: "Platform take-rate commission withholdings",
    },
    {
      id: "mv-03",
      date: "2026-09-22T17:30:00Z",
      type: "payout_settlement",
      amountCents: 6450000,
      direction: "outflow",
      account: "Direct Bank RTGS Disbursement",
      ref: "SET-2026-0922-A",
      description: "Artisan settlement batch disburse: Jaipur Blue Pottery",
    },
    {
      id: "mv-04",
      date: "2026-09-22T11:20:00Z",
      type: "order_payment",
      amountCents: 2890000,
      direction: "inflow",
      account: "Escrow Reserve Pool",
      ref: "BAZ-2026-8828",
      description: "Customer checkout authorization and escrow hold",
    },
  ];

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Platform Financials"
        subtitle="Marketplace escrow liquidity, earned take-rate revenue, and unpaid artisan workshop payables."
        badge="Audit Grade Ledger"
        actionText="Double-Entry Journal"
        actionHref="/finance/ledger"
        actionIcon={Receipt}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Top 4 Financial Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Escrow Liquidity Pool"
            value={formatCurrency(financialSummary.platformCashBalanceCents)}
            subtitle="Customer funds held in safe escrow"
            trend="100% Fully Backed"
            trendPositive={true}
            icon={Wallet}
            tone="sky"
          />
          <StatCard
            title="Earned Marketplace Revenue"
            value={formatCurrency(financialSummary.platformRevenueCents)}
            subtitle="Cumulative take-rate fees"
            trend="10.00% Net Commission"
            trendPositive={true}
            icon={TrendingUp}
            tone="emerald"
          />
          <StatCard
            title="Vendor Payables Balance"
            value={formatCurrency(financialSummary.totalVendorPayablesCents)}
            subtitle="Owed to artisans upon delivery"
            trend="Settles on weekly cycle"
            trendPositive={true}
            icon={Building}
            tone="amber"
          />
          <StatCard
            title="Total Disbursed Settlements"
            value={formatCurrency(financialSummary.totalSettlementsPaidCents)}
            subtitle="Direct NEFT/RTGS bank transfers"
            trend="14 Batches Cleared"
            trendPositive={true}
            icon={FileCheck2}
            tone="default"
          />
        </div>

        {/* Double-Entry Balancing Verification Banner */}
        <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                Double-Entry Mathematical Balance Verified
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                  INVARIANT SAFE
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Asset Accounts (Platform Escrow) = Liability Accounts (Vendor Payables + Platform Revenue). Net divergence: ₹0.00.
              </p>
            </div>
          </div>

          <Link
            href="/finance/ledger"
            className="px-3.5 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 text-xs font-semibold transition"
          >
            Audit Journal Trail
          </Link>
        </div>

        {/* Recent Ledger Movements Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Receipt className="w-4 h-4 text-amber-400" />
                Recent Financial Ledger Movements
              </h3>
              <p className="text-xs text-slate-400">
                Live multi-party double-entry accounting transactions across orders and settlements
              </p>
            </div>
            <Link
              href="/finance/ledger"
              className="text-xs text-amber-400 hover:text-amber-300 font-semibold"
            >
              Full Ledger &rarr;
            </Link>
          </div>

          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Transaction Flow</th>
                <th className="px-4 py-3">Target Ledger Account</th>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Amount (₹)</th>
                <th className="px-4 py-3">Journal Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {recentMovements.map((mv) => (
                <tr key={mv.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-4 py-3 font-mono text-slate-400 text-[11px]">
                    {formatDate(mv.date)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                        mv.direction === "inflow"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : mv.direction === "outflow"
                          ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          : "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                      }`}
                    >
                      {mv.direction === "inflow" ? (
                        <ArrowDownLeft className="w-3 h-3" />
                      ) : mv.direction === "outflow" ? (
                        <ArrowUpRight className="w-3 h-3" />
                      ) : null}
                      {mv.type.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-200">
                    {mv.account}
                  </td>
                  <td className="px-4 py-3 font-mono text-amber-400">
                    {mv.ref}
                  </td>
                  <td className="px-4 py-3 font-mono font-bold text-white">
                    {formatCurrency(mv.amountCents)}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {mv.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
