"use client";

import { useState, useEffect } from "react";
import { Search, Filter, Stethoscope, Video, Building2, Star, ArrowUpDown } from "lucide-react";
import { defaultApiClient, type DoctorProfile } from "@careclinic/shared";
import { DoctorCard } from "@/components/doctor-card";

export default function DoctorsDirectoryPage() {
  const [doctors, setDoctors] = useState<DoctorProfile[]>([]);
  const [specialties, setSpecialties] = useState<{ specialty: string; doctor_count: number }[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>("All");
  const [selectedMode, setSelectedMode] = useState<"all" | "in_clinic" | "video">("all");
  const [sortBy, setSortBy] = useState<"rating" | "fee_asc" | "fee_desc" | "experience">("rating");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDirectory() {
      try {
        const [docsRes, specRes] = await Promise.allSettled([
          defaultApiClient.getDoctors(),
          defaultApiClient.getSpecialties(),
        ]);

        if (docsRes.status === "fulfilled" && docsRes.value.doctors) {
          setDoctors(docsRes.value.doctors);
        } else {
          // Fallback static list
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
            {
              doctor_id: "doc-5",
              full_name: "Dr. Vikram Sethi, MD",
              license_number: "KMC-55904",
              qualification: "MD (General Medicine)",
              specialties: ["General Medicine", "Diabetology"],
              experience_years: 14,
              consultation_fee_inr: 600,
              video_fee_inr: 500,
              bio: "Family physician and diabetologist focused on metabolic syndrome management, lifestyle counseling, and chronic disease prevention.",
              room_number: "OPD 103",
              rating_avg: 4.8,
              rating_count: 110,
              is_accepting_patients: true,
            },
            {
              doctor_id: "doc-6",
              full_name: "Dr. Meenakshi Raman, MD",
              license_number: "KMC-70192",
              qualification: "MD, DM (Neurology)",
              specialties: ["Neurology"],
              experience_years: 15,
              consultation_fee_inr: 1000,
              video_fee_inr: 900,
              bio: "Consultant neurologist specializing in migraine disorders, peripheral neuropathy, epilepsy management, and neuro-rehabilitation.",
              room_number: "OPD 205",
              rating_avg: 4.9,
              rating_count: 94,
              is_accepting_patients: true,
            },
          ]);
        }

        if (specRes.status === "fulfilled" && specRes.value.specialties) {
          setSpecialties(specRes.value.specialties);
        } else {
          setSpecialties([
            { specialty: "Cardiology", doctor_count: 2 },
            { specialty: "Pediatrics", doctor_count: 2 },
            { specialty: "Dermatology", doctor_count: 2 },
            { specialty: "Orthopedics", doctor_count: 2 },
            { specialty: "General Medicine", doctor_count: 2 },
            { specialty: "Neurology", doctor_count: 1 },
            { specialty: "Gynecology", doctor_count: 1 },
          ]);
        }
      } finally {
        setLoading(false);
      }
    }

    loadDirectory();
  }, []);

  // Filter & Sort Logic
  const filteredDoctors = doctors
    .filter((doc) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesName = doc.full_name?.toLowerCase().includes(q);
        const matchesSpec = doc.specialties?.some((s) => s.toLowerCase().includes(q));
        const matchesQual = doc.qualification?.toLowerCase().includes(q);
        if (!matchesName && !matchesSpec && !matchesQual) return false;
      }

      if (selectedSpecialty !== "All") {
        if (!doc.specialties?.includes(selectedSpecialty)) return false;
      }

      if (selectedMode === "video" && !doc.video_fee_inr) return false;

      return true;
    })
    .sort((a, b) => {
      if (sortBy === "rating") {
        return Number(b.rating_avg) - Number(a.rating_avg);
      }
      if (sortBy === "fee_asc") {
        return a.consultation_fee_inr - b.consultation_fee_inr;
      }
      if (sortBy === "fee_desc") {
        return b.consultation_fee_inr - a.consultation_fee_inr;
      }
      if (sortBy === "experience") {
        return b.experience_years - a.experience_years;
      }
      return 0;
    });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Find a Doctor
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Explore qualified specialists, compare consultation fees, and schedule visits online.
        </p>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Search Input */}
          <div className="md:col-span-2 relative flex items-center">
            <Search className="w-5 h-5 text-slate-400 absolute left-3.5" />
            <input
              type="text"
              placeholder="Search by doctor name, specialty, or condition..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
            />
          </div>

          {/* Sort Dropdown */}
          <div className="relative flex items-center">
            <ArrowUpDown className="w-4 h-4 text-slate-400 absolute left-3.5" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="w-full pl-10 pr-8 py-2.5 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden bg-white text-slate-700"
            >
              <option value="rating">Sort by: Highest Rated</option>
              <option value="experience">Sort by: Most Experienced</option>
              <option value="fee_asc">Sort by: Fee (Low to High)</option>
              <option value="fee_desc">Sort by: Fee (High to Low)</option>
            </select>
          </div>
        </div>

        {/* Mode & Specialty Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
          {/* Specialty Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1 max-w-3xl">
            <button
              onClick={() => setSelectedSpecialty("All")}
              className={`text-xs px-3 py-1.5 rounded-xl font-medium transition-colors cursor-pointer ${
                selectedSpecialty === "All"
                  ? "bg-teal-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              All Specialties
            </button>
            {specialties.map((spec) => (
              <button
                key={spec.specialty}
                onClick={() => setSelectedSpecialty(spec.specialty)}
                className={`text-xs px-3 py-1.5 rounded-xl font-medium transition-colors cursor-pointer ${
                  selectedSpecialty === spec.specialty
                    ? "bg-teal-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {spec.specialty} ({spec.doctor_count})
              </button>
            ))}
          </div>

          {/* Mode Selector Toggle */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold text-slate-600 shrink-0">
            <button
              onClick={() => setSelectedMode("all")}
              className={`px-3 py-1 rounded-lg transition-colors cursor-pointer ${
                selectedMode === "all" ? "bg-white text-teal-800 shadow-xs" : "hover:text-slate-900"
              }`}
            >
              All Modes
            </button>
            <button
              onClick={() => setSelectedMode("in_clinic")}
              className={`px-3 py-1 rounded-lg transition-colors cursor-pointer flex items-center gap-1 ${
                selectedMode === "in_clinic" ? "bg-white text-teal-800 shadow-xs" : "hover:text-slate-900"
              }`}
            >
              <Building2 className="w-3 h-3" />
              In-Clinic
            </button>
            <button
              onClick={() => setSelectedMode("video")}
              className={`px-3 py-1 rounded-lg transition-colors cursor-pointer flex items-center gap-1 ${
                selectedMode === "video" ? "bg-white text-teal-800 shadow-xs" : "hover:text-slate-900"
              }`}
            >
              <Video className="w-3 h-3" />
              Video
            </button>
          </div>
        </div>
      </div>

      {/* Doctors Grid */}
      <div>
        <div className="flex items-center justify-between text-xs text-slate-500 mb-4">
          <span>Showing {filteredDoctors.length} available physicians</span>
          {selectedSpecialty !== "All" && (
            <span>
              Filtered by: <strong className="text-teal-700">{selectedSpecialty}</strong>
            </span>
          )}
        </div>

        {filteredDoctors.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 text-center border border-slate-200">
            <Stethoscope className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-800">No physicians found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              We couldn’t find doctors matching your search filters. Try resetting the specialty filter.
            </p>
            <button
              onClick={() => {
                setSelectedSpecialty("All");
                setSearchQuery("");
                setSelectedMode("all");
              }}
              className="mt-4 px-4 py-2 bg-teal-50 text-teal-700 hover:bg-teal-100 text-xs font-semibold rounded-xl"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDoctors.map((doc) => (
              <DoctorCard key={doc.doctor_id} doctor={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
