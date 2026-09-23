"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Calendar,
  Clock,
  Building2,
  Video,
  FileText,
  AlertCircle,
  ArrowLeft,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  X,
  CreditCard,
  MapPin,
  Phone,
} from "lucide-react";
import {
  defaultApiClient,
  formatINR,
  formatSlotTime,
  getAppointmentStatusBadge,
  calculateCancellationRefund,
  type Appointment,
} from "@careclinic/shared";

export default function AppointmentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appointmentId = (params?.id as string) || "apt-demo";

  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [cancelResult, setCancelResult] = useState<any>(null);

  useEffect(() => {
    async function loadAppointment() {
      try {
        const res = await defaultApiClient.getAppointment(appointmentId);
        setAppointment(res.appointment);
      } catch {
        // Fallback for preview
        setAppointment({
          id: appointmentId,
          appointment_number: "APT-202609-089",
          patient_id: "pat-1",
          doctor_id: "doc-1",
          doctor_name: "Dr. Rajesh Varma, MD",
          qualification: "MD, DM (Cardiology), FACC",
          license_number: "KMC-48291",
          specialties: ["Cardiology", "Internal Medicine"],
          clinic_name: "CareClinic Indiranagar",
          clinic_address: "100 Feet Road, Indiranagar, Bengaluru 560038",
          clinic_phone: "+91 80 4912 3000",
          room_number: "OPD 101",
          appointment_type: "in_clinic",
          scheduled_date: new Date().toISOString().slice(0, 10),
          start_time: "10:20:00",
          end_time: "10:40:00",
          status: "checked_in",
          token_number: 4,
          fee_inr: 800,
          payment_status: "paid",
          invoice_id: "inv-89",
          invoice_number: "INV-202609-089",
          net_payable: 800,
          created_at: new Date().toISOString(),
        });
      } finally {
        setLoading(false);
      }
    }

    if (appointmentId) {
      loadAppointment();
    }
  }, [appointmentId]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      const res = await defaultApiClient.cancelAppointment(appointmentId, cancelReason);
      setCancelResult(res.cancellation);
      setAppointment((prev) => (prev ? { ...prev, status: "cancelled" } : null));
    } catch (err: any) {
      alert("Cancellation failed: " + err.message);
    } finally {
      setCancelling(false);
    }
  };

  const refundCalc = appointment
    ? calculateCancellationRefund(appointment.scheduled_date, appointment.start_time, appointment.fee_inr)
    : null;

  const stages = [
    { id: "booked", label: "Booked" },
    { id: "checked_in", label: "Checked In" },
    { id: "in_consult", label: "In Consult" },
    { id: "completed", label: "Completed" },
  ];

  const currentStageIndex = stages.findIndex((s) => s.id === appointment?.status);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/appointments"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-teal-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Appointments
        </Link>
      </div>

      {/* Main Appointment Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-extrabold text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-lg border border-teal-100">
                {appointment?.appointment_type.replace("_", " ")}
              </span>
              <span className="text-xs text-slate-400 font-medium">
                #{appointment?.appointment_number}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900">
              {appointment?.doctor_name}
            </h1>
            <p className="text-xs text-teal-700 font-medium">{appointment?.qualification}</p>
          </div>

          {appointment?.token_number && appointment.status !== "cancelled" && (
            <div className="bg-gradient-to-br from-teal-500 to-teal-700 text-white rounded-2xl p-4 text-center shadow-md">
              <span className="text-[10px] uppercase font-bold tracking-wider block opacity-90">
                Queue Token
              </span>
              <span className="text-2xl font-black block">#{appointment.token_number}</span>
              <span className="text-[10px] opacity-80 block mt-0.5">Show at OPD Desk</span>
            </div>
          )}
        </div>

        {/* 4-Stage Lifecycle Stepper */}
        {appointment?.status !== "cancelled" && appointment?.status !== "no_show" && (
          <div className="space-y-2 pt-2">
            <span className="text-xs font-bold text-slate-700 block">Consultation Progress</span>
            <div className="grid grid-cols-4 gap-2">
              {stages.map((stage, idx) => {
                const isPassed = currentStageIndex >= idx;
                const isCurrent = currentStageIndex === idx;
                return (
                  <div key={stage.id} className="space-y-1 text-center">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        isPassed ? "bg-teal-600" : "bg-slate-200"
                      }`}
                    ></div>
                    <span
                      className={`text-[11px] font-semibold block ${
                        isCurrent
                          ? "text-teal-800 font-bold"
                          : isPassed
                          ? "text-slate-700"
                          : "text-slate-400"
                      }`}
                    >
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Date, Time & Venue Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-100 text-xs">
          <div className="space-y-1">
            <span className="text-slate-400 font-medium flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-teal-600" /> Date
            </span>
            <span className="text-sm font-bold text-slate-900 block">{appointment?.scheduled_date}</span>
          </div>

          <div className="space-y-1">
            <span className="text-slate-400 font-medium flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-teal-600" /> Slot Time
            </span>
            <span className="text-sm font-bold text-teal-800 block">
              {appointment ? formatSlotTime(appointment.start_time) : "10:20 AM"}
            </span>
          </div>

          <div className="space-y-1">
            <span className="text-slate-400 font-medium flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5 text-teal-600" /> Location / Room
            </span>
            <span className="text-sm font-bold text-slate-900 block">
              Room {appointment?.room_number || "OPD 101"}
            </span>
          </div>
        </div>

        {/* Clinic Navigation info */}
        <div className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 space-y-2 text-xs">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <MapPin className="w-4 h-4 text-teal-600" />
            <span>{appointment?.clinic_name || "CareClinic Indiranagar"}</span>
          </div>
          <p className="text-slate-500 pl-6">
            {appointment?.clinic_address || "100 Feet Road, HAL 2nd Stage, Indiranagar, Bengaluru"}
          </p>
          <div className="flex items-center gap-2 text-slate-600 pl-6 pt-1">
            <Phone className="w-3.5 h-3.5 text-slate-400" />
            <span>Helpdesk: {appointment?.clinic_phone || "+91 80 4912 3000"}</span>
          </div>
        </div>

        {/* Actions Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-100">
          <div className="flex items-center gap-2">
            {appointment?.prescription_id && (
              <Link
                href={`/prescriptions/${appointment.prescription_id}`}
                className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs flex items-center gap-1.5"
              >
                <FileText className="w-4 h-4" />
                <span>Download Rx Prescription</span>
              </Link>
            )}

            {appointment?.appointment_type === "video" && appointment.status !== "completed" && appointment.status !== "cancelled" && (
              <Link
                href={`/telehealth/${appointment.id}`}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs flex items-center gap-1.5"
              >
                <Video className="w-4 h-4" />
                <span>Enter Telehealth Room</span>
              </Link>
            )}
          </div>

          {appointment?.status !== "completed" && appointment?.status !== "cancelled" && (
            <button
              onClick={() => setCancelModalOpen(true)}
              className="text-xs font-semibold text-rose-600 hover:text-rose-700 px-3 py-2 rounded-xl hover:bg-rose-50 transition-colors cursor-pointer"
            >
              Cancel Consultation
            </button>
          )}
        </div>
      </div>

      {/* Cancellation Modal with Refund Policy */}
      {cancelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-xl border border-slate-200 relative animate-fade-in space-y-4">
            <button
              onClick={() => setCancelModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Cancel Appointment</h3>
                <p className="text-xs text-slate-500">Refund calculation under CareClinic policy</p>
              </div>
            </div>

            {/* Refund policy calculation box */}
            {refundCalc && (
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs space-y-2">
                <div className="flex justify-between font-medium text-slate-600">
                  <span>Consultation Fee Paid</span>
                  <span>{formatINR(appointment?.fee_inr || 800)}</span>
                </div>
                <div className="flex justify-between font-bold text-teal-800">
                  <span>Eligible Refund ({refundCalc.refundPercent}%)</span>
                  <span>{formatINR(refundCalc.refundAmountInr)}</span>
                </div>
                {refundCalc.deductionInr > 0 && (
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>Deduction / Retention</span>
                    <span>{formatINR(refundCalc.deductionInr)}</span>
                  </div>
                )}
                <p className="text-[11px] text-teal-700 pt-1 border-t border-slate-200">
                  {refundCalc.policyNote}
                </p>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Reason for Cancellation
              </label>
              <textarea
                rows={2}
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. Schedule conflict, feeling better..."
                className="w-full text-xs p-2.5 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Keep Appointment
              </button>
              <button
                type="button"
                onClick={handleCancel}
                disabled={cancelling}
                className="px-4 py-2 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-xs"
              >
                {cancelling ? "Processing..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
