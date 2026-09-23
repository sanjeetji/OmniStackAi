"use client";

import { useState } from "react";
import { X, Activity, Heart, Thermometer, Droplet, Check } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

interface VitalsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function VitalsModal({ isOpen, onClose, onSuccess }: VitalsModalProps) {
  const [systolic, setSystolic] = useState("");
  const [diastolic, setDiastolic] = useState("");
  const [heartRate, setHeartRate] = useState("");
  const [temp, setTemp] = useState("");
  const [spo2, setSpo2] = useState("");
  const [glucose, setGlucose] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await defaultApiClient.logVitals({
        bpSystolic: systolic ? parseInt(systolic, 10) : undefined,
        bpDiastolic: diastolic ? parseInt(diastolic, 10) : undefined,
        heartRate: heartRate ? parseInt(heartRate, 10) : undefined,
        temperatureF: temp ? parseFloat(temp) : undefined,
        spo2Percent: spo2 ? parseFloat(spo2) : undefined,
        bloodGlucoseMgDl: glucose ? parseFloat(glucose) : undefined,
        notes: notes || "Patient logged vitals",
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to log vitals");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-xl border border-slate-200 relative animate-fade-in">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-600 p-1"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 mb-5">
          <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Record Vitals</h3>
            <p className="text-xs text-slate-500">Log your biometric readings for doctor review</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 text-xs bg-rose-50 border border-rose-200 text-rose-700 p-2.5 rounded-xl">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Blood Pressure */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Blood Pressure (mmHg)
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="Systolic (e.g. 120)"
                value={systolic}
                onChange={(e) => setSystolic(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
              <input
                type="number"
                placeholder="Diastolic (e.g. 80)"
                value={diastolic}
                onChange={(e) => setDiastolic(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>
          </div>

          {/* Pulse & SpO2 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Heart Rate (BPM)
              </label>
              <input
                type="number"
                placeholder="e.g. 72"
                value={heartRate}
                onChange={(e) => setHeartRate(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                SpO2 (%)
              </label>
              <input
                type="number"
                placeholder="e.g. 98"
                value={spo2}
                onChange={(e) => setSpo2(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>
          </div>

          {/* Temperature & Blood Sugar */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Temperature (°F)
              </label>
              <input
                type="number"
                step="0.1"
                placeholder="e.g. 98.6"
                value={temp}
                onChange={(e) => setTemp(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Blood Sugar (mg/dL)
              </label>
              <input
                type="number"
                placeholder="Fasting or PP"
                value={glucose}
                onChange={(e) => setGlucose(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Notes / Symptoms
            </label>
            <input
              type="text"
              placeholder="e.g. Felt dizzy after morning walk"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full text-xs px-3 py-2 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-sm flex items-center gap-1.5"
            >
              {submitting ? "Saving..." : "Save Readings"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
