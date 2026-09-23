"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FlaskConical,
  CheckCircle2,
  Clock,
  ArrowLeft,
  Check,
  AlertCircle,
  FileCheck,
} from "lucide-react";
import { defaultApiClient, formatINR } from "@careclinic/shared";

interface LabTestCatalogItem {
  code: string;
  name: string;
  category: string;
  turnaround_hours: number;
  standard_fee_inr: number;
  sample: string;
}

export default function LabOrderGeneratorPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = (params?.appointmentId as string) || "apt-201";

  const [catalog, setCatalog] = useState<LabTestCatalogItem[]>([
    {
      code: "LIPID-01",
      name: "Comprehensive Lipid Profile",
      category: "Biochemistry",
      turnaround_hours: 6,
      standard_fee_inr: 650,
      sample: "Fasting Venous Blood",
    },
    {
      code: "FBS-01",
      name: "Fasting Blood Glucose (FBS)",
      category: "Biochemistry",
      turnaround_hours: 4,
      standard_fee_inr: 150,
      sample: "Sodium Fluoride Blood",
    },
    {
      code: "HBA1C-01",
      name: "Glycated Hemoglobin (HbA1c)",
      category: "Biochemistry",
      turnaround_hours: 6,
      standard_fee_inr: 500,
      sample: "EDTA Whole Blood",
    },
    {
      code: "CBC-01",
      name: "Complete Blood Count with ESR",
      category: "Hematology",
      turnaround_hours: 4,
      standard_fee_inr: 350,
      sample: "EDTA Whole Blood",
    },
    {
      code: "RFT-01",
      name: "Renal Function Test (Creatinine & Urea)",
      category: "Biochemistry",
      turnaround_hours: 6,
      standard_fee_inr: 550,
      sample: "Serum",
    },
    {
      code: "TSH-01",
      name: "Thyroid Stimulating Hormone (TSH)",
      category: "Endocrinology",
      turnaround_hours: 8,
      standard_fee_inr: 400,
      sample: "Serum",
    },
    {
      code: "ECG-01",
      name: "12-Lead Diagnostic Resting ECG",
      category: "Cardiology Diagnostics",
      turnaround_hours: 1,
      standard_fee_inr: 450,
      sample: "Physiological Recording",
    },
  ]);

  const [selectedCodes, setSelectedCodes] = useState<string[]>(["LIPID-01", "FBS-01", "ECG-01"]);
  const [indication, setIndication] = useState("Hypertension risk stratification and exertional evaluation.");
  const [isUrgent, setIsUrgent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [createdOrder, setCreatedOrder] = useState<any>(null);

  const toggleTest = (code: string) => {
    if (selectedCodes.includes(code)) {
      setSelectedCodes(selectedCodes.filter((c) => c !== code));
    } else {
      setSelectedCodes([...selectedCodes, code]);
    }
  };

  const handleOrder = async () => {
    if (selectedCodes.length === 0) return;
    setSubmitting(true);

    try {
      const res = await defaultApiClient.orderLabs(appointmentId, selectedCodes);
      setCreatedOrder(res.order);
    } catch {
      // preview fallback
      setCreatedOrder({
        order_number: "LAB-2026-00105",
        status: "ordered",
        created_at: new Date().toISOString(),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const totalFee = selectedCodes.reduce((sum, code) => {
    const item = catalog.find((c) => c.code === code);
    return sum + (item?.standard_fee_inr || 0);
  }, 0);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          href={`/consult/${appointmentId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Consultation Overview
        </Link>

        {createdOrder && (
          <span className="text-xs text-purple-800 bg-purple-50 px-3 py-1 rounded-xl border border-purple-200 font-bold flex items-center gap-1.5 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-purple-600" />
            <span>Order #{createdOrder.order_number} Dispatched to Lab</span>
          </span>
        )}
      </div>

      {/* Patient Card */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-2xs flex items-center justify-between">
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-400">Diagnostic Laboratory Requisition</span>
          <h1 className="text-lg font-bold text-slate-900">Ananya Deshmukh • Token #4</h1>
        </div>
        <div className="text-right text-xs text-slate-500">
          <span>In-House Laboratory • CareClinic Indiranagar</span>
        </div>
      </div>

      {/* Clinical Indication */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-slate-700 block uppercase tracking-wide">
            Clinical Indication / Diagnosis Notes
          </label>
          <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700">
            <input
              type="checkbox"
              checked={isUrgent}
              onChange={(e) => setIsUrgent(e.target.checked)}
              className="text-rose-600 rounded"
            />
            <span className={isUrgent ? "text-rose-600 font-bold" : ""}>Urgent / Stat Priority</span>
          </label>
        </div>
        <textarea
          rows={2}
          value={indication}
          onChange={(e) => setIndication(e.target.value)}
          placeholder="Reason for diagnostic workup..."
          className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:border-purple-500 focus:outline-hidden"
        />
      </div>

      {/* Test Catalog Multi-Select */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <FlaskConical className="w-4 h-4 text-purple-600" />
            <span>Available Diagnostic Test Catalog</span>
          </div>
          <span className="text-xs font-semibold text-purple-700">
            {selectedCodes.length} Tests Selected ({formatINR(totalFee)})
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {catalog.map((t) => {
            const isSelected = selectedCodes.includes(t.code);
            return (
              <div
                key={t.code}
                onClick={() => !createdOrder && toggleTest(t.code)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-start justify-between gap-3 ${
                  isSelected
                    ? "bg-purple-50/70 border-purple-300 ring-1 ring-purple-200"
                    : "bg-white border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900">{t.name}</span>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Category: {t.category} • Sample: {t.sample}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-purple-800 font-semibold pt-0.5">
                    <Clock className="w-3 h-3 text-purple-600" />
                    <span>Report in {t.turnaround_hours} hours</span>
                  </div>
                </div>

                <div className="flex flex-col items-end justify-between h-full shrink-0">
                  <span className="text-xs font-extrabold text-slate-900">
                    {formatINR(t.standard_fee_inr)}
                  </span>
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center mt-3 border transition-colors ${
                      isSelected
                        ? "bg-purple-600 border-purple-600 text-white"
                        : "border-slate-300 bg-white"
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Order Dispatch Action */}
      <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500">
            Selected tests will be routed to CareClinic Pathology & Phlebotomy queue.
          </div>
          <div className="text-sm font-bold text-slate-900 mt-0.5">
            Total Diagnostic Fees: {formatINR(totalFee)}
          </div>
        </div>

        <button
          onClick={handleOrder}
          disabled={submitting || selectedCodes.length === 0 || !!createdOrder}
          className="w-full sm:w-auto bg-purple-600 hover:bg-purple-700 disabled:bg-slate-300 text-white font-bold text-xs sm:text-sm px-6 py-3 rounded-2xl transition-all shadow-md cursor-pointer flex items-center justify-center gap-2"
        >
          <FlaskConical className="w-4 h-4" />
          <span>
            {submitting
              ? "Dispatching Order..."
              : createdOrder
              ? "Requisition Dispatched"
              : `Confirm Lab Order (${selectedCodes.length} Tests)`}
          </span>
        </button>
      </div>
    </div>
  );
}
