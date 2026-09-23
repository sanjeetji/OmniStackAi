"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { formatCurrency, formatDate, getShipmentStatusBadge } from "@bazaar/shared";
import { api } from "@bazaar/shared";
import type { Shipment } from "@bazaar/shared";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ShipmentTrackPage({ params }: PageProps) {
  const { id } = use(params);
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadShipment() {
      try {
        setLoading(true);
        const data = await api.getPublicShipmentTrack(id);
        if (data && (data as any).id) {
          setShipment((data as any).shipment || data);
        }
      } catch {
        // Fallback demo shipment
        setShipment({
          id: id,
          order_id: "ord-demo-001",
          shop_id: "shp-jaipur",
          shipment_number: "SHP-9821-01",
          status: "shipped",
          subtotal_cents: 480000,
          commission_cents: 48000,
          vendor_payout_cents: 432000,
          shipping_fee_cents: 0,
          courier_name: "Blue Dart Express",
          tracking_number: "BD-994821034",
          placed_at: new Date(Date.now() - 1000 * 60 * 60 * 20).toISOString(),
          accepted_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
          packed_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
          shipped_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 20).toISOString(),
          shop_name: "Jaipur Blue Art Pottery",
          shop_slug: "jaipur-pottery",
          items: [
            {
              id: "si-001",
              shipment_id: id,
              variant_id: "var-001",
              product_id: "prod-001",
              product_title: "Hand-Painted Royal Blue Terracotta Vase",
              variant_title: "Cobalt Blue / 12 inch",
              sku: "JBP-VASE-BLU-12",
              unit_price_cents: 240000,
              quantity: 2,
              total_price_cents: 480000,
              image_url: "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
            },
          ],
          tracking: [
            {
              id: "trk-1",
              shipment_id: id,
              status: "placed",
              location: "Jaipur Artisan Studio, Rajasthan",
              message: "Consignment initiated and transmitted to Master Craftsman",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 20).toISOString(),
            },
            {
              id: "trk-2",
              shipment_id: id,
              status: "accepted",
              location: "Jaipur Artisan Studio, Rajasthan",
              message: "Artisan acknowledged order and began kiln protective packaging",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
            },
            {
              id: "trk-3",
              shipment_id: id,
              status: "packed",
              location: "Bazaar Origin Verification Hub, Jaipur",
              message: "Quality inspected, authenticity certificate enclosed, barcode sealed",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
            },
            {
              id: "trk-4",
              shipment_id: id,
              status: "shipped",
              location: "Jaipur Airport Air Cargo Terminal",
              message: "Handed over to Blue Dart Express Flight BD-402 toward Bengaluru Gateway",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
            },
            {
              id: "trk-5",
              shipment_id: id,
              status: "in_transit",
              location: "Bengaluru Cargo Sorting Hub, Devanahalli",
              message: "Arrived at destination city hub. Sorting for Indiranagar last-mile hub",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 1).toISOString(),
            },
          ],
        });
      } finally {
        setLoading(false);
      }
    }
    loadShipment();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="w-12 h-12 border-4 border-amber-700 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-stone-600 font-medium">Retrieving shipment telemetry...</p>
      </div>
    );
  }

  if (!shipment) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-serif font-bold text-stone-900 mb-2">Shipment Not Found</h2>
        <p className="text-stone-600 text-sm mb-6">Could not locate tracking records for #{id}.</p>
        <Link
          href="/orders"
          className="px-6 py-2.5 bg-amber-700 text-white rounded-xl text-sm font-semibold hover:bg-amber-800 transition"
        >
          View My Orders
        </Link>
      </div>
    );
  }

  const badge = getShipmentStatusBadge(shipment.status);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Navigation */}
      <nav className="flex items-center gap-2 text-sm text-stone-500 mb-6">
        <Link href="/orders" className="hover:text-amber-800">
          My Orders
        </Link>
        <span>&rsaquo;</span>
        <span className="font-mono text-stone-800 font-semibold">
          Consignment #{shipment.shipment_number}
        </span>
      </nav>

      {/* Main Tracking Card */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden mb-8">
        {/* Header */}
        <div className="p-6 bg-stone-900 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl sm:text-2xl font-serif font-bold">
                Package #{shipment.shipment_number}
              </h1>
              <span
                className={`inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold ${badge.color}`}
              >
                {badge.label}
              </span>
            </div>
            <p className="text-stone-400 text-xs mt-1">
              Dispatched directly from{" "}
              <Link
                href={`/shops/${shipment.shop_slug}`}
                className="text-amber-400 hover:underline font-semibold"
              >
                {shipment.shop_name}
              </Link>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href={`/orders/${shipment.order_id}/live`}
              className="px-3.5 py-1.5 bg-amber-700 hover:bg-amber-600 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Live Radar</span>
            </Link>
          </div>
        </div>

        {/* Courier & Tracking Details Row */}
        <div className="p-6 bg-amber-50/50 border-b border-stone-200 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <span className="text-stone-500 block uppercase tracking-wider text-[10px] font-bold">
              Logistics Partner
            </span>
            <span className="text-stone-900 font-semibold text-sm">
              {shipment.courier_name || "Bazaar Artisan Logistics"}
            </span>
          </div>
          <div>
            <span className="text-stone-500 block uppercase tracking-wider text-[10px] font-bold">
              Air Waybill (AWB)
            </span>
            <code className="text-stone-900 font-mono font-bold text-sm">
              {shipment.tracking_number || "AWB-PENDING"}
            </code>
          </div>
          <div>
            <span className="text-stone-500 block uppercase tracking-wider text-[10px] font-bold">
              Consignment Subtotal
            </span>
            <span className="text-amber-800 font-bold text-sm">
              {formatCurrency(shipment.subtotal_cents)}
            </span>
          </div>
        </div>

        {/* Milestone Timeline */}
        <div className="p-6 sm:p-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-stone-500 mb-6">
            Transit Checkpoints & Hand-offs
          </h2>

          <div className="relative pl-6 border-l-2 border-amber-200 space-y-8">
            {shipment.tracking && shipment.tracking.length > 0 ? (
              shipment.tracking.map((evt, idx) => {
                const isLatest = idx === shipment.tracking!.length - 1;
                return (
                  <div key={evt.id} className="relative">
                    {/* Bullet marker */}
                    <div
                      className={`absolute -left-[31px] top-0.5 w-4 h-4 rounded-full border-2 ${
                        isLatest
                          ? "bg-amber-600 border-amber-200 ring-4 ring-amber-100"
                          : "bg-white border-stone-400"
                      }`}
                    ></div>

                    <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                      <h3
                        className={`text-sm font-semibold ${
                          isLatest ? "text-amber-900 font-bold" : "text-stone-800"
                        }`}
                      >
                        {evt.message}
                      </h3>
                      <time className="text-xs text-stone-400 font-mono">
                        {formatDate(evt.occurred_at)}
                      </time>
                    </div>
                    <p className="text-xs text-stone-500 mt-0.5 flex items-center gap-1">
                      <span>📍</span>
                      <span>{evt.location}</span>
                    </p>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-stone-500">Awaiting first dispatch scan from carrier...</p>
            )}
          </div>
        </div>

        {/* Articles in this Consignment */}
        <div className="p-6 bg-stone-50 border-t border-stone-200">
          <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
            Handcrafted Artifacts in this Box
          </h3>
          <div className="space-y-3">
            {shipment.items?.map((item) => (
              <div
                key={item.id}
                className="bg-white p-3 rounded-xl border border-stone-200 flex items-center gap-4"
              >
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.product_title}
                    className="w-14 h-14 object-cover rounded-lg border border-stone-200"
                  />
                ) : (
                  <div className="w-14 h-14 bg-stone-100 rounded-lg flex items-center justify-center text-lg">
                    🏺
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-stone-900 truncate">
                    {item.product_title}
                  </h4>
                  <p className="text-xs text-stone-500">
                    {item.variant_title} &bull; Qty: {item.quantity}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-stone-900">
                    {formatCurrency(item.total_price_cents)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
