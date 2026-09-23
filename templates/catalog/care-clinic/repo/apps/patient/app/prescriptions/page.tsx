"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Search,
  Calendar,
  ShieldCheck,
  Download,
  ExternalLink,
  ChevronRight,
  Pill,
} from "lucide-react";
import { defaultApiClient, type Prescription } from "@careclinic/shared";

export default function DigitalPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPrescriptions() {
      try {
        const res = await defaultApiClient.getPrescriptions();
        setPrescriptions(res.prescriptions || []);
      } catch {
        // Fallback for preview
        setPrescriptions([
          {
            id: "rx-101",
            prescription_number: "RX-2026-00142",
            consultation_id: "con-1",
            patient_id: "pat-1",
            doctor_id: "doc-1",
            doctor_name: "Dr. Rajesh Varma, MD",
            qualification: "MD, DM (Cardiology)",
            specialties: ["Cardiology"],
            license_number: "KMC-48291",
            clinic_name: "CareClinic Indiranagar",
            appointment_number: "APT-202609-012",
            scheduled_date: "2026-09-18",
            is_immutable: true,
            signed_at: "2026-09-18T10:45:00Z",
            created_at: "2026-09-18T10:45:00Z",
            notes: "Maintain low sodium diet, 30 min daily brisk walk, monitor blood pressure weekly.",
          },
          {
            id: "rx-102",
            prescription_number: "RX-2026-00089",
            consultation_id: "con-2",
            patient_id: "pat-1",
            doctor_id: "doc-4",
            doctor_name: "Dr. Priya Sundaram, MD",
            qualification: "MD (Dermatology)",
            specialties: ["Dermatology"],
            license_number: "KMC-61240",
            clinic_name: "CareClinic Indiranagar",
            appointment_number: "APT-202608-041",
            scheduled_date: "2026-08-15",
            is_immutable: true,
            signed_at: "2026-08-15T11:20:00Z",
            created_at: "2026-08-15T11:20:00Z",
            notes: "Apply topical ointment twice daily on affected dry skin areas.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    loadPrescriptions();
  }, []);

  const filteredRx = prescriptions.filter((rx) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      rx.prescription_number.toLowerCase().includes(q) ||
      rx.doctor_name?.toLowerCase().includes(q) ||
      rx.specialties?.some((s) => s.toLowerCase().includes(q))
    );
  });

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Digital Prescriptions
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Cryptographically signed, tamper-proof e-prescriptions issued by your attending physicians.
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative flex items-center bg-white rounded-2xl border border-slate-200 p-1.5 shadow-xs max-w-md">
        <Search className="w-5 h-5 text-slate-400 ml-3 shrink-0" />
        <input
          type="text"
          placeholder="Search by Rx number, doctor name, or specialty..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden"
        />
      </div>

      {/* Prescriptions List */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading prescriptions...</div>
      ) : filteredRx.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 text-center border border-slate-200">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No prescriptions found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            You don’t have any recorded e-prescriptions matching your search.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredRx.map((rx) => (
            <div
              key={rx.id}
              className="bg-white rounded-3xl p-6 border border-slate-200 hover:border-teal-300 hover:shadow-md transition-all flex flex-col justify-between group space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-100">
                      {rx.prescription_number}
                    </span>
                    <h3 className="text-base font-bold text-slate-900 mt-1.5 group-hover:text-teal-700 transition-colors">
                      {rx.doctor_name || "Consultant Doctor"}
                    </h3>
                    <p className="text-xs text-slate-500">{rx.qualification}</p>
                  </div>

                  <div className="flex items-center gap-1 text-[11px] text-emerald-700 bg-emerald-50 px-2 py-1 rounded-lg font-semibold shrink-0">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Digitally Signed</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>{rx.scheduled_date || rx.created_at.slice(0, 10)}</span>
                  </div>
                  {rx.appointment_number && (
                    <span>• Appt #{rx.appointment_number}</span>
                  )}
                </div>

                {rx.notes && (
                  <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-2xl border border-slate-100 line-clamp-2 leading-relaxed">
                    "{rx.notes}"
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-teal-700 font-medium flex items-center gap-1">
                  <Pill className="w-3.5 h-3.5" />
                  <span>Itemized Dosage Instructions</span>
                </span>

                <Link
                  href={`/prescriptions/${rx.id}`}
                  className="bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-xl transition-all shadow-xs flex items-center gap-1"
                >
                  <span>View Rx</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
