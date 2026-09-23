"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@bazaar/shared";

export default function SellerLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("aryan@bazaar.test");
  const [password, setPassword] = useState("Vendor@2026");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await api.login(email, password);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Failed to authenticate artisan merchant.");
    } finally {
      setLoading(false);
    }
  }

  function handleDemoQuick() {
    setEmail("aryan@bazaar.test");
    setPassword("Vendor@2026");
    api.login("aryan@bazaar.test", "Vendor@2026")
      .then(() => router.push("/"))
      .catch(() => router.push("/"));
  }

  return (
    <div className="min-h-screen bg-stone-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl border border-stone-200 p-8 sm:p-10 max-w-md w-full shadow-lg">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-amber-800 text-amber-100 rounded-2xl flex items-center justify-center text-3xl font-bold mx-auto mb-3 shadow-sm">
            🏺
          </div>
          <h1 className="text-2xl font-serif font-bold text-stone-900">
            Artisan Atelier Portal
          </h1>
          <p className="text-xs text-stone-500 mt-1">
            Access your workshop fulfillment queue, product catalog, and escrow earnings.
          </p>
        </div>

        {/* 1-Click Demo Login */}
        <div className="mb-6 p-4 bg-amber-50/70 border border-amber-200 rounded-2xl">
          <p className="text-xs font-semibold text-amber-900 mb-2 text-center">
            Master Craftsman Demo Access
          </p>
          <button
            type="button"
            onClick={handleDemoQuick}
            className="w-full py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shadow-sm"
          >
            <span>✨</span>
            <span>Sign In as Kripal Singh (Jaipur Pottery)</span>
          </button>
          <p className="text-[11px] text-stone-500 text-center mt-2">
            Auto-loads verified artisan atelier with 8 active listings & orders
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
              Registered Artisan Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-sm font-semibold transition disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Sign In to Workshop"}
          </button>
        </form>

        <p className="text-center text-xs text-stone-500 mt-6">
          Looking for shopper storefront?{" "}
          <a
            href="http://localhost:3000"
            className="text-amber-800 font-semibold hover:underline"
          >
            Open Buyer Marketplace &rarr;
          </a>
        </p>
      </div>
    </div>
  );
}
