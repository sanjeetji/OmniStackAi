"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Stethoscope,
  Lock,
  Mail,
  ShieldCheck,
  UserCheck,
  ArrowRight,
  AlertCircle,
  Building2,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export default function DoctorLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("dr.rajesh@careclinic.test");
  const [password, setPassword] = useState("Doctor@2026");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await defaultApiClient.login(email, password);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Invalid doctor credentials");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setEmail("dr.rajesh@careclinic.test");
    setPassword("Doctor@2026");
    setLoading(true);
    setError("");

    try {
      await defaultApiClient.login("dr.rajesh@careclinic.test", "Doctor@2026");
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Failed to sign in demo doctor");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12 space-y-6">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-emerald-600 text-white flex items-center justify-center mx-auto shadow-sm">
          <Stethoscope className="w-7 h-7 text-white" />
        </div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">
          Physician Sign In
        </h1>
        <p className="text-xs text-slate-500">
          CareClinic Clinical Workstation & Telehealth Management Console
        </p>
      </div>

      {/* 1-Click Demo Login Box */}
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 p-4 rounded-3xl border border-emerald-200 text-xs space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="font-bold text-emerald-950 flex items-center gap-1.5">
            <UserCheck className="w-4 h-4 text-emerald-600" />
            <span>Pre-Configured Demo Physician</span>
          </span>
          <span className="text-[10px] uppercase font-bold text-emerald-800 bg-emerald-200/80 px-2 py-0.5 rounded">
            Cardiology
          </span>
        </div>
        <p className="text-emerald-900/90 text-[11px] leading-relaxed">
          Sign in as <strong>Dr. Rajesh Varma, MD</strong> (OPD Room 101, 15 pre-seeded appointments, live queue tokens, and active patient chart).
        </p>
        <button
          type="button"
          onClick={handleDemoLogin}
          disabled={loading}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs py-2.5 rounded-xl transition-all shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
        >
          <span>1-Click Dr. Rajesh Varma Login</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Login Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Physician Email / Staff ID
            </label>
            <div className="relative flex items-center">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Password</label>
            <div className="relative flex items-center">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl focus:border-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs sm:text-sm py-3 rounded-2xl transition-all shadow-md cursor-pointer mt-2"
          >
            {loading ? "Authenticating..." : "Unlock Clinical Station"}
          </button>
        </form>
      </div>

      <div className="text-center text-[11px] text-slate-400 flex items-center justify-center gap-1">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
        <span>CareClinic Clinical Auth • HIPAA Audit Trail Enforced</span>
      </div>
    </div>
  );
}
