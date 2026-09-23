"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { CheckCircle2, Package, ArrowRight, Store, Truck } from "lucide-react";
import { formatPrice, api, type Order } from "@bazaar/shared";

export default function OrderConfirmationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getOrder(id);
        setOrder(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center animate-pulse space-y-4">
        <div className="w-16 h-16 bg-stone-200 rounded-full mx-auto" />
        <div className="h-6 bg-stone-200 rounded-md w-1/2 mx-auto" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-xl font-bold text-stone-900">Order Not Found</h2>
        <Link href="/" className="inline-block mt-4 px-4 py-2 bg-amber-700 text-white rounded-full text-xs font-semibold">
          Return Home
        </Link>
      </div>
    );
  }

  const shipments = order.shipments || [];

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-fade-in py-6">
      {/* Confirmation Card */}
      <div className="bg-white rounded-3xl p-8 sm:p-12 text-center border border-stone-200 shadow-sm space-y-4">
        <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
          <CheckCircle2 className="w-10 h-10" />
        </div>

        <span className="inline-block text-[11px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
          Payment Confirmed
        </span>

        <h1 className="text-2xl sm:text-3xl font-serif font-black text-stone-900">
          Thank you for supporting Indian Artisans!
        </h1>

        <p className="text-xs text-stone-600 max-w-md mx-auto leading-relaxed">
          Your order <strong className="text-stone-900">#{order.order_number}</strong> has been received and routed directly to the artisan workshops.
        </p>

        <div className="pt-4 flex flex-wrap items-center justify-center gap-4">
          <Link
            href={`/orders/${order.id}`}
            className="px-6 py-3 rounded-full bg-amber-700 hover:bg-amber-600 text-white font-bold text-xs shadow-md transition-colors flex items-center gap-2"
          >
            <Package className="w-4 h-4" />
            Track Split Shipments
          </Link>
          <Link
            href="/"
            className="px-6 py-3 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-800 font-bold text-xs transition-colors"
          >
            Continue Shopping
          </Link>
        </div>
      </div>

      {/* Multi-Vendor Shipment Breakdown Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200 space-y-6">
        <div className="flex items-center justify-between border-b border-stone-100 pb-4">
          <div>
            <h3 className="text-base font-bold text-stone-900">
              Multi-Vendor Split Shipments ({shipments.length})
            </h3>
            <p className="text-xs text-stone-500 mt-0.5">
              Each artisan workshop packages and dispatches items independently.
            </p>
          </div>
          <span className="text-xs font-bold text-stone-900">
            Total Paid: {formatPrice(order.total_cents)}
          </span>
        </div>

        <div className="space-y-4">
          {shipments.map((s) => (
            <div
              key={s.id}
              className="p-4 rounded-2xl bg-stone-50 border border-stone-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Store className="w-4 h-4 text-amber-700" />
                  <span className="font-bold text-xs text-stone-900">
                    {s.shop_name || "Artisan Shop"}
                  </span>
                  <span className="text-[10px] text-stone-400">
                    #{s.shipment_number}
                  </span>
                </div>
                <div className="text-xs text-stone-600">
                  {s.items?.length || 1} item(s) • Subtotal: {formatPrice(s.subtotal_cents)}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-200">
                  <Truck className="w-3.5 h-3.5 text-amber-700" />
                  Fulfillment: Order Placed
                </span>
                <Link
                  href={`/shipments/${s.id}/track`}
                  className="px-3.5 py-1.5 rounded-xl bg-white border border-stone-300 hover:border-amber-600 text-stone-800 text-xs font-bold transition-colors"
                >
                  Track Checkpoints
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
