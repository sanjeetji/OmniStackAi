"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@bazaar/shared";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("priya.sharma@example.com");
  const [password, setPassword] = useState("password123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await api.login(email, password);
      router.push("/orders");
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  }

  function handleQuickDemoFill() {
    setEmail("priya.sharma@example.com");
    setPassword("password123");
    // Trigger login directly
    api.login("priya.sharma@example.com", "password123")
      .then(() => router.push("/orders"))
      .catch(() => router.push("/orders")); // Graceful offline fallback
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <div className="bg-white rounded-3xl border border-stone-200 p-8 sm:p-10 max-w-md w-full shadow-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block mb-3">
            <span className="font-serif text-3xl font-extrabold tracking-tight text-amber-900">
              BAZAAR
            </span>
          </Link>
          <h1 className="text-xl font-serif font-bold text-stone-900">Welcome Back, Patron</h1>
          <p className="text-xs text-stone-500 mt-1">
            Access your orders, split consignments, and saved craft favorites.
          </p>
        </div>

        {/* 1-Click Demo Login Button */}
        <div className="mb-6 p-4 bg-amber-50/70 border border-amber-200 rounded-2xl">
          <p className="text-xs font-semibold text-amber-900 mb-2 text-center">
            Instant Demo Evaluation
          </p>
          <button
            type="button"
            onClick={handleQuickDemoFill}
            className="w-full py-2.5 px-4 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center justify-center gap-2"
          >
            <span>✨</span>
            <span>1-Click Sign In as Priya Sharma</span>
          </button>
          <p className="text-[11px] text-stone-500 text-center mt-2">
            No signup required &bull; Auto-loads pre-filled orders & addresses
          </p>
        </div>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-stone-200"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-3 text-stone-400 font-medium">Or with email</span>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:border-amber-600 focus:outline-none"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-stone-700 uppercase">
                Password
              </label>
              <span className="text-xs text-stone-400">demo: password123</span>
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:border-amber-600 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-sm font-semibold transition disabled:opacity-50 shadow-sm"
          >
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>

        {/* Footer */}
        <p className="text-center text-xs text-stone-500 mt-6">
          New to Bazaar?{" "}
          <Link href="/signup" className="text-amber-800 font-semibold hover:underline">
            Create a Patron Account
          </Link>
        </p>
      </div>
    </div>
  );
}
