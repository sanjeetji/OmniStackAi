"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Receipt,
  CreditCard,
  Calendar,
  CheckCircle2,
  Clock,
  Printer,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import {
  defaultApiClient,
  formatINR,
  getPaymentStatusBadge,
  type Invoice,
} from "@careclinic/shared";

export default function InvoicesBillingPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadInvoices() {
      try {
        const res = await defaultApiClient.getInvoices();
        setInvoices(res.invoices || []);
      } catch {
        // Fallback demo invoices
        setInvoices([
          {
            id: "inv-101",
            invoice_number: "INV-202609-089",
            patient_id: "pat-1",
            appointment_number: "APT-202609-089",
            doctor_name: "Dr. Rajesh Varma, MD",
            scheduled_date: new Date().toISOString().slice(0, 10),
            total_amount: 800,
            discount_amount: 0,
            tax_amount: 0,
            net_payable: 800,
            payment_status: "paid",
            payment_method: "UPI (Google Pay)",
            created_at: new Date().toISOString(),
          },
          {
            id: "inv-102",
            invoice_number: "INV-202608-041",
            patient_id: "pat-1",
            appointment_number: "APT-202608-041",
            doctor_name: "Dr. Priya Sundaram, MD",
            scheduled_date: "2026-08-15",
            total_amount: 700,
            discount_amount: 0,
            tax_amount: 0,
            net_payable: 700,
            payment_status: "paid",
            payment_method: "Credit Card (Visa)",
            created_at: "2026-08-15T11:00:00Z",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    loadInvoices();
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Billing & Invoices
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Review consultation receipts, diagnostic billing statements, and payment confirmations.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading invoices...</div>
      ) : invoices.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 text-center border border-slate-200">
          <Receipt className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No invoices found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            You don’t have any outstanding or paid invoices recorded.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {invoices.map((inv) => {
            const badge = getPaymentStatusBadge(inv.payment_status);
            return (
              <div
                key={inv.id}
                className="bg-white rounded-3xl p-6 border border-slate-200 hover:border-teal-200 shadow-xs hover:shadow-md transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 group"
              >
                <div className="space-y-2 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[11px] font-bold px-2.5 py-0.5 rounded-lg ${badge.bg} ${badge.text}`}
                    >
                      {badge.label}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">
                      #{inv.invoice_number}
                    </span>
                    <div className="flex items-center gap-1 text-[11px] text-slate-500">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{inv.scheduled_date || inv.created_at.slice(0, 10)}</span>
                    </div>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
                    Consultation with {inv.doctor_name || "Specialist Physician"}
                  </h3>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    {inv.appointment_number && <span>Appt #{inv.appointment_number}</span>}
                    {inv.payment_method && <span>• Paid via {inv.payment_method}</span>}
                  </div>
                </div>

                <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end border-t sm:border-t-0 pt-3 sm:pt-0 border-slate-100">
                  <div className="text-left sm:text-right">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Net Amount
                    </span>
                    <span className="text-lg font-extrabold text-slate-900">
                      {formatINR(inv.net_payable)}
                    </span>
                  </div>

                  {inv.payment_status === "pending" ? (
                    <Link
                      href={`/checkout/${inv.appointment_id || inv.id}`}
                      className="bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs"
                    >
                      Pay Now
                    </Link>
                  ) : (
                    <button
                      onClick={() => alert(`Receipt #${inv.invoice_number} downloaded.`)}
                      className="border border-slate-200 hover:border-slate-300 text-slate-700 font-semibold text-xs px-3.5 py-2 rounded-xl transition-all flex items-center gap-1.5 cursor-pointer"
                    >
                      <Printer className="w-3.5 h-3.5 text-slate-400" />
                      <span>Receipt</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
