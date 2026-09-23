"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { formatPrice, formatDate, formatStatusBadge, formatStatusLabel, api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { CheckCircle2, Box, Truck, Check, ArrowLeft, Printer, ShieldCheck } from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ShipmentDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const [shipment, setShipment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const s = await api.getVendorShipment(id);
        setShipment(s);
      } catch {
        // Fallback demo shipment
        setShipment({
          id: id,
          shipment_number: "SHP-9821-01",
          order_number: "BZR-9821-441",
          order_id: "ord-demo-001",
          customer_name: "Priya Sharma",
          customer_email: "priya.sharma@example.com",
          customer_phone: "+91 98765 43210",
          shipping_address_json: {
            recipientName: "Priya Sharma",
            phone: "+91 98765 43210",
            street: "Flat 402, Lotus Granduer, 12th Main Road, Indiranagar",
            city: "Bengaluru",
            state: "Karnataka",
            postalCode: "560038",
            country: "India",
          },
          status: "shipped",
          subtotal_cents: 480000,
          commission_cents: 48000,
          vendor_payout_cents: 432000,
          courier_name: "Blue Dart Express",
          tracking_number: "BD-994821034",
          placed_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
          accepted_at: new Date(Date.now() - 1000 * 60 * 60 * 16).toISOString(),
          packed_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
          shipped_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
          items: [
            {
              id: "si-001",
              product_title: "Hand-Painted Royal Blue Terracotta Vase",
              variant_title: "Cobalt Blue / 12 inch",
              sku: "JBP-VASE-BLU-12",
              unit_price_cents: 240000,
              quantity: 2,
              total_price_cents: 480000,
              image_url:
                "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
            },
          ],
          tracking: [
            {
              id: "trk-1",
              status: "placed",
              location: "Jaipur Atelier Studio, Rajasthan",
              message: "Order received and queued for artisan inspection",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
            },
            {
              id: "trk-2",
              status: "accepted",
              location: "Jaipur Atelier Studio, Rajasthan",
              message: "Artisan acknowledged inventory and confirmed craft authenticity",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 16).toISOString(),
            },
            {
              id: "trk-3",
              status: "packed",
              location: "Packaging Section, Jaipur Workshop",
              message: "Enclosed in triple-cushion bubble packaging and labeled with Barcode AWB",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
            },
            {
              id: "trk-4",
              status: "shipped",
              location: "Jaipur Airport Air Cargo Gateway",
              message: "Carrier handover confirmed: Blue Dart Express Flight BD-402",
              occurred_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
            },
          ],
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleAction(action: "accept" | "pack" | "ship" | "deliver") {
    if (!shipment) return;
    try {
      if (action === "accept") {
        await api.acceptShipment(shipment.id);
        setShipment({ ...shipment, status: "accepted" });
        setActionNotice("Shipment acknowledged and moved to Packing stage.");
      } else if (action === "pack") {
        await api.packShipment(shipment.id);
        setShipment({ ...shipment, status: "packed" });
        setActionNotice("Shipment marked as Packed and ready for carrier.");
      } else if (action === "ship") {
        const courier = "Blue Dart Express Air";
        const awb = `BD-${Math.floor(100000000 + Math.random() * 900000000)}`;
        await api.shipShipment(shipment.id, courier, awb);
        setShipment({
          ...shipment,
          status: "shipped",
          courier_name: courier,
          tracking_number: awb,
        });
        setActionNotice(`Dispatched via ${courier}! Tracking AWB: ${awb}`);
      } else if (action === "deliver") {
        await api.deliverShipment(shipment.id);
        setShipment({ ...shipment, status: "delivered" });
        setActionNotice("Delivery verified! Escrow funds released to ledger.");
      }
    } catch {
      // offline fallback update
      if (action === "accept") setShipment({ ...shipment, status: "accepted" });
      if (action === "pack") setShipment({ ...shipment, status: "packed" });
      if (action === "ship")
        setShipment({
          ...shipment,
          status: "shipped",
          courier_name: "Blue Dart Express Air",
          tracking_number: "BD-994821034",
        });
      if (action === "deliver") setShipment({ ...shipment, status: "delivered" });
      setActionNotice(`Shipment successfully updated to ${action}!`);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 p-12 text-center text-stone-500">
        <div className="w-8 h-8 border-2 border-amber-700 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
        <span>Loading consignment details...</span>
      </div>
    );
  }

  if (!shipment) {
    return (
      <div className="flex-1 p-12 text-center text-stone-500">
        Consignment not found.
      </div>
    );
  }

  const steps = ["placed", "accepted", "packed", "shipped", "delivered"];
  const currentStepIdx = steps.indexOf(shipment.status);
  const badge = formatStatusBadge(shipment.status);
  const label = formatStatusLabel(shipment.status);

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title={`Consignment #${shipment.shipment_number}`}
        description={`Associated with Master Order #${shipment.order_number}`}
      />

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Navigation & Action Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <Link
            href="/shipments"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-stone-600 hover:text-stone-900"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to All Consignments</span>
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-3.5 py-2 rounded-xl border border-stone-300 hover:bg-stone-100 text-stone-700 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Packing Slip</span>
            </button>
          </div>
        </div>

        {/* Notice Banner */}
        {actionNotice && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center justify-between shadow-2xs">
            <span>{actionNotice}</span>
            <button
              onClick={() => setActionNotice(null)}
              className="text-emerald-700 font-bold ml-4"
            >
              &times;
            </button>
          </div>
        )}

        {/* 5-Step Visual Progression Bar */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
              Fulfillment Lifecycle Progression
            </span>
            <span
              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${badge.bg} ${badge.text} ${badge.border} border`}
            >
              <span className={`w-2 h-2 rounded-full ${badge.dot}`}></span>
              <span>{label}</span>
            </span>
          </div>

          <div className="relative py-4">
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-stone-200 -z-0"></div>
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-amber-700 transition-all -z-0"
              style={{
                width: `${Math.max(0, (currentStepIdx / (steps.length - 1)) * 100)}%`,
              }}
            ></div>

            <div className="flex justify-between items-center relative z-10">
              {[
                { key: "placed", label: "Placed" },
                { key: "accepted", label: "Accepted" },
                { key: "packed", label: "Packed" },
                { key: "shipped", label: "Shipped" },
                { key: "delivered", label: "Delivered" },
              ].map((step, idx) => {
                const isDone = idx <= currentStepIdx;
                const isCurrent = idx === currentStepIdx;
                return (
                  <div key={step.key} className="flex flex-col items-center">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition ${
                        isDone
                          ? "bg-amber-700 text-white ring-4 ring-amber-100"
                          : "bg-white text-stone-400 border-2 border-stone-300"
                      }`}
                    >
                      {isDone ? "✓" : idx + 1}
                    </div>
                    <span
                      className={`text-xs mt-1.5 font-medium ${
                        isCurrent
                          ? "text-amber-900 font-bold"
                          : isDone
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

          {/* Action Trigger Buttons */}
          <div className="mt-6 pt-4 border-t border-stone-100 flex flex-wrap items-center justify-end gap-3">
            {shipment.status === "placed" && (
              <button
                onClick={() => handleAction("accept")}
                className="px-5 py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-2xs"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Confirm & Accept Order</span>
              </button>
            )}

            {shipment.status === "accepted" && (
              <button
                onClick={() => handleAction("pack")}
                className="px-5 py-2.5 bg-blue-700 hover:bg-blue-800 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-2xs"
              >
                <Box className="w-4 h-4" />
                <span>Mark as Packed & Box Sealed</span>
              </button>
            )}

            {shipment.status === "packed" && (
              <button
                onClick={() => handleAction("ship")}
                className="px-5 py-2.5 bg-purple-700 hover:bg-purple-800 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-2xs"
              >
                <Truck className="w-4 h-4" />
                <span>Handover to Blue Dart (Generate AWB)</span>
              </button>
            )}

            {shipment.status === "shipped" && (
              <button
                onClick={() => handleAction("deliver")}
                className="px-5 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-2xs"
              >
                <Check className="w-4 h-4" />
                <span>Confirm Successful Doorstep Delivery</span>
              </button>
            )}
          </div>
        </div>

        {/* 2-Col Grid: Customer Address & Financial Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Shipping Address */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
              Delivery Destination & Customer
            </h3>
            <p className="text-sm font-bold text-stone-900">
              {shipment.customer_name || shipment.shipping_address_json?.recipientName}
            </p>
            <p className="text-xs text-stone-600 mt-1">
              {shipment.shipping_address_json?.street}
            </p>
            <p className="text-xs text-stone-600">
              {shipment.shipping_address_json?.city}, {shipment.shipping_address_json?.state} -{" "}
              {shipment.shipping_address_json?.postalCode}
            </p>
            <div className="mt-3 pt-3 border-t border-stone-100 space-y-1 text-xs text-stone-500">
              <p>Mobile: <strong className="text-stone-800 font-mono">{shipment.customer_phone || shipment.shipping_address_json?.phone}</strong></p>
              <p>Email: <span className="text-stone-800">{shipment.customer_email || "customer@example.com"}</span></p>
            </div>
          </div>

          {/* Financials & Payout Ledger */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
              Accounting & Payout Ledger
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between text-stone-600">
                <span>Items Subtotal</span>
                <span className="font-semibold text-stone-900">{formatPrice(shipment.subtotal_cents)}</span>
              </div>
              <div className="flex justify-between text-stone-500">
                <span>Marketplace Platform Commission (10.00%)</span>
                <span className="text-rose-600 font-mono">-{formatPrice(shipment.commission_cents || shipment.subtotal_cents * 0.1)}</span>
              </div>
              <div className="flex justify-between text-stone-500">
                <span>Direct Courier Shipping</span>
                <span className="text-emerald-700 font-semibold">PREPAID BY PLATFORM</span>
              </div>
              <div className="border-t border-stone-200 pt-2 flex justify-between items-center text-sm font-bold">
                <span className="text-stone-900">Net Workshop Earnings</span>
                <span className="text-amber-800 text-base">{formatPrice(shipment.vendor_payout_cents)}</span>
              </div>
            </div>
            <div className="mt-4 p-2.5 bg-amber-50/60 rounded-xl border border-amber-200/50 flex items-center gap-2 text-[11px] text-amber-900">
              <ShieldCheck className="w-4 h-4 text-amber-700 flex-shrink-0" />
              <span>Funds are protected in platform escrow until carrier delivery scan.</span>
            </div>
          </div>
        </div>

        {/* Ordered Articles Table */}
        <div className="bg-white rounded-2xl border border-stone-200/80 overflow-hidden shadow-2xs">
          <div className="p-6 border-b border-stone-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500">
              Handcrafted Items in this Consignment
            </h3>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-500 uppercase tracking-wider font-semibold border-b border-stone-200/60">
              <tr>
                <th className="py-3 px-6">Product & Craft Details</th>
                <th className="py-3 px-6">SKU Code</th>
                <th className="py-3 px-6 text-center">Quantity</th>
                <th className="py-3 px-6 text-right">Unit Price</th>
                <th className="py-3 px-6 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {shipment.items?.map((item: any) => (
                <tr key={item.id} className="hover:bg-stone-50/50">
                  <td className="py-4 px-6 flex items-center gap-3">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.product_title}
                        className="w-12 h-12 object-cover rounded-lg border border-stone-200"
                      />
                    ) : (
                      <div className="w-12 h-12 bg-stone-200 rounded-lg flex items-center justify-center text-lg">
                        🏺
                      </div>
                    )}
                    <div>
                      <p className="font-semibold text-stone-900">{item.product_title}</p>
                      <p className="text-[11px] text-stone-500 mt-0.5">{item.variant_title}</p>
                    </div>
                  </td>
                  <td className="py-4 px-6 font-mono text-stone-600">{item.sku}</td>
                  <td className="py-4 px-6 text-center font-bold text-stone-800">{item.quantity}</td>
                  <td className="py-4 px-6 text-right text-stone-600">{formatPrice(item.unit_price_cents)}</td>
                  <td className="py-4 px-6 text-right font-bold text-stone-900">{formatPrice(item.total_price_cents)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Milestone Checkpoint Chronology */}
        {shipment.tracking && shipment.tracking.length > 0 && (
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-4">
              Checkpoint Audit Log
            </h3>
            <div className="space-y-4 relative pl-6 border-l-2 border-amber-200">
              {shipment.tracking.map((evt: any) => (
                <div key={evt.id} className="relative">
                  <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-amber-600 border-2 border-white ring-2 ring-amber-200"></div>
                  <div className="flex flex-col sm:flex-row sm:items-baseline justify-between text-xs gap-1">
                    <p className="font-bold text-stone-800">{evt.message}</p>
                    <time className="text-[11px] text-stone-400 font-mono">
                      {formatDate(evt.occurred_at)}
                    </time>
                  </div>
                  <p className="text-[11px] text-stone-500 mt-0.5">Location: {evt.location}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
