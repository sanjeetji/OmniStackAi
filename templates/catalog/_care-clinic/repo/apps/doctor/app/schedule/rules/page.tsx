"use client";

import { useState } from "react";
import Link from "next/link";
import {
  CalendarDays,
  ShieldAlert,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  Sliders,
  DollarSign,
  AlertTriangle,
  ArrowLeft,
  Clock,
} from "lucide-react";

interface LeaveOverride {
  id: string;
  date: string;
  type: "full_day" | "partial";
  hours?: string;
  reason: string;
  status: "approved" | "pending";
}

export default function AvailabilityRulesPage() {
  const [maxInClinicTokens, setMaxInClinicTokens] = useState<number>(25);
  const [maxEmergencyWalkIns, setMaxEmergencyWalkIns] = useState<number>(5);
  const [maxTelehealth, setMaxTelehealth] = useState<number>(10);
  const [inClinicFee, setInClinicFee] = useState<number>(800);
  const [telehealthFee, setTelehealthFee] = useState<number>(600);
  const [freeFollowUpDays, setFreeFollowUpDays] = useState<number>(7);
  const [strictQueueCap, setStrictQueueCap] = useState<boolean>(true);

  const [overrides, setOverrides] = useState<LeaveOverride[]>([
    {
      id: "ov-1",
      date: "2026-10-02",
      type: "full_day",
      reason: "National Holiday (Gandhi Jayanti)",
      status: "approved",
    },
    {
      id: "ov-2",
      date: "2026-10-14",
      type: "full_day",
      reason: "Cardiological Society of India Annual Conclave (Speaker)",
      status: "approved",
    },
    {
      id: "ov-3",
      date: "2026-10-24",
      type: "partial",
      hours: "14:00 - 18:00",
      reason: "Departmental Clinical Audit Meeting",
      status: "approved",
    },
  ]);

  const [showAddModal, setShowAddModal] = useState(false);
  const [newDate, setNewDate] = useState("");
  const [newType, setNewType] = useState<"full_day" | "partial">("full_day");
  const [newHours, setNewHours] = useState("14:00 - 17:00");
  const [newReason, setNewReason] = useState("");
  const [saved, setSaved] = useState(false);

  const handleAddOverride = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDate || !newReason) return;
    const item: LeaveOverride = {
      id: `ov-${Date.now()}`,
      date: newDate,
      type: newType,
      hours: newType === "partial" ? newHours : undefined,
      reason: newReason,
      status: "approved",
    };
    setOverrides([...overrides, item]);
    setNewDate("");
    setNewReason("");
    setShowAddModal(false);
  };

  const removeOverride = (id: string) => {
    setOverrides(overrides.filter((o) => o.id !== id));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              href="/schedule"
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-semibold"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Shift Matrix
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Availability Rules & Leave Overrides
          </h1>
          <p className="text-sm text-slate-500">
            Define daily patient capacity throttles, consultation tariffs, and planned leave exceptions.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold inline-flex items-center gap-2 shadow-xs transition-colors self-start sm:self-auto"
        >
          <Save className="w-4 h-4" />
          <span>Save Rule Set</span>
        </button>
      </div>

      {saved && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span className="font-semibold">
            Availability rules and leave calendar synchronized with front desk booking engine.
          </span>
        </div>
      )}

      {/* Grid: Capacity & Tariffs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Patient Volume Controls */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
            <Sliders className="w-5 h-5 text-emerald-600" />
            <h2 className="font-bold text-slate-900 text-base">
              Daily OPD Capacity Caps
            </h2>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1 text-sm">
                <span className="font-semibold text-slate-700">
                  Maximum In-Clinic Appointments / Day
                </span>
                <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-sm">
                  {maxInClinicTokens} tokens
                </span>
              </div>
              <input
                type="range"
                min="10"
                max="40"
                value={maxInClinicTokens}
                onChange={(e) => setMaxInClinicTokens(Number(e.target.value))}
                className="w-full accent-emerald-600 cursor-pointer"
              />
              <span className="text-[11px] text-slate-400 block mt-0.5">
                Front desk stops regular token issuance once reached.
              </span>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 text-sm">
                <span className="font-semibold text-slate-700">
                  Emergency Walk-in Buffer
                </span>
                <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-sm">
                  {maxEmergencyWalkIns} slots
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                value={maxEmergencyWalkIns}
                onChange={(e) => setMaxEmergencyWalkIns(Number(e.target.value))}
                className="w-full accent-emerald-600 cursor-pointer"
              />
              <span className="text-[11px] text-slate-400 block mt-0.5">
                Reserved strictly for triaged urgent consultations (e.g. chest pain, dyspnea).
              </span>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 text-sm">
                <span className="font-semibold text-slate-700">
                  Telehealth Consultations / Day
                </span>
                <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-sm">
                  {maxTelehealth} sessions
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                value={maxTelehealth}
                onChange={(e) => setMaxTelehealth(Number(e.target.value))}
                className="w-full accent-teal-600 cursor-pointer"
              />
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-800 block">
                  Strict Reception Quota Enforcement
                </span>
                <span className="text-[11px] text-slate-500">
                  Requires doctor approval to exceed daily limits
                </span>
              </div>
              <input
                type="checkbox"
                checked={strictQueueCap}
                onChange={(e) => setStrictQueueCap(e.target.checked)}
                className="w-4 h-4 text-emerald-600 rounded-sm focus:ring-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* Tariffs & Fees */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
            <DollarSign className="w-5 h-5 text-teal-600" />
            <h2 className="font-bold text-slate-900 text-base">
              Consultation Fee Structure
            </h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Standard In-Clinic Consultation Fee (₹)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold">
                  ₹
                </span>
                <input
                  type="number"
                  value={inClinicFee}
                  onChange={(e) => setInClinicFee(Number(e.target.value))}
                  className="w-full pl-8 pr-4 py-2 border border-slate-300 rounded-lg text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <span className="text-[11px] text-slate-400 block mt-1">
                Published rate displayed to patients during online booking.
              </span>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Telemedicine Video Consultation Fee (₹)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold">
                  ₹
                </span>
                <input
                  type="number"
                  value={telehealthFee}
                  onChange={(e) => setTelehealthFee(Number(e.target.value))}
                  className="w-full pl-8 pr-4 py-2 border border-slate-300 rounded-lg text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Free Follow-Up Validity Window
              </label>
              <select
                value={freeFollowUpDays}
                onChange={(e) => setFreeFollowUpDays(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 bg-white"
              >
                <option value={0}>No free follow-up (Regular tariff applies)</option>
                <option value={7}>Within 7 calendar days of primary visit</option>
                <option value={14}>Within 14 calendar days of primary visit</option>
              </select>
              <span className="text-[11px] text-slate-400 block mt-1">
                Reviewing investigations and lab reports without repeating full consultation fee.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Leave Overrides & Emergency Blocks */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Leave Calendar & Schedule Overrides
            </h2>
            <p className="text-xs text-slate-500">
              Block bookings for conferences, emergency leave, or national holidays.
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Leave Override</span>
          </button>
        </div>

        <div className="divide-y divide-slate-100">
          {overrides.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              No leave overrides recorded. Regular weekly timetable will apply.
            </div>
          ) : (
            overrides.map((item) => (
              <div
                key={item.id}
                className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-red-50 text-red-600 flex items-center justify-center shrink-0 border border-red-200">
                    <CalendarDays className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">
                        {item.date}
                      </span>
                      <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">
                        {item.type === "full_day" ? "Full Day Off" : `Partial (${item.hours})`}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-0.5">{item.reason}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" />
                    Front Desk Blocked
                  </span>
                  <button
                    onClick={() => removeOverride(item.id)}
                    className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Remove leave override"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4 animate-in zoom-in-95 duration-150">
            <h3 className="text-lg font-bold text-slate-900">
              Add Schedule Override / Leave
            </h3>
            <form onSubmit={handleAddOverride} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Override Date
                </label>
                <input
                  type="date"
                  required
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Coverage
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setNewType("full_day")}
                    className={`py-2 text-xs font-bold rounded-lg border ${
                      newType === "full_day"
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-700 border-slate-300"
                    }`}
                  >
                    Full Day Off
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewType("partial")}
                    className={`py-2 text-xs font-bold rounded-lg border ${
                      newType === "partial"
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-700 border-slate-300"
                    }`}
                  >
                    Partial Hours
                  </button>
                </div>
              </div>

              {newType === "partial" && (
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Hours Blocked
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 14:00 - 17:00"
                    value={newHours}
                    onChange={(e) => setNewHours(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900"
                  />
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Reason / Purpose
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Medical Conference, Emergency Surgery, Personal"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold"
                >
                  Confirm & Block Slots
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
