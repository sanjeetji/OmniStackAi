"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Users,
  Clock,
  CheckCircle2,
  DollarSign,
  AlertTriangle,
  ArrowRight,
  Stethoscope,
  Video,
  Building2,
  FileText,
  FlaskConical,
  Activity,
  Calendar,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { defaultApiClient, formatINR, formatSlotTime } from "@careclinic/shared";

export default function DoctorDashboardPage() {
  const [metrics, setMetrics] = useState<any>({
    today_total: 15,
    waiting_count: 6,
    in_consult_count: 1,
    completed_count: 8,
    video_count: 4,
    today_earnings: 9800,
  });
  const [activeConsultation, setActiveConsultation] = useState<any>(null);
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [dashRes, qRes] = await Promise.allSettled([
          defaultApiClient.getDoctorDashboard(),
          defaultApiClient.getDoctorQueue(),
        ]);

        if (dashRes.status === "fulfilled" && dashRes.value.metrics) {
          setMetrics(dashRes.value.metrics);
          setActiveConsultation(dashRes.value.activeConsultation);
        } else {
          // Fallback demo active consult
          setActiveConsultation({
            id: "apt-201",
            appointment_number: "APT-202609-089",
            patient_name: "Ananya Deshmukh",
            patient_age: 32,
            gender: "female",
            blood_group: "O+",
            token_number: 4,
            start_time: "10:20:00",
            status: "in_consult",
            appointment_type: "in_clinic",
            notes: "Intermittent chest tightness after climbing stairs, mild morning occipital headaches.",
          });
        }

        if (qRes.status === "fulfilled" && qRes.value.queue) {
          setQueue(qRes.value.queue);
        } else {
          setQueue([
            {
              id: "apt-202",
              token_number: 5,
              patient_name: "Ramesh Narayan",
              patient_age: 58,
              gender: "male",
              start_time: "10:40:00",
              status: "checked_in",
              appointment_type: "in_clinic",
              notes: "Post-angioplasty 6-month routine review and lipid check.",
            },
            {
              id: "apt-203",
              token_number: 6,
              patient_name: "Pooja Hegde",
              patient_age: 29,
              gender: "female",
              start_time: "11:00:00",
              status: "booked",
              appointment_type: "video",
              notes: "Palpitations during stressful workdays; ECG review.",
            },
            {
              id: "apt-204",
              token_number: 7,
              patient_name: "Siddharth Rao",
              patient_age: 44,
              gender: "male",
              start_time: "11:20:00",
              status: "booked",
              appointment_type: "in_clinic",
              notes: "Hypertension medication dosage titration.",
            },
          ]);
        }
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const kpis = [
    {
      title: "Today's Consultations",
      value: metrics.today_total || 15,
      sub: "Total booked slots",
      icon: Users,
      color: "bg-blue-50 text-blue-700 border-blue-100",
    },
    {
      title: "Waiting in OPD Queue",
      value: metrics.waiting_count || 6,
      sub: "Arrived & checked in",
      icon: Clock,
      color: "bg-amber-50 text-amber-700 border-amber-100",
    },
    {
      title: "Completed Visits",
      value: metrics.completed_count || 8,
      sub: "Rx issued & signed",
      icon: CheckCircle2,
      color: "bg-emerald-50 text-emerald-700 border-emerald-100",
    },
    {
      title: "Today's Clinical Revenue",
      value: formatINR(metrics.today_earnings || 9800),
      sub: "Consultation fees collected",
      icon: DollarSign,
      color: "bg-teal-50 text-teal-700 border-teal-100",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Greeting & OPD Mode */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Clinical Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time outpatient queue, active consultations, and diagnostic alerts.
          </p>
        </div>

        <Link
          href="/queue"
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
        >
          <Users className="w-4 h-4" />
          <span>Open Patient Queue Board</span>
        </Link>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div
              key={idx}
              className="bg-white rounded-3xl p-5 border border-slate-200 shadow-xs flex items-start justify-between"
            >
              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  {kpi.title}
                </span>
                <span className="text-2xl font-black text-slate-900 block">{kpi.value}</span>
                <span className="text-[11px] text-slate-500 block">{kpi.sub}</span>
              </div>

              <div className={`p-3 rounded-2xl border ${kpi.color}`}>
                <Icon className="w-5 h-5" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Consultation Spotlight Card */}
      {activeConsultation && (
        <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-teal-950 rounded-3xl p-6 sm:p-7 text-white shadow-md border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                Patient In Consultation Room • Token #{activeConsultation.token_number || 4}
              </span>
            </div>

            <span className="text-xs text-slate-400">
              Reporting: {formatSlotTime(activeConsultation.start_time)} •{" "}
              <span className="capitalize">{activeConsultation.appointment_type.replace("_", " ")}</span>
            </span>
          </div>

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-t border-slate-800 pt-4">
            <div className="space-y-1">
              <h2 className="text-xl sm:text-2xl font-extrabold text-white">
                {activeConsultation.patient_name}
              </h2>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
                <span>Age: {activeConsultation.patient_age || 32} Yrs</span>
                <span>•</span>
                <span className="capitalize">{activeConsultation.gender || "Female"}</span>
                <span>•</span>
                <span>Blood: {activeConsultation.blood_group || "O+"}</span>
              </div>
              {activeConsultation.notes && (
                <p className="text-xs text-teal-200/90 italic pt-1">
                  Chief Complaint: "{activeConsultation.notes}"
                </p>
              )}
            </div>

            {/* Direct Workflow Buttons */}
            <div className="flex flex-wrap items-center gap-2.5">
              <Link
                href={`/consult/${activeConsultation.id}/soap`}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
              >
                <FileText className="w-4 h-4" />
                <span>Write SOAP Note</span>
              </Link>

              <Link
                href={`/consult/${activeConsultation.id}/prescription`}
                className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
              >
                <Stethoscope className="w-4 h-4" />
                <span>E-Prescribe</span>
              </Link>

              {activeConsultation.appointment_type === "video" && (
                <Link
                  href={`/telehealth/${activeConsultation.id}`}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
                >
                  <Video className="w-4 h-4" />
                  <span>Call Station</span>
                </Link>
              )}

              <Link
                href={`/patients/pat-1`}
                className="border border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white font-semibold text-xs px-3.5 py-2.5 rounded-xl transition-colors"
              >
                Full Chart
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Two Column Layout: Waiting Queue Preview & Urgent Clinical Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Next Patients in Waiting Queue (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">Next Up in OPD Queue</h2>
            </div>
            <Link
              href="/queue"
              className="text-xs font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
            >
              <span>View Full Queue ({queue.length})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {queue.slice(0, 4).map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-2xl border border-slate-100 hover:border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-900 text-white font-bold flex items-center justify-center text-sm shrink-0">
                    #{item.token_number || "--"}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">{item.patient_name}</h3>
                    <p className="text-xs text-slate-500">
                      {item.patient_age} Yrs • {item.gender} • Slot: {formatSlotTime(item.start_time)}
                    </p>
                    {item.notes && (
                      <p className="text-[11px] text-slate-600 line-clamp-1 mt-0.5">
                        Note: {item.notes}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  {item.appointment_type === "video" ? (
                    <span className="text-[10px] text-blue-700 bg-blue-50 px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                      <Video className="w-3 h-3" /> Video
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-700 bg-slate-100 px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                      <Building2 className="w-3 h-3" /> In-Clinic
                    </span>
                  )}

                  <Link
                    href={`/consult/${item.id}`}
                    className="bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs px-3.5 py-1.5 rounded-xl transition-colors shadow-2xs"
                  >
                    Call Patient
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Clinical Alerts & Quick Actions (1 Col) */}
        <div className="space-y-6">
          {/* Urgent Diagnostic Alerts */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center gap-2 text-rose-700 font-bold text-sm">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>Diagnostic Alerts</span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="p-3 rounded-2xl bg-rose-50 border border-rose-100 space-y-1">
                <div className="flex items-center justify-between font-bold text-rose-900">
                  <span>Ananya Deshmukh</span>
                  <span className="text-[10px] bg-rose-200/80 px-1.5 py-0.5 rounded">High LDL</span>
                </div>
                <p className="text-rose-800 text-[11px]">
                  LDL Cholesterol: 108 mg/dL (Ref &lt; 100 mg/dL). Statin titrate review needed.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-amber-50 border border-amber-100 space-y-1">
                <div className="flex items-center justify-between font-bold text-amber-900">
                  <span>Ramesh Narayan</span>
                  <span className="text-[10px] bg-amber-200/80 px-1.5 py-0.5 rounded">BP 142/90</span>
                </div>
                <p className="text-amber-800 text-[11px]">
                  Elevated systolic recorded at reception vitals check.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Physician Links */}
          <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Quick Shortcuts
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs font-semibold">
              <Link
                href="/schedule"
                className="p-3 rounded-2xl border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/40 text-slate-700 transition-all flex flex-col items-center gap-1.5 text-center"
              >
                <Calendar className="w-4 h-4 text-emerald-600" />
                <span>OPD Shifts</span>
              </Link>
              <Link
                href="/earnings"
                className="p-3 rounded-2xl border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/40 text-slate-700 transition-all flex flex-col items-center gap-1.5 text-center"
              >
                <DollarSign className="w-4 h-4 text-emerald-600" />
                <span>Earnings</span>
              </Link>
              <Link
                href="/reviews"
                className="p-3 rounded-2xl border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/40 text-slate-700 transition-all flex flex-col items-center gap-1.5 text-center"
              >
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>Reviews</span>
              </Link>
              <Link
                href="/patients/pat-1"
                className="p-3 rounded-2xl border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/40 text-slate-700 transition-all flex flex-col items-center gap-1.5 text-center"
              >
                <Activity className="w-4 h-4 text-emerald-600" />
                <span>Charts</span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
