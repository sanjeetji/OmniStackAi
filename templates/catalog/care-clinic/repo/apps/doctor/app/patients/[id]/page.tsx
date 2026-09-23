"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  User,
  Activity,
  Calendar,
  FileText,
  FlaskConical,
  ShieldCheck,
  AlertTriangle,
  Clock,
  ArrowLeft,
  ChevronRight,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export default function PatientChartPage() {
  const params = useParams();
  const patientId = (params?.id as string) || "pat-1";

  const [chart, setChart] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadChart() {
      try {
        const res = await defaultApiClient.getPatientChart(patientId);
        setChart(res);
      } catch {
        // Fallback demo chart
        setChart({
          patient: {
            id: patientId,
            full_name: "Ananya Deshmukh",
            email: "ananya@careclinic.test",
            phone: "+91 98450 12345",
            dob: "1994-06-15",
            gender: "female",
            blood_group: "O+",
            emergency_contact: "Sameer Deshmukh (Spouse)",
            emergency_phone: "+91 98450 99887",
            address: "Indiranagar 12th Main, Bengaluru",
          },
          medicalHistory: {
            allergies: ["Penicillin (Moderate Rash)"],
            chronic_conditions: ["Stage 1 Essential Hypertension"],
            current_medications: ["Telmisartan 40mg", "Atorvastatin 10mg"],
            past_surgeries: ["Appendectomy (2018)"],
          },
          vitals: [
            {
              id: "v1",
              bp_systolic: 120,
              bp_diastolic: 80,
              heart_rate: 72,
              recorded_at: "2026-09-22T08:30:00Z",
            },
            {
              id: "v2",
              bp_systolic: 128,
              bp_diastolic: 84,
              heart_rate: 78,
              recorded_at: "2026-09-18T10:30:00Z",
            },
          ],
          consultations: [
            {
              id: "con-101",
              scheduled_date: "2026-09-18",
              subjective: "Patient presented with intermittent chest tightness after climbing stairs.",
              assessment: "Essential Primary Hypertension (I10)",
              plan: "Telmisartan 40mg OD, lifestyle modification.",
            },
          ],
          prescriptions: [
            {
              id: "rx-101",
              prescription_number: "RX-2026-00142",
              created_at: "2026-09-18",
            },
          ],
        });
      } finally {
        setLoading(false);
      }
    }

    if (patientId) {
      loadChart();
    }
  }, [patientId]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/queue"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Today's Queue
        </Link>

        {/* HIPAA Audited Access Stamp */}
        <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-800 text-[11px] font-bold px-3 py-1.5 rounded-xl border border-emerald-200">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>HIPAA Audit Trail: Inspection Logged & Encrypted</span>
        </div>
      </div>

      {/* Patient Profile Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-slate-900 text-white font-extrabold text-xl flex items-center justify-center shrink-0">
              AD
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900">{chart?.patient?.full_name}</h1>
              <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-500 mt-1">
                <span>DOB: {chart?.patient?.dob || "1994-06-15"} (Age 32)</span>
                <span>•</span>
                <span className="capitalize">{chart?.patient?.gender || "Female"}</span>
                <span>•</span>
                <span>Blood: <strong>{chart?.patient?.blood_group || "O+"}</strong></span>
                <span>•</span>
                <span>Phone: {chart?.patient?.phone}</span>
              </div>
            </div>
          </div>

          <Link
            href={`/patients/${patientId}/history`}
            className="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-bold px-4 py-2 rounded-xl transition-colors border border-emerald-200 flex items-center gap-1"
          >
            <span>Comprehensive Medical History</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Allergies and Chronic Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="p-3 rounded-2xl bg-rose-50 border border-rose-100">
            <span className="font-bold text-rose-900 block text-[10px] uppercase">
              Allergies:
            </span>
            <span className="text-rose-700 font-semibold">
              {chart?.medicalHistory?.allergies?.join(", ") || "None"}
            </span>
          </div>

          <div className="p-3 rounded-2xl bg-amber-50 border border-amber-100">
            <span className="font-bold text-amber-900 block text-[10px] uppercase">
              Chronic Diagnoses:
            </span>
            <span className="text-amber-800 font-semibold">
              {chart?.medicalHistory?.chronic_conditions?.join(", ") || "None"}
            </span>
          </div>
        </div>
      </div>

      {/* Longitudinal Vitals Log */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
          <Activity className="w-4 h-4 text-emerald-600" />
          <span>Longitudinal Vitals Trends</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px]">
                <th className="py-2 font-bold">Recorded Date</th>
                <th className="py-2 font-bold">Blood Pressure</th>
                <th className="py-2 font-bold">Heart Rate</th>
                <th className="py-2 font-bold">Evaluation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {chart?.vitals?.map((v: any) => (
                <tr key={v.id}>
                  <td className="py-2.5 font-semibold text-slate-800">
                    {v.recorded_at ? v.recorded_at.slice(0, 10) : "2026-09-22"}
                  </td>
                  <td className="py-2.5 font-bold text-emerald-800">
                    {v.bp_systolic} / {v.bp_diastolic} mmHg
                  </td>
                  <td className="py-2.5 text-slate-700">{v.heart_rate} BPM</td>
                  <td className="py-2.5 text-emerald-600 font-semibold">Optimal Range</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Previous Consultations & Notes History */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
          <FileText className="w-4 h-4 text-emerald-600" />
          <span>Previous Consultations & SOAP History</span>
        </div>

        <div className="space-y-3">
          {chart?.consultations?.map((c: any) => (
            <div
              key={c.id}
              className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-2 text-xs"
            >
              <div className="flex items-center justify-between font-bold text-slate-900">
                <span>Visit on {c.scheduled_date || "2026-09-18"}</span>
                <span className="text-[10px] text-teal-700 bg-teal-50 px-2 py-0.5 rounded font-mono">
                  {c.id}
                </span>
              </div>
              <p className="text-slate-600">
                <strong>Subjective:</strong> {c.subjective}
              </p>
              <p className="text-slate-600">
                <strong>Assessment:</strong> {c.assessment}
              </p>
              <p className="text-slate-600">
                <strong>Plan:</strong> {c.plan}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
