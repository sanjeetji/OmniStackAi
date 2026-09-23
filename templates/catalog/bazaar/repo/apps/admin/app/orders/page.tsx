"use client";

import { useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import {
  ShoppingBag,
  Search,
  Filter,
  Download,
  Calendar,
  Layers,
  ChevronRight,
  Truck,
  CheckCircle2,
  Clock,
  Ban,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

interface GlobalOrder {
  id: string;
  orderNumber: string;
  customerName: string;
  customerEmail: string;
  totalCents: number;
  shipmentsCount: number;
  status: "placed" | "processing" | "delivered" | "cancelled";
  paymentMethod: string;
  createdAt: string;
  shops: string[];
}

export default function AdminOrdersPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [exported, setExported] = useState(false);

  const [orders, setOrders] = useState<GlobalOrder[]>([
    {
      id: "ord-8831",
      orderNumber: "BAZ-2026-8831",
      customerName: "Priya Sharma",
      customerEmail: "priya@bazaar.test",
      totalCents: 1840000,
      shipmentsCount: 2,
      status: "processing",
      paymentMethod: "Credit Card (Mock Payment)",
      createdAt: "2026-09-23T10:14:00Z",
      shops: ["Jaipur Blue Art Pottery", "Varanasi Heritage Weaves"],
    },
    {
      id: "ord-8830",
      orderNumber: "BAZ-2026-8830",
      customerName: "Arjun Mehta",
      customerEmail: "arjun.m@example.com",
      totalCents: 3250000,
      shipmentsCount: 1,
      status: "processing",
      paymentMethod: "UPI Instant (Mock UPI)",
      createdAt: "2026-09-23T08:30:00Z",
      shops: ["Kashmir Craftsmen Guild"],
    },
    {
      id: "ord-8829",
      orderNumber: "BAZ-2026-8829",
      customerName: "Ananya Deshmukh",
      customerEmail: "ananya.d@example.com",
      totalCents: 980000,
      shipmentsCount: 1,
      status: "delivered",
      paymentMethod: "Cash on Delivery",
      createdAt: "2026-09-22T16:45:00Z",
      shops: ["Bastar Tribal Bell Metal"],
    },
    {
      id: "ord-8828",
      orderNumber: "BAZ-2026-8828",
      customerName: "Rajesh Kannan",
      customerEmail: "rajesh.k@example.com",
      totalCents: 2890000,
      shipmentsCount: 2,
      status: "delivered",
      paymentMethod: "Credit Card (Mock Payment)",
      createdAt: "2026-09-22T11:20:00Z",
      shops: ["Kanchipuram Silk Loom", "Jaipur Blue Art Pottery"],
    },
    {
      id: "ord-8827",
      orderNumber: "BAZ-2026-8827",
      customerName: "Sunita Roy",
      customerEmail: "sunita.r@example.com",
      totalCents: 450000,
      shipmentsCount: 1,
      status: "cancelled",
      paymentMethod: "UPI Instant (Mock UPI)",
      createdAt: "2026-09-21T14:10:00Z",
      shops: ["Channapatna Wooden Toys"],
    },
  ]);

  const filteredOrders = orders.filter((o) => {
    const matchesSearch =
      o.orderNumber.toLowerCase().includes(search.toLowerCase()) ||
      o.customerName.toLowerCase().includes(search.toLowerCase()) ||
      o.customerEmail.toLowerCase().includes(search.toLowerCase()) ||
      o.shops.some((s) => s.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus =
      statusFilter === "all" || o.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleExportCsv = () => {
    setExported(true);
    setTimeout(() => setExported(false), 3000);
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Global Orders List"
        subtitle="Platform-wide order registry with multi-vendor split consignment indicators and audit links."
        badge={`${orders.length} Orders`}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Search, Filter & CSV Export */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by order number, customer name, email, or workshop..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Filter className="w-3.5 h-3.5" />
              <span>Status:</span>
            </div>
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {["all", "placed", "processing", "delivered", "cancelled"].map((st) => (
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

            <button
              onClick={handleExportCsv}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 text-xs text-slate-300 hover:text-white transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {exported && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            CSV export generated successfully: bazaar_orders_export.csv
          </div>
        )}

        {/* Global Orders Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Order Number</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Vendor Workshops</th>
                  <th className="px-4 py-3">Split Shipments</th>
                  <th className="px-4 py-3">Total (₹)</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filteredOrders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono font-medium text-amber-400">
                      {ord.orderNumber}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-100">{ord.customerName}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{ord.customerEmail}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                      {formatDate(ord.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        {ord.shops.map((s, idx) => (
                          <div key={idx} className="text-slate-300">
                            • {s}
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700 inline-flex items-center gap-1">
                        <Truck className="w-3 h-3 text-slate-400" />
                        {ord.shipmentsCount} consignments
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-white">
                      {formatCurrency(ord.totalCents)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                          ord.status === "delivered"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : ord.status === "processing"
                            ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                            : ord.status === "cancelled"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {ord.status === "delivered" ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : ord.status === "cancelled" ? (
                          <Ban className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        {ord.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/orders/${ord.id}`}
                        className="px-2.5 py-1 rounded bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-white font-semibold transition"
                      >
                        Investigate
                      </Link>
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
