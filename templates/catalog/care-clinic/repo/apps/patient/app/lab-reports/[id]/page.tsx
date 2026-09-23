"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  FlaskConical,
  Printer,
  ShieldCheck,
  Calendar,
  Building2,
  AlertTriangle,
  CheckCircle2,
  ArrowLeft,
} from "lucide-react";
import { defaultApiClient, type LabOrderItem } from "@careclinic/shared";

export default function LabReportDetailPage() {
  const params = useParams();
  const orderId = (params?.id as string) || "lo-demo";

  const [order, setOrder] = useState<any>(null);
  const [items, setItems] = useState<LabOrderItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadReport() {
      try {
        const res = await defaultApiClient.getLabReports();
        const found = res.orders?.find((o) => o.id === orderId);
        if (found) {
          setOrder(found);
          setItems(res.items?.filter((i) => i.lab_order_id === orderId) || []);
        } else {
          throw new Error("Not found");
        }
      } catch {
        // Fallback demo lab report
        setOrder({
          id: orderId,
          order_number: "LAB-2026-00104",
          patient_id: "pat-1",
          patient_name: "Ananya Deshmukh",
          patient_age: 32,
          patient_gender: "Female",
          doctor_name: "Dr. Rajesh Varma, MD",
          doctor_spec: "Cardiology",
          status: "completed",
          created_at: "2026-09-18T10:50:00Z",
          collected_at: "2026-09-18T11:15:00Z",
          reported_at: "2026-09-18T16:00:00Z",
        });
        setItems([
          {
            id: "loi-1",
            lab_order_id: orderId,
            test_id: "t1",
            test_name: "Total Cholesterol",
            category: "Lipid Profile",
            result_value: "182",
            reference_range: "< 200",
            unit: "mg/dL",
            flag: "normal" as const,
            technician_notes: "Desirable range",
          },
          {
            id: "loi-2",
            lab_order_id: orderId,
            test_id: "t2",
            test_name: "HDL Cholesterol (Good)",
            category: "Lipid Profile",
            result_value: "54",
            reference_range: "> 50",
            unit: "mg/dL",
            flag: "normal" as const,
            technician_notes: "Optimal protective level",
          },
          {
            id: "loi-3",
            lab_order_id: orderId,
            test_id: "t3",
            test_name: "LDL Cholesterol (Bad)",
            category: "Lipid Profile",
            result_value: "108",
            reference_range: "< 100",
            unit: "mg/dL",
            flag: "high" as const,
            technician_notes: "Borderline elevated; dietary modification recommended",
          },
          {
            id: "loi-4",
            lab_order_id: orderId,
            test_id: "t4",
            test_name: "Triglycerides",
            category: "Lipid Profile",
            result_value: "135",
            reference_range: "< 150",
            unit: "mg/dL",
            flag: "normal" as const,
            technician_notes: "Normal",
          },
          {
            id: "loi-5",
            lab_order_id: orderId,
            test_id: "t5",
            test_name: "Fasting Blood Glucose",
            category: "Biochemistry",
            result_value: "94",
            reference_range: "70 - 99",
            unit: "mg/dL",
            flag: "normal" as const,
            technician_notes: "Normal fasting euglycemia",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    if (orderId) {
      loadReport();
    }
  }, [orderId]);

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  if (!order) {
    return (
      <div className="max-w-3xl mx-auto p-12 text-center text-xs text-slate-500">
        Loading diagnostic report...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Bar Actions */}
      <div className="flex items-center justify-between no-print">
        <Link
          href="/lab-reports"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-teal-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Lab Reports
        </Link>

        <button
          onClick={handlePrint}
          className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
        >
          <Printer className="w-4 h-4" />
          <span>Print / Save PDF</span>
        </button>
      </div>

      {/* Official Lab Report Sheet */}
      <div className="bg-white rounded-3xl p-8 sm:p-12 border border-slate-200 shadow-md space-y-8 print:p-0 print:border-none print:shadow-none">
        {/* Lab Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b-2 border-teal-600 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-teal-600 text-white flex items-center justify-center font-bold">
              <FlaskConical className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                CareClinic Diagnostic Laboratories
              </h1>
              <p className="text-xs text-slate-500">
                100 Feet Road, Indiranagar, Bengaluru • Ph: +91 80 4912 3010
              </p>
              <div className="flex items-center gap-1 text-[10px] text-teal-800 font-bold uppercase tracking-wider mt-0.5">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span>NABL Accredited Medical Testing Laboratory (MC-2490)</span>
              </div>
            </div>
          </div>

          <div className="text-left sm:text-right">
            <div className="text-xs font-mono font-bold text-teal-800 bg-teal-50 px-3 py-1 rounded-lg border border-teal-200">
              {order.order_number}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Reported: <strong>{order.reported_at ? order.reported_at.slice(0, 10) : "2026-09-18"}</strong>
            </div>
          </div>
        </div>

        {/* Patient & Doctor Demographics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-5 rounded-2xl border border-slate-100 text-xs">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Patient Information
            </span>
            <div className="text-sm font-bold text-slate-900">Ananya Deshmukh</div>
            <div className="text-slate-600">Age: 32 Yrs • Gender: Female • UHID: CC-PAT-001</div>
            <div className="text-slate-500 mt-1">Sample Collected: Venous Blood (EDTA / Fluoride)</div>
          </div>

          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Referred By Physician
            </span>
            <div className="text-sm font-bold text-slate-900">{order.doctor_name || "Dr. Rajesh Varma, MD"}</div>
            <div className="text-slate-600">Department of Cardiology • CareClinic</div>
            <div className="text-slate-500 mt-1">Clinical Indication: {order.clinical_indication}</div>
          </div>
        </div>

        {/* Diagnostic Parameters Table */}
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
            Test Results & Reference Ranges
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200 text-slate-500 uppercase text-[10px]">
                  <th className="py-2.5 font-bold">Investigation Parameter</th>
                  <th className="py-2.5 font-bold">Observed Value</th>
                  <th className="py-2.5 font-bold">Unit</th>
                  <th className="py-2.5 font-bold">Biological Reference Range</th>
                  <th className="py-2.5 font-bold">Clinical Interpretation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/60">
                    <td className="py-3 font-semibold text-slate-900">
                      <div>{item.test_name}</div>
                      <div className="text-[10px] text-slate-400">{item.category}</div>
                    </td>
                    <td className="py-3 font-bold">
                      <span
                        className={
                          item.flag !== "normal" ? "text-rose-600 font-extrabold" : "text-slate-900"
                        }
                      >
                        {item.result_value}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500">{item.unit || "--"}</td>
                    <td className="py-3 text-slate-600 font-mono">{item.reference_range || "--"}</td>
                    <td className="py-3 text-xs">
                      {item.flag !== "normal" ? (
                        <span className="inline-flex items-center gap-1 text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-semibold text-[11px] border border-rose-100">
                          <AlertTriangle className="w-3 h-3 text-rose-600" />
                          <span>Abnormal ({item.technician_notes ?? item.flag})</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-semibold text-[11px]">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Normal</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pathologist Sign-off */}
        <div className="pt-8 border-t border-slate-200 flex flex-col sm:flex-row items-start sm:items-end justify-between gap-6">
          <div className="space-y-1 text-[11px] text-slate-500">
            <div className="flex items-center gap-1 text-emerald-700 font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Certified NABL Medical Laboratory Sign-Off</span>
            </div>
            <p>Verification Code: LAB-NABL-SECURE-2026</p>
            <p>Report End of Transmission</p>
          </div>

          <div className="text-left sm:text-right space-y-1">
            <div className="text-sm font-bold text-slate-900">Dr. Sunita Rao, MD (Pathology)</div>
            <div className="text-xs text-teal-700 font-medium">Head of Clinical Biochemistry</div>
            <div className="text-[10px] text-slate-400">CareClinic Central Diagnostic Facility</div>
          </div>
        </div>
      </div>
    </div>
  );
}
