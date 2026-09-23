"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Sliders,
  Save,
  ArrowRight,
  ShieldCheck,
  Building,
  Video,
} from "lucide-react";

interface DaySchedule {
  day: string;
  enabled: boolean;
  morningStart: string;
  morningEnd: string;
  eveningStart: string;
  eveningEnd: string;
  telehealthStart: string;
  telehealthEnd: string;
  telehealthEnabled: boolean;
}

const DEFAULT_SCHEDULE: DaySchedule[] = [
  {
    day: "Monday",
    enabled: true,
    morningStart: "09:00",
    morningEnd: "13:00",
    eveningStart: "17:00",
    eveningEnd: "20:00",
    telehealthStart: "14:00",
    telehealthEnd: "16:00",
    telehealthEnabled: true,
  },
  {
    day: "Tuesday",
    enabled: true,
    morningStart: "09:00",
    morningEnd: "13:00",
    eveningStart: "17:00",
    eveningEnd: "20:00",
    telehealthStart: "14:00",
    telehealthEnd: "16:00",
    telehealthEnabled: true,
  },
  {
    day: "Wednesday",
    enabled: true,
    morningStart: "09:00",
    morningEnd: "13:00",
    eveningStart: "17:00",
    eveningEnd: "20:00",
    telehealthStart: "14:00",
    telehealthEnd: "16:00",
    telehealthEnabled: false,
  },
  {
    day: "Thursday",
    enabled: true,
    morningStart: "09:00",
    morningEnd: "13:00",
    eveningStart: "17:00",
    eveningEnd: "20:00",
    telehealthStart: "14:00",
    telehealthEnd: "16:00",
    telehealthEnabled: true,
  },
  {
    day: "Friday",
    enabled: true,
    morningStart: "09:00",
    morningEnd: "13:00",
    eveningStart: "17:00",
    eveningEnd: "20:00",
    telehealthStart: "14:00",
    telehealthEnd: "16:00",
    telehealthEnabled: true,
  },
  {
    day: "Saturday",
    enabled: true,
    morningStart: "09:30",
    morningEnd: "13:30",
    eveningStart: "",
    eveningEnd: "",
    telehealthStart: "15:00",
    telehealthEnd: "17:00",
    telehealthEnabled: true,
  },
  {
    day: "Sunday",
    enabled: false,
    morningStart: "",
    morningEnd: "",
    eveningStart: "",
    eveningEnd: "",
    telehealthStart: "",
    telehealthEnd: "",
    telehealthEnabled: false,
  },
];

export default function DoctorSchedulePage() {
  const [schedule, setSchedule] = useState<DaySchedule[]>(DEFAULT_SCHEDULE);
  const [slotDuration, setSlotDuration] = useState<number>(20);
  const [bufferTime, setBufferTime] = useState<number>(5);
  const [saved, setSaved] = useState(false);

  const toggleDay = (index: number) => {
    setSchedule((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, enabled: !item.enabled } : item
      )
    );
  };

  const updateTime = (
    index: number,
    field: keyof DaySchedule,
    value: any
  ) => {
    setSchedule((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      )
    );
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  // Capacity estimate:
  const activeDays = schedule.filter((d) => d.enabled).length;
  const estimatedWeeklySlots = activeDays * (slotDuration === 15 ? 28 : slotDuration === 20 ? 21 : 14);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <ShieldCheck className="w-3.5 h-3.5" />
              OPD Timetable Engine
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Schedule Configuration
          </h1>
          <p className="text-sm text-slate-500">
            Define recurring weekly clinic hours, consultation slot granularity, and telemedicine blocks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/schedule/rules"
            className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 inline-flex items-center gap-1.5 transition-colors"
          >
            <span>Availability Rules</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>

          <button
            onClick={handleSave}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold inline-flex items-center gap-2 shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Save Timetable</span>
          </button>
        </div>
      </div>

      {saved && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm animate-in fade-in duration-200">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span className="font-semibold">
            Weekly schedule matrix successfully committed to OPD slot booking engine.
          </span>
        </div>
      )}

      {/* Global Shift & Slot Settings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Slot Granularity
            </span>
            <Sliders className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-xs text-slate-500">
            Duration allocated per standard patient consultation.
          </p>
          <div className="grid grid-cols-3 gap-2">
            {[15, 20, 30].map((mins) => (
              <button
                key={mins}
                onClick={() => setSlotDuration(mins)}
                className={`py-2 px-3 rounded-lg text-xs font-bold transition-colors ${
                  slotDuration === mins
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {mins} mins
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Consultation Buffer
            </span>
            <Clock className="w-4 h-4 text-teal-600" />
          </div>
          <p className="text-xs text-slate-500">
            Sanitization and charting interval between tokens.
          </p>
          <div className="grid grid-cols-3 gap-2">
            {[0, 5, 10].map((mins) => (
              <button
                key={mins}
                onClick={() => setBufferTime(mins)}
                className={`py-2 px-3 rounded-lg text-xs font-bold transition-colors ${
                  bufferTime === mins
                    ? "bg-slate-900 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {mins} mins
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Assigned Chamber
            </span>
            <Building className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-base font-bold text-slate-900">OPD Chamber 101</p>
          <p className="text-xs text-slate-500">
            Cardiology Wing • First Floor • Desk A
          </p>
          <span className="inline-block text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
            Biometric Access Active
          </span>
        </div>
      </div>

      {/* Weekly Matrix Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Weekly Shift Matrix</h2>
            <p className="text-xs text-slate-500">
              Configure shift hours for in-clinic OPD and video telemedicine sessions.
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-600 bg-white px-3 py-1 rounded-lg border border-slate-200">
            ~{estimatedWeeklySlots} total slots / week
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {schedule.map((item, index) => (
            <div
              key={item.day}
              className={`p-4 transition-colors ${
                item.enabled ? "bg-white" : "bg-slate-50/50"
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Day Toggle */}
                <div className="flex items-center gap-3 w-40">
                  <input
                    type="checkbox"
                    checked={item.enabled}
                    onChange={() => toggleDay(index)}
                    className="w-4 h-4 text-emerald-600 rounded-sm border-slate-300 focus:ring-emerald-500 cursor-pointer"
                  />
                  <div>
                    <span
                      className={`text-sm font-bold block ${
                        item.enabled ? "text-slate-900" : "text-slate-400"
                      }`}
                    >
                      {item.day}
                    </span>
                    <span className="text-[11px] text-slate-400 block">
                      {item.enabled ? "Active Clinic Day" : "Off Duty / Weekly Off"}
                    </span>
                  </div>
                </div>

                {/* Shift Hours Inputs */}
                {item.enabled ? (
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Morning Shift */}
                    <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-bold text-slate-700 uppercase">
                          Morning OPD
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">In-Clinic</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="time"
                          value={item.morningStart}
                          onChange={(e) =>
                            updateTime(index, "morningStart", e.target.value)
                          }
                          className="w-full text-xs font-mono py-1 px-2 border border-slate-300 rounded-md bg-white text-slate-800"
                        />
                        <span className="text-xs text-slate-400">to</span>
                        <input
                          type="time"
                          value={item.morningEnd}
                          onChange={(e) =>
                            updateTime(index, "morningEnd", e.target.value)
                          }
                          className="w-full text-xs font-mono py-1 px-2 border border-slate-300 rounded-md bg-white text-slate-800"
                        />
                      </div>
                    </div>

                    {/* Evening Shift */}
                    <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-bold text-slate-700 uppercase">
                          Evening OPD
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">In-Clinic</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="time"
                          value={item.eveningStart}
                          onChange={(e) =>
                            updateTime(index, "eveningStart", e.target.value)
                          }
                          className="w-full text-xs font-mono py-1 px-2 border border-slate-300 rounded-md bg-white text-slate-800"
                        />
                        <span className="text-xs text-slate-400">to</span>
                        <input
                          type="time"
                          value={item.eveningEnd}
                          onChange={(e) =>
                            updateTime(index, "eveningEnd", e.target.value)
                          }
                          className="w-full text-xs font-mono py-1 px-2 border border-slate-300 rounded-md bg-white text-slate-800"
                        />
                      </div>
                    </div>

                    {/* Telehealth Block */}
                    <div className="bg-teal-50/60 p-3 rounded-lg border border-teal-200/70">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-bold text-teal-900 uppercase flex items-center gap-1">
                          <Video className="w-3 h-3 text-teal-600" />
                          Telehealth Window
                        </span>
                        <input
                          type="checkbox"
                          checked={item.telehealthEnabled}
                          onChange={(e) =>
                            updateTime(index, "telehealthEnabled", e.target.checked)
                          }
                          className="w-3.5 h-3.5 text-teal-600 rounded-sm focus:ring-teal-500"
                        />
                      </div>
                      {item.telehealthEnabled ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="time"
                            value={item.telehealthStart}
                            onChange={(e) =>
                              updateTime(index, "telehealthStart", e.target.value)
                            }
                            className="w-full text-xs font-mono py-1 px-2 border border-teal-300 rounded-md bg-white text-slate-800"
                          />
                          <span className="text-xs text-teal-600">to</span>
                          <input
                            type="time"
                            value={item.telehealthEnd}
                            onChange={(e) =>
                              updateTime(index, "telehealthEnd", e.target.value)
                            }
                            className="w-full text-xs font-mono py-1 px-2 border border-teal-300 rounded-md bg-white text-slate-800"
                          />
                        </div>
                      ) : (
                        <span className="text-xs text-teal-600/70 italic block py-1">
                          Telehealth disabled for this day
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 py-3 text-xs text-slate-400 italic">
                    Chamber closed. Patients cannot book appointments on this day.
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
