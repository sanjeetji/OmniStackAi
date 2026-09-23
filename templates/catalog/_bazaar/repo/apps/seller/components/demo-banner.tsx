"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@bazaar/shared";
import type { User, Shop } from "@bazaar/shared";

export function SellerDemoBanner() {
  const [user, setUser] = useState<User | null>(null);
  const [shop, setShop] = useState<Shop | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedUser = localStorage.getItem("bazaar_user");
      const storedShop = localStorage.getItem("bazaar_shop");
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          // ignore
        }
      }
      if (storedShop) {
        try {
          setShop(JSON.parse(storedShop));
        } catch {
          // ignore
        }
      }
    }
  }, []);

  async function handleKripalLogin() {
    try {
      const res = await api.login("kripal.singh@example.com", "password123");
      setUser(res.user);
      if (res.shop) setShop(res.shop);
      window.location.reload();
    } catch {
      // Mock fallback
      const mockUser: User = {
        id: "u-vendor-001",
        email: "kripal.singh@example.com",
        name: "Master Artisan Kripal Singh",
        role: "vendor",
        phone: "+91 98290 12345",
      };
      const mockShop: Shop = {
        id: "shp-jaipur",
        user_id: "u-vendor-001",
        slug: "jaipur-pottery",
        name: "Jaipur Blue Art Pottery",
        tagline: "Authentic UNESCO Heritage GI-tagged Blue Pottery",
        kyc_status: "verified",
        commission_rate_basis_points: 1000,
        rating_avg: 4.9,
        rating_count: 84,
        is_active: true,
      };
      localStorage.setItem("bazaar_user", JSON.stringify(mockUser));
      localStorage.setItem("bazaar_shop", JSON.stringify(mockShop));
      setUser(mockUser);
      setShop(mockShop);
      window.location.reload();
    }
  }

  function handleLogout() {
    api.logout();
    setUser(null);
    setShop(null);
    window.location.reload();
  }

  return (
    <div className="bg-stone-900 text-stone-200 text-xs py-2 px-4 border-b border-stone-800">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-900/80 text-amber-300 border border-amber-700/50">
            DEMO ARTISAN WORKSPACE
          </span>
          <span className="hidden sm:inline text-stone-400">
            Evaluating Bazaar Multi-Vendor Vendor Portal (Hono API + PG Ledger)
          </span>
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-2">
              <span className="text-stone-300 font-medium truncate max-w-[200px]">
                👨‍🎨 {user.name} ({shop?.name || "Artisan Workshop"})
              </span>
              <button
                onClick={handleLogout}
                className="text-stone-400 hover:text-white underline text-[11px] ml-1"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={handleKripalLogin}
              className="px-3 py-1 bg-amber-800 hover:bg-amber-700 text-white rounded-md text-[11px] font-semibold transition flex items-center gap-1.5 shadow-2xs"
            >
              <span>⚡</span>
              <span>1-Click Sign In as Kripal Singh (Jaipur Pottery)</span>
            </button>
          )}

          <span className="text-stone-600">|</span>
          <Link
            href="/login"
            className="text-stone-400 hover:text-white text-[11px] font-medium"
          >
            Custom Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
