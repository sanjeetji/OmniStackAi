"use client";

import { useState } from "react";
import {
  Star,
  ShieldCheck,
  CheckCircle2,
  TrendingUp,
  MessageSquare,
  ThumbsUp,
  Filter,
  User,
  Heart,
  Activity,
  Award,
} from "lucide-react";

interface PatientReview {
  id: string;
  patientName: string;
  appointmentType: "In-Clinic OPD" | "Telehealth Video";
  rating: number;
  date: string;
  condition: string;
  verifiedToken: string;
  comment: string;
  tags: string[];
  doctorReply?: string;
}

const REVIEWS: PatientReview[] = [
  {
    id: "rev-1",
    patientName: "Ananya Deshmukh",
    appointmentType: "In-Clinic OPD",
    rating: 5,
    date: "22 Sep 2026",
    condition: "Hypertension Management",
    verifiedToken: "OPD-TK-001",
    comment:
      "Dr. Rajesh Varma took the time to meticulously explain my 24-hr ambulatory BP report. He adjusted my Telmisartan dosage without jumping straight to higher combinations, and gave very practical dietary advice on sodium intake. Outstanding physician!",
    tags: ["Thorough Explanation", "Rational Prescribing", "Patient Centered"],
    doctorReply:
      "Thank you Ananya. Keep monitoring your morning BP readings twice a week as discussed. See you in 4 weeks!",
  },
  {
    id: "rev-2",
    patientName: "Vikram Malhotra",
    appointmentType: "Telehealth Video",
    rating: 5,
    date: "18 Sep 2026",
    condition: "Diabetic Dyslipidemia Review",
    verifiedToken: "TEL-TK-042",
    comment:
      "The video consultation felt just as comprehensive as an in-person visit. Dr. Varma reviewed my lipid profile screen-shared on the call and uploaded the digital signed prescription within 2 minutes. Very seamless experience.",
    tags: ["Punctual Video Call", "Instant Digital Rx", "Clear Lipid Targets"],
  },
  {
    id: "rev-3",
    patientName: "Sunita Ramanathan",
    appointmentType: "In-Clinic OPD",
    rating: 5,
    date: "15 Sep 2026",
    condition: "Post-CABG Cardiac Follow-up",
    verifiedToken: "OPD-TK-008",
    comment:
      "My family has trusted Dr. Varma for post-bypass rehabilitation. He examined my chest auscultation, checked for pedal edema, and answered all our anxiety-related questions with great warmth.",
    tags: ["Compassionate Care", "Cardiac Specialist", "Excellent Auscultation"],
  },
  {
    id: "rev-4",
    patientName: "Arjun Nair",
    appointmentType: "In-Clinic OPD",
    rating: 4,
    date: "10 Sep 2026",
    condition: "Chest Tightness & Exercise Tolerance",
    verifiedToken: "OPD-TK-014",
    comment:
      "Dr. Varma was very attentive and ordered an immediate ECG which was normal. The clinic wait time was slightly longer than estimated (25 mins past slot), but the consultation itself was top-tier.",
    tags: ["Accurate Diagnostics", "Minor Wait Time", "Professional"],
  },
  {
    id: "rev-5",
    patientName: "Meera Kulkarni",
    appointmentType: "Telehealth Video",
    rating: 5,
    date: "02 Sep 2026",
    condition: "Hypothyroidism & Palpitations",
    verifiedToken: "TEL-TK-019",
    comment:
      "Reassuring demeanor. Clearly outlined why my palpitations were anxiety-related rather than thyroid storm. Prescribed routine Holter monitoring to be safe.",
    tags: ["Empathetic", "Evidence Based", "Reassuring"],
  },
];

export default function DoctorReviewsPage() {
  const [filterRating, setFilterRating] = useState<number | "all">("all");
  const [filterType, setFilterType] = useState<string>("all");

  const filteredReviews = REVIEWS.filter((r) => {
    const matchesRating = filterRating === "all" || r.rating === filterRating;
    const matchesType =
      filterType === "all" ||
      (filterType === "clinic" && r.appointmentType === "In-Clinic OPD") ||
      (filterType === "telehealth" && r.appointmentType === "Telehealth Video");
    return matchesRating && matchesType;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <ShieldCheck className="w-3.5 h-3.5" />
              100% Verified Patient Audits
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Patient Satisfaction & Clinical Reviews
          </h1>
          <p className="text-sm text-slate-500">
            Real-time feedback collected post-consultation with verified token cross-referencing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="bg-white border border-slate-200 px-4 py-2 rounded-xl shadow-xs text-right">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Department Rank
            </span>
            <span className="text-sm font-black text-emerald-700 flex items-center gap-1 justify-end">
              <Award className="w-4 h-4 text-amber-500" />
              #1 in Cardiology (Q3)
            </span>
          </div>
        </div>
      </div>

      {/* Hero Benchmark Rating Strip */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scorecard */}
        <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 block mb-2">
              Overall Clinical Rating
            </span>
            <div className="flex items-baseline gap-3">
              <span className="text-5xl font-black text-white">4.9</span>
              <span className="text-slate-400 text-lg font-bold">/ 5.0</span>
            </div>

            <div className="flex items-center gap-1 text-amber-400 my-3">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className="w-5 h-5 fill-amber-400 text-amber-400"
                />
              ))}
            </div>

            <p className="text-xs text-slate-300">
              Aggregated across 312 verified in-clinic consultations and telehealth video appointments.
            </p>
          </div>

          <div className="pt-4 mt-4 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Department Avg: 4.6</span>
            <span className="text-emerald-400 font-bold">+0.3 above benchmark</span>
          </div>
        </div>

        {/* Breakdown by Star Rating */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Rating Distribution
          </h3>

          <div className="space-y-2.5">
            {[
              { stars: 5, pct: 92, count: 287 },
              { stars: 4, pct: 6, count: 19 },
              { stars: 3, pct: 1.5, count: 5 },
              { stars: 2, pct: 0.5, count: 1 },
              { stars: 1, pct: 0, count: 0 },
            ].map((row) => (
              <div key={row.stars} className="flex items-center gap-3 text-xs">
                <span className="w-12 font-bold text-slate-700 flex items-center gap-1">
                  <span>{row.stars}</span>
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                </span>
                <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-600 h-full rounded-full"
                    style={{ width: `${row.pct}%` }}
                  ></div>
                </div>
                <span className="w-10 text-right font-mono text-slate-400 text-[11px]">
                  {row.count}
                </span>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Net Promoter Score (NPS)</span>
            <span className="font-bold text-emerald-700 font-mono text-xs">+94</span>
          </div>
        </div>

        {/* Quality Pillars */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Clinical Quality Pillars
          </h3>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-700">Diagnosis & Medication Clarity</span>
                <span className="text-emerald-700 font-bold">4.95 / 5.0</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-600 h-full w-[99%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-700">Empathy & Active Listening</span>
                <span className="text-emerald-700 font-bold">4.98 / 5.0</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-600 h-full w-[99.6%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-700">Treatment Efficacy & Follow-up</span>
                <span className="text-emerald-700 font-bold">4.91 / 5.0</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-600 h-full w-[98.2%]"></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-700">OPD Wait Time Management</span>
                <span className="text-slate-700 font-bold">4.72 / 5.0</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="bg-teal-600 h-full w-[94.4%]"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Review Filters & Feed */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Verified Patient Testimonials
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={filterRating === "all" ? "all" : String(filterRating)}
              onChange={(e) =>
                setFilterRating(e.target.value === "all" ? "all" : Number(e.target.value))
              }
              className="text-xs px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-700"
            >
              <option value="all">All Star Ratings</option>
              <option value="5">5 Stars Only</option>
              <option value="4">4 Stars Only</option>
            </select>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="text-xs px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-700"
            >
              <option value="all">All Channels</option>
              <option value="clinic">In-Clinic OPD</option>
              <option value="telehealth">Telehealth Video</option>
            </select>
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {filteredReviews.map((review) => (
            <div key={review.id} className="p-5 space-y-3 hover:bg-slate-50/50 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-bold flex items-center justify-center text-xs">
                    {review.patientName
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">
                        {review.patientName}
                      </span>
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        Verified Consultation
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                      <span>{review.appointmentType}</span>
                      <span>•</span>
                      <span>Token #{review.verifiedToken}</span>
                      <span>•</span>
                      <span>{review.condition}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <div className="flex items-center gap-0.5 text-amber-400">
                    {[...Array(review.rating)].map((_, i) => (
                      <Star
                        key={i}
                        className="w-4 h-4 fill-amber-400 text-amber-400"
                      />
                    ))}
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {review.date}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-700 leading-relaxed">
                "{review.comment}"
              </p>

              <div className="flex flex-wrap items-center gap-1.5">
                {review.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[11px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md"
                  >
                    #{tag}
                  </span>
                ))}
              </div>

              {review.doctorReply && (
                <div className="mt-2 p-3 bg-emerald-50/60 rounded-xl border border-emerald-200/60 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-900 text-[11px]">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Response from Dr. Rajesh Varma, MD</span>
                  </div>
                  <p className="text-emerald-800 text-[11px] italic">
                    "{review.doctorReply}"
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
