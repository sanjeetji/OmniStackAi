"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AdminHeader } from "@/components/admin-header";
import {
  FileCheck2,
  Building,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Receipt,
  ArrowRight,
  ShieldCheck,
  CreditCard,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

export default function AdminPayoutApprovalPage() {
  const params = useParams();
  const batchId = (params?.id as string) || "set-002";

  const [batchStatus, setBatchStatus] = useState<"approved" | "processed">("approved");
  const [disbursing, setDisbursing] = useState(false);
  const [successMessage, setSuccessMessage] = useState(false);

  const batch = {
    id: batchId,
    batchNumber: "SET-2026-0923-B",
    status: batchStatus,
    shopName: "Varanasi Heritage Weaves",
    artisanName: "Munna Lal Ansari",
    artisanEmail: "ansari@bazaar.test",
    periodStart: "2026-09-16T00:00:00Z",
    periodEnd: "2026-09-23T00:00:00Z",
    grossSalesCents: 9000000,
    commissionBps: 800, // 8% preferred
    commissionCents: 720000,
    refundDeductionsCents: 0,
    netPayoutCents: 8280000,
    bankDetails: {
      beneficiary: "Varanasi Heritage Weaves Guild",
      bankName: "HDFC Bank",
      accountNumber: "50100294829104",
      ifscCode: "HDFC0001248",
      branch: "Chowk Main Branch, Varanasi",
    },
    consignments: [
      {
        id: "shp-8822-01",
        orderNumber: "BAZ-2026-8822",
        deliveredAt: "2026-09-18T14:20:00Z",
        grossCents: 5000000,
        commissionCents: 400000,
        netCents: 4600000,
      },
      {
        id: "shp-8825-01",
        orderNumber: "BAZ-2026-8825",
        deliveredAt: "2026-09-20T11:15:00Z",
        grossCents: 4000000,
        commissionCents: 320000,
        netCents: 3680000,
      },
    ],
  };

  const handleApproveDisbursement = () => {
    setDisbursing(true);
    setTimeout(() => {
      setBatchStatus("processed");
      setDisbursing(false);
      setSuccessMessage(true);
      setTimeout(() => setSuccessMessage(false), 5000);
    }, 600);
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title={`Approve Payout Batch: ${batch.batchNumber}`}
        subtitle={`Artisan Beneficiary: ${batch.shopName} • Net Settlement: ${formatCurrency(batch.netPayoutCents)}`}
        badge={batch.status.toUpperCase()}
      />

      <div className="p-6 space-y-6 flex-1 max-w-5xl">
        <Link
          href="/settlements"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Settlement Batches
        </Link>

        {/* Payout Calculation Ledger Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Receipt className="w-4 h-4 text-emerald-400" />
              Net Settlement Calculation Breakdown
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Period: {formatDate(batch.periodStart)} – {formatDate(batch.periodEnd)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs">
            <div>
              <div className="text-slate-400 mb-1">Gross Delivered Sales (+)</div>
              <div className="text-lg font-mono font-bold text-white">
                {formatCurrency(batch.grossSalesCents)}
              </div>
            </div>
            <div>
              <div className="text-slate-400 mb-1">Marketplace Commission (8%) (-)</div>
              <div className="text-lg font-mono font-bold text-amber-400">
                - {formatCurrency(batch.commissionCents)}
              </div>
            </div>
            <div>
              <div className="text-slate-400 mb-1">Returns / Clawbacks (-)</div>
              <div className="text-lg font-mono font-bold text-slate-400">
                {formatCurrency(batch.refundDeductionsCents)}
              </div>
            </div>
            <div>
              <div className="text-emerald-400 font-semibold mb-1">Net Artisan Bank Payout (=)</div>
              <div className="text-xl font-mono font-bold text-emerald-400">
                {formatCurrency(batch.netPayoutCents)}
              </div>
            </div>
          </div>
        </div>

        {/* Beneficiary Bank Account */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Building className="w-4 h-4 text-emerald-400" />
              Verified Beneficiary Bank Account
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Beneficiary:</span>
                <span className="text-white font-medium">{batch.bankDetails.beneficiary}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Bank:</span>
                <span className="text-white">{batch.bankDetails.bankName}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Account Number:</span>
                <span className="text-white font-mono">{batch.bankDetails.accountNumber}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">IFSC Code:</span>
                <span className="text-amber-400 font-mono font-bold">{batch.bankDetails.ifscCode}</span>
              </div>
            </div>
          </div>

          {/* Action Approval Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                Administrative Authorization
              </h3>
              <p className="text-xs text-slate-400">
                Authorizes direct RTGS disbursement from platform escrow reserve account to the artisan workshop bank account.
              </p>
            </div>

            {batch.status === "approved" ? (
              <button
                type="button"
                onClick={handleApproveDisbursement}
                disabled={disbursing}
                className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <CreditCard className="w-4 h-4" />
                <span>{disbursing ? "Disbursing via RTGS..." : "Disburse Net Payout via RTGS"}</span>
              </button>
            ) : (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                DISBURSED &amp; RECONCILED (Ref: RTGS-HDFC-9912048)
              </div>
            )}

            {successMessage && (
              <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Disbursement confirmed: ledger debited and journal audit committed.
              </div>
            )}
          </div>
        </div>

        {/* Consignments in this Batch */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">
              Delivered Consignments Reconciled in this Batch ({batch.consignments.length})
            </h3>
            <span className="text-xs text-slate-400">Delivered &amp; past 7-day return escrow window</span>
          </div>

          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Consignment ID</th>
                <th className="px-4 py-3">Order Number</th>
                <th className="px-4 py-3">Delivered Date</th>
                <th className="px-4 py-3">Gross Amount</th>
                <th className="px-4 py-3">Commission (8%)</th>
                <th className="px-4 py-3 font-mono text-emerald-400">Net Artisan Payout</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {batch.consignments.map((c) => (
                <tr key={c.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-4 py-3 font-mono text-amber-400">{c.id}</td>
                  <td className="px-4 py-3 font-mono text-slate-200">{c.orderNumber}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                    {formatDate(c.deliveredAt)}
                  </td>
                  <td className="px-4 py-3 font-mono text-white">
                    {formatCurrency(c.grossCents)}
                  </td>
                  <td className="px-4 py-3 font-mono text-amber-400">
                    - {formatCurrency(c.commissionCents)}
                  </td>
                  <td className="px-4 py-3 font-mono font-bold text-emerald-400">
                    {formatCurrency(c.netCents)}
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
