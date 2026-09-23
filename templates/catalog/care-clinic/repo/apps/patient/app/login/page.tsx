"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  HeartPulse,
  Mail,
  Lock,
  User,
  Phone,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export default function PatientLoginPage() {
  const router = useRouter();
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("ananya@careclinic.test");
  const [password, setPassword] = useState("Patient@2026");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (isRegistering) {
        await defaultApiClient.register({
          email,
          password,
          fullName,
          phone,
        });
      } else {
        await defaultApiClient.login(email, password);
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = async () => {
    setEmail("ananya@careclinic.test");
    setPassword("Patient@2026");
    setIsRegistering(false);
    setLoading(true);
    setError("");

    try {
      await defaultApiClient.login("ananya@careclinic.test", "Patient@2026");
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Failed to sign in demo user");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-12 space-y-6">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-teal-600 text-white flex items-center justify-center mx-auto shadow-sm">
          <HeartPulse className="w-7 h-7 text-white" />
        </div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">
          {isRegistering ? "Create Patient Account" : "Patient Portal Sign In"}
        </h1>
        <p className="text-xs text-slate-500">
          Access your medical charts, appointment queue passes, and digital prescriptions.
        </p>
      </div>

      {/* 1-Click Demo Patient Quick Login Card */}
      {!isRegistering && (
        <div className="bg-gradient-to-r from-teal-50 to-teal-100/60 p-4 rounded-3xl border border-teal-200 text-xs space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-bold text-teal-900 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-teal-600" />
              Demo Patient Account
            </span>
            <span className="text-[10px] uppercase font-bold text-teal-700 bg-teal-200/80 px-2 py-0.5 rounded">
              Ready to Demo
            </span>
          </div>
          <p className="text-teal-800/90 text-[11px] leading-relaxed">
            Sign in as <strong>Ananya Deshmukh</strong> (with past appointments, prescriptions, and lipid panel lab reports pre-seeded).
          </p>
          <button
            type="button"
            onClick={handleDemoFill}
            disabled={loading}
            className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs py-2.5 rounded-xl transition-all shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
          >
            <span>1-Click Ananya Deshmukh Login</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Form */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {isRegistering && (
            <>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Full Legal Name</label>
                <div className="relative flex items-center">
                  <User className="w-4 h-4 text-slate-400 absolute left-3" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ananya Deshmukh"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Mobile Phone</label>
                <div className="relative flex items-center">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3" />
                  <input
                    type="tel"
                    placeholder="+91 98450 12345"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Email Address</label>
            <div className="relative flex items-center">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3" />
              <input
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
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
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-hidden"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs sm:text-sm py-3 rounded-2xl transition-all shadow-md cursor-pointer mt-2"
          >
            {loading ? "Verifying..." : isRegistering ? "Create Patient Account" : "Sign In to Portal"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-100 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError("");
            }}
            className="text-teal-700 hover:text-teal-800 text-xs font-semibold cursor-pointer"
          >
            {isRegistering
              ? "Already have an account? Sign in here"
              : "New patient? Register for online consultations"}
          </button>
        </div>
      </div>

      <div className="text-center text-[11px] text-slate-400 flex items-center justify-center gap-1">
        <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
        <span>End-to-end encrypted medical data privacy</span>
      </div>
    </div>
  );
}
