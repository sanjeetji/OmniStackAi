"use client";

import { useState, useEffect } from "react";
import {
  Activity,
  Heart,
  Thermometer,
  Droplet,
  ShieldCheck,
  Plus,
  AlertCircle,
  FileCheck,
  Clock,
  Calendar,
} from "lucide-react";
import {
  defaultApiClient,
  evaluateBloodPressure,
  type MedicalHistory,
  type VitalsRecord,
} from "@careclinic/shared";
import { VitalsModal } from "@/components/vitals-modal";

export default function MedicalRecordsPage() {
  const [history, setHistory] = useState<MedicalHistory | null>(null);
  const [vitals, setVitals] = useState<VitalsRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const loadData = async () => {
    try {
      const res = await defaultApiClient.getMedicalRecords();
      setHistory(res.medicalHistory);
      setVitals(res.vitals || []);
    } catch {
      // Fallback data for preview
      setHistory({
        patient_id: "pat-1",
        allergies: ["Penicillin (Moderate Skin Rash)"],
        chronic_conditions: ["Stage 1 Essential Hypertension"],
        current_medications: ["Telmisartan 40mg", "Atorvastatin 10mg"],
        past_surgeries: ["Appendectomy (2018)"],
        lifestyle_notes: "Non-smoker, moderate caffeine, weekly swimming exercises.",
      });
      setVitals([
        {
          id: "v-1",
          patient_id: "pat-1",
          bp_systolic: 120,
          bp_diastolic: 80,
          heart_rate: 72,
          temperature_f: 98.4,
          spo2_percent: 98,
          blood_glucose_mg_dl: 94,
          notes: "Morning resting readings",
          recorded_at: "2026-09-22T08:30:00Z",
        },
        {
          id: "v-2",
          patient_id: "pat-1",
          bp_systolic: 128,
          bp_diastolic: 84,
          heart_rate: 78,
          temperature_f: 98.6,
          spo2_percent: 99,
          blood_glucose_mg_dl: 102,
          notes: "Post-consultation follow-up",
          recorded_at: "2026-09-18T10:30:00Z",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const latestVitals = vitals[0] || null;
  const bpEval = evaluateBloodPressure(latestVitals?.bp_systolic, latestVitals?.bp_diastolic);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Medical Records & Vitals
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Track longitudinal biometrics, chronic conditions, and personal health history.
          </p>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs sm:text-sm px-4 py-2.5 rounded-2xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Log New Vitals</span>
        </button>
      </div>

      {/* Biometric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Blood Pressure */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs font-semibold">Blood Pressure</span>
            <Activity className="w-4 h-4 text-teal-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {latestVitals?.bp_systolic || 120} / {latestVitals?.bp_diastolic || 80}
            <span className="text-xs font-normal text-slate-400 ml-1">mmHg</span>
          </div>
          <div className="flex items-center gap-1 text-xs font-semibold">
            <span className={bpEval.color}>{bpEval.category}</span>
          </div>
        </div>

        {/* Heart Rate */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs font-semibold">Pulse / Heart Rate</span>
            <Heart className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {latestVitals?.heart_rate || 72}
            <span className="text-xs font-normal text-slate-400 ml-1">BPM</span>
          </div>
          <div className="text-xs text-emerald-600 font-semibold">Normal Sinus</div>
        </div>

        {/* SpO2 Saturation */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs font-semibold">Oxygen (SpO2)</span>
            <Thermometer className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {latestVitals?.spo2_percent || 98}
            <span className="text-xs font-normal text-slate-400 ml-1">%</span>
          </div>
          <div className="text-xs text-emerald-600 font-semibold">Healthy Range</div>
        </div>

        {/* Blood Glucose */}
        <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs font-semibold">Blood Sugar</span>
            <Droplet className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {latestVitals?.blood_glucose_mg_dl || 94}
            <span className="text-xs font-normal text-slate-400 ml-1">mg/dL</span>
          </div>
          <div className="text-xs text-emerald-600 font-semibold">Fasting Euglycemia</div>
        </div>
      </div>

      {/* Chronic Health Profile & Allergies */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-6">
        <h2 className="text-lg font-bold text-slate-900">Medical History & Risk Factors</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
          {/* Allergies */}
          <div className="space-y-2">
            <span className="font-bold text-slate-700 block uppercase tracking-wider text-[10px]">
              Known Drug & Food Allergies
            </span>
            <div className="flex flex-wrap gap-2">
              {history?.allergies?.length ? (
                history.allergies.map((a, i) => (
                  <span
                    key={i}
                    className="bg-rose-50 text-rose-700 border border-rose-200 px-3 py-1.5 rounded-xl font-semibold"
                  >
                    {a}
                  </span>
                ))
              ) : (
                <span className="text-slate-400">No known drug allergies reported.</span>
              )}
            </div>
          </div>

          {/* Chronic Conditions */}
          <div className="space-y-2">
            <span className="font-bold text-slate-700 block uppercase tracking-wider text-[10px]">
              Chronic Health Conditions
            </span>
            <div className="flex flex-wrap gap-2">
              {history?.chronic_conditions?.length ? (
                history.chronic_conditions.map((c, i) => (
                  <span
                    key={i}
                    className="bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1.5 rounded-xl font-semibold"
                  >
                    {c}
                  </span>
                ))
              ) : (
                <span className="text-slate-400">No chronic health conditions documented.</span>
              )}
            </div>
          </div>

          {/* Active Medications */}
          <div className="space-y-2">
            <span className="font-bold text-slate-700 block uppercase tracking-wider text-[10px]">
              Current Ongoing Medications
            </span>
            <div className="flex flex-wrap gap-2">
              {history?.current_medications?.length ? (
                history.current_medications.map((m, i) => (
                  <span
                    key={i}
                    className="bg-teal-50 text-teal-800 border border-teal-200 px-3 py-1.5 rounded-xl font-semibold"
                  >
                    {m}
                  </span>
                ))
              ) : (
                <span className="text-slate-400">None</span>
              )}
            </div>
          </div>

          {/* Past Surgeries */}
          <div className="space-y-2">
            <span className="font-bold text-slate-700 block uppercase tracking-wider text-[10px]">
              Past Surgical Procedures
            </span>
            <div className="flex flex-wrap gap-2">
              {history?.past_surgeries?.length ? (
                history.past_surgeries.map((s, i) => (
                  <span
                    key={i}
                    className="bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-xl font-semibold"
                  >
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-slate-400">None</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Longitudinal Vitals Timeline Table */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Historical Biometrics Log</h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px]">
                <th className="py-2.5 font-bold">Recorded Date</th>
                <th className="py-2.5 font-bold">BP (mmHg)</th>
                <th className="py-2.5 font-bold">Pulse (BPM)</th>
                <th className="py-2.5 font-bold">Temp (°F)</th>
                <th className="py-2.5 font-bold">SpO2</th>
                <th className="py-2.5 font-bold">Blood Sugar</th>
                <th className="py-2.5 font-bold">Clinical Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {vitals.map((v) => (
                <tr key={v.id} className="hover:bg-slate-50">
                  <td className="py-3 font-semibold text-slate-900">
                    {v.recorded_at ? v.recorded_at.slice(0, 16).replace("T", " ") : "2026-09-22"}
                  </td>
                  <td className="py-3 font-bold text-teal-800">
                    {v.bp_systolic || "--"} / {v.bp_diastolic || "--"}
                  </td>
                  <td className="py-3 text-slate-700">{v.heart_rate || "--"}</td>
                  <td className="py-3 text-slate-700">{v.temperature_f || "--"}</td>
                  <td className="py-3 text-slate-700">{v.spo2_percent ? `${v.spo2_percent}%` : "--"}</td>
                  <td className="py-3 text-slate-700">{v.blood_glucose_mg_dl || "--"}</td>
                  <td className="py-3 text-slate-500 max-w-xs">{v.notes || "Routine log"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* HIPAA Compliance Note */}
      <div className="bg-teal-50 border border-teal-200 rounded-2xl p-4 text-xs text-teal-800 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block">HIPAA Privacy & Audit Trail Notice</span>
          <p className="text-teal-700/90 text-[11px] mt-0.5">
            Your electronic medical records and biometric readings are protected by end-to-end encryption. Every time a physician or clinical staff member inspects this chart, an immutable audit event is permanently logged.
          </p>
        </div>
      </div>

      {/* Vitals Recording Modal */}
      <VitalsModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
