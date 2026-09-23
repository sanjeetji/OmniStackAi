"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Stethoscope,
  FlaskConical,
  CheckCircle2,
  Video,
  Activity,
  AlertTriangle,
  Heart,
  Thermometer,
  Droplet,
  ArrowLeft,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import { defaultApiClient, formatSlotTime } from "@careclinic/shared";

export default function ActiveConsultationPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = (params?.appointmentId as string) || "apt-201";

  const [appointment, setAppointment] = useState<any>(null);
  const [vitals, setVitals] = useState<any>({
    bp_systolic: 120,
    bp_diastolic: 80,
    heart_rate: 72,
    temperature_f: 98.4,
    spo2_percent: 98,
    blood_glucose_mg_dl: 94,
  });
  const [finalizing, setFinalizing] = useState(false);

  useEffect(() => {
    async function initConsultation() {
      try {
        await defaultApiClient.startConsultation(appointmentId);
      } catch {
        // Already started or preview
      }

      setAppointment({
        id: appointmentId,
        appointment_number: "APT-202609-089",
        token_number: 4,
        patient_name: "Ananya Deshmukh",
        patient_id: "pat-1",
        patient_age: 32,
        gender: "Female",
        blood_group: "O+",
        start_time: "10:20:00",
        appointment_type: "in_clinic",
        notes: "Intermittent chest tightness after climbing stairs, mild morning headaches.",
        allergies: ["Penicillin (Moderate Rash)"],
      });
    }

    initConsultation();
  }, [appointmentId]);

  const handleCompleteVisit = async () => {
    setFinalizing(true);
    try {
      await defaultApiClient.completeConsultation(appointmentId);
      router.push("/queue");
    } catch {
      router.push("/queue");
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header with Back to Queue */}
      <div className="flex items-center justify-between">
        <Link
          href="/queue"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Today's Queue
        </Link>

        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
            Active Clinical Consultation
          </span>
        </div>
      </div>

      {/* Patient Banner */}
      <div className="bg-slate-900 text-white rounded-3xl p-6 sm:p-7 border border-slate-800 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-teal-700/80 text-teal-100 font-extrabold text-xl flex items-center justify-center shrink-0">
              AD
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-white">{appointment?.patient_name}</h1>
                <span className="text-xs bg-slate-800 text-teal-300 font-mono font-bold px-2 py-0.5 rounded">
                  Token #{appointment?.token_number || 4}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-300 mt-1">
                <span>Age: 32 Yrs</span>
                <span>•</span>
                <span>Female</span>
                <span>•</span>
                <span>Blood: O+</span>
                <span>•</span>
                <span>UHID: CC-PAT-001</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href={`/patients/pat-1`}
              className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors border border-slate-700"
            >
              Full History & Chart
            </Link>

            {appointment?.appointment_type === "video" && (
              <Link
                href={`/telehealth/${appointmentId}`}
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors flex items-center gap-1.5"
              >
                <Video className="w-4 h-4" />
                <span>Call Screen</span>
              </Link>
            )}
          </div>
        </div>

        {/* Allergy Red Tag Banner */}
        <div className="p-3 rounded-2xl bg-rose-950/60 border border-rose-800/80 flex items-center gap-2 text-xs text-rose-200">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span className="font-bold">Drug Allergy Warning:</span>
          <span>Penicillin (Moderate skin rash & angioedema risk). Avoid all beta-lactam derivatives.</span>
        </div>
      </div>

      {/* Vitals Recorded at Reception Desk */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-slate-400 text-[10px] font-bold uppercase">Blood Pressure</span>
          <div className="text-lg font-black text-slate-900">
            {vitals.bp_systolic} / {vitals.bp_diastolic}{" "}
            <span className="text-xs font-normal text-slate-400">mmHg</span>
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold block">Resting Optimal</span>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-slate-400 text-[10px] font-bold uppercase">Heart Rate</span>
          <div className="text-lg font-black text-slate-900">
            {vitals.heart_rate} <span className="text-xs font-normal text-slate-400">BPM</span>
          </div>
          <span className="text-[10px] text-slate-500 font-semibold block">Regular Rhythm</span>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-slate-400 text-[10px] font-bold uppercase">Oxygen Saturation</span>
          <div className="text-lg font-black text-slate-900">
            {vitals.spo2_percent}% <span className="text-xs font-normal text-slate-400">SpO2</span>
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold block">Room Air</span>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-1">
          <span className="text-slate-400 text-[10px] font-bold uppercase">Blood Glucose</span>
          <div className="text-lg font-black text-slate-900">
            {vitals.blood_glucose_mg_dl}{" "}
            <span className="text-xs font-normal text-slate-400">mg/dL</span>
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold block">Fasting</span>
        </div>
      </div>

      {/* Clinical Workflow Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* SOAP Notes Module */}
        <Link
          href={`/consult/${appointmentId}/soap`}
          className="bg-white p-6 rounded-3xl border border-slate-200 hover:border-emerald-300 hover:shadow-md transition-all group flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
              SOAP Documentation
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Record Subjective symptoms, Objective exam, ICD-10 clinical Assessment, and Plan.
            </p>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-emerald-700">
            <span>Open SOAP Editor</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* E-Prescription Module */}
        <Link
          href={`/consult/${appointmentId}/prescription`}
          className="bg-white p-6 rounded-3xl border border-slate-200 hover:border-teal-300 hover:shadow-md transition-all group flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold">
              <Stethoscope className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
              Digital E-Prescription
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Select medications, dosage guidelines, duration, and cryptographically sign the Rx.
            </p>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-teal-700">
            <span>Prescribe Medications</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Diagnostic Lab Ordering */}
        <Link
          href={`/consult/${appointmentId}/labs`}
          className="bg-white p-6 rounded-3xl border border-slate-200 hover:border-purple-300 hover:shadow-md transition-all group flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
              <FlaskConical className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 group-hover:text-purple-700 transition-colors">
              Diagnostic Lab Orders
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Order blood tests, lipid panels, ECGs, and automated reference range analyses.
            </p>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-purple-700">
            <span>Order Diagnostic Labs</span>
            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>

      {/* Finalize Consultation Bar */}
      <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-slate-500">
          Ready to wrap up? Completing the visit finalizes the electronic chart and updates queue status.
        </div>

        <button
          onClick={handleCompleteVisit}
          disabled={finalizing}
          className="w-full sm:w-auto bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs sm:text-sm px-6 py-3 rounded-2xl transition-all shadow-md cursor-pointer flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{finalizing ? "Finalizing Visit..." : "Complete & Finalize Consultation"}</span>
        </button>
      </div>
    </div>
  );
}
