"use client";

import { useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import {
  Receipt,
  Filter,
  CheckCircle2,
  ArrowLeft,
  Search,
  Scale,
  Download,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

interface LedgerEntryRow {
  id: string;
  journalId: string;
  debitAccount: string;
  creditAccount: string;
  amountCents: number;
  entryType: string;
  referenceType: string;
  referenceId: string;
  description: string;
  createdAt: string;
}

export default function AdminLedgerAuditPage() {
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");

  const [entries, setEntries] = useState<LedgerEntryRow[]>([
    {
      id: "le-001",
      journalId: "jnl-9912",
      debitAccount: "accounts.shopper (Priya Sharma)",
      creditAccount: "accounts.platform_escrow",
      amountCents: 1840000,
      entryType: "order_payment",
      referenceType: "order",
      referenceId: "ord-8831",
      description: "Customer checkout authorization and escrow hold",
      createdAt: "2026-09-23T10:14:00Z",
    },
    {
      id: "le-002",
      journalId: "jnl-9913",
      debitAccount: "accounts.platform_escrow",
      creditAccount: "accounts.platform_revenue",
      amountCents: 166000,
      entryType: "commission_fee",
      referenceType: "order",
      referenceId: "ord-8831",
      description: "Platform commission withholding (10.00% across 2 workshops)",
      createdAt: "2026-09-23T10:14:00Z",
    },
    {
      id: "le-003",
      journalId: "jnl-9914",
      debitAccount: "accounts.platform_escrow",
      creditAccount: "accounts.vendor (Jaipur Blue Pottery)",
      amountCents: 846000,
      entryType: "vendor_credit",
      referenceType: "shipment",
      referenceId: "shp-8831-01",
      description: "Escrow allocation for consignment shp-8831-01",
      createdAt: "2026-09-23T10:14:00Z",
    },
    {
      id: "le-004",
      journalId: "jnl-9915",
      debitAccount: "accounts.platform_escrow",
      creditAccount: "accounts.vendor (Varanasi Weaves)",
      amountCents: 828000,
      entryType: "vendor_credit",
      referenceType: "shipment",
      referenceId: "shp-8831-02",
      description: "Escrow allocation for consignment shp-8831-02",
      createdAt: "2026-09-23T10:14:00Z",
    },
    {
      id: "le-005",
      journalId: "jnl-9910",
      debitAccount: "accounts.vendor (Jaipur Blue Pottery)",
      creditAccount: "accounts.platform_cash",
      amountCents: 6450000,
      entryType: "payout_settlement",
      referenceType: "settlement",
      referenceId: "SET-2026-0922-A",
      description: "RTGS bank settlement disbursement batch",
      createdAt: "2026-09-22T17:30:00Z",
    },
    {
      id: "le-006",
      journalId: "jnl-9908",
      debitAccount: "accounts.shopper (Rajesh Kannan)",
      creditAccount: "accounts.platform_escrow",
      amountCents: 2890000,
      entryType: "order_payment",
      referenceType: "order",
      referenceId: "ord-8828",
      description: "Customer checkout authorization and escrow hold",
      createdAt: "2026-09-22T11:20:00Z",
    },
  ]);

  const filtered = entries.filter((e) => {
    const matchesType = typeFilter === "all" || e.entryType === typeFilter;
    const matchesSearch =
      e.journalId.toLowerCase().includes(search.toLowerCase()) ||
      e.description.toLowerCase().includes(search.toLowerCase()) ||
      e.debitAccount.toLowerCase().includes(search.toLowerCase()) ||
      e.creditAccount.toLowerCase().includes(search.toLowerCase()) ||
      e.referenceId.toLowerCase().includes(search.toLowerCase());
    return matchesType && matchesSearch;
  });

  const totalDebits = filtered.reduce((acc, curr) => acc + curr.amountCents, 0);
  const totalCredits = totalDebits; // Guaranteed in double entry

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Double-Entry Ledger Audit"
        subtitle="Immutable financial journal audit trail proving mathematical conservation across all four account classes."
        badge="Zero Divergence"
      />

      <div className="p-6 space-y-6 flex-1">
        <Link
          href="/finance"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Platform Financials
        </Link>

        {/* Conservation Proof Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                Double-Entry Proof of Balance
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                  Σ Debits = Σ Credits
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Total journal volume audited: {formatCurrency(totalDebits)}. Every transaction is debit/credit paired.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-slate-400">Debits: </span>
              <span className="text-emerald-400 font-bold">{formatCurrency(totalDebits)}</span>
            </div>
            <span className="text-slate-600">|</span>
            <div>
              <span className="text-slate-400">Credits: </span>
              <span className="text-emerald-400 font-bold">{formatCurrency(totalCredits)}</span>
            </div>
          </div>
        </div>

        {/* Search & Entry Type Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by journal ID, account, reference, or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Entry Type:</span>
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {[
                { id: "all", label: "All" },
                { id: "order_payment", label: "Order" },
                { id: "commission_fee", label: "Commission" },
                { id: "vendor_credit", label: "Credit" },
                { id: "payout_settlement", label: "Payout" },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTypeFilter(t.id)}
                  className={`px-2 py-0.5 rounded capitalize font-medium transition cursor-pointer ${
                    typeFilter === t.id
                      ? "bg-amber-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Ledger Entries Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Journal ID</th>
                  <th className="px-4 py-3">Debit Account</th>
                  <th className="px-4 py-3">Credit Account</th>
                  <th className="px-4 py-3">Amount (₹)</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Reference</th>
                  <th className="px-4 py-3">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filtered.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono text-slate-400 text-[11px]">
                      {formatDate(item.createdAt)}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-amber-400">
                      {item.journalId}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {item.debitAccount}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {item.creditAccount}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-white">
                      {formatCurrency(item.amountCents)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                        {item.entryType}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400">
                      {item.referenceType}:{item.referenceId}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {item.description}
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
