"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { UserCheck, LogOut, ArrowRight, ShieldCheck } from "lucide-react";
import { api } from "@bazaar/shared";

export function DemoBanner() {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const raw = typeof localStorage !== "undefined"
      ? localStorage.getItem("bazaar_user") || localStorage.getItem("bazaar.buyer.session")
      : null;
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        setUser(parsed.user || parsed);
      } catch {}
    }
  }, []);

  const handleQuickLogin = async () => {
    try {
      await api.login({ email: "priya@bazaar.test", password: "Shopper@2026" });
      const raw = localStorage.getItem("bazaar_user");
      if (raw) setUser(JSON.parse(raw));
      window.location.reload();
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    window.location.reload();
  };

  return (
    <aside aria-label="Demo Credentials and Role Switcher" className="bg-amber-950 text-amber-100 text-xs py-2 px-4 border-b border-amber-900/60 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 font-semibold text-amber-400 bg-amber-900/60 px-2 py-0.5 rounded-full border border-amber-800">
            <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
            Bazaar Demo Mode
          </span>
          {user ? (
            <span className="flex items-center gap-1.5">
              <span>Shopping as</span>
              <strong className="text-white font-medium">{user.name}</strong>
              <span className="text-amber-300">({user.email})</span>
            </span>
          ) : (
            <span>Explore the multi-vendor experience with pre-seeded demo accounts.</span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <button
              onClick={handleLogout}
              className="hover:text-white inline-flex items-center gap-1 transition-colors text-amber-300"
            >
              <LogOut className="w-3 h-3" />
              Sign Out
            </button>
          ) : (
            <button
              onClick={handleQuickLogin}
              className="bg-amber-500 hover:bg-amber-400 text-amber-950 font-semibold px-2.5 py-0.5 rounded transition-colors inline-flex items-center gap-1 shadow-xs"
            >
              <UserCheck className="w-3.5 h-3.5" />
              1-Click Login (Priya Sharma)
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
