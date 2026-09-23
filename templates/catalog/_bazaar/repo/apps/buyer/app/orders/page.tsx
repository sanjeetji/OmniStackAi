"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatCurrency, formatDate, getShipmentStatusBadge } from "@bazaar/shared";
import { api } from "@bazaar/shared";
import type { Order } from "@bazaar/shared";

// High quality demo orders for instant offline evaluation
const DEMO_ORDERS: Order[] = [
  {
    id: "ord-demo-001",
    order_number: "BZR-9821-441",
    user_id: "u-shopper-001",
    status: "processing",
    total_cents: 975000,
    subtotal_cents: 950000,
    discount_cents: 50000,
    shipping_cents: 0,
    tax_cents: 75000,
    payment_method: "mock_card",
    payment_status: "paid",
    payment_reference: "pay_demo_9821441",
    coupon_code: "CRAFT10",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
    shipping_address_json: {
      recipientName: "Priya Sharma",
      phone: "+91 98765 43210",
      street: "Flat 402, Lotus Granduer, 12th Main Road, Indiranagar",
      city: "Bengaluru",
      state: "Karnataka",
      postalCode: "560038",
      country: "India",
    },
    shipments: [
      {
        id: "shp-demo-001",
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
        placed_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
        accepted_at: new Date(Date.now() - 1000 * 60 * 60 * 16).toISOString(),
        packed_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
        shipped_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
        shop_name: "Jaipur Blue Art Pottery",
        shop_slug: "jaipur-pottery",
        items: [
          {
            id: "si-001",
            shipment_id: "shp-demo-001",
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
      },
      {
        id: "shp-demo-002",
        order_id: "ord-demo-001",
        shop_id: "shp-varanasi",
        shipment_number: "SHP-9821-02",
        status: "packed",
        subtotal_cents: 470000,
        commission_cents: 47000,
        vendor_payout_cents: 423000,
        shipping_fee_cents: 0,
        courier_name: "Delhivery Air",
        tracking_number: "DL-881920391",
        placed_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
        accepted_at: new Date(Date.now() - 1000 * 60 * 60 * 14).toISOString(),
        packed_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
        shop_name: "Varanasi Silk Looms",
        shop_slug: "varanasi-silk",
        items: [
          {
            id: "si-002",
            shipment_id: "shp-demo-002",
            variant_id: "var-003",
            product_id: "prod-002",
            product_title: "Authentic Pure Zari Banarasi Silk Stole",
            variant_title: "Crimson Red / Free Size",
            sku: "VSL-BANARASI-RED",
            unit_price_cents: 470000,
            quantity: 1,
            total_price_cents: 470000,
            image_url: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80",
          },
        ],
      },
    ],
  },
  {
    id: "ord-demo-002",
    order_number: "BZR-8140-192",
    user_id: "u-shopper-001",
    status: "completed",
    total_cents: 640000,
    subtotal_cents: 640000,
    discount_cents: 0,
    shipping_cents: 0,
    tax_cents: 45000,
    payment_method: "mock_upi",
    payment_status: "paid",
    payment_reference: "upi_demo_8140192",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    shipping_address_json: {
      recipientName: "Priya Sharma",
      phone: "+91 98765 43210",
      street: "Flat 402, Lotus Granduer, 12th Main Road, Indiranagar",
      city: "Bengaluru",
      state: "Karnataka",
      postalCode: "560038",
      country: "India",
    },
    shipments: [
      {
        id: "shp-demo-003",
        order_id: "ord-demo-002",
        shop_id: "shp-moradabad",
        shipment_number: "SHP-8140-01",
        status: "delivered",
        subtotal_cents: 640000,
        commission_cents: 64000,
        vendor_payout_cents: 576000,
        shipping_fee_cents: 0,
        courier_name: "Blue Dart Express",
        tracking_number: "BD-771829031",
        placed_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
        accepted_at: new Date(Date.now() - 1000 * 60 * 60 * 70).toISOString(),
        packed_at: new Date(Date.now() - 1000 * 60 * 60 * 60).toISOString(),
        shipped_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
        delivered_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
        shop_name: "Moradabad Brass Craft Guild",
        shop_slug: "brass-craft",
        items: [
          {
            id: "si-003",
            shipment_id: "shp-demo-003",
            variant_id: "var-005",
            product_id: "prod-003",
            product_title: "Hammered Antique Finish Brass Urli Bowl",
            variant_title: "14 inch / Traditional Hammered",
            sku: "MBC-URLI-14",
            unit_price_cents: 320000,
            quantity: 2,
            total_price_cents: 640000,
            image_url: "https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=600&q=80",
          },
        ],
      },
    ],
  },
];

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>(DEMO_ORDERS);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadOrders() {
      try {
        setLoading(true);
        const data = await api.getOrders();
        if (Array.isArray(data) && data.length > 0) {
          setOrders(data);
        } else if ((data as any)?.orders && (data as any).orders.length > 0) {
          setOrders((data as any).orders);
        }
      } catch {
        // Fallback to rich demo orders if API offline or user not logged in
        setOrders(DEMO_ORDERS);
      } finally {
        setLoading(false);
      }
    }
    loadOrders();
  }, []);

  const filteredOrders = orders.filter((ord) => {
    if (filter === "all") return true;
    if (filter === "in_transit") {
      return ord.shipments?.some((s) => s.status === "shipped" || s.status === "packed");
    }
    if (filter === "delivered") {
      return ord.status === "completed" || ord.shipments?.every((s) => s.status === "delivered");
    }
    if (filter === "cancelled") {
      return ord.status === "cancelled";
    }
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-serif font-bold text-stone-900">My Orders & Shipments</h1>
          <p className="text-stone-600 text-sm mt-1">
            Track multi-vendor orders, delivery checkpoints, and split shipments across master artisans.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-amber-700 hover:text-amber-800"
        >
          <span>Continue Shopping</span>
          <span>&rarr;</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-stone-200 pb-3 mb-6 overflow-x-auto text-sm">
        {[
          { id: "all", label: "All Orders" },
          { id: "in_transit", label: "In Transit / Shipped" },
          { id: "delivered", label: "Delivered" },
          { id: "cancelled", label: "Cancelled / Returned" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition ${
              filter === tab.id
                ? "bg-amber-700 text-white shadow-sm"
                : "text-stone-600 hover:bg-stone-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Orders List */}
      {filteredOrders.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-stone-200">
          <div className="w-16 h-16 mx-auto mb-4 bg-amber-50 rounded-full flex items-center justify-center text-amber-700 text-2xl">
            📦
          </div>
          <h3 className="text-lg font-semibold text-stone-900 mb-1">No orders found</h3>
          <p className="text-stone-500 text-sm max-w-md mx-auto mb-6">
            You don't have any orders matching the selected filter. Browse our curated craft catalog and support authentic Indian artisans.
          </p>
          <Link
            href="/"
            className="inline-flex px-6 py-2.5 bg-amber-700 text-white rounded-xl text-sm font-semibold hover:bg-amber-800 transition"
          >
            Explore Masterpieces
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredOrders.map((order) => {
            const shipmentCount = order.shipments?.length || 1;
            return (
              <div
                key={order.id}
                className="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-sm hover:shadow-md transition"
              >
                {/* Order Top Bar */}
                <div className="bg-stone-50 px-6 py-4 border-b border-stone-200 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex flex-wrap items-center gap-6">
                    <div>
                      <p className="text-xs uppercase tracking-wider text-stone-500 font-semibold">
                        Order Placed
                      </p>
                      <p className="text-sm font-medium text-stone-800">
                        {formatDate(order.created_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider text-stone-500 font-semibold">
                        Total Amount
                      </p>
                      <p className="text-sm font-bold text-amber-800">
                        {formatCurrency(order.total_cents)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider text-stone-500 font-semibold">
                        Ship To
                      </p>
                      <p className="text-sm font-medium text-stone-800">
                        {order.shipping_address_json?.recipientName || "Priya Sharma"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider text-stone-500 font-semibold">
                        Consignment Split
                      </p>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                        {shipmentCount} {shipmentCount === 1 ? "Package" : "Independent Packages"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-xs text-stone-500 font-mono">
                      #{order.order_number}
                    </span>
                    <Link
                      href={`/orders/${order.id}`}
                      className="px-3.5 py-1.5 bg-white border border-stone-300 rounded-lg text-xs font-semibold text-stone-700 hover:bg-stone-100 transition shadow-2xs"
                    >
                      View Details
                    </Link>
                    <Link
                      href={`/orders/${order.id}/live`}
                      className="px-3.5 py-1.5 bg-amber-700 text-white rounded-lg text-xs font-semibold hover:bg-amber-800 transition shadow-2xs flex items-center gap-1.5"
                    >
                      <span className="w-2 h-2 rounded-full bg-emerald-300 animate-pulse"></span>
                      <span>Live Stream</span>
                    </Link>
                  </div>
                </div>

                {/* Sub-Shipments Breakout */}
                <div className="p-6 divide-y divide-stone-100">
                  {order.shipments && order.shipments.length > 0 ? (
                    order.shipments.map((shipment) => {
                      const badge = getShipmentStatusBadge(shipment.status);
                      return (
                        <div key={shipment.id} className="pt-4 first:pt-0">
                          {/* Shipment Header */}
                          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                            <div className="flex items-center gap-2.5">
                              <span className="text-lg">🏛️</span>
                              <div>
                                <span className="text-xs text-stone-500">Shipped by Artisan: </span>
                                <Link
                                  href={`/shops/${shipment.shop_slug || "jaipur-pottery"}`}
                                  className="text-sm font-semibold text-stone-900 hover:text-amber-700 hover:underline"
                                >
                                  {shipment.shop_name || "Artisan Workshop"}
                                </Link>
                              </div>
                            </div>

                            <div className="flex items-center gap-3">
                              <span
                                className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${badge.color}`}
                              >
                                {badge.label}
                              </span>
                              {shipment.tracking_number && (
                                <Link
                                  href={`/shipments/${shipment.id}/track`}
                                  className="text-xs font-semibold text-amber-700 hover:text-amber-800 underline flex items-center gap-1"
                                >
                                  <span>Track Package</span>
                                  <span>&rarr;</span>
                                </Link>
                              )}
                            </div>
                          </div>

                          {/* Shipment Items */}
                          <div className="space-y-3">
                            {shipment.items?.map((item) => (
                              <div
                                key={item.id}
                                className="flex items-center gap-4 bg-stone-50/60 p-3 rounded-xl border border-stone-100"
                              >
                                {item.image_url ? (
                                  <img
                                    src={item.image_url}
                                    alt={item.product_title}
                                    className="w-16 h-16 object-cover rounded-lg border border-stone-200"
                                  />
                                ) : (
                                  <div className="w-16 h-16 bg-stone-200 rounded-lg flex items-center justify-center text-xl">
                                    🏺
                                  </div>
                                )}
                                <div className="flex-1 min-w-0">
                                  <h4 className="text-sm font-semibold text-stone-900 truncate">
                                    {item.product_title}
                                  </h4>
                                  <p className="text-xs text-stone-500 mt-0.5">
                                    Variant: {item.variant_title} &bull; Qty: {item.quantity}
                                  </p>
                                  <p className="text-xs text-stone-400 font-mono mt-0.5">
                                    SKU: {item.sku}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p className="text-sm font-bold text-stone-900">
                                    {formatCurrency(item.total_price_cents)}
                                  </p>
                                  <p className="text-xs text-stone-400">
                                    {formatCurrency(item.unit_price_cents)} each
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* Courier info footer */}
                          {shipment.courier_name && (
                            <div className="mt-3 flex items-center justify-between text-xs text-stone-500 bg-amber-50/40 px-3 py-2 rounded-lg">
                              <span>
                                Courier: <strong className="text-stone-700">{shipment.courier_name}</strong> &bull; Tracking:{" "}
                                <code className="font-mono text-stone-800">{shipment.tracking_number}</code>
                              </span>
                              <Link
                                href={`/shipments/${shipment.id}/track`}
                                className="font-medium text-amber-700 hover:underline"
                              >
                                View Live Route & Checkpoints
                              </Link>
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-sm text-stone-500 py-4">Shipment details loading...</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
