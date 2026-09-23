"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AdminHeader } from "@/components/admin-header";
import {
  Store,
  ShieldCheck,
  Building,
  CreditCard,
  Percent,
  Package,
  Truck,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
} from "lucide-react";
import { formatCurrency } from "@bazaar/shared";

export default function AdminShopReviewPage() {
  const params = useParams();
  const shopId = (params?.id as string) || "shop-001";

  const [commissionRate, setCommissionRate] = useState("10.00");
  const [savedCommission, setSavedCommission] = useState(false);
  const [shopStatus, setShopStatus] = useState<"verified" | "suspended">("verified");

  const shop = {
    id: shopId,
    name: "Jaipur Blue Art Pottery",
    slug: "jaipur-blue-pottery",
    artisanName: "Kripal Singh Shekhawat",
    artisanEmail: "kripal@bazaar.test",
    phone: "+91 98290 12345",
    heritage: "UNESCO Recognized Quartz Glazed Blue Ceramic Pottery",
    giTag: "GI Tag #39 (Jaipur Blue Pottery)",
    address: "Kripal Kumbh, B-18, Shiv Marg, Bani Park, Jaipur 302016",
    bank: {
      accountHolder: "Jaipur Blue Art Pottery Atelier",
      bankName: "State Bank of India",
      accountNumber: "389201948291",
      ifscCode: "SBIN0004123",
      branch: "Bani Park Main Branch, Jaipur",
    },
    metrics: {
      gmvCents: 6450000,
      totalOrders: 48,
      rating: 4.9,
      reviewCount: 32,
    },
  };

  const activeProducts = [
    {
      id: "p-01",
      title: "Royal Mughal Cobalt Floral Vase (12\")",
      sku: "JBP-MUG-12",
      category: "Home & Decor",
      priceCents: 245000,
      stock: 12,
    },
    {
      id: "p-02",
      title: "Hand-Painted Peacock Indigo Serving Platter",
      sku: "JBP-PLT-PEA",
      category: "Kitchen & Dining",
      priceCents: 185000,
      stock: 8,
    },
    {
      id: "p-03",
      title: "Traditional Floral Tile Coasters (Set of 6)",
      sku: "JBP-CST-06",
      category: "Tableware",
      priceCents: 85000,
      stock: 25,
    },
  ];

  const handleSaveCommission = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedCommission(true);
    setTimeout(() => setSavedCommission(false), 3000);
  };

  const handleToggleStatus = () => {
    setShopStatus((prev) => (prev === "verified" ? "suspended" : "verified"));
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title={shop.name}
        subtitle={`Master Craftsman: ${shop.artisanName} • ${shop.heritage}`}
        badge={shop.giTag}
        actionText="KYC Verification"
        actionHref={`/shops/${shop.id}/kyc`}
        actionIcon={ShieldCheck}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Back Link */}
        <Link
          href="/shops"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Vendor Directory
        </Link>

        {/* Top Profile Summary Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Atelier Overview */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Workshop Profile
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                  shopStatus === "verified"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                }`}
              >
                {shopStatus.toUpperCase()}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <span className="text-slate-400">Master Craftsman:</span>{" "}
                <span className="text-white font-semibold">{shop.artisanName}</span>
              </div>
              <div>
                <span className="text-slate-400">Email:</span>{" "}
                <span className="text-slate-200 font-mono">{shop.artisanEmail}</span>
              </div>
              <div>
                <span className="text-slate-400">Contact:</span>{" "}
                <span className="text-slate-200">{shop.phone}</span>
              </div>
              <div>
                <span className="text-slate-400">Atelier Studio:</span>{" "}
                <span className="text-slate-300">{shop.address}</span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
              <button
                type="button"
                onClick={handleToggleStatus}
                className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition cursor-pointer ${
                  shopStatus === "verified"
                    ? "bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/30"
                    : "bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30"
                }`}
              >
                {shopStatus === "verified" ? "Suspend Workshop" : "Re-activate Workshop"}
              </button>

              <a
                href={`http://localhost:3001/shops/${shop.slug}`}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
              >
                Public Storefront <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Commission Policy Editor */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Percent className="w-3.5 h-3.5 text-amber-400" />
                Commission Take-Rate
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Bps Rule</span>
            </div>

            <p className="text-xs text-slate-400">
              Contracted platform service fee withheld from gross consignment settlements.
            </p>

            <form onSubmit={handleSaveCommission} className="space-y-3">
              <div>
                <label className="block text-[11px] text-slate-300 font-medium mb-1">
                  Commission Percentage (%)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    max="50"
                    value={commissionRate}
                    onChange={(e) => setCommissionRate(e.target.value)}
                    className="w-24 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-white font-mono text-sm focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-xs text-slate-400 font-mono">% (Basis Points: {Math.round(parseFloat(commissionRate || "0") * 100)})</span>
                </div>
              </div>

              <button
                type="submit"
                className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition cursor-pointer"
              >
                Update Commission Policy
              </button>

              {savedCommission && (
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Commission rate updated and logged to audit trail.
                </div>
              )}
            </form>
          </div>

          {/* Bank & Settlement Route */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-emerald-400" />
                Settlement Banking
              </span>
              <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                Verified NEFT/RTGS
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <span className="text-slate-400">Account Name:</span>{" "}
                <span className="text-white font-medium">{shop.bank.accountHolder}</span>
              </div>
              <div>
                <span className="text-slate-400">Bank:</span>{" "}
                <span className="text-slate-200">{shop.bank.bankName}</span>
              </div>
              <div>
                <span className="text-slate-400">Account Number:</span>{" "}
                <span className="text-slate-200 font-mono">{shop.bank.accountNumber}</span>
              </div>
              <div>
                <span className="text-slate-400">IFSC Code:</span>{" "}
                <span className="text-amber-400 font-mono font-bold">{shop.bank.ifscCode}</span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
              Auto-payouts disburse every Tuesday following a 7-day escrow hold.
            </div>
          </div>
        </div>

        {/* Active Product Listings */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Package className="w-4 h-4 text-amber-400" />
              Active Craft Catalog ({activeProducts.length} items)
            </h3>
            <span className="text-xs text-slate-400">Stock actively reserved in live carts</span>
          </div>

          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Product Name</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Base Price</th>
                <th className="px-4 py-3">Available Stock</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {activeProducts.map((p) => (
                <tr key={p.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-4 py-3 font-medium text-white">{p.title}</td>
                  <td className="px-4 py-3 font-mono text-slate-400">{p.sku}</td>
                  <td className="px-4 py-3 text-slate-300">{p.category}</td>
                  <td className="px-4 py-3 font-mono font-bold text-amber-400">
                    {formatCurrency(p.priceCents)}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-200">{p.stock} units</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
