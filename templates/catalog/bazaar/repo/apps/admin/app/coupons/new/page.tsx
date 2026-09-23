"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AdminHeader } from "@/components/admin-header";
import {
  Tag,
  ArrowLeft,
  Percent,
  CheckCircle2,
  Sparkles,
  Calendar,
} from "lucide-react";
import { formatCurrency } from "@bazaar/shared";

export default function AdminCreateCouponPage() {
  const router = useRouter();

  const [code, setCode] = useState("CRAFTFEST20");
  const [description, setDescription] = useState("20% off on all artisan woodwork and handlooms");
  const [discountType, setDiscountType] = useState<"percentage" | "flat">("percentage");
  const [discountValue, setDiscountValue] = useState(20);
  const [minOrder, setMinOrder] = useState(2500);
  const [maxDiscount, setMaxDiscount] = useState(1500);
  const [usageLimit, setUsageLimit] = useState(250);
  const [expiresAt, setExpiresAt] = useState("2026-11-30");
  const [created, setCreated] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCreated(true);
    setTimeout(() => {
      router.push("/coupons");
    }, 1200);
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Create Promotional Coupon"
        subtitle="Configure discount rules, cart thresholds, and customer redemption limits."
      />

      <div className="p-6 space-y-6 flex-1 max-w-4xl">
        <Link
          href="/coupons"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Coupons
        </Link>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Coupon Form */}
          <form
            onSubmit={handleSubmit}
            className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 text-xs"
          >
            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Coupon Code
              </label>
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="e.g. HERITAGE20"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono uppercase font-bold tracking-wider focus:outline-none focus:border-amber-500"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Marketing Description
              </label>
              <input
                type="text"
                required
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. 15% off across all handloom sarees"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Discount Type
                </label>
                <select
                  value={discountType}
                  onChange={(e) => setDiscountType(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500"
                >
                  <option value="percentage">Percentage Discount (%)</option>
                  <option value="flat">Flat Amount Discount (₹)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Discount Value {discountType === "percentage" ? "(%)" : "(₹)"}
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={discountValue}
                  onChange={(e) => setDiscountValue(parseInt(e.target.value || "0", 10))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Minimum Cart Spend (₹)
                </label>
                <input
                  type="number"
                  min="0"
                  value={minOrder}
                  onChange={(e) => setMinOrder(parseInt(e.target.value || "0", 10))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Maximum Discount Cap (₹)
                </label>
                <input
                  type="number"
                  min="0"
                  value={maxDiscount}
                  onChange={(e) => setMaxDiscount(parseInt(e.target.value || "0", 10))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Redemption Limit
                </label>
                <input
                  type="number"
                  min="1"
                  value={usageLimit}
                  onChange={(e) => setUsageLimit(parseInt(e.target.value || "0", 10))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Expiration Date
                </label>
                <input
                  type="date"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold transition cursor-pointer"
            >
              Publish Active Coupon
            </button>

            {created && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Coupon {code} published and activated across buyer storefront carts.
              </div>
            )}
          </form>

          {/* Live Storefront Preview */}
          <div className="space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                Storefront Badge Preview
              </span>

              <div className="p-4 rounded-xl bg-gradient-to-br from-amber-950/60 to-slate-950 border border-amber-500/30 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-amber-300 text-sm tracking-wide">
                    {code || "PROMO_CODE"}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-300 font-mono text-[10px] font-bold">
                    {discountType === "percentage" ? `${discountValue}% OFF` : `₹${discountValue} OFF`}
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  {description || "Marketing offer description."}
                </p>
                <div className="pt-2 border-t border-amber-500/20 text-[10px] text-slate-400 font-mono flex justify-between">
                  <span>Min Cart: ₹{minOrder}</span>
                  <span>Expires: {expiresAt}</span>
                </div>
              </div>

              <p className="text-[11px] text-slate-400">
                Shoppers can apply this code directly in the multi-vendor shopping cart and checkout review.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
