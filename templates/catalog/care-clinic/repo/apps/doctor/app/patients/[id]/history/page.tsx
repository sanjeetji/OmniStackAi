"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  AlertTriangle,
  Heart,
  Pill,
  Scissors,
  Users,
  ShieldCheck,
  ArrowLeft,
  Plus,
} from "lucide-react";

export default function ComprehensiveMedicalHistoryPage() {
  const params = useParams();
  const patientId = (params?.id as string) || "pat-1";

  const [history, setHistory] = useState({
    allergies: [
      { name: "Penicillin", reaction: "Moderate skin rash & angioedema", verified: true },
      { name: "Sulfa Drugs", reaction: "Mild gastrointestinal upset", verified: false },
    ],
    chronicConditions: [
      { condition: "Stage 1 Essential Hypertension", diagnosedYear: 2024, status: "Active (Managed)" },
      { condition: "Dyslipidemia", diagnosedYear: 2025, status: "Diet & Statin controlled" },
    ],
    activeMedications: [
      { name: "Telmisartan", dose: "40 mg", freq: "Once daily" },
      { name: "Atorvastatin", dose: "10 mg", freq: "Once daily at bedtime" },
    ],
    pastSurgeries: [
      { procedure: "Appendectomy (Laparoscopic)", year: 2018, hospital: "Manipal Hospital" },
    ],
    familyHistory: [
      { relative: "Father", conditions: "Hypertension, Coronary Artery Disease (Onset age 62)" },
      { relative: "Mother", conditions: "Type 2 Diabetes Mellitus" },
    ],
    lifestyle: {
      smoking: "Never smoker",
      alcohol: "Occasional social wine",
      diet: "Predominantly vegetarian, low sodium",
      physicalActivity: "Brisk walking 30 mins, 4 days/week",
    },
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          href={`/patients/${patientId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Patient Chart
        </Link>

        <span className="text-xs text-slate-400">UHID: CC-PAT-001</span>
      </div>

      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs flex items-center justify-between">
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-400">Comprehensive Clinical History</span>
          <h1 className="text-xl font-bold text-slate-900">Ananya Deshmukh (Age 32, Female)</h1>
        </div>
        <div className="text-xs text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200 font-semibold">
          Verified Electronic Health Record
        </div>
      </div>

      {/* Allergies Card */}
      <div className="bg-white rounded-3xl p-6 border border-rose-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 text-rose-800 font-bold text-sm">
          <AlertTriangle className="w-4 h-4 text-rose-600" />
          <span>Known Drug & Substance Allergies</span>
        </div>

        <div className="space-y-2 text-xs">
          {history.allergies.map((a, i) => (
            <div
              key={i}
              className="p-3 rounded-2xl bg-rose-50/70 border border-rose-100 flex items-center justify-between"
            >
              <div>
                <span className="font-extrabold text-rose-900 text-sm">{a.name}</span>
                <span className="text-rose-700 block mt-0.5">Reaction: {a.reaction}</span>
              </div>
              <span className="text-[10px] uppercase font-bold text-rose-800 bg-rose-200/70 px-2 py-0.5 rounded">
                Verified Allergy
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Chronic Conditions */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
          <Heart className="w-4 h-4 text-emerald-600" />
          <span>Chronic Diagnoses & Conditions</span>
        </div>

        <div className="space-y-2 text-xs">
          {history.chronicConditions.map((c, i) => (
            <div
              key={i}
              className="p-3 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-between"
            >
              <div>
                <span className="font-bold text-slate-900">{c.condition}</span>
                <span className="text-slate-500 block text-[11px]">Diagnosed: {c.diagnosedYear}</span>
              </div>
              <span className="text-[10px] text-teal-800 bg-teal-50 px-2.5 py-1 rounded-lg font-semibold border border-teal-200">
                {c.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Family History & Past Surgeries Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Past Surgeries */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <Scissors className="w-4 h-4 text-slate-600" />
            <span>Past Surgical Procedures</span>
          </div>

          <div className="space-y-2 text-xs">
            {history.pastSurgeries.map((s, i) => (
              <div key={i} className="p-3 rounded-2xl bg-slate-50 border border-slate-100">
                <span className="font-bold text-slate-900 block">{s.procedure}</span>
                <span className="text-slate-500 text-[11px] block mt-0.5">
                  Year: {s.year} • {s.hospital}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Family Medical History */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <Users className="w-4 h-4 text-slate-600" />
            <span>Family Health History</span>
          </div>

          <div className="space-y-2 text-xs">
            {history.familyHistory.map((f, i) => (
              <div key={i} className="p-3 rounded-2xl bg-slate-50 border border-slate-100">
                <span className="font-bold text-slate-900 block">{f.relative}</span>
                <span className="text-slate-600 text-[11px] block mt-0.5">{f.conditions}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Social & Lifestyle Profile */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
        <h2 className="text-sm font-bold text-slate-900">Lifestyle & Cardiovascular Risk Profile</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 text-[10px] block font-bold">Tobacco</span>
            <span className="font-semibold text-slate-800">{history.lifestyle.smoking}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 text-[10px] block font-bold">Alcohol</span>
            <span className="font-semibold text-slate-800">{history.lifestyle.alcohol}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 text-[10px] block font-bold">Diet</span>
            <span className="font-semibold text-slate-800">{history.lifestyle.diet}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 text-[10px] block font-bold">Exercise</span>
            <span className="font-semibold text-slate-800">{history.lifestyle.physicalActivity}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
