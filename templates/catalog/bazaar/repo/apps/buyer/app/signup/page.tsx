"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@bazaar/shared";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await api.register({
        name,
        email,
        phone,
        password,
        role: "shopper",
      });
      router.push("/orders");
    } catch (err: any) {
      setError(err.message || "Failed to create account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleDemoPreset() {
    setName("Aarav Mehta");
    setEmail("aarav.mehta@example.com");
    setPhone("+91 98200 11223");
    setPassword("password123");
  }

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="bg-white rounded-3xl border border-stone-200 p-8 sm:p-10 max-w-md w-full shadow-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block mb-3">
            <span className="font-serif text-3xl font-extrabold tracking-tight text-amber-900">
              BAZAAR
            </span>
          </Link>
          <h1 className="text-xl font-serif font-bold text-stone-900">Join as an Artisan Patron</h1>
          <p className="text-xs text-stone-500 mt-1">
            Support authentic heritage arts, handlooms, and independent craft guilds across India.
          </p>
        </div>

        {/* Quick Demo Pre-fill */}
        <div className="mb-6 flex justify-end">
          <button
            type="button"
            onClick={handleDemoPreset}
            className="text-xs text-amber-800 hover:text-amber-900 font-semibold underline"
          >
            ⚡ Auto-fill sample details
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. Aarav Mehta"
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:border-amber-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="aarav.mehta@example.com"
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:border-amber-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
              Mobile Number
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98200 11223"
              className="w-full text-sm rounded-xl border border-stone-300 p-3 font-mono focus:border-amber-600 focus:outline-none"
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
              placeholder="At least 8 characters"
              className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:border-amber-600 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="newsletterCheck"
              defaultChecked
              className="w-4 h-4 text-amber-700 rounded border-stone-300"
            />
            <label htmlFor="newsletterCheck" className="text-xs text-stone-600">
              Receive artisan stories and exclusive seasonal craft drop announcements
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-sm font-semibold transition disabled:opacity-50 shadow-sm"
          >
            {loading ? "Creating Account..." : "Create Patron Account"}
          </button>
        </form>

        {/* Footer */}
        <p className="text-center text-xs text-stone-500 mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-amber-800 font-semibold hover:underline">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
