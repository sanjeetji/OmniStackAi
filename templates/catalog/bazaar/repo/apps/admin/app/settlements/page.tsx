"use client";

import { useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import { StatCard } from "@/components/stat-card";
import {
  FileCheck2,
  Building,
  CheckCircle2,
  Clock,
  ArrowRight,
  Plus,
  Search,
  Filter,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

interface SettlementBatchRow {
  id: string;
  batchNumber: string;
  shopName: string;
  shopSlug: string;
  grossSalesCents: number;
  commissionCents: number;
  netPayoutCents: number;
  status: "approved" | "processed" | "draft";
  periodStart: string;
  periodEnd: string;
  payoutReference: string;
  processedAt?: string;
}

export default function AdminSettlementsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [generating, setGenerating] = useState(false);
  const [generatedSuccess, setGeneratedSuccess] = useState(false);

  const [settlements, setSettlements] = useState<SettlementBatchRow[]>([
    {
      id: "set-001",
      batchNumber: "SET-2026-0922-A",
      shopName: "Jaipur Blue Art Pottery",
      shopSlug: "jaipur-blue-pottery",
      grossSalesCents: 7166667,
      commissionCents: 716667,
      netPayoutCents: 6450000,
      status: "processed",
      periodStart: "2026-09-15T00:00:00Z",
      periodEnd: "2026-09-22T00:00:00Z",
      payoutReference: "NEFT-SBI-991204812",
      processedAt: "2026-09-22T17:30:00Z",
    },
    {
      id: "set-002",
      batchNumber: "SET-2026-0923-B",
      shopName: "Varanasi Heritage Weaves",
      shopSlug: "varanasi-weaves",
      grossSalesCents: 9000000,
      commissionCents: 720000, // 8% preferred
      netPayoutCents: 8280000,
      status: "approved",
      periodStart: "2026-09-16T00:00:00Z",
      periodEnd: "2026-09-23T00:00:00Z",
      payoutReference: "RTGS-HDFC-PENDING",
    },
    {
      id: "set-003",
      batchNumber: "SET-2026-0923-C",
      shopName: "Kashmir Craftsmen Guild",
      shopSlug: "kashmir-craftsmen",
      grossSalesCents: 4577778,
      commissionCents: 457778,
      netPayoutCents: 4120000,
      status: "approved",
      periodStart: "2026-09-16T00:00:00Z",
      periodEnd: "2026-09-23T00:00:00Z",
      payoutReference: "RTGS-ICICI-PENDING",
    },
  ]);

  const handleGenerateBatch = () => {
    setGenerating(true);
    setTimeout(() => {
      const newBatch: SettlementBatchRow = {
        id: `set-${Date.now()}`,
        batchNumber: `SET-${Date.now().toString(36).toUpperCase()}`,
        shopName: "Bastar Tribal Bell Metal",
        shopSlug: "bastar-bell-metal",
        grossSalesCents: 2422222,
        commissionCents: 242222,
        netPayoutCents: 2180000,
        status: "approved",
        periodStart: "2026-09-16T00:00:00Z",
        periodEnd: "2026-09-23T00:00:00Z",
        payoutReference: "RTGS-AXIS-PENDING",
      };
      setSettlements([newBatch, ...settlements]);
      setGenerating(false);
      setGeneratedSuccess(true);
      setTimeout(() => setGeneratedSuccess(false), 4000);
    }, 600);
  };

  const filtered = settlements.filter((s) => {
    const matchesSearch =
      s.batchNumber.toLowerCase().includes(search.toLowerCase()) ||
      s.shopName.toLowerCase().includes(search.toLowerCase()) ||
      s.payoutReference.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || s.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Settlement Batches"
        subtitle="Approve and disburse multi-vendor payout batches reconciled against delivered shipments and escrow holds."
        badge={`${settlements.length} Batches`}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Settlement Summary Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            title="Total Disbursed to Date"
            value="₹2,43,950.00"
            subtitle="Processed bank transfers"
            trend="All NEFT cleared"
            trendPositive={true}
            icon={CheckCircle2}
            tone="emerald"
          />
          <StatCard
            title="Pending Disbursement Approval"
            value="₹1,24,000.00"
            subtitle="2 batches ready for bank release"
            trend="Needs operator approval"
            trendPositive={false}
            icon={Clock}
            tone="amber"
          />
          <StatCard
            title="Average Artisan Split"
            value="90.00%"
            subtitle="Net vendor payout ratio"
            trend="10.00% Platform Fee"
            trendPositive={true}
            icon={Building}
            tone="default"
          />
        </div>

        {/* Action Controls & Batch Generator */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by batch number, workshop, or payout reference..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {["all", "approved", "processed"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded capitalize font-medium transition cursor-pointer ${
                    statusFilter === st
                      ? "bg-amber-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <button
              onClick={handleGenerateBatch}
              disabled={generating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{generating ? "Generating..." : "Generate Settlement Batch"}</span>
            </button>
          </div>
        </div>

        {generatedSuccess && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            New settlement batch generated for delivered shipments: Bastar Tribal Bell Metal (₹21,800.00).
          </div>
        )}

        {/* Batches Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Batch Number</th>
                  <th className="px-4 py-3">Artisan Workshop</th>
                  <th className="px-4 py-3">Gross Sales</th>
                  <th className="px-4 py-3">Platform Fee</th>
                  <th className="px-4 py-3">Net Payout (₹)</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Settlement Reference</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filtered.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono font-medium text-amber-400">
                      {b.batchNumber}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-100">
                      {b.shopName}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {formatCurrency(b.grossSalesCents)}
                    </td>
                    <td className="px-4 py-3 font-mono text-amber-400/90">
                      - {formatCurrency(b.commissionCents)}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-emerald-400 text-sm">
                      {formatCurrency(b.netPayoutCents)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                          b.status === "processed"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {b.status === "processed" ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        {b.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400 text-[11px]">
                      {b.payoutReference}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/settlements/${b.id}`}
                        className="px-2.5 py-1 rounded bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-white font-semibold transition inline-flex items-center gap-1"
                      >
                        <span>Inspect &amp; Disburse</span>
                        <ArrowRight className="w-3 h-3" />
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
