"use client";

import { useState } from "react";
import { AdminHeader } from "@/components/admin-header";
import {
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  User,
  Tag,
  Store,
  Wallet,
} from "lucide-react";
import { formatDate } from "@bazaar/shared";

interface AuditEntry {
  id: string;
  actorName: string;
  actorEmail: string;
  action: string;
  entityType: string;
  entityId: string;
  metadata: Record<string, any>;
  createdAt: string;
}

export default function AdminAuditPage() {
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");

  const [logs, setLogs] = useState<AuditEntry[]>([
    {
      id: "aud-001",
      actorName: "Vikram Malhotra",
      actorEmail: "admin@bazaar.test",
      action: "update_shop_kyc",
      entityType: "shop",
      entityId: "shop-001",
      metadata: { newStatus: "verified", certificate: "GI/IN/2006/0039" },
      createdAt: "2026-09-23T11:30:00Z",
    },
    {
      id: "aud-002",
      actorName: "Vikram Malhotra",
      actorEmail: "admin@bazaar.test",
      action: "update_shop_commission",
      entityType: "shop",
      entityId: "shop-003",
      metadata: { previousBps: 1000, newCommissionBps: 800, reason: "Preferred Heritage Guild" },
      createdAt: "2026-09-23T10:45:00Z",
    },
    {
      id: "aud-003",
      actorName: "Vikram Malhotra",
      actorEmail: "admin@bazaar.test",
      action: "approve_settlement_batch",
      entityType: "settlement_batch",
      entityId: "set-001",
      metadata: { netPayoutCents: 6450000, bankRef: "NEFT-SBI-991204812" },
      createdAt: "2026-09-22T17:30:00Z",
    },
    {
      id: "aud-004",
      actorName: "Vikram Malhotra",
      actorEmail: "admin@bazaar.test",
      action: "create_coupon",
      entityType: "coupon",
      entityId: "cp-01",
      metadata: { code: "HERITAGE15", discountValue: 15, discountType: "percentage" },
      createdAt: "2026-09-21T09:15:00Z",
    },
    {
      id: "aud-005",
      actorName: "System Automation",
      actorEmail: "cron@bazaar.internal",
      action: "escrow_reserve_release",
      entityType: "shipment",
      entityId: "shp-8828-01",
      metadata: { amountCents: 2890000, status: "delivered_7d_elapsed" },
      createdAt: "2026-09-20T00:00:00Z",
    },
  ]);

  const filtered = logs.filter((l) => {
    const matchesAction = actionFilter === "all" || l.action === actionFilter;
    const matchesSearch =
      l.action.toLowerCase().includes(search.toLowerCase()) ||
      l.actorName.toLowerCase().includes(search.toLowerCase()) ||
      l.entityId.toLowerCase().includes(search.toLowerCase()) ||
      JSON.stringify(l.metadata).toLowerCase().includes(search.toLowerCase());
    return matchesAction && matchesSearch;
  });

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Audit Logs"
        subtitle="Tamper-evident record of all administrative state transitions, KYC approvals, and financial disbursements."
        badge={`${logs.length} Audit Entries`}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Search & Action Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by action name, actor, entity ID, or metadata..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Action:</span>
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {[
                { id: "all", label: "All" },
                { id: "update_shop_kyc", label: "KYC" },
                { id: "update_shop_commission", label: "Commission" },
                { id: "approve_settlement_batch", label: "Settlement" },
                { id: "create_coupon", label: "Coupon" },
              ].map((a) => (
                <button
                  key={a.id}
                  onClick={() => setActionFilter(a.id)}
                  className={`px-2 py-0.5 rounded capitalize font-medium transition cursor-pointer ${
                    actionFilter === a.id
                      ? "bg-amber-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Operator / Actor</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Target Entity</th>
                  <th className="px-4 py-3">Audit Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filtered.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono text-slate-400 text-[11px]">
                      {formatDate(log.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-200">{log.actorName}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{log.actorEmail}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-bold text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {log.entityType}:{log.entityId}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400 text-[11px]">
                      <code className="bg-slate-950 px-2 py-1 rounded border border-slate-800/80 text-amber-200/90 block max-w-sm truncate">
                        {JSON.stringify(log.metadata)}
                      </code>
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
