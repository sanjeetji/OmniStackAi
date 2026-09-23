"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Users,
  Search,
  Filter,
  Activity,
  Calendar,
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  FileText,
  Phone,
  ArrowUpRight,
} from "lucide-react";

interface PatientDirectoryItem {
  id: string;
  uhid: string;
  name: string;
  age: number;
  gender: string;
  bloodGroup: string;
  phone: string;
  primaryCondition: string;
  conditionCategory: "cardiac" | "endocrine" | "respiratory" | "general";
  lastConsultation: string;
  nextFollowUp: string;
  activeMedsCount: number;
  riskStatus: "stable" | "elevated" | "review_due";
}

const DEMO_PATIENTS: PatientDirectoryItem[] = [
  {
    id: "pat-1",
    uhid: "CC-PAT-0091",
    name: "Ananya Deshmukh",
    age: 32,
    gender: "Female",
    bloodGroup: "O+",
    phone: "+91 98450 12345",
    primaryCondition: "Essential Hypertension",
    conditionCategory: "cardiac",
    lastConsultation: "2026-09-22 (Today)",
    nextFollowUp: "2026-10-06",
    activeMedsCount: 2,
    riskStatus: "stable",
  },
  {
    id: "pat-2",
    uhid: "CC-PAT-0092",
    name: "Vikram Malhotra",
    age: 48,
    gender: "Male",
    bloodGroup: "B+",
    phone: "+91 98210 99881",
    primaryCondition: "Type 2 Diabetes Mellitus & Dyslipidemia",
    conditionCategory: "endocrine",
    lastConsultation: "2026-09-18",
    nextFollowUp: "2026-09-25",
    activeMedsCount: 4,
    riskStatus: "elevated",
  },
  {
    id: "pat-3",
    uhid: "CC-PAT-0093",
    name: "Sunita Ramanathan",
    age: 61,
    gender: "Female",
    bloodGroup: "A+",
    phone: "+91 94480 33445",
    primaryCondition: "Post-CABG Follow-up & Atrial Fib",
    conditionCategory: "cardiac",
    lastConsultation: "2026-09-15",
    nextFollowUp: "2026-09-29",
    activeMedsCount: 5,
    riskStatus: "review_due",
  },
  {
    id: "pat-4",
    uhid: "CC-PAT-0094",
    name: "Arjun Nair",
    age: 27,
    gender: "Male",
    bloodGroup: "AB+",
    phone: "+91 97410 77654",
    primaryCondition: "Exercise-Induced Asthma",
    conditionCategory: "respiratory",
    lastConsultation: "2026-09-10",
    nextFollowUp: "2026-10-10",
    activeMedsCount: 1,
    riskStatus: "stable",
  },
  {
    id: "pat-5",
    uhid: "CC-PAT-0095",
    name: "Meera Kulkarni",
    age: 41,
    gender: "Female",
    bloodGroup: "O-",
    phone: "+91 99001 22334",
    primaryCondition: "Hypothyroidism & Hypercholesterolemia",
    conditionCategory: "endocrine",
    lastConsultation: "2026-09-02",
    nextFollowUp: "2026-10-02",
    activeMedsCount: 3,
    riskStatus: "stable",
  },
  {
    id: "pat-6",
    uhid: "CC-PAT-0096",
    name: "Deepak Seshadri",
    age: 54,
    gender: "Male",
    bloodGroup: "A-",
    phone: "+91 98860 55432",
    primaryCondition: "Mild Chronic Bronchitis",
    conditionCategory: "respiratory",
    lastConsultation: "2026-08-28",
    nextFollowUp: "2026-09-28",
    activeMedsCount: 2,
    riskStatus: "stable",
  },
];

export default function PatientsDirectoryPage() {
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");

  const filteredPatients = DEMO_PATIENTS.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.uhid.toLowerCase().includes(search.toLowerCase()) ||
      p.phone.includes(search) ||
      p.primaryCondition.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      filterCategory === "all" || p.conditionCategory === filterCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <ShieldCheck className="w-3.5 h-3.5" />
              HIPAA Compliant Record Index
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Patient Medical Directory
          </h1>
          <p className="text-sm text-slate-500">
            Search and manage long-term longitudinal records for active panel patients.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="bg-white border border-slate-200 px-4 py-2 rounded-xl shadow-xs text-right">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Active Panel
            </span>
            <span className="text-lg font-black text-slate-900">184 Patients</span>
          </div>
        </div>
      </div>

      {/* Metric Quick Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block">Cardiac Care</span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">78</span>
          <span className="text-[11px] text-emerald-600 font-medium">42% of panel</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block">Endocrine / Diabetic</span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">56</span>
          <span className="text-[11px] text-teal-600 font-medium">30% of panel</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block">Vitals Review Required</span>
          <span className="text-xl font-bold text-amber-600 mt-1 block">12</span>
          <span className="text-[11px] text-amber-700 font-medium">High BP / Glycemic shift</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium block">Scheduled Follow-ups</span>
          <span className="text-xl font-bold text-emerald-600 mt-1 block">24</span>
          <span className="text-[11px] text-slate-500 font-medium">Next 7 calendar days</span>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name, UHID, phone number, or clinical condition..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setFilterCategory("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              filterCategory === "all"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            All Conditions
          </button>
          <button
            onClick={() => setFilterCategory("cardiac")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              filterCategory === "cardiac"
                ? "bg-emerald-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Cardiac
          </button>
          <button
            onClick={() => setFilterCategory("endocrine")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              filterCategory === "endocrine"
                ? "bg-teal-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Endocrine
          </button>
          <button
            onClick={() => setFilterCategory("respiratory")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              filterCategory === "respiratory"
                ? "bg-cyan-700 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Respiratory
          </button>
        </div>
      </div>

      {/* Patient Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5">Patient Details</th>
                <th className="px-6 py-3.5">Primary Clinical Indication</th>
                <th className="px-6 py-3.5">Active Medications</th>
                <th className="px-6 py-3.5">Last Visit</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredPatients.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    No patients match your search or filter criteria.
                  </td>
                </tr>
              ) : (
                filteredPatients.map((patient) => (
                  <tr
                    key={patient.id}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-xs shrink-0 border border-slate-200">
                          {patient.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </div>
                        <div>
                          <Link
                            href={`/patients/${patient.id}`}
                            className="font-bold text-slate-900 hover:text-emerald-600 transition-colors block"
                          >
                            {patient.name}
                          </Link>
                          <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                            <span>
                              {patient.age} yrs • {patient.gender}
                            </span>
                            <span>•</span>
                            <span className="font-semibold text-slate-700">
                              {patient.bloodGroup}
                            </span>
                            <span>•</span>
                            <span className="font-mono text-slate-400 text-[11px]">
                              {patient.uhid}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <span className="font-medium text-slate-800 block text-xs">
                        {patient.primaryCondition}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        Follow-up: {patient.nextFollowUp}
                      </span>
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span>{patient.activeMedsCount} Rx Regimens</span>
                      </div>
                    </td>

                    <td className="px-6 py-4 text-xs text-slate-600">
                      {patient.lastConsultation}
                    </td>

                    <td className="px-6 py-4">
                      {patient.riskStatus === "stable" && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Stable
                        </span>
                      )}
                      {patient.riskStatus === "elevated" && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          <AlertCircle className="w-3 h-3" />
                          Vitals Alert
                        </span>
                      )}
                      {patient.riskStatus === "review_due" && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          Follow-up Due
                        </span>
                      )}
                    </td>

                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/patients/${patient.id}`}
                          className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-xs font-semibold text-slate-700 inline-flex items-center gap-1 transition-colors"
                        >
                          <span>Chart</span>
                          <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
                        </Link>
                        <Link
                          href={`/patients/${patient.id}/history`}
                          className="px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-xs font-semibold text-emerald-700 transition-colors"
                        >
                          History
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
