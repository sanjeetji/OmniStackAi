"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { formatCurrency, formatDate, getShipmentStatusBadge } from "@bazaar/shared";
import { api } from "@bazaar/shared";
import type { Order, Shipment } from "@bazaar/shared";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function OrderDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedShipmentForReturn, setSelectedShipmentForReturn] = useState<Shipment | null>(null);
  const [returnReason, setReturnReason] = useState("");
  const [returnSubmitting, setReturnSubmitting] = useState(false);
  const [returnSuccessMsg, setReturnSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadOrder() {
      try {
        setLoading(true);
        const data = await api.getOrder(id);
        if (data && (data as any).id) {
          setOrder((data as any).order || data);
        }
      } catch {
        // Fallback demo order with multi-vendor split shipments
        setOrder({
          id: id,
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
              order_id: id,
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
              tracking: [
                {
                  id: "trk-1",
                  shipment_id: "shp-demo-001",
                  status: "placed",
                  location: "Jaipur Workshop, Rajasthan",
                  message: "Order received by Master Artisan Kripal Singh",
                  occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
                },
                {
                  id: "trk-2",
                  shipment_id: "shp-demo-001",
                  status: "accepted",
                  location: "Jaipur Workshop, Rajasthan",
                  message: "Artisan verified inventory and packed with triple-bubble fragile cushioning",
                  occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 16).toISOString(),
                },
                {
                  id: "trk-3",
                  shipment_id: "shp-demo-001",
                  status: "shipped",
                  location: "Blue Dart Air Hub, Jaipur Airport",
                  message: "Handed over to carrier. Dispatched toward Bengaluru Gateway",
                  occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
                },
              ],
            },
            {
              id: "shp-demo-002",
              order_id: id,
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
              tracking: [
                {
                  id: "trk-4",
                  shipment_id: "shp-demo-002",
                  status: "placed",
                  location: "Varanasi Silk Looms Weaving Center",
                  message: "Order confirmed with weaver collective",
                  occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
                },
                {
                  id: "trk-5",
                  shipment_id: "shp-demo-002",
                  status: "packed",
                  location: "Varanasi Dispatch Hub",
                  message: "Silkmark certified seal attached and packaged in moisture-proof box",
                  occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
                },
              ],
            },
          ],
        });
      } finally {
        setLoading(false);
      }
    }
    loadOrder();
  }, [id]);

  async function handleReturnSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedShipmentForReturn || !returnReason.trim()) return;

    try {
      setReturnSubmitting(true);
      await api.requestReturn(selectedShipmentForReturn.id, returnReason);
      setReturnSuccessMsg(
        `Return request lodged for Shipment #${selectedShipmentForReturn.shipment_number}. Our courier partner will schedule pickup within 48 hours.`
      );
      setSelectedShipmentForReturn(null);
      setReturnReason("");
    } catch (err: any) {
      alert(err.message || "Failed to submit return request");
    } finally {
      setReturnSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <div className="w-12 h-12 border-4 border-amber-700 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-stone-600 font-medium">Loading order details...</p>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-serif font-bold text-stone-900 mb-2">Order Not Found</h2>
        <p className="text-stone-600 text-sm mb-6">We could not find the requested order reference.</p>
        <Link
          href="/orders"
          className="px-6 py-2.5 bg-amber-700 text-white rounded-xl font-medium text-sm hover:bg-amber-800 transition"
        >
          Back to Orders
        </Link>
      </div>
    );
  }

  const shipmentSteps = ["placed", "accepted", "packed", "shipped", "delivered"];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-stone-500 mb-6">
        <Link href="/orders" className="hover:text-amber-800">
          My Orders
        </Link>
        <span>&rsaquo;</span>
        <span className="font-mono text-stone-800 font-semibold">#{order.order_number}</span>
      </nav>

      {/* Return Success Notification */}
      {returnSuccessMsg && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-start gap-3">
          <span className="text-xl">✅</span>
          <div className="flex-1 text-sm font-medium">{returnSuccessMsg}</div>
          <button
            onClick={() => setReturnSuccessMsg(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold"
          >
            &times;
          </button>
        </div>
      )}

      {/* Order Header Card */}
      <div className="bg-white rounded-2xl border border-stone-200 p-6 mb-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-stone-100 pb-6 mb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900">
                Order #{order.order_number}
              </h1>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                {order.status.replace("_", " ").toUpperCase()}
              </span>
            </div>
            <p className="text-stone-500 text-sm mt-1">
              Placed on {formatDate(order.created_at)} &bull; Paid via {order.payment_method.toUpperCase()}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href={`/orders/${order.id}/live`}
              className="px-4 py-2 bg-amber-700 text-white rounded-xl text-sm font-semibold hover:bg-amber-800 transition flex items-center gap-2 shadow-sm"
            >
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-300 animate-ping"></span>
              <span>Live Delivery Map</span>
            </Link>
          </div>
        </div>

        {/* Address and Financial Summary 2-Col Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Shipping Address */}
          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200/70">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-2">
              Delivery Destination
            </h3>
            <p className="text-sm font-semibold text-stone-900">
              {order.shipping_address_json.recipientName}
            </p>
            <p className="text-sm text-stone-600 mt-0.5">{order.shipping_address_json.street}</p>
            <p className="text-sm text-stone-600">
              {order.shipping_address_json.city}, {order.shipping_address_json.state} -{" "}
              {order.shipping_address_json.postalCode}
            </p>
            <p className="text-xs text-stone-500 mt-2 font-mono">
              Phone: {order.shipping_address_json.phone}
            </p>
          </div>

          {/* Payment & Invoice Breakdown */}
          <div className="bg-stone-50 p-4 rounded-xl border border-stone-200/70">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-2">
              Payment Summary
            </h3>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between text-stone-600">
                <span>Items Subtotal</span>
                <span>{formatCurrency(order.subtotal_cents)}</span>
              </div>
              {order.discount_cents > 0 && (
                <div className="flex justify-between text-emerald-700 font-medium">
                  <span>Coupon Discount ({order.coupon_code})</span>
                  <span>-{formatCurrency(order.discount_cents)}</span>
                </div>
              )}
              <div className="flex justify-between text-stone-600">
                <span>Direct Artisan Shipping</span>
                <span className="text-emerald-700 font-medium">FREE</span>
              </div>
              <div className="flex justify-between text-stone-600">
                <span>GST Tax (Included)</span>
                <span>{formatCurrency(order.tax_cents)}</span>
              </div>
              <div className="border-t border-stone-200 pt-2 flex justify-between font-bold text-stone-900 text-base">
                <span>Total Charged</span>
                <span className="text-amber-800">{formatCurrency(order.total_cents)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Vendor Split Consignments */}
      <div className="space-y-8">
        <div>
          <h2 className="text-xl font-serif font-bold text-stone-900">
            Multi-Vendor Consignments ({order.shipments?.length || 0})
          </h2>
          <p className="text-sm text-stone-600 mt-1">
            Because Bazaar connects you directly to independent artisan ateliers across India, each
            workshop prepares and ships its own parcel independently.
          </p>
        </div>

        {order.shipments?.map((shipment, sIdx) => {
          const badge = getShipmentStatusBadge(shipment.status);
          const currentStepIdx = shipmentSteps.indexOf(shipment.status);

          return (
            <div
              key={shipment.id}
              className="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-sm"
            >
              {/* Shipment Header Banner */}
              <div className="bg-stone-900 text-white p-5 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
                    Consignment {sIdx + 1} of {order.shipments?.length}
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <h3 className="text-lg font-bold">{shipment.shop_name}</h3>
                    <Link
                      href={`/shops/${shipment.shop_slug}`}
                      className="text-xs bg-stone-800 hover:bg-stone-700 px-2.5 py-1 rounded-md text-stone-300 font-medium transition"
                    >
                      Visit Artisan Store &rarr;
                    </Link>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${badge.color}`}
                  >
                    {badge.label}
                  </span>
                  {shipment.tracking_number && (
                    <Link
                      href={`/shipments/${shipment.id}/track`}
                      className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold transition"
                    >
                      Track Shipment &rarr;
                    </Link>
                  )}
                </div>
              </div>

              {/* 5-Step Visual Progress Tracker */}
              <div className="p-6 bg-stone-50 border-b border-stone-200">
                <div className="max-w-3xl mx-auto">
                  <div className="flex items-center justify-between relative">
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-stone-200 -z-0"></div>
                    <div
                      className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-amber-700 transition-all -z-0"
                      style={{
                        width: `${Math.max(0, (currentStepIdx / (shipmentSteps.length - 1)) * 100)}%`,
                      }}
                    ></div>

                    {[
                      { key: "placed", label: "Placed" },
                      { key: "accepted", label: "Accepted" },
                      { key: "packed", label: "Packed" },
                      { key: "shipped", label: "Shipped" },
                      { key: "delivered", label: "Delivered" },
                    ].map((step, idx) => {
                      const isComplete = idx <= currentStepIdx;
                      const isCurrent = idx === currentStepIdx;
                      return (
                        <div key={step.key} className="flex flex-col items-center relative z-10">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition ${
                              isComplete
                                ? "bg-amber-700 text-white ring-4 ring-amber-100"
                                : "bg-white text-stone-400 border-2 border-stone-300"
                            }`}
                          >
                            {isComplete ? "✓" : idx + 1}
                          </div>
                          <span
                            className={`text-xs mt-1.5 font-medium ${
                              isCurrent
                                ? "text-amber-800 font-bold"
                                : isComplete
                                ? "text-stone-800"
                                : "text-stone-400"
                            }`}
                          >
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Shipment Items List */}
              <div className="p-6">
                <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
                  Articles in this Package
                </h4>
                <div className="divide-y divide-stone-100">
                  {shipment.items?.map((item) => (
                    <div key={item.id} className="py-3 flex items-center gap-4">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.product_title}
                          className="w-16 h-16 object-cover rounded-lg border border-stone-200"
                        />
                      ) : (
                        <div className="w-16 h-16 bg-stone-100 rounded-lg flex items-center justify-center text-xl">
                          🏺
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <h5 className="text-sm font-semibold text-stone-900">{item.product_title}</h5>
                        <p className="text-xs text-stone-500 mt-0.5">
                          {item.variant_title} &bull; Qty: {item.quantity} &bull; SKU: {item.sku}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-stone-900">
                          {formatCurrency(item.total_price_cents)}
                        </p>
                        <p className="text-xs text-stone-400">
                          {formatCurrency(item.unit_price_cents)} ea
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Tracking Milestones Accordion / List */}
                {shipment.tracking && shipment.tracking.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-stone-100">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
                      Checkpoint Chronology
                    </h4>
                    <div className="space-y-3">
                      {shipment.tracking.map((evt) => (
                        <div key={evt.id} className="flex items-start gap-3 text-xs">
                          <span className="w-2 h-2 mt-1.5 rounded-full bg-amber-600 flex-shrink-0"></span>
                          <div className="flex-1">
                            <p className="font-semibold text-stone-800">{evt.message}</p>
                            <p className="text-stone-500">
                              {evt.location} &bull; {formatDate(evt.occurred_at)}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Shipment Bottom Actions */}
                <div className="mt-6 pt-4 border-t border-stone-100 flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-stone-500">
                    {shipment.courier_name && (
                      <span>
                        Air Courier: <strong>{shipment.courier_name}</strong> (AWB:{" "}
                        <span className="font-mono font-semibold">{shipment.tracking_number}</span>)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    {shipment.status === "delivered" && (
                      <button
                        onClick={() => setSelectedShipmentForReturn(shipment)}
                        className="px-3.5 py-1.5 rounded-lg border border-red-200 text-red-700 hover:bg-red-50 text-xs font-semibold transition"
                      >
                        Request Return / Exchange
                      </button>
                    )}
                    <Link
                      href={`/shipments/${shipment.id}/track`}
                      className="px-3.5 py-1.5 rounded-lg border border-stone-300 text-stone-700 hover:bg-stone-50 text-xs font-semibold transition"
                    >
                      Detailed Tracking
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Return Request Modal */}
      {selectedShipmentForReturn && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold font-serif text-stone-900 mb-2">
              Request Return: {selectedShipmentForReturn.shop_name}
            </h3>
            <p className="text-xs text-stone-500 mb-4">
              Consignment #{selectedShipmentForReturn.shipment_number}. Handcrafted items are covered by
              our 7-day Artisan Authenticity Guarantee.
            </p>

            <form onSubmit={handleReturnSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Reason for Return
                </label>
                <select
                  value={returnReason}
                  onChange={(e) => setReturnReason(e.target.value)}
                  required
                  className="w-full text-sm rounded-lg border border-stone-300 p-2.5 bg-stone-50 focus:bg-white"
                >
                  <option value="">Select a reason...</option>
                  <option value="Damaged in transit">Damaged in transit / broken craft</option>
                  <option value="Item not as described">Artisan variation exceeds tolerance</option>
                  <option value="Wrong item delivered">Received incorrect product or variant</option>
                  <option value="Quality dissatisfaction">Quality did not meet expectations</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Refund Method
                </label>
                <p className="text-xs text-stone-600 bg-stone-100 p-2.5 rounded-lg">
                  Original payment method (
                  {formatCurrency(selectedShipmentForReturn.subtotal_cents)}) will be credited via
                  automated ledger rollback upon reverse pickup scan.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-stone-100">
                <button
                  type="button"
                  onClick={() => setSelectedShipmentForReturn(null)}
                  className="px-4 py-2 rounded-xl text-stone-600 text-xs font-semibold hover:bg-stone-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={returnSubmitting || !returnReason}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition"
                >
                  {returnSubmitting ? "Lodging..." : "Confirm Return Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
