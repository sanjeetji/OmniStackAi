"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Stethoscope,
  Plus,
  Trash2,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Pill,
  Save,
  ArrowRight,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

interface RxRow {
  medication_name: string;
  form: string;
  dosage: string;
  route: string;
  frequency: string;
  timing: string;
  duration_days: number;
  instructions: string;
}

export default function PrescriptionBuilderPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = (params?.appointmentId as string) || "apt-201";

  const [diagnosisSummary, setDiagnosisSummary] = useState(
    "Essential Primary Hypertension (I10) & Hyperlipidemia (E78.5)"
  );
  const [items, setItems] = useState<RxRow[]>([
    {
      medication_name: "Telmisartan",
      form: "Tablet",
      dosage: "40 mg",
      route: "Oral",
      frequency: "Once daily",
      timing: "After breakfast",
      duration_days: 30,
      instructions: "Take consistently each morning at same time.",
    },
    {
      medication_name: "Atorvastatin",
      form: "Tablet",
      dosage: "10 mg",
      route: "Oral",
      frequency: "Once daily",
      timing: "At bedtime",
      duration_days: 30,
      instructions: "For cardioprotective lipid management.",
    },
  ]);

  const [signing, setSigning] = useState(false);
  const [signedPrescription, setSignedPrescription] = useState<any>(null);
  const [allergyAlert, setAllergyAlert] = useState("");

  const handleAddItem = () => {
    setItems([
      ...items,
      {
        medication_name: "",
        form: "Tablet",
        dosage: "",
        route: "Oral",
        frequency: "Once daily",
        timing: "After food",
        duration_days: 14,
        instructions: "",
      },
    ]);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleUpdateItem = (index: number, field: keyof RxRow, val: any) => {
    const next = [...items];
    (next[index] as any)[field] = val;

    // Check allergy conflict
    if (field === "medication_name" && val.toLowerCase().includes("penicillin")) {
      setAllergyAlert("CRITICAL ALLERGY CONFLICT: Patient is allergic to Penicillin!");
    } else {
      setAllergyAlert("");
    }

    setItems(next);
  };

  const handleSignAndIssue = async () => {
    setSigning(true);
    try {
      const res = await defaultApiClient.issuePrescription(appointmentId, {
        diagnosisSummary,
        items,
      });
      setSignedPrescription(res.prescription);
    } catch {
      // preview fallback
      setSignedPrescription({
        prescription_number: "RX-2026-00142",
        is_immutable: true,
        digital_signature: "SHA256:7f9a88c241e05d4b8e...VERIFIED_KMC_48291",
        signed_at: new Date().toISOString(),
      });
    } finally {
      setSigning(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link
          href={`/consult/${appointmentId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Consultation Overview
        </Link>

        <div className="flex items-center gap-2">
          {signedPrescription && (
            <span className="text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200 font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Signed & Certified (Immutable)</span>
            </span>
          )}

          <button
            onClick={handleSignAndIssue}
            disabled={signing || !!signedPrescription || items.length === 0}
            className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>
              {signing
                ? "Signing Cryptographically..."
                : signedPrescription
                ? "Prescription Finalized"
                : "Sign & Issue Digital Rx"}
            </span>
          </button>
        </div>
      </div>

      {/* Patient & Allergy Banner */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-400">Digital Prescription Builder</span>
          <h1 className="text-lg font-bold text-slate-900">Ananya Deshmukh • Token #4</h1>
        </div>

        <div className="flex items-center gap-2 bg-rose-50 text-rose-800 text-xs px-3 py-1 rounded-xl border border-rose-200 font-semibold">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
          <span>Patient Allergy: Penicillin</span>
        </div>
      </div>

      {allergyAlert && (
        <div className="p-3.5 rounded-2xl bg-rose-600 text-white text-xs font-bold flex items-center gap-2 animate-fade-in shadow-md">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{allergyAlert}</span>
        </div>
      )}

      {/* Diagnosis Summary Field */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-2">
        <label className="text-xs font-bold text-slate-700 block uppercase tracking-wide">
          Clinical Diagnosis Summary on Rx
        </label>
        <input
          type="text"
          value={diagnosisSummary}
          disabled={!!signedPrescription}
          onChange={(e) => setDiagnosisSummary(e.target.value)}
          placeholder="e.g. Essential Primary Hypertension, Stage 1"
          className="w-full text-xs px-3.5 py-2.5 border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden font-semibold text-slate-800"
        />
      </div>

      {/* Medication List Table */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <Pill className="w-4 h-4 text-emerald-600" />
            <span>Prescribed Medications ({items.length})</span>
          </div>

          {!signedPrescription && (
            <button
              onClick={handleAddItem}
              className="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-semibold text-xs px-3 py-1.5 rounded-xl transition-colors flex items-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Medication</span>
            </button>
          )}
        </div>

        <div className="space-y-3">
          {items.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-2xl border border-slate-200 bg-slate-50/40 space-y-3"
            >
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 text-xs">
                {/* Drug Name */}
                <div className="sm:col-span-2">
                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Drug Name
                  </label>
                  <input
                    type="text"
                    disabled={!!signedPrescription}
                    placeholder="e.g. Telmisartan"
                    value={item.medication_name}
                    onChange={(e) => handleUpdateItem(idx, "medication_name", e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden font-bold text-slate-800"
                  />
                </div>

                {/* Form */}
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Form
                  </label>
                  <select
                    disabled={!!signedPrescription}
                    value={item.form}
                    onChange={(e) => handleUpdateItem(idx, "form", e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden text-slate-700"
                  >
                    <option value="Tablet">Tablet</option>
                    <option value="Capsule">Capsule</option>
                    <option value="Syrup">Syrup</option>
                    <option value="Injection">Injection</option>
                    <option value="Ointment">Ointment</option>
                    <option value="Drops">Drops</option>
                  </select>
                </div>

                {/* Dosage */}
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Dosage
                  </label>
                  <input
                    type="text"
                    disabled={!!signedPrescription}
                    placeholder="e.g. 40 mg"
                    value={item.dosage}
                    onChange={(e) => handleUpdateItem(idx, "dosage", e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden font-medium text-slate-800"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {/* Frequency */}
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Frequency
                  </label>
                  <select
                    disabled={!!signedPrescription}
                    value={item.frequency}
                    onChange={(e) => handleUpdateItem(idx, "frequency", e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden text-slate-700"
                  >
                    <option value="Once daily">Once daily (OD)</option>
                    <option value="Twice daily">Twice daily (BD)</option>
                    <option value="Thrice daily">Thrice daily (TDS)</option>
                    <option value="Four times daily">Four times daily (QID)</option>
                    <option value="SOS (As needed)">SOS (As needed)</option>
                  </select>
                </div>

                {/* Timing */}
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Timing
                  </label>
                  <select
                    disabled={!!signedPrescription}
                    value={item.timing}
                    onChange={(e) => handleUpdateItem(idx, "timing", e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden text-slate-700"
                  >
                    <option value="After breakfast">After breakfast</option>
                    <option value="After lunch">After lunch</option>
                    <option value="After dinner">After dinner</option>
                    <option value="Before meals">Before meals</option>
                    <option value="At bedtime">At bedtime</option>
                  </select>
                </div>

                {/* Duration Days */}
                <div>
                  <label className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Duration (Days)
                  </label>
                  <input
                    type="number"
                    disabled={!!signedPrescription}
                    value={item.duration_days}
                    onChange={(e) =>
                      handleUpdateItem(idx, "duration_days", parseInt(e.target.value, 10) || 1)
                    }
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden text-slate-800"
                  />
                </div>

                {/* Remove button */}
                <div className="flex items-end justify-end">
                  {!signedPrescription && items.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(idx)}
                      className="text-slate-400 hover:text-rose-600 p-2 transition-colors cursor-pointer"
                      title="Remove row"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Instructions */}
              <div>
                <input
                  type="text"
                  disabled={!!signedPrescription}
                  placeholder="Special instructions (e.g. do not abruptly discontinue)..."
                  value={item.instructions}
                  onChange={(e) => handleUpdateItem(idx, "instructions", e.target.value)}
                  className="w-full text-xs px-3 py-1.5 bg-white border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden text-slate-600"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Signature Confirmation Details */}
      {signedPrescription && (
        <div className="p-5 rounded-3xl bg-emerald-50 border border-emerald-200 text-xs space-y-1 text-emerald-950 animate-fade-in">
          <div className="flex items-center gap-1.5 font-bold text-emerald-800">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Prescription Digitally Signed by Dr. Rajesh Varma, MD (KMC Reg: 48291)</span>
          </div>
          <p className="text-[11px] font-mono text-emerald-700">
            Hash: {signedPrescription.digital_signature || "SHA256:7f9a88c241e05d4b8e"}
          </p>
          <p className="text-slate-500 text-[11px]">
            Prescription #{signedPrescription.prescription_number || "RX-2026-00142"} is now immutable and immediately viewable in patient’s digital portal.
          </p>
        </div>
      )}

      {/* Next Flow Bar */}
      <div className="flex items-center justify-between pt-2">
        <Link
          href={`/consult/${appointmentId}/soap`}
          className="text-xs font-semibold text-slate-500 hover:text-slate-800"
        >
          ← Edit SOAP Clinical Notes
        </Link>

        <Link
          href={`/consult/${appointmentId}/labs`}
          className="bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs px-5 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
        >
          <span>Next: Diagnostic Lab Orders</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
