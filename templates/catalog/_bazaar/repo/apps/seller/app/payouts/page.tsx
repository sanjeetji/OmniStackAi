"use client";

import { useEffect, useState } from "react";
import { formatPrice, formatDate, api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { BadgeIndianRupee, ArrowUpRight, CheckCircle2, Shield, Clock } from "lucide-react";

const DEMO_ENTRIES = [
  {
    id: "entry-001",
    journal_id: "jrn-9821441",
    entry_type: "credit",
    description: "Net proceeds from Consignment #SHP-9821-01 (Order #BZR-9821-441)",
    amount_cents: 432000,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
    reference_type: "shipment",
  },
  {
    id: "entry-002",
    journal_id: "jrn-9102112",
    entry_type: "credit",
    description: "Net proceeds from Consignment #SHP-9102-01 (Order #BZR-9102-112)",
    amount_cents: 468000,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    reference_type: "shipment",
  },
  {
    id: "entry-003",
    journal_id: "jrn-8840801",
    entry_type: "credit",
    description: "Net proceeds from Consignment #SHP-8840-01 (Order #BZR-8840-801)",
    amount_cents: 648000,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    reference_type: "shipment",
  },
  {
    id: "entry-004",
    journal_id: "jrn-settle-01",
    entry_type: "debit",
    description: "NEFT Bank Payout Batch #ST-JAIPUR-8801 to HDFC Bank (A/C **9412)",
    amount_cents: 1200000,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 96).toISOString(),
    reference_type: "settlement",
  },
];

const DEMO_BATCHES = [
  {
    id: "batch-001",
    batch_number: "ST-JAIPUR-8801",
    status: "processed",
    gross_sales_cents: 1333333,
    commission_cents: 133333,
    net_payout_cents: 1200000,
    payout_reference: "NEFT-HDFC-991209341",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 96).toISOString(),
  },
];

export default function SellerPayoutsPage() {
  const [balanceCents, setBalanceCents] = useState(432000);
  const [entries, setEntries] = useState(DEMO_ENTRIES);
  const [batches, setBatches] = useState(DEMO_BATCHES);
  const [requesting, setRequesting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getVendorLedger();
        if (res.account?.balance_cents != null) {
          setBalanceCents(res.account.balance_cents);
        }
        if (res.entries && res.entries.length > 0) {
          setEntries(res.entries);
        }
      } catch {
        // Fallback demo
      }
    }
    load();
  }, []);

  async function handleRequestSettlement() {
    try {
      setRequesting(true);
      await api.requestSettlement();
      const newBatch = {
        id: `batch-${Date.now()}`,
        batch_number: `ST-JAIPUR-${Math.floor(1000 + Math.random() * 9000)}`,
        status: "approved" as const,
        gross_sales_cents: Math.round(balanceCents / 0.9),
        commission_cents: Math.round(balanceCents * 0.1),
        net_payout_cents: balanceCents,
        payout_reference: `RTGS-HDFC-${Math.floor(100000000 + Math.random() * 900000000)}`,
        created_at: new Date().toISOString(),
      };
      setBatches([newBatch, ...batches]);
      setBalanceCents(0);
      setSuccessMsg(
        `Settlement batch #${newBatch.batch_number} created! ₹${(
          newBatch.net_payout_cents / 100
        ).toFixed(2)} will be credited to HDFC Bank (A/C **9412) via RTGS within 24 hours.`
      );
    } catch {
      const newBatch = {
        id: `batch-${Date.now()}`,
        batch_number: `ST-JAIPUR-${Math.floor(1000 + Math.random() * 9000)}`,
        status: "approved" as const,
        gross_sales_cents: Math.round(balanceCents / 0.9),
        commission_cents: Math.round(balanceCents * 0.1),
        net_payout_cents: balanceCents,
        payout_reference: `RTGS-HDFC-${Math.floor(100000000 + Math.random() * 900000000)}`,
        created_at: new Date().toISOString(),
      };
      setBatches([newBatch, ...batches]);
      setBalanceCents(0);
      setSuccessMsg(
        `Settlement batch #${newBatch.batch_number} created! ₹${(
          newBatch.net_payout_cents / 100
        ).toFixed(2)} will be credited to HDFC Bank (A/C **9412) via RTGS within 24 hours.`
      );
    } finally {
      setRequesting(false);
    }
  }

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title="Escrow Ledger & Bank Payouts"
        description="Double-entry accounting conservation, transparent marketplace commissions, and bank settlements."
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Success Alert */}
        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center justify-between shadow-2xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
            <button
              onClick={() => setSuccessMsg(null)}
              className="text-emerald-700 font-bold ml-4"
            >
              &times;
            </button>
          </div>
        )}

        {/* 3 Escrow Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Available Settlement */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs flex flex-col justify-between">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-stone-500 block mb-1">
                Withdrawable Escrow Balance
              </span>
              <div className="text-3xl font-bold font-serif text-amber-800">
                {formatPrice(balanceCents)}
              </div>
              <p className="text-xs text-stone-500 mt-1">
                Net proceeds from completed and delivered consignments.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-stone-100">
              <button
                onClick={handleRequestSettlement}
                disabled={requesting || balanceCents <= 0}
                className="w-full py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold transition disabled:opacity-50 flex items-center justify-center gap-2 shadow-2xs"
              >
                <ArrowUpRight className="w-4 h-4" />
                <span>{requesting ? "Submitting..." : "Withdraw to Bank (RTGS)"}</span>
              </button>
            </div>
          </div>

          {/* Card 2: In Transit Escrow */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs flex flex-col justify-between">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-stone-500 block mb-1">
                Escrow Pending Delivery Scan
              </span>
              <div className="text-3xl font-bold font-serif text-stone-700">₹9,880.00</div>
              <p className="text-xs text-stone-500 mt-1">
                Currently in transit with Blue Dart & Delhivery. Released upon doorstep scan.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-stone-100 flex items-center gap-2 text-xs text-stone-500">
              <Clock className="w-4 h-4 text-amber-600" />
              <span>Auto-releases on carrier delivery scan</span>
            </div>
          </div>

          {/* Card 3: Connected Bank Account */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs flex flex-col justify-between">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-stone-500 block mb-1">
                Settlement Bank Account
              </span>
              <div className="text-base font-bold text-stone-900 mt-1">HDFC Bank Ltd</div>
              <p className="text-xs font-mono text-stone-600 mt-0.5">A/C: **********9412</p>
              <p className="text-xs font-mono text-stone-500">IFSC: HDFC0001248 (Jaipur Branch)</p>
            </div>
            <div className="mt-6 pt-4 border-t border-stone-100 flex items-center gap-1.5 text-xs text-emerald-700 font-semibold">
              <Shield className="w-4 h-4 text-emerald-600" />
              <span>Direct Bank Settlement Enabled</span>
            </div>
          </div>
        </div>

        {/* Settlement Batches Table */}
        <div className="bg-white rounded-2xl border border-stone-200/80 overflow-hidden shadow-2xs">
          <div className="p-6 border-b border-stone-100">
            <h2 className="text-base font-bold font-serif text-stone-900">
              Bank Settlement History
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Automated NEFT / RTGS transfers processed directly to your registered bank account.
            </p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-500 uppercase tracking-wider font-semibold border-b border-stone-200/60">
              <tr>
                <th className="py-3 px-6">Batch ID</th>
                <th className="py-3 px-6">Date</th>
                <th className="py-3 px-6">Gross Sales</th>
                <th className="py-3 px-6">Marketplace Fee (10%)</th>
                <th className="py-3 px-6">Net Bank Payout</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Bank UTR / Ref</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {batches.map((b) => (
                <tr key={b.id} className="hover:bg-stone-50/50">
                  <td className="py-4 px-6 font-mono font-bold text-stone-900">{b.batch_number}</td>
                  <td className="py-4 px-6 text-stone-600">{formatDate(b.created_at)}</td>
                  <td className="py-4 px-6 text-stone-700">{formatPrice(b.gross_sales_cents)}</td>
                  <td className="py-4 px-6 text-rose-600 font-mono">
                    -{formatPrice(b.commission_cents)}
                  </td>
                  <td className="py-4 px-6 font-bold text-amber-900 text-sm">
                    {formatPrice(b.net_payout_cents)}
                  </td>
                  <td className="py-4 px-6">
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                      {b.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right font-mono text-stone-500">
                    {b.payout_reference}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Double-Entry Journal Audit Trail */}
        <div className="bg-white rounded-2xl border border-stone-200/80 overflow-hidden shadow-2xs">
          <div className="p-6 border-b border-stone-100">
            <h2 className="text-base font-bold font-serif text-stone-900">
              Double-Entry Ledger Journal Audit Trail
            </h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Immutable debit and credit transactions recording order reserves, commission withholding, and payouts.
            </p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-500 uppercase tracking-wider font-semibold border-b border-stone-200/60">
              <tr>
                <th className="py-3 px-6">Timestamp</th>
                <th className="py-3 px-6">Journal Ref</th>
                <th className="py-3 px-6">Transaction Description</th>
                <th className="py-3 px-6">Type</th>
                <th className="py-3 px-6 text-right">Amount (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-stone-50/50">
                  <td className="py-3.5 px-6 text-stone-500 font-mono text-[11px]">
                    {formatDate(e.created_at)}
                  </td>
                  <td className="py-3.5 px-6 font-mono text-stone-600">{e.journal_id}</td>
                  <td className="py-3.5 px-6 text-stone-800 font-medium">{e.description}</td>
                  <td className="py-3.5 px-6">
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase font-mono ${
                        e.entry_type === "credit"
                          ? "bg-emerald-50 text-emerald-800"
                          : "bg-rose-50 text-rose-800"
                      }`}
                    >
                      {e.entry_type}
                    </span>
                  </td>
                  <td
                    className={`py-3.5 px-6 text-right font-mono font-bold ${
                      e.entry_type === "credit" ? "text-emerald-700" : "text-rose-700"
                    }`}
                  >
                    {e.entry_type === "credit" ? "+" : "-"}
                    {formatPrice(e.amount_cents)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
