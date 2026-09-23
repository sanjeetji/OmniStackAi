"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  Calendar,
  Video,
  FileText,
  FlaskConical,
  Activity,
  Users,
  ShieldCheck,
  Clock,
  ArrowRight,
  HeartPulse,
  Award,
  CheckCircle2,
  AlertCircle,
  PhoneCall,
} from "lucide-react";
import { defaultApiClient, formatINR, type DoctorProfile, type Appointment } from "@careclinic/shared";
import { DoctorCard } from "@/components/doctor-card";

export default function PatientHomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [doctors, setDoctors] = useState<DoctorProfile[]>([]);
  const [upcomingAppointment, setUpcomingAppointment] = useState<Appointment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [docsRes, aptsRes] = await Promise.allSettled([
          defaultApiClient.getDoctors(),
          defaultApiClient.getAppointments("upcoming"),
        ]);

        if (docsRes.status === "fulfilled" && docsRes.value.doctors) {
          setDoctors(docsRes.value.doctors);
        } else {
          // Fallback doctors list for offline/standalone preview
          setDoctors([
            {
              doctor_id: "doc-1",
              full_name: "Dr. Rajesh Varma, MD",
              license_number: "KMC-48291",
              qualification: "MD, DM (Cardiology), FACC",
              specialties: ["Cardiology", "Internal Medicine"],
              experience_years: 18,
              consultation_fee_inr: 800,
              video_fee_inr: 700,
              bio: "Senior interventional cardiologist with 18+ years of clinical excellence in hypertension, preventive cardiology, and adult cardiac disorders.",
              room_number: "OPD 101",
              rating_avg: 4.9,
              rating_count: 142,
              is_accepting_patients: true,
            },
            {
              doctor_id: "doc-2",
              full_name: "Dr. Sneha Kulkarni, MD",
              license_number: "KMC-53102",
              qualification: "MD (Pediatrics), DNB",
              specialties: ["Pediatrics", "Neonatology"],
              experience_years: 12,
              consultation_fee_inr: 650,
              video_fee_inr: 600,
              bio: "Dedicated pediatric specialist passionate about child nutrition, neonatal developmental milestones, and routine immunization.",
              room_number: "OPD 104",
              rating_avg: 4.8,
              rating_count: 98,
              is_accepting_patients: true,
            },
            {
              doctor_id: "doc-3",
              full_name: "Dr. Arvind Swaminathan, MS",
              license_number: "KMC-39011",
              qualification: "MS (Orthopedics), M.Ch (Joint Replacement)",
              specialties: ["Orthopedics", "Sports Medicine"],
              experience_years: 16,
              consultation_fee_inr: 900,
              video_fee_inr: 800,
              bio: "Consultant orthopedic surgeon specializing in minimally invasive arthroscopy, sports injury rehabilitation, and joint pain management.",
              room_number: "OPD 108",
              rating_avg: 4.9,
              rating_count: 124,
              is_accepting_patients: true,
            },
            {
              doctor_id: "doc-4",
              full_name: "Dr. Priya Sundaram, MD",
              license_number: "KMC-61240",
              qualification: "MD (Dermatology, Venereology & Leprosy)",
              specialties: ["Dermatology", "Cosmetology"],
              experience_years: 10,
              consultation_fee_inr: 700,
              video_fee_inr: 650,
              bio: "Expert dermatologist offering evidence-based medical skincare, acne management, eczema treatment, and clinical dermatosurgery.",
              room_number: "OPD 202",
              rating_avg: 4.7,
              rating_count: 86,
              is_accepting_patients: true,
            },
          ]);
        }

        if (aptsRes.status === "fulfilled" && aptsRes.value.appointments?.length > 0) {
          setUpcomingAppointment(aptsRes.value.appointments[0]);
        }
      } catch {
        // graceful fallback
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const services = [
    {
      title: "Book In-Clinic Visit",
      desc: "Reserve 20-minute consultation slots with verified specialists at Indiranagar center.",
      icon: Calendar,
      href: "/doctors",
      color: "bg-teal-50 text-teal-700 border-teal-100",
    },
    {
      title: "Telehealth Video Consult",
      desc: "Connect directly with experienced physicians via high-definition encrypted video.",
      icon: Video,
      href: "/doctors",
      color: "bg-blue-50 text-blue-700 border-blue-100",
    },
    {
      title: "Digital Prescriptions",
      desc: "Access verified e-prescriptions with digital signatures and medication dosage guides.",
      icon: FileText,
      href: "/prescriptions",
      color: "bg-emerald-50 text-emerald-700 border-emerald-100",
    },
    {
      title: "Diagnostic Lab Reports",
      desc: "View diagnostic test results with automated physiological reference ranges.",
      icon: FlaskConical,
      href: "/lab-reports",
      color: "bg-purple-50 text-purple-700 border-purple-100",
    },
    {
      title: "Health Records & Vitals",
      desc: "Track longitudinal biometric vitals: Blood Pressure, Sugar, SpO2, and pulse trends.",
      icon: Activity,
      href: "/records",
      color: "bg-amber-50 text-amber-700 border-amber-100",
    },
    {
      title: "Family Profiles",
      desc: "Manage dependents, children, and senior parents from a single patient account.",
      icon: Users,
      href: "/family",
      color: "bg-indigo-50 text-indigo-700 border-indigo-100",
    },
  ];

  const filteredDoctors = doctors.filter((doc) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      doc.full_name?.toLowerCase().includes(q) ||
      doc.specialties?.some((s) => s.toLowerCase().includes(q)) ||
      doc.qualification?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-teal-50/80 via-white to-slate-50 border-b border-teal-100/60 pt-12 pb-16 sm:pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <div className="inline-flex items-center gap-2 bg-teal-100/70 text-teal-800 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide border border-teal-200/80">
              <HeartPulse className="w-4 h-4 text-teal-600 animate-pulse" />
              NABH Accredited Multi-Specialty Clinical Center
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight sm:leading-none">
              Compassionate Care, <br className="hidden sm:inline" />
              <span className="text-teal-700">Seamless Digital Health.</span>
            </h1>

            <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
              Book same-day in-clinic consultations or secure video visits with Bangalore’s top medical specialists. Complete electronic health records at your fingertips.
            </p>

            {/* Quick Search Doctor Bar */}
            <div className="mt-8 max-w-xl mx-auto">
              <div className="relative flex items-center bg-white rounded-2xl shadow-md border border-slate-200 p-1.5 focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-100 transition-all">
                <Search className="w-5 h-5 text-slate-400 ml-3 shrink-0" />
                <input
                  type="text"
                  placeholder="Search doctor by name, specialty (e.g. Cardiology), or symptom..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden"
                />
                <Link
                  href={`/doctors${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ""}`}
                  className="bg-teal-600 hover:bg-teal-700 text-white font-medium text-xs sm:text-sm px-4 py-2.5 rounded-xl shrink-0 transition-colors"
                >
                  Find Doctor
                </Link>
              </div>

              {/* Specialty quick pills */}
              <div className="flex flex-wrap items-center justify-center gap-2 mt-4 text-xs text-slate-600">
                <span className="font-semibold text-slate-400">Popular:</span>
                {["Cardiology", "Pediatrics", "Dermatology", "Orthopedics", "General Medicine"].map((spec) => (
                  <Link
                    key={spec}
                    href={`/doctors?specialty=${encodeURIComponent(spec)}`}
                    className="bg-white/80 hover:bg-teal-50 border border-slate-200 hover:border-teal-200 px-2.5 py-1 rounded-lg transition-colors text-slate-700"
                  >
                    {spec}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Upcoming Active Appointment Banner (if available) */}
      {upcomingAppointment && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-teal-800 to-teal-900 rounded-3xl p-6 sm:p-8 text-white shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border border-teal-700">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-teal-300 text-xs font-semibold uppercase tracking-wider">
                <Clock className="w-4 h-4 text-teal-400" />
                <span>Upcoming Appointment • Token #{upcomingAppointment.token_number || 4}</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white">
                {upcomingAppointment.doctor_name || "Dr. Rajesh Varma, MD"}
              </h3>
              <p className="text-sm text-teal-100">
                {upcomingAppointment.scheduled_date} at {upcomingAppointment.start_time.slice(0, 5)} •{" "}
                <span className="capitalize">{upcomingAppointment.appointment_type.replace("_", " ")}</span>
                {upcomingAppointment.room_number ? ` (Room: ${upcomingAppointment.room_number})` : ""}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {upcomingAppointment.appointment_type === "video" ? (
                <Link
                  href={`/telehealth/${upcomingAppointment.id}`}
                  className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors shadow flex items-center gap-2"
                >
                  <Video className="w-4 h-4" />
                  Join Video Room
                </Link>
              ) : (
                <Link
                  href={`/appointments/${upcomingAppointment.id}`}
                  className="bg-white text-teal-900 hover:bg-teal-50 font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors shadow flex items-center gap-2"
                >
                  View Queue Pass
                </Link>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Services Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Integrated Clinical Services
          </h2>
          <p className="text-sm text-slate-500 mt-2">
            Everything you need to navigate your healthcare journey with zero friction.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.title}
                href={item.href}
                className="bg-white rounded-3xl p-6 border border-slate-200 hover:border-teal-300 hover:shadow-md transition-all group flex flex-col justify-between"
              >
                <div>
                  <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-4 border ${item.color}`}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">{item.desc}</p>
                </div>

                <div className="mt-6 flex items-center text-xs font-semibold text-teal-600 group-hover:text-teal-700 gap-1">
                  <span>Access Service</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Featured Doctors Directory */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 mb-8">
          <div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Our Senior Physicians
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Experienced consultants across 8 medical and surgical departments.
            </p>
          </div>
          <Link
            href="/doctors"
            className="text-xs font-bold text-teal-700 hover:text-teal-800 flex items-center gap-1.5 bg-teal-50 px-3.5 py-2 rounded-xl"
          >
            <span>View All Doctors</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {filteredDoctors.slice(0, 4).map((doctor) => (
            <DoctorCard key={doctor.doctor_id} doctor={doctor} />
          ))}
        </div>
      </section>

      {/* Clinical Quality & Safety Promise */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-slate-900 text-white rounded-3xl p-8 sm:p-12 relative overflow-hidden">
          <div className="max-w-2xl space-y-4">
            <span className="text-xs uppercase font-bold tracking-widest text-teal-400">
              The CareClinic Benchmark
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-white leading-tight">
              Modern Medical Facilities with Patient-First Transparency.
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              We eliminate hospital waiting room bottlenecks through dynamic appointment slots, verified token tracking, and structured digital records.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <span className="font-bold text-white block">Strict 20-Min Slot Windows</span>
                  <span className="text-slate-400">Zero double-booking via database-enforced scheduling rules.</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <span className="font-bold text-white block">HIPAA-Compliant E-Records</span>
                  <span className="text-slate-400">Every chart access is permanently audited for your medical privacy.</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <span className="font-bold text-white block">Tamper-Proof Digital Rx</span>
                  <span className="text-slate-400">Prescriptions are cryptographically signed and immutable.</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <span className="font-bold text-white block">Transparent Refund Policy</span>
                  <span className="text-slate-400">100% refund for cancellations made 24h prior to visit.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
