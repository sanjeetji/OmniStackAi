"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck, LogIn, LogOut, CheckCircle2 } from "lucide-react";

export function DemoBanner() {
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("bazaar_user") || localStorage.getItem("bazaar.admin.session");
      if (stored) {
        const parsed = JSON.parse(stored);
        setCurrentUser(parsed.user || parsed);
      }
    } catch {
      // ignore
    }
  }, []);

  const handleAdminLogin = () => {
    const adminUser = {
      id: "admin-seed-uuid-0001",
      email: "admin@bazaar.test",
      name: "Vikram Malhotra",
      role: "admin",
    };
    localStorage.setItem("bazaar_token", "demo-token-admin-vikram");
    localStorage.setItem("bazaar_user", JSON.stringify(adminUser));
    setCurrentUser(adminUser);
    window.location.reload();
  };

  const handleLogout = () => {
    localStorage.removeItem("bazaar_token");
    localStorage.removeItem("bazaar_user");
    setCurrentUser(null);
    window.location.href = "/login";
  };

  return (
    <aside aria-label="Demo environment notice" className="bg-slate-900 border-b border-slate-800 text-xs text-slate-300 px-4 py-2 flex flex-wrap items-center justify-between gap-3 sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <span className="flex h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
        <span className="font-semibold tracking-wider uppercase text-amber-400 text-[11px]">
          Demo Environment
        </span>
        <span className="text-slate-400 hidden sm:inline">•</span>
        <span className="text-slate-400 hidden sm:inline">
          Bazaar Marketplace Operations Console (All ledger accounting & logistics run offline)
        </span>
      </div>

      <div className="flex items-center gap-3">
        {currentUser ? (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              {currentUser.name} (Admin)
            </span>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-white flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-slate-800 transition"
              title="Sign out"
            >
              <LogOut className="w-3 h-3" />
              <span className="hidden md:inline">Sign Out</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={handleAdminLogin}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white font-medium transition cursor-pointer"
            >
              <LogIn className="w-3 h-3" />
              1-Click Login: Vikram Malhotra (Admin)
            </button>
            <Link
              href="/login"
              className="text-slate-400 hover:text-white underline underline-offset-2 ml-1"
            >
              Credentials
            </Link>
          </div>
        )}
      </div>
    </aside>
  );
}
