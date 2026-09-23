"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Calendar as CalendarIcon,
  Clock,
  Building2,
  Video,
  User,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  ChevronRight,
} from "lucide-react";
import {
  defaultApiClient,
  formatINR,
  formatSlotTime,
  type DoctorProfile,
  type AvailableSlot,
  type FamilyMember,
} from "@careclinic/shared";

export default function BookAppointmentPage() {
  const params = useParams();
  const router = useRouter();
  const doctorId = (params?.doctorId as string) || "doc-1";

  const [doctor, setDoctor] = useState<DoctorProfile | null>(null);
  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [selectedMode, setSelectedMode] = useState<"in_clinic" | "video">("in_clinic");
  const [selectedPatient, setSelectedPatient] = useState<string>("self");
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Dates for next 7 days
  const dateOptions = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);
    const dayLabel = i === 0 ? "Today" : i === 1 ? "Tomorrow" : d.toLocaleDateString("en-US", { weekday: "short" });
    const dayNum = d.getDate();
    const month = d.toLocaleDateString("en-US", { month: "short" });
    return { dateStr, dayLabel, dayNum, month };
  });

  useEffect(() => {
    async function loadDoctorAndFamily() {
      try {
        const [docRes, famRes] = await Promise.allSettled([
          defaultApiClient.getDoctor(doctorId),
          defaultApiClient.getFamilyMembers(),
        ]);

        if (docRes.status === "fulfilled" && docRes.value.doctor) {
          setDoctor(docRes.value.doctor);
        } else {
          setDoctor({
            doctor_id: doctorId,
            full_name: "Dr. Rajesh Varma, MD",
            qualification: "MD, DM (Cardiology)",
            specialties: ["Cardiology"],
            experience_years: 18,
            consultation_fee_inr: 800,
            video_fee_inr: 700,
            room_number: "OPD 101",
            license_number: "KMC-48291",
            rating_avg: 4.9,
            rating_count: 142,
            is_accepting_patients: true,
          });
        }

        if (famRes.status === "fulfilled" && famRes.value.familyMembers) {
          setFamilyMembers(famRes.value.familyMembers);
        } else {
          setFamilyMembers([
            { id: "fam-1", primary_patient_id: "pat-1", full_name: "Aarav Deshmukh", relationship: "Child", blood_group: "O+" },
            { id: "fam-2", primary_patient_id: "pat-1", full_name: "Sunita Deshmukh", relationship: "Parent", blood_group: "B+" },
          ]);
        }
      } catch {
        // fallback
      }
    }

    loadDoctorAndFamily();
  }, [doctorId]);

  // Load slots whenever doctor or selectedDate changes
  useEffect(() => {
    async function loadSlots() {
      setLoadingSlots(true);
      setSelectedSlot(null);
      setError("");

      try {
        const res = await defaultApiClient.getDoctorSlots(doctorId, selectedDate);
        setSlots(res.slots || []);
      } catch {
        // Static slots fallback for offline previews
        const staticSlots: AvailableSlot[] = [
          { startTime: "09:00:00", endTime: "09:20:00", label: "09:00 AM", available: true },
          { startTime: "09:20:00", endTime: "09:40:00", label: "09:20 AM", available: true },
          { startTime: "09:40:00", endTime: "10:00:00", label: "09:40 AM", available: false },
          { startTime: "10:00:00", endTime: "10:20:00", label: "10:00 AM", available: true },
          { startTime: "10:20:00", endTime: "10:40:00", label: "10:20 AM", available: true },
          { startTime: "10:40:00", endTime: "11:00:00", label: "10:40 AM", available: true },
          { startTime: "11:00:00", endTime: "11:20:00", label: "11:00 AM", available: false },
          { startTime: "11:20:00", endTime: "11:40:00", label: "11:20 AM", available: true },
          { startTime: "11:40:00", endTime: "12:00:00", label: "11:40 AM", available: true },
          { startTime: "12:00:00", endTime: "12:20:00", label: "12:00 PM", available: true },
          { startTime: "12:20:00", endTime: "12:40:00", label: "12:20 PM", available: true },
          { startTime: "12:40:00", endTime: "13:00:00", label: "12:40 PM", available: true },
        ];
        setSlots(staticSlots);
      } finally {
        setLoadingSlots(false);
      }
    }

    if (doctorId && selectedDate) {
      loadSlots();
    }
  }, [doctorId, selectedDate]);

  const handleBooking = async () => {
    if (!selectedSlot) {
      setError("Please select an available consultation slot.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const res = await defaultApiClient.bookAppointment({
        doctorId,
        appointmentType: selectedMode,
        scheduledDate: selectedDate,
        startTime: selectedSlot,
        forFamilyMemberId: selectedPatient === "self" ? undefined : selectedPatient,
        notes: notes || undefined,
        paymentMethod: "upi",
      });

      // Redirect to payment checkout
      router.push(`/checkout/${res.appointment.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to book appointment. Please try another slot.");
      setSubmitting(false);
    }
  };

  const currentFee =
    selectedMode === "video"
      ? doctor?.video_fee_inr || doctor?.consultation_fee_inr || 700
      : doctor?.consultation_fee_inr || 800;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <Link
          href={`/doctors/${doctorId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-teal-700 transition-colors mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Doctor Profile
        </Link>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Schedule Appointment
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Select consultation mode, date, and 20-minute slot window.
        </p>
      </div>

      {/* Selected Doctor Summary Card */}
      {doctor && (
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 font-bold flex items-center justify-center text-lg shrink-0">
              {doctor.full_name ? doctor.full_name.replace("Dr. ", "").charAt(0) : "D"}
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">{doctor.full_name}</h3>
              <p className="text-xs text-teal-700 font-medium">{doctor.qualification}</p>
              <p className="text-[11px] text-slate-400">
                {doctor.specialties?.join(", ")} • Room: {doctor.room_number || "OPD 101"}
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Consultation Fee</div>
            <div className="text-base font-extrabold text-slate-900">{formatINR(currentFee)}</div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Step 1: Consultation Mode */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-teal-600 text-white text-[11px] flex items-center justify-center">1</span>
          Select Consultation Mode
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setSelectedMode("in_clinic")}
            className={`p-4 rounded-2xl border text-left transition-all cursor-pointer flex items-start gap-3 ${
              selectedMode === "in_clinic"
                ? "border-teal-500 bg-teal-50/50 ring-2 ring-teal-200"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="p-2.5 rounded-xl bg-teal-100/70 text-teal-700 shrink-0">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <span className="text-sm font-bold text-slate-900 block">In-Clinic Consultation</span>
              <span className="text-xs text-slate-500 block mt-0.5">
                CareClinic Indiranagar • Room {doctor?.room_number || "OPD 101"}
              </span>
              <span className="text-xs font-semibold text-teal-800 mt-1 block">
                {formatINR(doctor?.consultation_fee_inr || 800)}
              </span>
            </div>
          </button>

          <button
            type="button"
            onClick={() => setSelectedMode("video")}
            className={`p-4 rounded-2xl border text-left transition-all cursor-pointer flex items-start gap-3 ${
              selectedMode === "video"
                ? "border-teal-500 bg-teal-50/50 ring-2 ring-teal-200"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="p-2.5 rounded-xl bg-blue-100/70 text-blue-700 shrink-0">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <span className="text-sm font-bold text-slate-900 block">Telehealth Video Call</span>
              <span className="text-xs text-slate-500 block mt-0.5">
                Encrypted in-browser WebRTC consultation
              </span>
              <span className="text-xs font-semibold text-blue-800 mt-1 block">
                {formatINR(doctor?.video_fee_inr || 700)}
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* Step 2: Patient Selection */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-teal-600 text-white text-[11px] flex items-center justify-center">2</span>
          Who is this visit for?
        </h2>

        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            onClick={() => setSelectedPatient("self")}
            className={`px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5 ${
              selectedPatient === "self"
                ? "bg-teal-600 text-white border-teal-600 shadow-xs"
                : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Self (Ananya Deshmukh)</span>
          </button>

          {familyMembers.map((fam) => (
            <button
              key={fam.id}
              type="button"
              onClick={() => setSelectedPatient(fam.id)}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5 ${
                selectedPatient === fam.id
                  ? "bg-teal-600 text-white border-teal-600 shadow-xs"
                  : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
              }`}
            >
              <span>{fam.full_name}</span>
              <span className="text-[10px] opacity-80">({fam.relationship})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Step 3: Date Picker */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-teal-600 text-white text-[11px] flex items-center justify-center">3</span>
          Select Consultation Date
        </h2>

        <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
          {dateOptions.map((opt) => {
            const isSelected = selectedDate === opt.dateStr;
            return (
              <button
                key={opt.dateStr}
                type="button"
                onClick={() => setSelectedDate(opt.dateStr)}
                className={`py-3 px-2 rounded-2xl border text-center transition-all cursor-pointer ${
                  isSelected
                    ? "bg-teal-600 text-white border-teal-600 shadow-xs"
                    : "bg-white text-slate-700 border-slate-200 hover:border-teal-200"
                }`}
              >
                <span className="text-[10px] uppercase font-semibold block opacity-80">
                  {opt.dayLabel}
                </span>
                <span className="text-lg font-bold block my-0.5">{opt.dayNum}</span>
                <span className="text-[10px] block opacity-80">{opt.month}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step 4: 20-Min Dynamic Slot Picker */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-teal-600 text-white text-[11px] flex items-center justify-center">4</span>
            Select 20-Minute Time Slot
          </h2>
          <span className="text-xs text-slate-400">Strict zero double-booking policy</span>
        </div>

        {loadingSlots ? (
          <div className="p-8 text-center text-xs text-slate-400">Calculating available slot windows...</div>
        ) : slots.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded-2xl">
            No consultation slots available on this date. Please select another date.
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
            {slots.map((s, idx) => {
              const isSelected = selectedSlot === s.startTime;
              return (
                <button
                  key={idx}
                  type="button"
                  disabled={!s.available}
                  onClick={() => setSelectedSlot(s.startTime)}
                  className={`py-2.5 px-2 rounded-xl text-xs font-semibold border transition-all text-center ${
                    !s.available
                      ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed line-through"
                      : isSelected
                      ? "bg-teal-600 text-white border-teal-600 shadow-xs cursor-pointer"
                      : "bg-white text-slate-700 border-slate-200 hover:border-teal-400 hover:text-teal-700 cursor-pointer"
                  }`}
                >
                  {formatSlotTime(s.startTime)}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Step 5: Symptoms & Notes */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-3">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-teal-600 text-white text-[11px] flex items-center justify-center">5</span>
          Symptoms & Reason for Visit (Optional)
        </h2>
        <textarea
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Briefly describe your symptoms, current discomfort, or follow-up reason for the doctor..."
          className="w-full text-xs p-3 border border-slate-200 rounded-2xl focus:border-teal-500 focus:outline-hidden"
        ></textarea>
      </div>

      {/* Booking CTA Bar */}
      <div className="bg-white rounded-3xl p-6 border border-teal-200 shadow-md flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500">
            Selected:{" "}
            <strong>
              {selectedDate} at {selectedSlot ? formatSlotTime(selectedSlot) : "--:--"}
            </strong>
          </div>
          <div className="text-sm font-extrabold text-slate-900 mt-0.5">
            Total Payable: {formatINR(currentFee)}
          </div>
        </div>

        <button
          type="button"
          onClick={handleBooking}
          disabled={submitting || !selectedSlot}
          className="w-full sm:w-auto bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 text-white font-bold text-sm px-8 py-3 rounded-2xl transition-all shadow-md cursor-pointer flex items-center justify-center gap-2"
        >
          {submitting ? "Reserving Slot..." : "Proceed to Payment"}
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
