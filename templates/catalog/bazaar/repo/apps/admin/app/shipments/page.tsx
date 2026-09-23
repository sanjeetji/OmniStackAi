"use client";

import { useState } from "react";
import Link from "next/link";
import { AdminHeader } from "@/components/admin-header";
import { StatCard } from "@/components/stat-card";
import {
  Truck,
  Search,
  Filter,
  Package,
  MapPin,
  Clock,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import { formatDate } from "@bazaar/shared";

interface AdminShipment {
  id: string;
  orderNumber: string;
  orderId: string;
  shopName: string;
  customerName: string;
  destinationCity: string;
  courierName: string;
  trackingNumber: string;
  status: "placed" | "accepted" | "packed" | "shipped" | "delivered" | "returned";
  updatedAt: string;
  slaDaysRemaining: number;
}

export default function AdminShipmentsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [shipments, setShipments] = useState<AdminShipment[]>([
    {
      id: "shp-8831-01",
      orderNumber: "BAZ-2026-8831",
      orderId: "ord-8831",
      shopName: "Jaipur Blue Art Pottery",
      customerName: "Priya Sharma",
      destinationCity: "Bengaluru, Karnataka",
      courierName: "Blue Dart Express",
      trackingNumber: "BD-88392190-IN",
      status: "packed",
      updatedAt: "2026-09-23T11:45:00Z",
      slaDaysRemaining: 2,
    },
    {
      id: "shp-8831-02",
      orderNumber: "BAZ-2026-8831",
      orderId: "ord-8831",
      shopName: "Varanasi Heritage Weaves",
      customerName: "Priya Sharma",
      destinationCity: "Bengaluru, Karnataka",
      courierName: "Delhivery Surface",
      trackingNumber: "DEL-44120982-IN",
      status: "accepted",
      updatedAt: "2026-09-23T10:30:00Z",
      slaDaysRemaining: 3,
    },
    {
      id: "shp-8830-01",
      orderNumber: "BAZ-2026-8830",
      orderId: "ord-8830",
      shopName: "Kashmir Craftsmen Guild",
      customerName: "Arjun Mehta",
      destinationCity: "Mumbai, Maharashtra",
      courierName: "Blue Dart Express",
      trackingNumber: "BD-99128472-IN",
      status: "shipped",
      updatedAt: "2026-09-23T09:15:00Z",
      slaDaysRemaining: 1,
    },
    {
      id: "shp-8829-01",
      orderNumber: "BAZ-2026-8829",
      orderId: "ord-8829",
      shopName: "Bastar Tribal Bell Metal",
      customerName: "Ananya Deshmukh",
      destinationCity: "Pune, Maharashtra",
      courierName: "India Post Speed Post",
      trackingNumber: "SP-77123984-IN",
      status: "delivered",
      updatedAt: "2026-09-22T17:10:00Z",
      slaDaysRemaining: 0,
    },
    {
      id: "shp-8828-01",
      orderNumber: "BAZ-2026-8828",
      orderId: "ord-8828",
      shopName: "Kanchipuram Silk Loom",
      customerName: "Rajesh Kannan",
      destinationCity: "Chennai, Tamil Nadu",
      courierName: "Blue Dart Express",
      trackingNumber: "BD-77120934-IN",
      status: "delivered",
      updatedAt: "2026-09-22T14:30:00Z",
      slaDaysRemaining: 0,
    },
  ]);

  const filteredShipments = shipments.filter((shp) => {
    const matchesSearch =
      shp.id.toLowerCase().includes(search.toLowerCase()) ||
      shp.orderNumber.toLowerCase().includes(search.toLowerCase()) ||
      shp.shopName.toLowerCase().includes(search.toLowerCase()) ||
      shp.trackingNumber.toLowerCase().includes(search.toLowerCase()) ||
      shp.destinationCity.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || shp.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Global Shipments Monitor"
        subtitle="Cross-vendor logistics supervision tracking carrier dispatch telemetry and SLA compliance."
        badge="Carrier Sync Active"
        actionText="Live Logistics Map"
        actionHref="/live-map"
        actionIcon={MapPin}
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Logistics KPI Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="In-Transit Consignments"
            value="18"
            subtitle="Air & Surface linehaul"
            trend="99.4% On Schedule"
            trendPositive={true}
            icon={Truck}
            tone="sky"
          />
          <StatCard
            title="Delivered Today"
            value="34"
            subtitle="Verified OTP handovers"
            trend="+12% vs yesterday"
            trendPositive={true}
            icon={CheckCircle2}
            tone="emerald"
          />
          <StatCard
            title="Pending Atelier Dispatch"
            value="6"
            subtitle="Waiting for courier pickup"
            trend="Average SLA: 1.4 days"
            trendPositive={true}
            icon={Clock}
            tone="amber"
          />
          <StatCard
            title="Carrier Bottlenecks"
            value="0"
            subtitle="Zero transit exceptions"
            trend="All hubs normal"
            trendPositive={true}
            icon={AlertCircle}
            tone="default"
          />
        </div>

        {/* Search & Status Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by consignment ID, AWB, workshop atelier, or destination..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Milestone:</span>
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {["all", "placed", "accepted", "packed", "shipped", "delivered"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2 py-0.5 rounded capitalize font-medium transition cursor-pointer ${
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

        {/* Shipments Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Consignment ID</th>
                  <th className="px-4 py-3">Order #</th>
                  <th className="px-4 py-3">Origin Workshop</th>
                  <th className="px-4 py-3">Destination</th>
                  <th className="px-4 py-3">Courier &amp; AWB</th>
                  <th className="px-4 py-3">Milestone</th>
                  <th className="px-4 py-3">Last Updated</th>
                  <th className="px-4 py-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filteredShipments.map((shp) => (
                  <tr key={shp.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-mono font-medium text-amber-400">
                      {shp.id}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">
                      <Link
                        href={`/orders/${shp.orderId}`}
                        className="hover:underline text-slate-200"
                      >
                        {shp.orderNumber}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-200">
                      {shp.shopName}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {shp.destinationCity}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      <div className="text-white font-semibold">{shp.courierName}</div>
                      <div className="text-[11px] text-amber-400">{shp.trackingNumber}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                          shp.status === "delivered"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : shp.status === "shipped"
                            ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {shp.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                      {formatDate(shp.updatedAt)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/orders/${shp.orderId}`}
                        className="text-amber-400 hover:text-amber-300 font-semibold"
                      >
                        View Order
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
