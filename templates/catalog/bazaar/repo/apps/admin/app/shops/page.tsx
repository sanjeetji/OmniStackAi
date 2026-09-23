"use client";

import { useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import {
  Store,
  ShieldCheck,
  Search,
  Filter,
  ExternalLink,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Ban,
} from "lucide-react";
import { formatCurrency } from "@bazaar/shared";

interface ShopEntry {
  id: string;
  name: string;
  slug: string;
  artisanName: string;
  artisanEmail: string;
  craftHeritage: string;
  giTag: string;
  location: string;
  kycStatus: "verified" | "pending" | "suspended" | "rejected";
  commissionBps: number;
  productCount: number;
  gmvCents: number;
  rating: number;
}

export default function AdminShopsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [shops, setShops] = useState<ShopEntry[]>([
    {
      id: "shop-001",
      name: "Jaipur Blue Art Pottery",
      slug: "jaipur-blue-pottery",
      artisanName: "Kripal Singh Shekhawat",
      artisanEmail: "kripal@bazaar.test",
      craftHeritage: "Quartz glazed ceramic pottery",
      giTag: "GI Tag #39",
      location: "Jaipur, Rajasthan",
      kycStatus: "verified",
      commissionBps: 1000,
      productCount: 14,
      gmvCents: 6450000,
      rating: 4.9,
    },
    {
      id: "shop-002",
      name: "Bastar Tribal Bell Metal",
      slug: "bastar-bell-metal",
      artisanName: "Devnath Baghel",
      artisanEmail: "devnath@bazaar.test",
      craftHeritage: "Dhokra lost-wax bronze casting",
      giTag: "GI Tag #84",
      location: "Kondagaon, Chhattisgarh",
      kycStatus: "pending",
      commissionBps: 1000,
      productCount: 8,
      gmvCents: 2180000,
      rating: 4.8,
    },
    {
      id: "shop-003",
      name: "Varanasi Heritage Weaves",
      slug: "varanasi-weaves",
      artisanName: "Munna Lal Ansari",
      artisanEmail: "ansari@bazaar.test",
      craftHeritage: "Zari brocade pure silk sarees",
      giTag: "GI Tag #69",
      location: "Varanasi, Uttar Pradesh",
      kycStatus: "verified",
      commissionBps: 800, // 8% preferred rate
      productCount: 19,
      gmvCents: 8940000,
      rating: 5.0,
    },
    {
      id: "shop-004",
      name: "Kashmir Craftsmen Guild",
      slug: "kashmir-craftsmen",
      artisanName: "Ghulam Hassan",
      artisanEmail: "ghulam@bazaar.test",
      craftHeritage: "Hand-spun Pashmina & Sozni embroidery",
      giTag: "GI Tag #46",
      location: "Srinagar, Kashmir",
      kycStatus: "verified",
      commissionBps: 1000,
      productCount: 11,
      gmvCents: 4120000,
      rating: 4.9,
    },
    {
      id: "shop-005",
      name: "Channapatna Wooden Toys",
      slug: "channapatna-toys",
      artisanName: "Syed Basha",
      artisanEmail: "syed@bazaar.test",
      craftHeritage: "Natural lacquer turned ivory wood",
      giTag: "GI Tag #19",
      location: "Channapatna, Karnataka",
      kycStatus: "pending",
      commissionBps: 1000,
      productCount: 6,
      gmvCents: 1250000,
      rating: 4.7,
    },
    {
      id: "shop-006",
      name: "Kanchipuram Silk Loom",
      slug: "kanchipuram-loom",
      artisanName: "S. Swaminathan",
      artisanEmail: "swami@bazaar.test",
      craftHeritage: "Korvai woven temple border silks",
      giTag: "GI Tag #1",
      location: "Kanchipuram, Tamil Nadu",
      kycStatus: "verified",
      commissionBps: 1000,
      productCount: 16,
      gmvCents: 7300000,
      rating: 4.9,
    },
  ]);

  const filteredShops = shops.filter((shop) => {
    const matchesSearch =
      shop.name.toLowerCase().includes(search.toLowerCase()) ||
      shop.artisanName.toLowerCase().includes(search.toLowerCase()) ||
      shop.location.toLowerCase().includes(search.toLowerCase()) ||
      shop.craftHeritage.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || shop.kycStatus === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Vendor Directory"
        subtitle="Supervise all artisan guild workshops, Geographical Indication (GI) accreditations, and take-rate commission policies."
        badge={`${shops.length} Workshops`}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Search & Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by workshop name, master artisan, GI tag, or craft lineage..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">KYC Status:</span>
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {["all", "verified", "pending", "suspended"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md capitalize font-medium transition cursor-pointer ${
                    statusFilter === st
                      ? "bg-amber-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Workshops Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Artisan Workshop</th>
                  <th className="px-4 py-3">Master Craftsman</th>
                  <th className="px-4 py-3">Craft Heritage &amp; GI</th>
                  <th className="px-4 py-3">Listings</th>
                  <th className="px-4 py-3">Commission</th>
                  <th className="px-4 py-3">Gross Sales</th>
                  <th className="px-4 py-3">KYC Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filteredShops.map((shop) => (
                  <tr key={shop.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-semibold text-white">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-amber-400">
                          <Store className="w-3.5 h-3.5" />
                        </div>
                        <div>
                          <div className="text-slate-100 font-bold">{shop.name}</div>
                          <div className="text-[11px] text-slate-400">{shop.location}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-slate-200 font-medium">{shop.artisanName}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{shop.artisanEmail}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-slate-300">{shop.craftHeritage}</div>
                      <span className="inline-block mt-0.5 text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        {shop.giTag}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      {shop.productCount} items
                    </td>
                    <td className="px-4 py-3 font-mono text-amber-400 font-semibold">
                      {(shop.commissionBps / 100).toFixed(2)}%
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-white">
                      {formatCurrency(shop.gmvCents)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                          shop.kycStatus === "verified"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : shop.kycStatus === "pending"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {shop.kycStatus === "verified" ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : shop.kycStatus === "pending" ? (
                          <Clock className="w-3 h-3" />
                        ) : (
                          <Ban className="w-3 h-3" />
                        )}
                        {shop.kycStatus.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/shops/${shop.id}/kyc`}
                          className="px-2 py-1 rounded bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-white font-semibold transition"
                        >
                          KYC
                        </Link>
                        <Link
                          href={`/shops/${shop.id}`}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                        >
                          Review
                        </Link>
                      </div>
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
