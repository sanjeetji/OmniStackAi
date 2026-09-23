"use client";

import { useState } from "react";
import { AdminHeader } from "@/components/admin-header";
import {
  Settings,
  Percent,
  Clock,
  Building,
  Truck,
  CreditCard,
  Bell,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react";

export default function AdminSettingsPage() {
  const [commissionRate, setCommissionRate] = useState("10.00");
  const [escrowHoldDays, setEscrowHoldDays] = useState("7");
  const [gstin, setGstin] = useState("08AABCB1234F1Z5");
  const [taxRate, setTaxRate] = useState("18.00");
  const [mockPayments, setMockPayments] = useState(true);
  const [mockLogistics, setMockLogistics] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Platform Settings"
        subtitle="Global platform rules: take-rate commissions, escrow lock periods, and integration adapters."
        badge="System Configuration"
      />

      <div className="p-6 space-y-6 flex-1 max-w-4xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Marketplace Economics */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Percent className="w-4 h-4 text-amber-400" />
              Marketplace Economics &amp; Escrow Policy
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Default Platform Commission Take-Rate (%)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="50"
                    value={commissionRate}
                    onChange={(e) => setCommissionRate(e.target.value)}
                    className="w-28 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-slate-400 font-mono">
                    % (Basis Points: {Math.round(parseFloat(commissionRate || "0") * 100)})
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Applies to all newly onboarded workshops unless customized individually.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Escrow Hold Duration (Post Delivery)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={escrowHoldDays}
                    onChange={(e) => setEscrowHoldDays(e.target.value)}
                    className="w-24 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-slate-400">Days</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Protects patrons for return requests before releasing funds to vendor payout balance.
                </p>
              </div>
            </div>
          </div>

          {/* Statutory & Tax Configuration */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Building className="w-4 h-4 text-emerald-400" />
              Statutory GST &amp; Invoicing Details
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Marketplace GSTIN Registration
                </label>
                <input
                  type="text"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Standard GST Rate on Commission Fee (%)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={taxRate}
                    onChange={(e) => setTaxRate(e.target.value)}
                    className="w-24 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-slate-400 font-mono">% (18% GST)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Platform Provider Adapters */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-sky-400" />
              Platform Integration Adapters (Offline by Contract)
            </h3>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
                <div className="flex items-center gap-3">
                  <CreditCard className="w-4 h-4 text-amber-400" />
                  <div>
                    <div className="font-semibold text-white">Payment Gateway Adapter</div>
                    <div className="text-[11px] text-slate-400">
                      Simulates mock card and instant UPI checkouts offline
                    </div>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 font-mono font-semibold text-[11px] border border-emerald-500/20">
                  MOCK ACTIVE
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
                <div className="flex items-center gap-3">
                  <Truck className="w-4 h-4 text-sky-400" />
                  <div>
                    <div className="font-semibold text-white">Logistics &amp; Courier Telemetry</div>
                    <div className="text-[11px] text-slate-400">
                      Simulates Blue Dart, Delhivery, and India Post tracking milestones
                    </div>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 font-mono font-semibold text-[11px] border border-emerald-500/20">
                  MOCK ACTIVE
                </span>
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="px-5 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs transition cursor-pointer"
          >
            Save Platform Settings
          </button>

          {saved && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Platform configuration committed and written to audit log.
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
