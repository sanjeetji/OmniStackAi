"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatPrice, formatStatusBadge, formatStatusLabel, api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import {
  TrendingUp,
  PackageCheck,
  Clock,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
} from "lucide-react";

const DEMO_METRICS = {
  grossSalesCents: 1480000,
  netEarningsCents: 1332000,
  commissionCents: 148000,
  pendingFulfillmentCount: 2,
  activeListingCount: 8,
  lowStockCount: 1,
};

const RECENT_SHIPMENTS = [
  {
    id: "shp-demo-001",
    shipment_number: "SHP-9821-01",
    order_number: "BZR-9821-441",
    customer_name: "Priya Sharma",
    status: "shipped",
    subtotal_cents: 480000,
    vendor_payout_cents: 432000,
    item_count: 2,
    courier_name: "Blue Dart Express",
    tracking_number: "BD-994821034",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
  },
  {
    id: "shp-demo-004",
    shipment_number: "SHP-9102-01",
    order_number: "BZR-9102-112",
    customer_name: "Vikram Mehta",
    status: "placed",
    subtotal_cents: 520000,
    vendor_payout_cents: 468000,
    item_count: 1,
    courier_name: null,
    tracking_number: null,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  },
  {
    id: "shp-demo-005",
    shipment_number: "SHP-8840-01",
    order_number: "BZR-8840-801",
    customer_name: "Sunita Patel",
    status: "delivered",
    subtotal_cents: 720000,
    vendor_payout_cents: 648000,
    item_count: 3,
    courier_name: "Delhivery Air",
    tracking_number: "DL-399102941",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
  },
];

export default function SellerDashboardPage() {
  const [metrics, setMetrics] = useState(DEMO_METRICS);
  const [shipments, setShipments] = useState(RECENT_SHIPMENTS);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getVendorDashboard();
        if (res.metrics) {
          setMetrics({ ...DEMO_METRICS, ...res.metrics });
        }
        const sRes = await api.getVendorShipments();
        if (sRes.shipments && sRes.shipments.length > 0) {
          setShipments(sRes.shipments.slice(0, 5) as any);
        }
      } catch {
        // Fallback to demo metrics
      }
    }
    load();
  }, []);

  return (
    <div className="flex-1 pb-12">
      <SellerHeader
        title="Atelier Workshop Operations"
        description="Master Artisan Kripal Singh • Jaipur Blue Art Pottery"
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* KPI Tiles 4-Col Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs">
            <div className="flex items-center justify-between text-stone-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Gross Sales</span>
              <TrendingUp className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold font-serif text-stone-900">
              {formatPrice(metrics.grossSalesCents)}
            </div>
            <p className="text-[11px] text-stone-500 mt-1">Across 8 multi-vendor orders</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs">
            <div className="flex items-center justify-between text-stone-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Net Payouts</span>
              <span className="text-xs font-mono font-bold text-amber-700">90% Split</span>
            </div>
            <div className="text-2xl font-bold font-serif text-amber-800">
              {formatPrice(metrics.netEarningsCents)}
            </div>
            <p className="text-[11px] text-stone-500 mt-1">Credited directly to escrow</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs">
            <div className="flex items-center justify-between text-stone-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Needs Action</span>
              <Clock className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-2xl font-bold font-serif text-amber-600">
              {metrics.pendingFulfillmentCount}
            </div>
            <p className="text-[11px] text-stone-500 mt-1">Orders awaiting packing or carrier</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-stone-200/80 shadow-2xs">
            <div className="flex items-center justify-between text-stone-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Stock Alert</span>
              <AlertTriangle className="w-4 h-4 text-rose-600" />
            </div>
            <div className="text-2xl font-bold font-serif text-rose-600">
              {metrics.lowStockCount}
            </div>
            <p className="text-[11px] text-stone-500 mt-1">Vase variant below 5 units</p>
          </div>
        </div>

        {/* Priority Action Alert Card */}
        {metrics.pendingFulfillmentCount > 0 && (
          <div className="bg-amber-900 text-white rounded-2xl p-6 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <span className="text-3xl p-3 bg-amber-800/80 rounded-xl">📦</span>
              <div>
                <h3 className="text-base font-bold">
                  {metrics.pendingFulfillmentCount} Consignment(s) Awaiting Dispatch
                </h3>
                <p className="text-xs text-amber-200/90 mt-1 max-w-xl">
                  Buyers are tracking delivery in real-time. Please accept, package in bubble wrap,
                  and hand over to our verified air courier partner.
                </p>
              </div>
            </div>
            <Link
              href="/shipments"
              className="px-5 py-2.5 bg-white text-stone-900 rounded-xl text-xs font-bold hover:bg-stone-100 transition self-start md:self-auto shadow-sm"
            >
              Open Fulfillment Board &rarr;
            </Link>
          </div>
        )}

        {/* Recent Consignments Table */}
        <div className="bg-white rounded-2xl border border-stone-200/80 overflow-hidden shadow-2xs">
          <div className="p-6 border-b border-stone-100 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold font-serif text-stone-900">
                Recent Orders & Consignments
              </h2>
              <p className="text-xs text-stone-500 mt-0.5">
                Independent packages dispatched from your Jaipur atelier.
              </p>
            </div>
            <Link
              href="/shipments"
              className="text-xs font-semibold text-amber-800 hover:text-amber-900 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-stone-50/80 text-stone-500 uppercase tracking-wider font-semibold border-b border-stone-200/60">
                <tr>
                  <th className="py-3 px-6">Consignment #</th>
                  <th className="py-3 px-6">Customer</th>
                  <th className="py-3 px-6">Items</th>
                  <th className="py-3 px-6">Net Payout</th>
                  <th className="py-3 px-6">Status</th>
                  <th className="py-3 px-6">Carrier / AWB</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {shipments.map((s) => {
                  const badge = formatStatusBadge(s.status);
                  const label = formatStatusLabel(s.status);
                  return (
                    <tr key={s.id} className="hover:bg-stone-50/60 transition">
                      <td className="py-4 px-6 font-mono font-semibold text-stone-900">
                        {s.shipment_number}
                        <span className="block text-[10px] text-stone-400 font-sans">
                          Order: {s.order_number}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className="font-semibold text-stone-800">{s.customer_name}</span>
                      </td>
                      <td className="py-4 px-6 text-stone-600">{s.item_count} piece(s)</td>
                      <td className="py-4 px-6 font-bold text-amber-900">
                        {formatPrice(s.vendor_payout_cents)}
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${badge.bg} ${badge.text} ${badge.border} border`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
                          <span>{label}</span>
                        </span>
                      </td>
                      <td className="py-4 px-6 text-stone-500">
                        {s.courier_name ? (
                          <span>
                            {s.courier_name}{" "}
                            <code className="text-[10px] block font-mono text-stone-700">
                              {s.tracking_number}
                            </code>
                          </span>
                        ) : (
                          <span className="text-stone-400 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-right">
                        <Link
                          href={`/shipments/${s.id}`}
                          className="px-3 py-1.5 rounded-lg border border-stone-300 hover:bg-stone-100 font-semibold text-stone-700 text-xs transition"
                        >
                          Manage &rarr;
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
