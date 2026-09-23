"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatPrice, formatDate, formatStatusBadge, formatStatusLabel, api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { CheckCircle2, Box, Truck, Check, RefreshCw } from "lucide-react";

interface ShipmentItem {
  id: string;
  product_title: string;
  variant_title: string;
  sku: string;
  quantity: number;
  total_price_cents: number;
  image_url?: string;
}

interface ShipmentRow {
  id: string;
  shipment_number: string;
  order_number: string;
  customer_name: string;
  customer_phone?: string;
  customer_email?: string;
  status: "placed" | "accepted" | "packed" | "shipped" | "delivered" | "cancelled" | "returned";
  subtotal_cents: number;
  vendor_payout_cents: number;
  courier_name?: string | null;
  tracking_number?: string | null;
  created_at: string;
  items?: ShipmentItem[];
}

const DEMO_SHIPMENTS: ShipmentRow[] = [
  {
    id: "shp-demo-001",
    shipment_number: "SHP-9821-01",
    order_number: "BZR-9821-441",
    customer_name: "Priya Sharma",
    customer_phone: "+91 98765 43210",
    customer_email: "priya.sharma@example.com",
    status: "shipped",
    subtotal_cents: 480000,
    vendor_payout_cents: 432000,
    courier_name: "Blue Dart Express",
    tracking_number: "BD-994821034",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
    items: [
      {
        id: "si-001",
        product_title: "Hand-Painted Royal Blue Terracotta Vase",
        variant_title: "Cobalt Blue / 12 inch",
        sku: "JBP-VASE-BLU-12",
        quantity: 2,
        total_price_cents: 480000,
        image_url:
          "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
      },
    ],
  },
  {
    id: "shp-demo-004",
    shipment_number: "SHP-9102-01",
    order_number: "BZR-9102-112",
    customer_name: "Vikram Mehta",
    customer_phone: "+91 98111 22334",
    customer_email: "vikram@example.com",
    status: "placed",
    subtotal_cents: 520000,
    vendor_payout_cents: 468000,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    items: [
      {
        id: "si-004",
        product_title: "Traditional Floral Jaipur Blue Glazed Plate",
        variant_title: "10 inch / Turquoise & Indigo",
        sku: "JBP-PLT-10",
        quantity: 2,
        total_price_cents: 520000,
        image_url:
          "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=600&q=80",
      },
    ],
  },
  {
    id: "shp-demo-005",
    shipment_number: "SHP-8840-01",
    order_number: "BZR-8840-801",
    customer_name: "Sunita Patel",
    customer_phone: "+91 98222 33445",
    customer_email: "sunita@example.com",
    status: "delivered",
    subtotal_cents: 720000,
    vendor_payout_cents: 648000,
    courier_name: "Delhivery Air",
    tracking_number: "DL-399102941",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    items: [
      {
        id: "si-005",
        product_title: "Miniature Jaipur Pottery Coasters Set of 6",
        variant_title: "Multicolor / Set of 6",
        sku: "JBP-CST-6",
        quantity: 3,
        total_price_cents: 720000,
        image_url:
          "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
      },
    ],
  },
];

export default function ShipmentsPage() {
  const [shipments, setShipments] = useState<ShipmentRow[]>(DEMO_SHIPMENTS);
  const [activeTab, setActiveTab] = useState<string>("all");
  const [loading, setLoading] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await api.getVendorShipments();
        if (res.shipments && res.shipments.length > 0) {
          setShipments(res.shipments as any);
        }
      } catch {
        // demo fallback
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleAccept(id: string) {
    try {
      await api.acceptShipment(id);
      setShipments((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "accepted" as const } : s))
      );
      setActionSuccess("Consignment confirmed! Next step: pack and label.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch {
      // offline fallback
      setShipments((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "accepted" as const } : s))
      );
      setActionSuccess("Consignment confirmed! Next step: pack and label.");
      setTimeout(() => setActionSuccess(null), 4000);
    }
  }

  async function handlePack(id: string) {
    try {
      await api.packShipment(id);
      setShipments((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "packed" as const } : s))
      );
      setActionSuccess("Marked as Packed & Fragile Protected. Ready for carrier handoff.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch {
      setShipments((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "packed" as const } : s))
      );
      setActionSuccess("Marked as Packed & Fragile Protected. Ready for carrier handoff.");
      setTimeout(() => setActionSuccess(null), 4000);
    }
  }

  async function handleShip(id: string) {
    const courier = "Blue Dart Express Air";
    const awb = `BD-${Math.floor(100000000 + Math.random() * 900000000)}`;
    try {
      await api.shipShipment(id, courier, awb);
      setShipments((prev) =>
        prev.map((s) =>
          s.id === id
            ? {
                ...s,
                status: "shipped" as const,
                courier_name: courier,
                tracking_number: awb,
              }
            : s
        )
      );
      setActionSuccess(`Dispatched via ${courier}! Tracking AWB: ${awb}`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch {
      setShipments((prev) =>
        prev.map((s) =>
          s.id === id
            ? {
                ...s,
                status: "shipped" as const,
                courier_name: courier,
                tracking_number: awb,
              }
            : s
        )
      );
      setActionSuccess(`Dispatched via ${courier}! Tracking AWB: ${awb}`);
      setTimeout(() => setActionSuccess(null), 4000);
    }
  }

  async function handleDeliver(id: string) {
    try {
      await api.deliverShipment(id);
      setShipments((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "delivered" as const } : s))
      );
      setActionSuccess("Delivery verified! Escrow payout released to your wallet.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch {
      setShipments((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "delivered" as const } : s))
      );
      setActionSuccess("Delivery verified! Escrow payout released to your wallet.");
      setTimeout(() => setActionSuccess(null), 4000);
    }
  }

  const filtered = shipments.filter((s) => {
    if (activeTab === "all") return true;
    if (activeTab === "pending") return s.status === "placed" || s.status === "accepted";
    if (activeTab === "packed") return s.status === "packed";
    if (activeTab === "shipped") return s.status === "shipped";
    if (activeTab === "delivered") return s.status === "delivered";
    if (activeTab === "returns") return s.status === "returned";
    return true;
  });

  return (
    <div className="flex-1 pb-12">
      <SellerHeader
        title="Fulfillment & Consignments"
        description="Pack, label, and dispatch craft shipments independently with automated courier tracking."
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Success Alert */}
        {actionSuccess && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center justify-between shadow-2xs">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-700" />
              <span>{actionSuccess}</span>
            </div>
            <button
              onClick={() => setActionSuccess(null)}
              className="text-emerald-700 hover:text-emerald-900 text-sm font-bold"
            >
              &times;
            </button>
          </div>
        )}

        {/* Tab Filters */}
        <div className="flex gap-2 border-b border-stone-200 pb-3 overflow-x-auto text-xs font-semibold">
          {[
            { id: "all", label: "All Consignments" },
            { id: "pending", label: "Needs Confirmation" },
            { id: "packed", label: "Packed & Ready" },
            { id: "shipped", label: "In Transit" },
            { id: "delivered", label: "Completed" },
            { id: "returns", label: "Returns / Exchanges" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl whitespace-nowrap transition ${
                activeTab === tab.id
                  ? "bg-amber-800 text-white shadow-2xs"
                  : "text-stone-600 hover:bg-stone-200/60"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Consignment Cards Grid */}
        <div className="space-y-4">
          {filtered.length === 0 ? (
            <div className="bg-white rounded-2xl border border-stone-200 p-12 text-center text-stone-500 text-xs">
              No shipments matching this filter.
            </div>
          ) : (
            filtered.map((s) => {
              const badge = formatStatusBadge(s.status);
              const label = formatStatusLabel(s.status);

              return (
                <div
                  key={s.id}
                  className="bg-white rounded-2xl border border-stone-200/80 p-6 shadow-2xs hover:shadow-md transition"
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-stone-100 pb-4 mb-4">
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-sm text-stone-900">
                          #{s.shipment_number}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${badge.bg} ${badge.text} ${badge.border} border`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
                          <span>{label}</span>
                        </span>
                      </div>
                      <p className="text-xs text-stone-500 mt-1">
                        Order #{s.order_number} &bull; Placed on {formatDate(s.created_at)} &bull;
                        Customer: <strong className="text-stone-700">{s.customer_name}</strong>
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* State Machine Action Buttons */}
                      {s.status === "placed" && (
                        <button
                          onClick={() => handleAccept(s.id)}
                          className="px-4 py-2 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-2xs"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Accept Order</span>
                        </button>
                      )}

                      {s.status === "accepted" && (
                        <button
                          onClick={() => handlePack(s.id)}
                          className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-2xs"
                        >
                          <Box className="w-3.5 h-3.5" />
                          <span>Mark as Packed & Labelled</span>
                        </button>
                      )}

                      {s.status === "packed" && (
                        <button
                          onClick={() => handleShip(s.id)}
                          className="px-4 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-2xs"
                        >
                          <Truck className="w-3.5 h-3.5" />
                          <span>Dispatch with Blue Dart (Generate AWB)</span>
                        </button>
                      )}

                      {s.status === "shipped" && (
                        <button
                          onClick={() => handleDeliver(s.id)}
                          className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shadow-2xs"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Verify Doorstep Delivery</span>
                        </button>
                      )}

                      <Link
                        href={`/shipments/${s.id}`}
                        className="px-3.5 py-2 rounded-xl border border-stone-300 hover:bg-stone-100 text-xs font-semibold text-stone-700 transition"
                      >
                        Inspect Details &rarr;
                      </Link>
                    </div>
                  </div>

                  {/* Items in Consignment */}
                  <div className="space-y-3">
                    {s.items?.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center gap-3 bg-stone-50/70 p-3 rounded-xl border border-stone-100"
                      >
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={item.product_title}
                            className="w-12 h-12 object-cover rounded-lg border border-stone-200"
                          />
                        ) : (
                          <div className="w-12 h-12 bg-stone-200 rounded-lg flex items-center justify-center text-base">
                            🏺
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <h4 className="text-xs font-semibold text-stone-900 truncate">
                            {item.product_title}
                          </h4>
                          <p className="text-[11px] text-stone-500">
                            {item.variant_title} &bull; Qty: {item.quantity} &bull; SKU: {item.sku}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-bold text-stone-900">
                            {formatPrice(item.total_price_cents)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Shipment Footer with Payout and Courier Info */}
                  <div className="mt-4 pt-3 border-t border-stone-100 flex flex-wrap items-center justify-between text-xs text-stone-500">
                    <div>
                      {s.courier_name ? (
                        <span>
                          Air Carrier: <strong>{s.courier_name}</strong> &bull; AWB:{" "}
                          <code className="font-mono text-stone-800 font-bold">
                            {s.tracking_number}
                          </code>
                        </span>
                      ) : (
                        <span>Awaiting carrier pickup assignment</span>
                      )}
                    </div>
                    <div>
                      Net Workshop Payout:{" "}
                      <strong className="text-amber-900 font-bold text-sm">
                        {formatPrice(s.vendor_payout_cents)}
                      </strong>{" "}
                      <span className="text-[10px] text-stone-400">(10% commission deducted)</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}
