"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Clock,
  Sparkles,
  Users,
  ShieldCheck,
  Video,
  UserCheck,
  Bell,
  Stethoscope,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export function DoctorHeader() {
  const [currentTime, setCurrentTime] = useState("");
  const [user, setUser] = useState<any>(null);
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    try {
      const u = localStorage.getItem("careclinic_user");
      if (u) setUser(JSON.parse(u));
    } catch {}
  }, []);

  const handleQuickLogin = async () => {
    setSigningIn(true);
    try {
      await defaultApiClient.login("dr.rajesh@careclinic.test", "Doctor@2026");
      window.location.reload();
    } catch (err: any) {
      alert("Sign-in failed: " + err.message);
    } finally {
      setSigningIn(false);
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-2xs">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-extrabold text-slate-900">Physician Workstation</span>
          <span className="text-slate-300">•</span>
          <span className="text-xs text-slate-500 font-medium">CareClinic Indiranagar</span>
        </div>

        <div className="hidden md:flex items-center gap-2 bg-emerald-50 text-emerald-800 text-xs px-2.5 py-1 rounded-lg border border-emerald-200 font-semibold">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Room OPD 101 • Ready for Next Patient</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Live Clock */}
        <div className="hidden sm:flex items-center gap-1.5 text-slate-600 text-xs font-mono font-bold bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>{currentTime || "10:30:00 AM"}</span>
        </div>

        {/* 1-Click Demo Login Button if not logged in as doctor */}
        {!user || user.role !== "doctor" ? (
          <button
            onClick={handleQuickLogin}
            disabled={signingIn}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs px-3.5 py-1.5 rounded-xl transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            <UserCheck className="w-3.5 h-3.5 text-emerald-200" />
            <span>{signingIn ? "Authenticating..." : "1-Click Dr. Rajesh Varma"}</span>
          </button>
        ) : (
          <div className="flex items-center gap-2 text-xs">
            <span className="bg-slate-100 text-slate-800 font-bold px-3 py-1 rounded-xl border border-slate-200">
              Dr. Rajesh Varma (Attending)
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
