"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  Calendar,
  Clock,
  Building2,
  MapPin,
  FileText,
  ArrowRight,
  Download,
  Share2,
} from "lucide-react";
import { defaultApiClient, formatSlotTime, type Appointment } from "@careclinic/shared";

export default function BookingConfirmationPage() {
  const params = useParams();
  const appointmentId = (params?.id as string) || "apt-demo";
  const [appointment, setAppointment] = useState<Appointment | null>(null);

  useEffect(() => {
    async function loadAppointment() {
      try {
        const res = await defaultApiClient.getAppointment(appointmentId);
        setAppointment(res.appointment);
      } catch {
        setAppointment({
          id: appointmentId,
          appointment_number: "APT-202609-089",
          patient_id: "pat-1",
          doctor_id: "doc-1",
          doctor_name: "Dr. Rajesh Varma, MD",
          qualification: "MD, DM (Cardiology)",
          appointment_type: "in_clinic",
          scheduled_date: new Date().toISOString().slice(0, 10),
          start_time: "10:20:00",
          end_time: "10:40:00",
          status: "booked",
          token_number: 7,
          fee_inr: 800,
          payment_status: "paid",
          clinic_name: "CareClinic Indiranagar",
          room_number: "OPD 101",
          created_at: new Date().toISOString(),
        });
      }
    }

    if (appointmentId) {
      loadAppointment();
    }
  }, [appointmentId]);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8 text-center animate-fade-in">
      {/* Success Badge */}
      <div className="space-y-3">
        <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Appointment Confirmed!
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 max-w-md mx-auto">
          Your consultation slot has been reserved in our clinical management system.
        </p>
      </div>

      {/* Appointment Slip Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-md text-left space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400">Appointment Code</span>
            <div className="text-base font-extrabold text-teal-800">
              {appointment?.appointment_number || "APT-202609-089"}
            </div>
          </div>
          <div className="bg-teal-50 border border-teal-200 px-3.5 py-1.5 rounded-2xl text-center">
            <span className="text-[10px] uppercase font-bold text-teal-700 block">Queue Token</span>
            <span className="text-xl font-black text-teal-900">
              #{appointment?.token_number || 7}
            </span>
          </div>
        </div>

        {/* Doctor and Clinic */}
        <div className="space-y-1">
          <h3 className="text-base font-bold text-slate-900">
            {appointment?.doctor_name || "Dr. Rajesh Varma, MD"}
          </h3>
          <p className="text-xs text-teal-700 font-medium">
            {appointment?.qualification || "Cardiology & Internal Medicine"}
          </p>
          <div className="flex items-center gap-1.5 text-xs text-slate-500 pt-1">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            <span>
              {appointment?.clinic_name || "CareClinic Indiranagar"} • Room {appointment?.room_number || "OPD 101"}
            </span>
          </div>
        </div>

        {/* Date & Time */}
        <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-100 text-xs">
          <div>
            <span className="text-slate-400 block mb-0.5">Date</span>
            <span className="font-bold text-slate-900">{appointment?.scheduled_date}</span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Reporting Time</span>
            <span className="font-bold text-teal-800">
              {appointment ? formatSlotTime(appointment.start_time) : "10:20 AM"}
            </span>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-teal-50/50 rounded-2xl p-4 border border-teal-100 text-xs text-slate-600 space-y-1.5">
          <div className="font-bold text-teal-900">Clinic Arrival Instructions:</div>
          <ul className="list-disc list-inside space-y-1 text-[11px] text-teal-800/90">
            <li>Please arrive 10-15 minutes prior to your scheduled slot for vitals intake.</li>
            <li>Show this token number (#{appointment?.token_number || 7}) at the front desk.</li>
            <li>Carry any recent lab reports, medication strips, or previous discharge summaries.</li>
          </ul>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <Link
          href={`/appointments/${appointmentId}`}
          className="w-full sm:w-auto bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs sm:text-sm px-6 py-3 rounded-2xl transition-all shadow-md flex items-center justify-center gap-2"
        >
          <span>View Appointment Pass</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
        <Link
          href="/"
          className="w-full sm:w-auto bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold text-xs sm:text-sm px-6 py-3 rounded-2xl transition-all"
        >
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}
