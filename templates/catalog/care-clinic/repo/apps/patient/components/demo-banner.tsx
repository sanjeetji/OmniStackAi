"use client";

import { useState, useEffect } from "react";
import { UserCheck, Sparkles, LogOut } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export function DemoBanner() {
  const [currentUser, setCurrentUser] = useState<{ email: string; name: string } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("careclinic_user");
      if (stored) {
        const u = JSON.parse(stored);
        setCurrentUser({ email: u.email, name: u.full_name || u.name });
      }
    } catch {
      // ignore
    }
  }, []);

  const handleQuickLogin = async () => {
    setLoading(true);
    try {
      const res = await defaultApiClient.login("ananya@careclinic.test", "Patient@2026");
      setCurrentUser({ email: res.user.email, name: res.user.full_name });
      window.location.reload();
    } catch (err: any) {
      alert("Demo sign-in failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    defaultApiClient.clearSession();
    setCurrentUser(null);
    window.location.reload();
  };

  return (
    <div className="bg-teal-900 text-teal-50 px-4 py-2 text-xs md:text-sm border-b border-teal-800">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 bg-teal-800/80 text-teal-200 px-2 py-0.5 rounded font-medium text-xs">
            <Sparkles className="w-3 h-3 text-teal-400" />
            CareClinic Demo
          </span>
          <span className="hidden sm:inline text-teal-200/90">
            Interactive healthcare portal with electronic records, e-prescriptions, and telemedicine.
          </span>
        </div>

        <div className="flex items-center gap-3">
          {currentUser ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-teal-100 font-medium">
                <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
                {currentUser.name}
              </span>
              <button
                onClick={handleLogout}
                className="text-teal-300 hover:text-white underline ml-1 cursor-pointer flex items-center gap-0.5"
                title="Sign out"
              >
                <LogOut className="w-3 h-3" />
                Sign out
              </button>
            </div>
          ) : (
            <button
              onClick={handleQuickLogin}
              disabled={loading}
              className="bg-teal-600 hover:bg-teal-500 text-white font-medium px-3 py-1 rounded transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
            >
              <UserCheck className="w-3.5 h-3.5 text-teal-200" />
              {loading ? "Signing in..." : "1-Click Patient Login (Ananya Deshmukh)"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
