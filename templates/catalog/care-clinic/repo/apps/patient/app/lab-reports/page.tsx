"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  FlaskConical,
  Calendar,
  CheckCircle2,
  Clock,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { defaultApiClient, type LabOrder, type LabOrderItem } from "@careclinic/shared";

export default function DiagnosticLabReportsPage() {
  const [orders, setOrders] = useState<LabOrder[]>([]);
  const [items, setItems] = useState<LabOrderItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadLabs() {
      try {
        const res = await defaultApiClient.getLabReports();
        setOrders(res.orders || []);
        setItems(res.items || []);
      } catch {
        // Fallback demo lab orders
        setOrders([
          {
            id: "lo-1",
            order_number: "LAB-2026-00104",
            patient_id: "pat-1",
            doctor_id: "doc-1",
            doctor_name: "Dr. Rajesh Varma, MD",
            status: "completed",
            created_at: "2026-09-18T10:50:00Z",
          },
          {
            id: "lo-2",
            order_number: "LAB-2026-00082",
            patient_id: "pat-1",
            doctor_id: "doc-4",
            doctor_name: "Dr. Priya Sundaram, MD",
            status: "completed",
            created_at: "2026-08-15T11:30:00Z",
          },
        ]);
        setItems([
          {
            id: "loi-1",
            lab_order_id: "lo-1",
            test_id: "test-lipid",
            test_name: "Lipid Profile Comprehensive",
            category: "Biochemistry",
            result_value: "Normal",
            flag: "normal" as const,
          },
          {
            id: "loi-2",
            lab_order_id: "lo-1",
            test_id: "test-fbs",
            test_name: "Fasting Blood Glucose",
            category: "Biochemistry",
            result_value: "94 mg/dL",
            flag: "normal" as const,
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    loadLabs();
  }, []);

  const getOrderStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return { label: "Results Ready", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" };
      case "processing":
        return { label: "In Laboratory", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" };
      case "collected":
        return { label: "Sample Collected", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" };
      default:
        return { label: "Ordered", bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" };
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Diagnostic Lab Reports
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          NABL-accredited diagnostic test results, physiological ranges, and pathologist sign-offs.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading diagnostic records...</div>
      ) : orders.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 text-center border border-slate-200">
          <FlaskConical className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No diagnostic orders found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            You don’t have any diagnostic laboratory tests requested or conducted yet.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => {
            const badge = getOrderStatusBadge(order.status);
            const orderItems = items.filter((i) => i.lab_order_id === order.id);

            return (
              <div
                key={order.id}
                className="bg-white rounded-3xl p-6 border border-slate-200 hover:border-teal-200 shadow-xs hover:shadow-md transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 group"
              >
                <div className="space-y-2 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[11px] font-bold px-2.5 py-0.5 rounded-lg border ${badge.bg} ${badge.text} ${badge.border}`}
                    >
                      {badge.label}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">
                      #{order.order_number}
                    </span>
                    <div className="flex items-center gap-1 text-[11px] text-slate-500">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{order.created_at.slice(0, 10)}</span>
                    </div>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
                    Ordered by {order.doctor_name || "Physician"}
                  </h3>

                  {order.completed_at && (
                    <p className="text-xs text-slate-600 leading-relaxed">
                      Reported on {new Date(order.completed_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                    </p>
                  )}

                  {/* Test items preview */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {orderItems.map((item) => (
                      <span
                        key={item.id}
                        className="bg-slate-100 text-slate-700 text-[11px] font-medium px-2.5 py-0.5 rounded-md"
                      >
                        {item.test_name || "Diagnostic Test"}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="shrink-0 w-full sm:w-auto flex justify-end">
                  <Link
                    href={`/lab-reports/${order.id}`}
                    className="bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
                  >
                    <span>View Report</span>
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
