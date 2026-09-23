"use client";

import { useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import {
  Tag,
  Plus,
  Percent,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
  Search,
  Filter,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

interface CouponRow {
  id: string;
  code: string;
  description: string;
  discountType: "percentage" | "flat";
  discountValue: number;
  minOrderCents: number;
  maxDiscountCents?: number;
  timesUsed: number;
  usageLimit?: number;
  isActive: boolean;
  expiresAt?: string;
}

export default function AdminCouponsPage() {
  const [search, setSearch] = useState("");
  const [coupons, setCoupons] = useState<CouponRow[]>([
    {
      id: "cp-01",
      code: "HERITAGE15",
      description: "15% off on handloom and GI-tagged pottery for festive patrons",
      discountType: "percentage",
      discountValue: 15,
      minOrderCents: 200000,
      maxDiscountCents: 150000,
      timesUsed: 42,
      usageLimit: 500,
      isActive: true,
      expiresAt: "2026-12-31T23:59:59Z",
    },
    {
      id: "cp-02",
      code: "WELCOME500",
      description: "Flat ₹500 discount on first multi-vendor marketplace order",
      discountType: "flat",
      discountValue: 50000,
      minOrderCents: 300000,
      timesUsed: 118,
      usageLimit: 1000,
      isActive: true,
      expiresAt: "2026-10-31T23:59:59Z",
    },
    {
      id: "cp-03",
      code: "DIWALI25",
      description: "Flash festive discount on handcrafted home decor items",
      discountType: "percentage",
      discountValue: 25,
      minOrderCents: 500000,
      maxDiscountCents: 250000,
      timesUsed: 0,
      usageLimit: 250,
      isActive: false,
      expiresAt: "2026-11-15T23:59:59Z",
    },
  ]);

  const toggleCouponStatus = (id: string) => {
    setCoupons((prev) =>
      prev.map((c) => (c.id === id ? { ...c, isActive: !c.isActive } : c))
    );
  };

  const filtered = coupons.filter(
    (c) =>
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Promotional Coupons"
        subtitle="Manage sitewide discounts, spending thresholds, and usage limits across multi-vendor checkouts."
        badge={`${coupons.length} Promo Codes`}
        actionText="Create Coupon"
        actionHref="/coupons/new"
        actionIcon={Plus}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Search */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by promo code or promotional description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
          />
        </div>

        {/* Coupons Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Promo Code</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Discount Value</th>
                  <th className="px-4 py-3">Min Order</th>
                  <th className="px-4 py-3">Max Cap</th>
                  <th className="px-4 py-3">Usage</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono font-bold text-amber-400 text-sm">
                      {c.code}
                    </td>
                    <td className="px-4 py-3 text-slate-300 max-w-xs">
                      {c.description}
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-white">
                      {c.discountType === "percentage" ? (
                        <span>{c.discountValue}% OFF</span>
                      ) : (
                        <span>{formatCurrency(c.discountValue)} FLAT</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400">
                      {formatCurrency(c.minOrderCents)}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400">
                      {c.maxDiscountCents ? formatCurrency(c.maxDiscountCents) : "No Cap"}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {c.timesUsed} / {c.usageLimit ?? "∞"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                          c.isActive
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-slate-800 text-slate-400 border border-slate-700"
                        }`}
                      >
                        {c.isActive ? "ACTIVE" : "PAUSED"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => toggleCouponStatus(c.id)}
                        className={`px-2.5 py-1 rounded text-xs font-semibold transition cursor-pointer inline-flex items-center gap-1 ${
                          c.isActive
                            ? "bg-slate-800 hover:bg-slate-700 text-slate-300"
                            : "bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-white"
                        }`}
                      >
                        {c.isActive ? (
                          <>
                            <PauseCircle className="w-3.5 h-3.5" /> Pause
                          </>
                        ) : (
                          <>
                            <PlayCircle className="w-3.5 h-3.5" /> Activate
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
