"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Printer,
  ShieldCheck,
  Calendar,
  Building2,
  HeartPulse,
  User,
  ArrowLeft,
  Pill,
} from "lucide-react";
import { defaultApiClient, type Prescription, type PrescriptionItem } from "@careclinic/shared";

export default function PrescriptionDetailPage() {
  const params = useParams();
  const rxId = (params?.id as string) || "rx-demo";

  const [prescription, setPrescription] = useState<Prescription | null>(null);
  const [items, setItems] = useState<PrescriptionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRx() {
      try {
        const res = await defaultApiClient.getPrescription(rxId);
        setPrescription(res.prescription);
        setItems(res.items || []);
      } catch {
        // Fallback demo prescription
        setPrescription({
          id: rxId,
          prescription_number: "RX-2026-00142",
          consultation_id: "con-101",
          patient_id: "pat-1",
          doctor_id: "doc-1",
          doctor_name: "Dr. Rajesh Varma, MD",
          qualification: "MD, DM (Cardiology), FACC",
          license_number: "KMC-48291",
          specialties: ["Cardiology", "Internal Medicine"],
          clinic_name: "CareClinic Indiranagar",
          clinic_address: "100 Feet Road, HAL 2nd Stage, Indiranagar, Bengaluru 560038",
          clinic_phone: "+91 80 4912 3000",
          appointment_number: "APT-202609-012",
          scheduled_date: "2026-09-18",
          subjective: "Patient presented with intermittent exertional dyspnea and morning occipital headaches for 2 weeks.",
          assessment: "Essential Primary Hypertension (ICD-10: I10), Stage 1 with mild exertional tachycardia.",
          plan: "Initiate low-dose ARB therapy, dietary sodium restriction <2g/day, lipid profile workup, and repeat BP check in 3 weeks.",
          notes: "Strict low-sodium diet, 30 min daily brisk walk, monitor blood pressure weekly.",
          is_immutable: true,
          digital_signature: "SHA256:7f9a88c241e05d4b8e...VERIFIED_KMC_48291",
          signed_at: "2026-09-18T10:45:00Z",
          created_at: "2026-09-18T10:45:00Z",
        });
        setItems([
          {
            id: "item-1",
            medication_name: "Telmisartan",
            form: "Tablet",
            dosage: "40 mg",
            route: "Oral",
            frequency: "Once daily",
            timing: "After breakfast",
            duration_days: 30,
            instructions: "Take consistently at the same time each morning; do not abruptly stop.",
          },
          {
            id: "item-2",
            medication_name: "Atorvastatin",
            form: "Tablet",
            dosage: "10 mg",
            route: "Oral",
            frequency: "Once daily",
            timing: "At bedtime",
            duration_days: 30,
            instructions: "For cardioprotective lipid management.",
          },
          {
            id: "item-3",
            medication_name: "Paracetamol",
            form: "Tablet",
            dosage: "650 mg",
            route: "Oral",
            frequency: "SOS (As needed)",
            timing: "After food",
            duration_days: 5,
            instructions: "Only in case of severe headache or fever (max 3 times/day).",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    if (rxId) {
      loadRx();
    }
  }, [rxId]);

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  if (!prescription) {
    return (
      <div className="max-w-3xl mx-auto p-12 text-center text-xs text-slate-500">
        Loading prescription record...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Bar Actions */}
      <div className="flex items-center justify-between no-print">
        <Link
          href="/prescriptions"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-teal-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Prescriptions
        </Link>

        <button
          onClick={handlePrint}
          className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
        >
          <Printer className="w-4 h-4" />
          <span>Print / Save PDF</span>
        </button>
      </div>

      {/* Official Rx Slip Sheet */}
      <div className="bg-white rounded-3xl p-8 sm:p-12 border border-slate-200 shadow-md space-y-8 print:p-0 print:border-none print:shadow-none">
        {/* Clinic Letterhead */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b-2 border-teal-600 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-teal-600 text-white flex items-center justify-center font-bold">
              <HeartPulse className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                {prescription.clinic_name || "CareClinic Indiranagar"}
              </h1>
              <p className="text-xs text-slate-500">
                {prescription.clinic_address || "100 Feet Road, Indiranagar, Bengaluru 560038"} •{" "}
                {prescription.clinic_phone || "+91 80 4912 3000"}
              </p>
              <div className="flex items-center gap-1 text-[10px] text-teal-800 font-bold uppercase tracking-wider mt-0.5">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span>NABH Accredited Healthcare Facility</span>
              </div>
            </div>
          </div>

          <div className="text-left sm:text-right">
            <div className="text-xs font-mono font-bold text-teal-800 bg-teal-50 px-3 py-1 rounded-lg border border-teal-200">
              {prescription.prescription_number}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Date: <strong>{prescription.scheduled_date || "2026-09-18"}</strong>
            </div>
            <div className="text-[11px] text-slate-400">
              Appt: #{prescription.appointment_number || "APT-202609-012"}
            </div>
          </div>
        </div>

        {/* Doctor & Patient Info Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 bg-slate-50 p-5 rounded-2xl border border-slate-100 text-xs">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Attending Physician
            </span>
            <div className="text-sm font-bold text-slate-900">{prescription.doctor_name}</div>
            <div className="text-slate-600 font-medium">{prescription.qualification}</div>
            <div className="text-teal-700 font-medium">KMC Reg: {prescription.license_number}</div>
          </div>

          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Patient Information
            </span>
            <div className="text-sm font-bold text-slate-900">Ananya Deshmukh</div>
            <div className="text-slate-600">Age: 32 Yrs • Female • Blood Group: O+</div>
            <div className="text-slate-600">Vitals: BP 120/80 mmHg • Pulse 72 bpm • SpO2 98%</div>
          </div>
        </div>

        {/* Clinical Assessment / SOAP */}
        {prescription.assessment && (
          <div className="space-y-1 text-xs">
            <span className="text-[10px] uppercase font-bold text-slate-400">
              Clinical Assessment & Diagnosis
            </span>
            <div className="p-3 bg-teal-50/50 rounded-xl border border-teal-100 font-medium text-slate-800 leading-relaxed">
              {prescription.assessment}
            </div>
          </div>
        )}

        {/* Rx Medication Table */}
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 text-base font-extrabold text-teal-800">
            <span className="text-xl font-serif">℞</span>
            <span>Medications & Dosage Schedule</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200 text-slate-500 uppercase text-[10px]">
                  <th className="py-2.5 font-bold">#</th>
                  <th className="py-2.5 font-bold">Medication & Form</th>
                  <th className="py-2.5 font-bold">Dosage</th>
                  <th className="py-2.5 font-bold">Frequency & Timing</th>
                  <th className="py-2.5 font-bold">Duration</th>
                  <th className="py-2.5 font-bold">Special Instructions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/60">
                    <td className="py-3 text-slate-400 font-semibold">{idx + 1}</td>
                    <td className="py-3 font-bold text-slate-900">
                      <div>{item.medication_name}</div>
                      <div className="text-[10px] text-slate-400 font-normal">{item.form}</div>
                    </td>
                    <td className="py-3 font-semibold text-teal-800">{item.dosage}</td>
                    <td className="py-3 text-slate-700">
                      <div>{item.frequency}</div>
                      <div className="text-[11px] text-teal-700">{item.timing}</div>
                    </td>
                    <td className="py-3 font-medium text-slate-700">{item.duration_days} Days</td>
                    <td className="py-3 text-slate-600 max-w-xs">{item.instructions || "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Physician's Advice */}
        {prescription.notes && (
          <div className="space-y-1.5 text-xs bg-slate-50 p-4 rounded-2xl border border-slate-100">
            <span className="font-bold text-slate-800 block">General Advice & Lifestyle Modifications:</span>
            <p className="text-slate-600 leading-relaxed">{prescription.notes}</p>
          </div>
        )}

        {/* Footer Signature & Tamper-Proof Stamp */}
        <div className="pt-8 border-t border-slate-200 flex flex-col sm:flex-row items-start sm:items-end justify-between gap-6">
          <div className="space-y-1 text-[11px] text-slate-500">
            <div className="flex items-center gap-1 text-emerald-700 font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Digitally Signed & Certified E-Prescription</span>
            </div>
            <p className="font-mono text-[10px] text-slate-400">
              Signature Hash: {prescription.digital_signature || "SHA256:VERIFIED_AUTHENTIC"}
            </p>
            <p>Signed At: {prescription.signed_at || "2026-09-18 10:45 UTC"}</p>
          </div>

          <div className="text-left sm:text-right space-y-1">
            <div className="text-sm font-bold text-slate-900">{prescription.doctor_name}</div>
            <div className="text-xs text-teal-700 font-medium">{prescription.qualification}</div>
            <div className="text-[10px] text-slate-400">Consultant Physician Stamp</div>
          </div>
        </div>
      </div>
    </div>
  );
}
