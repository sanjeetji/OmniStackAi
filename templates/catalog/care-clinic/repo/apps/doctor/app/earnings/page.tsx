"use client";

import { useState } from "react";
import {
  DollarSign,
  TrendingUp,
  Download,
  Calendar,
  CreditCard,
  Building,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  ShieldCheck,
  Video,
  UserCheck,
} from "lucide-react";
import { formatINR } from "@careclinic/shared";

interface SettlementBatch {
  id: string;
  period: string;
  inClinicCount: number;
  telehealthCount: number;
  grossAmount: number;
  clinicShareAmount: number;
  tdsDeduction: number;
  netPayout: number;
  status: "settled" | "processing";
  utrNumber: string;
  settledAt: string;
}

const SETTLEMENT_HISTORY: SettlementBatch[] = [
  {
    id: "SET-2026-09B1",
    period: "01 Sep 2026 – 15 Sep 2026",
    inClinicCount: 112,
    telehealthCount: 38,
    grossAmount: 112400,
    clinicShareAmount: 33720,
    tdsDeduction: 7868,
    netPayout: 70812,
    status: "settled",
    utrNumber: "HDFCN26258019482",
    settledAt: "16 Sep 2026",
  },
  {
    id: "SET-2026-08B2",
    period: "16 Aug 2026 – 31 Aug 2026",
    inClinicCount: 124,
    telehealthCount: 42,
    grossAmount: 124400,
    clinicShareAmount: 37320,
    tdsDeduction: 8708,
    netPayout: 78372,
    status: "settled",
    utrNumber: "HDFCN26243009214",
    settledAt: "01 Sep 2026",
  },
  {
    id: "SET-2026-08B1",
    period: "01 Aug 2026 – 15 Aug 2026",
    inClinicCount: 108,
    telehealthCount: 35,
    grossAmount: 107400,
    clinicShareAmount: 32220,
    tdsDeduction: 7518,
    netPayout: 67662,
    status: "settled",
    utrNumber: "HDFCN26228004123",
    settledAt: "16 Aug 2026",
  },
];

export default function DoctorEarningsPage() {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownloadSlip = (id: string) => {
    setDownloadingId(id);
    setTimeout(() => {
      setDownloadingId(null);
      alert(`Settlement statement ${id} downloaded (PDF).`);
    }, 1000);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <ShieldCheck className="w-3.5 h-3.5" />
              Verified Physician Revenue Ledger
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Consultation Revenue & Payouts
          </h1>
          <p className="text-sm text-slate-500">
            Track daily OPD fee collections, telehealth settlements, and direct bank payouts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-white border border-slate-200 px-4 py-2 rounded-xl shadow-xs text-right">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Direct Payout A/C
            </span>
            <span className="text-xs font-bold text-slate-800">
              HDFC Bank ••••• 4192
            </span>
          </div>
        </div>
      </div>

      {/* Primary KPI Ribbon */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">
              Gross Billings (MTD)
            </span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {formatINR(248000)}
          </div>
          <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1 mt-1">
            <span>+14.8%</span>
            <span className="text-slate-400 font-normal">vs previous month</span>
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">
              Doctor Share (70%)
            </span>
            <DollarSign className="w-4 h-4 text-teal-600" />
          </div>
          <div className="text-2xl font-black text-emerald-700">
            {formatINR(173600)}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">
            Net payable after clinic facility fee
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">
              In-Clinic OPD Share
            </span>
            <UserCheck className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {formatINR(128800)}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">
            230 patients • ₹800 standard tariff
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">
              Telehealth Video Share
            </span>
            <Video className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {formatINR(44800)}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">
            80 sessions • ₹600 video tariff
          </span>
        </div>
      </div>

      {/* Active Settlement In-Progress Alert */}
      <div className="bg-linear-to-r from-emerald-900 to-slate-900 text-white p-5 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
              Current Cycle In Progress
            </span>
          </div>
          <h2 className="text-lg font-bold">16 Sep 2026 – 30 Sep 2026</h2>
          <p className="text-xs text-slate-300">
            Unsettled cashier collections: 94 consultations logged. Automatic batch transfer scheduled for 01 Oct 2026.
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-xs px-5 py-3 rounded-xl border border-white/15 text-right self-start md:self-auto">
          <span className="text-[11px] uppercase tracking-wider text-slate-300 block font-semibold">
            Accrued Cycle Net
          </span>
          <span className="text-2xl font-black text-emerald-300 block">
            {formatINR(59200)}
          </span>
        </div>
      </div>

      {/* Historical Payout Ledger */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Settlement Statements & Bank Remittances
            </h2>
            <p className="text-xs text-slate-500">
              Twice-monthly automated direct deposits with itemized TDS and clinic overhead breakdown.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5">Settlement Cycle</th>
                <th className="px-6 py-3.5">Consultations</th>
                <th className="px-6 py-3.5">Gross Billing</th>
                <th className="px-6 py-3.5">Clinic Fee (30%)</th>
                <th className="px-6 py-3.5">TDS (10%)</th>
                <th className="px-6 py-3.5">Net Remitted</th>
                <th className="px-6 py-3.5 text-right">Statement</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {SETTLEMENT_HISTORY.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-4">
                    <span className="font-bold text-slate-900 block text-xs">
                      {item.period}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 mt-0.5 block">
                      {item.utrNumber} • {item.settledAt}
                    </span>
                  </td>

                  <td className="px-6 py-4 text-xs text-slate-700">
                    <span className="font-semibold">{item.inClinicCount} In-Clinic</span>
                    <span className="text-slate-400"> + </span>
                    <span className="font-semibold text-teal-700">{item.telehealthCount} Video</span>
                  </td>

                  <td className="px-6 py-4 font-mono font-semibold text-slate-900 text-xs">
                    {formatINR(item.grossAmount)}
                  </td>

                  <td className="px-6 py-4 font-mono text-slate-500 text-xs">
                    -{formatINR(item.clinicShareAmount)}
                  </td>

                  <td className="px-6 py-4 font-mono text-slate-500 text-xs">
                    -{formatINR(item.tdsDeduction)}
                  </td>

                  <td className="px-6 py-4">
                    <span className="font-mono font-bold text-emerald-700 text-xs block">
                      {formatINR(item.netPayout)}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.2 rounded-sm border border-emerald-200">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      Remitted
                    </span>
                  </td>

                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleDownloadSlip(item.id)}
                      disabled={downloadingId === item.id}
                      className="px-3 py-1.5 border border-slate-200 hover:bg-slate-100 rounded-lg text-xs font-semibold text-slate-700 inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
                    >
                      <Download className="w-3.5 h-3.5 text-slate-400" />
                      <span>{downloadingId === item.id ? "Preparing..." : "Tax PDF"}</span>
                    </button>
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
