"use client";

import { useState } from "react";
import Link from "next/link";
import { ShieldCheck, Lock, Mail, ArrowRight, Layers, CheckCircle2 } from "lucide-react";

export default function AdminLoginPage() {
  const [email, setEmail] = useState("admin@bazaar.test");
  const [password, setPassword] = useState("Admin@2026");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Authenticate operator credentials
    if (email === "admin@bazaar.test" && password === "Admin@2026") {
      const adminUser = {
        id: "admin-seed-uuid-0001",
        email: "admin@bazaar.test",
        name: "Vikram Malhotra",
        role: "admin",
      };
      localStorage.setItem("bazaar_token", "demo-token-admin-vikram");
      localStorage.setItem("bazaar_user", JSON.stringify(adminUser));
      setTimeout(() => {
        window.location.href = "/";
      }, 400);
    } else {
      setLoading(false);
      setError("Invalid operator credentials. Use the 1-click login below.");
    }
  };

  const handleDemoLogin = () => {
    setEmail("admin@bazaar.test");
    setPassword("Admin@2026");
    const adminUser = {
      id: "admin-seed-uuid-0001",
      email: "admin@bazaar.test",
      name: "Vikram Malhotra",
      role: "admin",
    };
    localStorage.setItem("bazaar_token", "demo-token-admin-vikram");
    localStorage.setItem("bazaar_user", JSON.stringify(adminUser));
    setLoading(true);
    setTimeout(() => {
      window.location.href = "/";
    }, 400);
  };

  return (
    <div className="w-full max-w-md mx-auto space-y-6">
      {/* Brand Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 text-white shadow-lg shadow-amber-950/40 mb-2">
          <Layers className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Operator Sign In
        </h1>
        <p className="text-xs text-slate-400">
          Bazaar Marketplace Operations &amp; Ledger Supervision Console
        </p>
      </div>

      {/* 1-Click Credentials Card */}
      <div className="p-4 rounded-xl bg-slate-900/90 border border-amber-500/30 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-amber-400 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            Operator Demo Credentials
          </span>
          <span className="px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-300 font-mono text-[10px]">
            Supervisor
          </span>
        </div>
        <div className="text-xs text-slate-300 space-y-1 font-mono bg-slate-950/70 p-2.5 rounded-lg border border-slate-800">
          <div><span className="text-slate-400">Email:</span> admin@bazaar.test</div>
          <div><span className="text-slate-400">Password:</span> Admin@2026</div>
          <div><span className="text-slate-400">Operator:</span> Vikram Malhotra (Chief Operator)</div>
        </div>
        <button
          type="button"
          onClick={handleDemoLogin}
          className="w-full py-2 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
        >
          <span>1-Click Sign In as Vikram Malhotra</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Login Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
              {error}
            </div>
          )}

          <div>
            <label className="block text-slate-300 font-medium mb-1.5">
              Operator Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1.5">
              Security Passcode
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {loading ? "Authenticating Operator..." : "Authenticate Session"}
          </button>
        </form>
      </div>

      <div className="text-center text-[11px] text-slate-400 space-y-1">
        <p>Restricted to authorized marketplace administrators only.</p>
        <p>All administrative actions are immutable and recorded in the audit trail.</p>
      </div>
    </div>
  );
}
