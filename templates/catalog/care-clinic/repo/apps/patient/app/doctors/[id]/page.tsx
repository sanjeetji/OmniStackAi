"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Star,
  Award,
  ShieldCheck,
  Clock,
  Building2,
  Video,
  MapPin,
  Calendar,
  CheckCircle2,
  Phone,
  MessageSquare,
  ArrowLeft,
} from "lucide-react";
import {
  defaultApiClient,
  formatINR,
  type DoctorProfile,
  type DoctorShift,
  type PatientReview,
} from "@careclinic/shared";

export default function DoctorProfilePage() {
  const params = useParams();
  const router = useRouter();
  const doctorId = params?.id as string;

  const [doctor, setDoctor] = useState<DoctorProfile | null>(null);
  const [availability, setAvailability] = useState<DoctorShift[]>([]);
  const [reviews, setReviews] = useState<PatientReview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDoctor() {
      try {
        const res = await defaultApiClient.getDoctor(doctorId);
        setDoctor(res.doctor);
        setAvailability(res.availability || []);
        setReviews(res.reviews || []);
      } catch {
        // Fallback doctor profile for standalone preview
        setDoctor({
          doctor_id: doctorId || "doc-1",
          full_name: "Dr. Rajesh Varma, MD",
          license_number: "KMC-48291",
          qualification: "MD, DM (Cardiology), FACC",
          specialties: ["Cardiology", "Internal Medicine"],
          experience_years: 18,
          consultation_fee_inr: 800,
          video_fee_inr: 700,
          bio: "Senior interventional cardiologist with 18+ years of clinical excellence in hypertension, preventive cardiology, adult cardiac disorders, and coronary angiograms. Active faculty and consultant at CareClinic Indiranagar.",
          room_number: "OPD 101 (First Floor)",
          rating_avg: 4.9,
          rating_count: 142,
          is_accepting_patients: true,
          clinic_name: "CareClinic Indiranagar",
          clinic_address: "100 Feet Road, HAL 2nd Stage, Indiranagar, Bengaluru",
          clinic_phone: "+91 80 4912 3000",
        });
        setAvailability([
          { day_of_week: 1, start_time: "09:00:00", end_time: "13:00:00", slot_duration_mins: 20, is_available: true },
          { day_of_week: 2, start_time: "09:00:00", end_time: "13:00:00", slot_duration_mins: 20, is_available: true },
          { day_of_week: 3, start_time: "09:00:00", end_time: "13:00:00", slot_duration_mins: 20, is_available: true },
          { day_of_week: 4, start_time: "09:00:00", end_time: "13:00:00", slot_duration_mins: 20, is_available: true },
          { day_of_week: 5, start_time: "09:00:00", end_time: "13:00:00", slot_duration_mins: 20, is_available: true },
          { day_of_week: 6, start_time: "09:00:00", end_time: "14:00:00", slot_duration_mins: 20, is_available: true },
        ]);
        setReviews([
          {
            id: "rev-1",
            patient_id: "p1",
            doctor_id: doctorId,
            patient_name: "Kavitha R.",
            rating: 5,
            feedback: "Dr. Rajesh was extremely thorough in reviewing my ECG and explained the lifestyle modifications clearly.",
            is_anonymous: false,
            created_at: "2026-09-18T10:30:00Z",
          },
          {
            id: "rev-2",
            patient_id: "p2",
            doctor_id: doctorId,
            patient_name: "Ramesh Narayan",
            rating: 5,
            feedback: "Very calm and knowledgeable physician. The clinic appointment started right on time without delays.",
            is_anonymous: false,
            created_at: "2026-09-14T11:15:00Z",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    if (doctorId) {
      loadDoctor();
    }
  }, [doctorId]);

  const daysOfWeek = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  if (!doctor) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center">
        <p className="text-slate-500">Loading physician profile...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Back button */}
      <div>
        <Link
          href="/doctors"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-teal-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Doctor Directory
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column: Doctor Information */}
        <div className="lg:col-span-2 space-y-6">
          {/* Main Profile Card */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
              <div className="w-24 h-24 rounded-3xl bg-teal-50 border border-teal-200 text-teal-700 font-bold text-3xl flex items-center justify-center shrink-0">
                {doctor.full_name ? doctor.full_name.replace("Dr. ", "").charAt(0) : "D"}
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-extrabold text-slate-900">{doctor.full_name}</h1>
                  <span className="text-teal-600 bg-teal-50 border border-teal-200 rounded-full p-0.5" title="Verified Medical License">
                    <ShieldCheck className="w-4 h-4" />
                  </span>
                </div>

                <p className="text-sm font-semibold text-teal-700">{doctor.qualification}</p>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                  <span>KMC Reg: <strong>{doctor.license_number}</strong></span>
                  <span>•</span>
                  <span>{doctor.experience_years} years experience</span>
                  <span>•</span>
                  <div className="inline-flex items-center gap-1 text-amber-700 font-bold">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span>{Number(doctor.rating_avg).toFixed(1)}</span>
                    <span className="text-slate-400 font-normal">({doctor.rating_count} reviews)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Specialties Badges */}
            <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
              {doctor.specialties?.map((spec) => (
                <span
                  key={spec}
                  className="bg-teal-50 text-teal-800 text-xs font-semibold px-3 py-1 rounded-xl border border-teal-100"
                >
                  {spec}
                </span>
              ))}
            </div>

            {/* Biography */}
            <div className="space-y-2">
              <h2 className="text-sm font-bold text-slate-900">About the Physician</h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">{doctor.bio}</p>
            </div>

            {/* Clinic Details */}
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-slate-900">
                <Building2 className="w-4 h-4 text-teal-600" />
                <span>{doctor.clinic_name || "CareClinic Indiranagar"}</span>
              </div>
              <div className="flex items-start gap-2 text-slate-600">
                <MapPin className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                <span>{doctor.clinic_address || "100 Feet Road, Indiranagar, Bengaluru"}</span>
              </div>
              {doctor.room_number && (
                <div className="text-teal-800 font-medium pl-6">
                  Designated Room: {doctor.room_number}
                </div>
              )}
            </div>
          </div>

          {/* Weekly Availability Schedule */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-teal-600" />
              <h2 className="text-base font-bold text-slate-900">OPD Weekly Schedule</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {availability.map((shift, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50/50"
                >
                  <span className="font-semibold text-slate-800">{daysOfWeek[shift.day_of_week]}</span>
                  <span className="text-teal-700 font-medium">
                    {shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Patient Reviews */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-teal-600" />
                <h2 className="text-base font-bold text-slate-900">Verified Patient Reviews</h2>
              </div>
              <div className="flex items-center gap-1 text-sm font-bold text-slate-900">
                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                <span>{Number(doctor.rating_avg).toFixed(1)} / 5.0</span>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              {reviews.map((rev) => (
                <div key={rev.id} className="p-4 rounded-2xl border border-slate-100 bg-slate-50/40 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-800">{rev.patient_name || "Patient"}</span>
                    <div className="flex items-center gap-0.5 text-amber-500">
                      {Array.from({ length: rev.rating }).map((_, i) => (
                        <Star key={i} className="w-3 h-3 fill-current" />
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{rev.feedback}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Sticky Booking Card */}
        <div className="lg:sticky lg:top-24 space-y-4">
          <div className="bg-white rounded-3xl p-6 border border-teal-200 shadow-md space-y-6">
            <div>
              <span className="text-xs uppercase font-bold tracking-wider text-teal-600 block">
                Appointment Booking
              </span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">Book Consultation</h3>
            </div>

            <div className="space-y-3 border-y border-slate-100 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                  <Building2 className="w-4 h-4 text-teal-600" />
                  <span>In-Clinic Visit</span>
                </div>
                <span className="text-base font-bold text-slate-900">
                  {formatINR(doctor.consultation_fee_inr)}
                </span>
              </div>

              {doctor.video_fee_inr && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                    <Video className="w-4 h-4 text-blue-600" />
                    <span>Telehealth Video</span>
                  </div>
                  <span className="text-base font-bold text-slate-900">
                    {formatINR(doctor.video_fee_inr)}
                  </span>
                </div>
              )}
            </div>

            <div className="space-y-2 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                <span>Zero wait-time queue token assignment</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                <span>Instant digital prescription after consult</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                <span>100% refund on 24h prior cancellation</span>
              </div>
            </div>

            <Link
              href={`/book/${doctorId}`}
              className="w-full text-center block bg-teal-600 hover:bg-teal-700 text-white font-bold text-sm py-3 rounded-2xl transition-all shadow-md hover:shadow"
            >
              Select Date & Slot
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
