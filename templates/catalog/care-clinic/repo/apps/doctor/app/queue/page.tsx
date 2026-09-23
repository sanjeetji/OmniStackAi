"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Users,
  Clock,
  CheckCircle2,
  Video,
  Building2,
  ChevronRight,
  Filter,
  Stethoscope,
  FileText,
  AlertCircle,
  Search,
} from "lucide-react";
import {
  defaultApiClient,
  formatSlotTime,
  getAppointmentStatusBadge,
} from "@careclinic/shared";

export default function DoctorQueuePage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadQueue() {
      try {
        const res = await defaultApiClient.getDoctorQueue();
        setQueue(res.queue || []);
      } catch {
        // Fallback pre-seeded queue
        setQueue([
          {
            id: "apt-201",
            appointment_number: "APT-202609-089",
            token_number: 4,
            patient_name: "Ananya Deshmukh",
            patient_phone: "+91 98450 12345",
            patient_age: 32,
            gender: "female",
            blood_group: "O+",
            scheduled_date: new Date().toISOString().slice(0, 10),
            start_time: "10:20:00",
            status: "in_consult",
            appointment_type: "in_clinic",
            notes: "Intermittent chest tightness, occipital headaches in morning.",
            consultation_id: "con-101",
          },
          {
            id: "apt-202",
            appointment_number: "APT-202609-090",
            token_number: 5,
            patient_name: "Ramesh Narayan",
            patient_phone: "+91 98450 23456",
            patient_age: 58,
            gender: "male",
            blood_group: "B+",
            scheduled_date: new Date().toISOString().slice(0, 10),
            start_time: "10:40:00",
            status: "checked_in",
            appointment_type: "in_clinic",
            notes: "Post-angioplasty 6-month routine review and lipid check.",
          },
          {
            id: "apt-203",
            appointment_number: "APT-202609-091",
            token_number: 6,
            patient_name: "Pooja Hegde",
            patient_phone: "+91 98450 34567",
            patient_age: 29,
            gender: "female",
            blood_group: "A+",
            scheduled_date: new Date().toISOString().slice(0, 10),
            start_time: "11:00:00",
            status: "booked",
            appointment_type: "video",
            notes: "Palpitations during stressful workdays; ECG review.",
          },
          {
            id: "apt-204",
            appointment_number: "APT-202609-092",
            token_number: 7,
            patient_name: "Siddharth Rao",
            patient_phone: "+91 98450 45678",
            patient_age: 44,
            gender: "male",
            blood_group: "AB+",
            scheduled_date: new Date().toISOString().slice(0, 10),
            start_time: "11:20:00",
            status: "booked",
            appointment_type: "in_clinic",
            notes: "Hypertension medication dosage titration.",
          },
          {
            id: "apt-205",
            appointment_number: "APT-202609-085",
            token_number: 1,
            patient_name: "Meera Krishnan",
            patient_age: 62,
            gender: "female",
            start_time: "09:20:00",
            status: "completed",
            appointment_type: "in_clinic",
            notes: "Annual diabetic checkup; e-prescription issued.",
            prescription_id: "rx-85",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    loadQueue();
  }, []);

  const filteredQueue = queue.filter((item) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchName = item.patient_name?.toLowerCase().includes(q);
      const matchNotes = item.notes?.toLowerCase().includes(q);
      if (!matchName && !matchNotes) return false;
    }

    if (filter === "waiting") return item.status === "checked_in";
    if (filter === "in_consult") return item.status === "in_consult";
    if (filter === "completed") return item.status === "completed";
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Today's Patient Queue
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time outpatient queue ordered by token numbers with instant clinical documentation.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-2xl border border-slate-200 text-xs text-slate-600">
          <span className="font-semibold">Queue Total:</span>
          <span className="font-extrabold text-slate-900">{queue.length} Patients</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto text-xs font-semibold">
          <button
            onClick={() => setFilter("all")}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              filter === "all" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            All Tokens ({queue.length})
          </button>
          <button
            onClick={() => setFilter("waiting")}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              filter === "waiting" ? "bg-amber-500 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Checked In ({queue.filter((q) => q.status === "checked_in").length})
          </button>
          <button
            onClick={() => setFilter("in_consult")}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              filter === "in_consult" ? "bg-teal-600 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            In Consult ({queue.filter((q) => q.status === "in_consult").length})
          </button>
          <button
            onClick={() => setFilter("completed")}
            className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer ${
              filter === "completed" ? "bg-emerald-600 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            Completed ({queue.filter((q) => q.status === "completed").length})
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search patient..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs pl-8 pr-3 py-2 border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden"
          />
        </div>
      </div>

      {/* Queue List Table / Cards */}
      <div className="space-y-3">
        {filteredQueue.map((item) => {
          const badge = getAppointmentStatusBadge(item.status);
          const isInConsult = item.status === "in_consult";

          return (
            <div
              key={item.id}
              className={`p-5 rounded-3xl border transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                isInConsult
                  ? "bg-teal-50/70 border-teal-300 shadow-md ring-1 ring-teal-200"
                  : "bg-white border-slate-200 hover:border-slate-300 shadow-xs"
              }`}
            >
              {/* Left Details */}
              <div className="flex items-start gap-4 flex-1 min-w-0">
                <div
                  className={`w-12 h-12 rounded-2xl flex flex-col items-center justify-center shrink-0 font-black ${
                    isInConsult
                      ? "bg-teal-600 text-white shadow-xs"
                      : "bg-slate-900 text-white"
                  }`}
                >
                  <span className="text-[9px] uppercase tracking-wider block opacity-70">Token</span>
                  <span className="text-base leading-none">#{item.token_number || "--"}</span>
                </div>

                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900 truncate">
                      {item.patient_name}
                    </h3>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${badge.bg} ${badge.text} ${badge.border}`}
                    >
                      {badge.label}
                    </span>

                    {item.appointment_type === "video" ? (
                      <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded flex items-center gap-1">
                        <Video className="w-3 h-3" /> Telehealth Video
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded flex items-center gap-1">
                        <Building2 className="w-3 h-3" /> In-Clinic
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>
                      {item.patient_age ? `${item.patient_age} Yrs` : "Adult"} • {item.gender}
                    </span>
                    {item.blood_group && <span>• Blood: {item.blood_group}</span>}
                    <span>• Slot: <strong>{formatSlotTime(item.start_time)}</strong></span>
                  </div>

                  {item.notes && (
                    <p className="text-xs text-slate-600 pt-0.5 leading-relaxed line-clamp-1">
                      Reason: "{item.notes}"
                    </p>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 w-full md:w-auto justify-end border-t md:border-t-0 pt-3 md:pt-0 border-slate-100">
                {item.status !== "completed" ? (
                  <Link
                    href={`/consult/${item.id}`}
                    className={`font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5 cursor-pointer ${
                      isInConsult
                        ? "bg-teal-700 hover:bg-teal-800 text-white"
                        : "bg-emerald-600 hover:bg-emerald-700 text-white"
                    }`}
                  >
                    <Stethoscope className="w-3.5 h-3.5" />
                    <span>{isInConsult ? "Resume Visit" : "Start Consult"}</span>
                  </Link>
                ) : (
                  <Link
                    href={`/consult/${item.id}/soap`}
                    className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs px-3.5 py-2 rounded-xl transition-colors flex items-center gap-1"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Review SOAP</span>
                  </Link>
                )}

                <Link
                  href={`/patients/pat-1`}
                  className="border border-slate-200 hover:border-slate-300 text-slate-700 text-xs font-semibold px-3 py-2 rounded-xl transition-colors"
                  title="Patient Longitudinal Health Chart"
                >
                  Chart
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
