"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@bazaar/shared";
import type { User } from "@bazaar/shared";

export default function AccountPage() {
  const [user, setUser] = useState<User>({
    id: "u-shopper-001",
    name: "Priya Sharma",
    email: "priya.sharma@example.com",
    role: "shopper",
    phone: "+91 98765 43210",
    avatarUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80",
    createdAt: "2026-01-15T10:00:00Z",
  });
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [whatsappUpdates, setWhatsappUpdates] = useState(true);

  useEffect(() => {
    async function loadProfile() {
      try {
        const res = await api.getProfile();
        if (res && (res as any).id) {
          setUser((res as any).user || res);
        }
      } catch {
        // Keep default demo user
      }
    }
    loadProfile();
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header Profile Card */}
      <div className="bg-white rounded-2xl border border-stone-200 p-6 sm:p-8 mb-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            {user.avatarUrl ? (
              <img
                src={user.avatarUrl}
                alt={user.name}
                className="w-20 h-20 rounded-full object-cover border-2 border-amber-600 shadow-sm"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center text-2xl font-bold">
                {user.name.charAt(0)}
              </div>
            )}

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-serif font-bold text-stone-900">{user.name}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                  Craft Patron
                </span>
              </div>
              <p className="text-stone-500 text-sm mt-0.5">{user.email}</p>
              {user.phone && <p className="text-stone-500 text-xs font-mono">{user.phone}</p>}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/orders"
              className="px-5 py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-xs font-semibold transition shadow-sm"
            >
              View My Orders &rarr;
            </Link>
          </div>
        </div>

        {/* Impact Counters */}
        <div className="grid grid-cols-3 gap-4 border-t border-stone-100 mt-6 pt-6 text-center">
          <div className="p-3 bg-stone-50 rounded-xl">
            <span className="block text-xl font-serif font-bold text-amber-800">2</span>
            <span className="text-xs text-stone-500">Orders Placed</span>
          </div>
          <div className="p-3 bg-stone-50 rounded-xl">
            <span className="block text-xl font-serif font-bold text-amber-800">5</span>
            <span className="text-xs text-stone-500">Crafts Acquired</span>
          </div>
          <div className="p-3 bg-stone-50 rounded-xl">
            <span className="block text-xl font-serif font-bold text-amber-800">3</span>
            <span className="text-xs text-stone-500">Ateliers Supported</span>
          </div>
        </div>
      </div>

      {/* Account Navigation Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <Link
          href="/orders"
          className="p-5 bg-white rounded-2xl border border-stone-200 hover:border-amber-400 hover:shadow-md transition flex items-start gap-4 group"
        >
          <span className="text-3xl p-3 bg-amber-50 rounded-xl group-hover:bg-amber-100 transition">
            📦
          </span>
          <div>
            <h3 className="font-semibold text-stone-900 group-hover:text-amber-800 transition">
              Orders & Consignments
            </h3>
            <p className="text-xs text-stone-500 mt-1">
              Check shipment checkpoints, dispatch dates, and courier tracking across multiple sellers.
            </p>
          </div>
        </Link>

        <Link
          href="/addresses"
          className="p-5 bg-white rounded-2xl border border-stone-200 hover:border-amber-400 hover:shadow-md transition flex items-start gap-4 group"
        >
          <span className="text-3xl p-3 bg-amber-50 rounded-xl group-hover:bg-amber-100 transition">
            📍
          </span>
          <div>
            <h3 className="font-semibold text-stone-900 group-hover:text-amber-800 transition">
              Saved Address Book
            </h3>
            <p className="text-xs text-stone-500 mt-1">
              Manage residential and studio delivery addresses for 1-click checkout.
            </p>
          </div>
        </Link>

        <Link
          href="/reviews"
          className="p-5 bg-white rounded-2xl border border-stone-200 hover:border-amber-400 hover:shadow-md transition flex items-start gap-4 group"
        >
          <span className="text-3xl p-3 bg-amber-50 rounded-xl group-hover:bg-amber-100 transition">
            ⭐
          </span>
          <div>
            <h3 className="font-semibold text-stone-900 group-hover:text-amber-800 transition">
              Artisan Reviews
            </h3>
            <p className="text-xs text-stone-500 mt-1">
              View your published reviews and read direct responses from Indian master craftsmen.
            </p>
          </div>
        </Link>

        <Link
          href="/cart"
          className="p-5 bg-white rounded-2xl border border-stone-200 hover:border-amber-400 hover:shadow-md transition flex items-start gap-4 group"
        >
          <span className="text-3xl p-3 bg-amber-50 rounded-xl group-hover:bg-amber-100 transition">
            🛍️
          </span>
          <div>
            <h3 className="font-semibold text-stone-900 group-hover:text-amber-800 transition">
              Active Multi-Vendor Cart
            </h3>
            <p className="text-xs text-stone-500 mt-1">
              Review reserved pottery, textiles, and jewelry before single-click split checkout.
            </p>
          </div>
        </Link>
      </div>

      {/* Preferences & Notification Settings */}
      <div className="bg-white rounded-2xl border border-stone-200 p-6 mb-8 shadow-sm">
        <h3 className="text-base font-serif font-bold text-stone-900 mb-4">
          Communication & Dispatch Alerts
        </h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-stone-100">
            <div>
              <p className="text-sm font-semibold text-stone-800">
                Real-Time Delivery & Dispatch SMS
              </p>
              <p className="text-xs text-stone-500">
                Receive carrier milestone pings when your package leaves the artisan workshop.
              </p>
            </div>
            <input
              type="checkbox"
              checked={notificationsEnabled}
              onChange={(e) => setNotificationsEnabled(e.target.checked)}
              className="w-5 h-5 text-amber-700 rounded border-stone-300"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-stone-800">WhatsApp Delivery Updates</p>
              <p className="text-xs text-stone-500">
                Receive live GPS tracking links and delivery OTP directly on your WhatsApp number.
              </p>
            </div>
            <input
              type="checkbox"
              checked={whatsappUpdates}
              onChange={(e) => setWhatsappUpdates(e.target.checked)}
              className="w-5 h-5 text-amber-700 rounded border-stone-300"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
