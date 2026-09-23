import Link from "next/link";
import { Star, Clock, Video, Building2, Award } from "lucide-react";
import { formatINR, type DoctorProfile } from "@careclinic/shared";

export function DoctorCard({ doctor }: { doctor: DoctorProfile }) {
  // The public directory returns the user's `id`; rows joined from doctor_profiles carry
  // `doctor_id`. Either is the id the profile and booking pages expect.
  const doctorId = doctor.id ?? doctor.doctor_id;
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 hover:border-teal-300 hover:shadow-md transition-all flex flex-col justify-between group">
      <div>
        {/* Doctor Header & Avatar */}
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-2xl bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center font-bold text-xl shrink-0 overflow-hidden relative">
            {doctor.avatar_url ? (
              <img
                src={doctor.avatar_url}
                alt={doctor.full_name || "Doctor"}
                className="w-full h-full object-cover"
              />
            ) : (
              <span>{doctor.full_name ? doctor.full_name.replace("Dr. ", "").charAt(0) : "D"}</span>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-1">
              <h3 className="text-base font-bold text-slate-900 group-hover:text-teal-700 transition-colors truncate">
                {doctor.full_name}
              </h3>
              <div className="flex items-center gap-1 bg-amber-50 text-amber-800 px-2 py-0.5 rounded-lg text-xs font-semibold shrink-0">
                <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                <span>{Number(doctor.rating_avg).toFixed(1)}</span>
                <span className="text-amber-600/70 font-normal">({doctor.rating_count})</span>
              </div>
            </div>

            <p className="text-xs text-teal-700 font-medium mt-0.5">{doctor.qualification}</p>

            <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-1">
              <Award className="w-3.5 h-3.5 text-slate-400" />
              <span>{doctor.experience_years} years experience</span>
            </div>
          </div>
        </div>

        {/* Specialties Badges */}
        <div className="flex flex-wrap gap-1.5 mt-3.5">
          {doctor.specialties?.map((spec) => (
            <span
              key={spec}
              className="inline-block text-[11px] font-medium bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-md"
            >
              {spec}
            </span>
          ))}
        </div>

        {/* Doctor Bio Snippet */}
        {doctor.bio && (
          <p className="text-xs text-slate-600 line-clamp-2 mt-2.5 leading-relaxed">
            {doctor.bio}
          </p>
        )}
      </div>

      {/* Footer: Fees & Action */}
      <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
        <div>
          <div className="text-[10px] text-slate-400 uppercase font-semibold">Consultation Fee</div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-slate-900">
              {formatINR(doctor.consultation_fee_inr)}
            </span>
            {doctor.video_fee_inr && (
              <span className="text-[11px] text-teal-600 flex items-center gap-0.5" title="Video Consult">
                <Video className="w-3 h-3" />
                {formatINR(doctor.video_fee_inr)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`/doctors/${doctorId}`}
            className="text-xs font-medium text-slate-600 hover:text-teal-700 px-2.5 py-1.5 rounded-lg hover:bg-slate-50"
          >
            Profile
          </Link>
          <Link
            href={`/book/${doctorId}`}
            className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors shadow-sm"
          >
            Book Slot
          </Link>
        </div>
      </div>
    </div>
  );
}
