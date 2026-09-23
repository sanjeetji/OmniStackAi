"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Users,
  UserPlus,
  Heart,
  Calendar,
  X,
  Plus,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import { defaultApiClient, type FamilyMember } from "@careclinic/shared";

export default function FamilyMembersPage() {
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [relationship, setRelationship] = useState("Child");
  const [dob, setDob] = useState("");
  const [gender, setGender] = useState("male");
  const [bloodGroup, setBloodGroup] = useState("O+");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const loadMembers = async () => {
    try {
      const res = await defaultApiClient.getFamilyMembers();
      setMembers(res.familyMembers || []);
    } catch {
      // Fallback preview
      setMembers([
        {
          id: "fam-1",
          primary_patient_id: "pat-1",
          full_name: "Aarav Deshmukh",
          relationship: "Child",
          dob: "2018-04-12",
          gender: "Male",
          blood_group: "O+",
        },
        {
          id: "fam-2",
          primary_patient_id: "pat-1",
          full_name: "Sunita Deshmukh",
          relationship: "Parent",
          dob: "1960-11-20",
          gender: "Female",
          blood_group: "B+",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, []);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) return;

    setSubmitting(true);
    setError("");

    try {
      await defaultApiClient.addFamilyMember({
        fullName: fullName.trim(),
        relationship,
        dob: dob || undefined,
        gender: gender || undefined,
        bloodGroup: bloodGroup || undefined,
      });
      setModalOpen(false);
      setFullName("");
      loadMembers();
    } catch (err: any) {
      setError(err.message || "Failed to add family member");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Family Health Profiles
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage dependent medical charts, book appointments for children or parents from a single account.
          </p>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs sm:text-sm px-4 py-2.5 rounded-2xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
        >
          <UserPlus className="w-4 h-4" />
          <span>Add Family Member</span>
        </button>
      </div>

      {/* Primary Patient Card */}
      <div className="bg-teal-900 text-white rounded-3xl p-6 sm:p-8 border border-teal-800 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-teal-700/80 text-teal-100 font-black text-xl flex items-center justify-center">
            AD
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-teal-300 tracking-wider">
              Primary Account Holder
            </span>
            <h2 className="text-xl font-bold text-white">Ananya Deshmukh</h2>
            <p className="text-xs text-teal-200/80">UHID: CC-PAT-001 • Age: 32 Yrs • Blood Group: O+</p>
          </div>
        </div>

        <Link
          href="/records"
          className="text-xs font-semibold text-teal-200 hover:text-white bg-teal-800/80 hover:bg-teal-700 px-4 py-2 rounded-xl transition-colors"
        >
          View Personal Records
        </Link>
      </div>

      {/* Dependents Grid */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
          Linked Dependents ({members.length})
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {members.map((member) => (
            <div
              key={member.id}
              className="bg-white rounded-3xl p-6 border border-slate-200 hover:border-teal-200 shadow-xs hover:shadow-md transition-all flex flex-col justify-between space-y-4"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-100">
                    {member.relationship}
                  </span>
                  <h3 className="text-base font-bold text-slate-900 mt-1">{member.full_name}</h3>
                  <div className="flex items-center gap-3 text-xs text-slate-500 pt-0.5">
                    {member.dob && <span>DOB: {member.dob}</span>}
                    {member.blood_group && <span>• Blood: {member.blood_group}</span>}
                    {member.gender && <span>• {member.gender}</span>}
                  </div>
                </div>

                <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 font-bold flex items-center justify-center text-sm">
                  {member.full_name.charAt(0)}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400">Linked to primary account</span>
                <Link
                  href="/doctors"
                  className="bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-xl transition-all shadow-xs flex items-center gap-1"
                >
                  <span>Book for {member.full_name.split(" ")[0]}</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Family Member Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-xl border border-slate-200 relative animate-fade-in space-y-4">
            <button
              onClick={() => setModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
                <UserPlus className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Add Family Member</h3>
                <p className="text-xs text-slate-500">Create dependent profile for unified care</p>
              </div>
            </div>

            {error && (
              <div className="text-xs bg-rose-50 text-rose-700 p-2.5 rounded-xl border border-rose-200">
                {error}
              </div>
            )}

            <form onSubmit={handleAddMember} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rohan Deshmukh"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Relationship
                  </label>
                  <select
                    value={relationship}
                    onChange={(e) => setRelationship(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden bg-white"
                  >
                    <option value="Child">Child</option>
                    <option value="Spouse">Spouse</option>
                    <option value="Parent">Parent</option>
                    <option value="Sibling">Sibling</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Gender
                  </label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden bg-white"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Date of Birth
                  </label>
                  <input
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Blood Group
                  </label>
                  <select
                    value={bloodGroup}
                    onChange={(e) => setBloodGroup(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden bg-white"
                  >
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-xs"
                >
                  {submitting ? "Saving..." : "Add Dependent"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
