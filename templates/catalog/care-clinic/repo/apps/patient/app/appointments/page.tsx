"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Calendar,
  Clock,
  Building2,
  Video,
  FileText,
  AlertCircle,
  Plus,
  ArrowRight,
  ChevronRight,
  Filter,
} from "lucide-react";
import {
  defaultApiClient,
  formatSlotTime,
  getAppointmentStatusBadge,
  type Appointment,
} from "@careclinic/shared";

export default function AppointmentsListPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [filter, setFilter] = useState<"upcoming" | "past" | "all">("upcoming");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAppointments() {
      setLoading(true);
      try {
        const queryParam = filter === "all" ? undefined : filter;
        const res = await defaultApiClient.getAppointments(queryParam);
        setAppointments(res.appointments || []);
      } catch {
        // Fallback appointments for preview
        setAppointments([
          {
            id: "apt-101",
            appointment_number: "APT-202609-089",
            patient_id: "pat-1",
            doctor_id: "doc-1",
            doctor_name: "Dr. Rajesh Varma, MD",
            qualification: "MD, DM (Cardiology)",
            specialties: ["Cardiology"],
            room_number: "OPD 101",
            appointment_type: "in_clinic",
            scheduled_date: new Date().toISOString().slice(0, 10),
            start_time: "10:20:00",
            end_time: "10:40:00",
            status: "checked_in",
            token_number: 4,
            fee_amount: 800,
            is_paid: true,
            clinic_name: "CareClinic Indiranagar",
            created_at: new Date().toISOString(),
          },
          {
            id: "apt-102",
            appointment_number: "APT-202609-094",
            patient_id: "pat-1",
            doctor_id: "doc-2",
            doctor_name: "Dr. Sneha Kulkarni, MD",
            qualification: "MD (Pediatrics)",
            specialties: ["Pediatrics"],
            appointment_type: "video",
            scheduled_date: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
            start_time: "14:00:00",
            end_time: "14:20:00",
            status: "booked",
            fee_amount: 600,
            is_paid: true,
            created_at: new Date().toISOString(),
          },
          {
            id: "apt-103",
            appointment_number: "APT-202608-041",
            patient_id: "pat-1",
            doctor_id: "doc-4",
            doctor_name: "Dr. Priya Sundaram, MD",
            qualification: "MD (Dermatology)",
            specialties: ["Dermatology"],
            appointment_type: "in_clinic",
            scheduled_date: "2026-08-15",
            start_time: "11:00:00",
            end_time: "11:20:00",
            status: "completed",
            fee_amount: 700,
            is_paid: true,
            prescription_id: "rx-41",
            created_at: "2026-08-15T11:00:00Z",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    loadAppointments();
  }, [filter]);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header & Book Button */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            My Appointments
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Track your upcoming consultations, queue token numbers, and clinical visit history.
          </p>
        </div>

        <Link
          href="/doctors"
          className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs sm:text-sm px-4 py-2.5 rounded-2xl transition-all shadow-sm flex items-center gap-1.5 shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Book New Visit</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3 text-xs font-semibold">
        <button
          onClick={() => setFilter("upcoming")}
          className={`px-4 py-2 rounded-xl transition-all cursor-pointer ${
            filter === "upcoming"
              ? "bg-teal-600 text-white shadow-xs"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Upcoming Visits
        </button>
        <button
          onClick={() => setFilter("past")}
          className={`px-4 py-2 rounded-xl transition-all cursor-pointer ${
            filter === "past"
              ? "bg-teal-600 text-white shadow-xs"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Past Consultations
        </button>
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 rounded-xl transition-all cursor-pointer ${
            filter === "all"
              ? "bg-teal-600 text-white shadow-xs"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          All Appointments
        </button>
      </div>

      {/* Appointment Cards List */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading appointments...</div>
      ) : appointments.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 text-center border border-slate-200">
          <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No appointments found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            You don’t have any consultations scheduled in this category.
          </p>
          <Link
            href="/doctors"
            className="inline-block mt-4 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl"
          >
            Find a Doctor & Book
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {appointments.map((apt) => {
            const badge = getAppointmentStatusBadge(apt.status);
            return (
              <div
                key={apt.id}
                className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 hover:border-teal-200 shadow-xs hover:shadow-md transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5"
              >
                {/* Left side: Doctor & details */}
                <div className="space-y-2 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[11px] font-bold px-2.5 py-0.5 rounded-lg border ${badge.bg} ${badge.text} ${badge.border}`}
                    >
                      {badge.label}
                    </span>

                    <span className="text-xs font-medium text-slate-400">
                      #{apt.appointment_number}
                    </span>

                    {apt.token_number && (
                      <span className="bg-teal-50 text-teal-800 text-[11px] font-extrabold px-2.5 py-0.5 rounded-md border border-teal-200">
                        Token #{apt.token_number}
                      </span>
                    )}

                    {apt.appointment_type === "video" ? (
                      <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-[11px] font-semibold px-2 py-0.5 rounded-md">
                        <Video className="w-3 h-3" /> Telehealth Video
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 text-[11px] font-semibold px-2 py-0.5 rounded-md">
                        <Building2 className="w-3 h-3" /> In-Clinic
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-slate-900 truncate">
                    {apt.doctor_name || "Specialist Physician"}
                  </h3>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{apt.scheduled_date}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>{formatSlotTime(apt.start_time)}</span>
                    </div>
                    {apt.room_number && (
                      <div className="text-teal-700 font-medium">Room: {apt.room_number}</div>
                    )}
                  </div>
                </div>

                {/* Right side: Action CTAs */}
                <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end border-t sm:border-t-0 pt-3 sm:pt-0 border-slate-100">
                  {apt.appointment_type === "video" && apt.status !== "completed" && apt.status !== "cancelled" && (
                    <Link
                      href={`/telehealth/${apt.id}`}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs flex items-center gap-1.5"
                    >
                      <Video className="w-3.5 h-3.5" />
                      <span>Enter Call</span>
                    </Link>
                  )}

                  {apt.prescription_id && (
                    <Link
                      href={`/prescriptions/${apt.prescription_id}`}
                      className="bg-teal-50 hover:bg-teal-100 text-teal-800 text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors flex items-center gap-1.5"
                    >
                      <FileText className="w-3.5 h-3.5 text-teal-600" />
                      <span>View Rx</span>
                    </Link>
                  )}

                  <Link
                    href={`/appointments/${apt.id}`}
                    className="border border-slate-200 hover:border-slate-300 text-slate-700 text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors flex items-center gap-1"
                  >
                    <span>Details</span>
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
