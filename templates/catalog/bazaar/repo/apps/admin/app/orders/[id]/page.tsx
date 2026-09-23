"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AdminHeader } from "@/components/admin-header";
import {
  ShoppingBag,
  Truck,
  CreditCard,
  Receipt,
  User,
  MapPin,
  CheckCircle2,
  Clock,
  ArrowLeft,
  Store,
  ExternalLink,
  ShieldCheck,
  Ban,
  RotateCcw,
} from "lucide-react";
import { formatCurrency, formatDate } from "@bazaar/shared";

export default function AdminOrderDetailPage() {
  const params = useParams();
  const orderId = (params?.id as string) || "ord-8831";

  const [orderStatus, setOrderStatus] = useState<string>("processing");
  const [refundIssued, setRefundIssued] = useState(false);

  const order = {
    id: orderId,
    orderNumber: "BAZ-2026-8831",
    createdAt: "2026-09-23T10:14:00Z",
    status: orderStatus,
    totalCents: 1840000,
    subtotalCents: 1690000,
    shippingFeeCents: 150000,
    customer: {
      name: "Priya Sharma",
      email: "priya@bazaar.test",
      phone: "+91 98765 43210",
      shippingAddress: "Flat 402, Heritage Palms, Indiranagar, Bengaluru, Karnataka 560038",
    },
    payment: {
      provider: "Mock Card Gateway",
      paymentId: "PAY_MOCK_99214_SUCCESS",
      method: "Mastercard •••• 4242",
      status: "captured",
    },
    shipments: [
      {
        id: "shp-8831-01",
        shopName: "Jaipur Blue Art Pottery",
        shopSlug: "jaipur-blue-pottery",
        status: "packed",
        courierName: "Blue Dart Express",
        trackingNumber: "BD-88392190-IN",
        subtotalCents: 940000,
        commissionCents: 94000,
        vendorPayoutCents: 846000,
        items: [
          {
            title: "Royal Mughal Cobalt Floral Vase (12\")",
            sku: "JBP-MUG-12",
            quantity: 1,
            unitPriceCents: 245000,
          },
          {
            title: "Traditional Floral Tile Coasters (Set of 6)",
            sku: "JBP-CST-06",
            quantity: 2,
            unitPriceCents: 85000,
          },
        ],
      },
      {
        id: "shp-8831-02",
        shopName: "Varanasi Heritage Weaves",
        shopSlug: "varanasi-weaves",
        status: "accepted",
        courierName: "Delhivery Surface",
        trackingNumber: "DEL-44120982-IN",
        subtotalCents: 900000,
        commissionCents: 72000, // 8% preferred commission
        vendorPayoutCents: 828000,
        items: [
          {
            title: "Authentic Zari Katan Silk Stole",
            sku: "VNS-KAT-SILK",
            quantity: 1,
            unitPriceCents: 900000,
          },
        ],
      },
    ],
    ledgerEntries: [
      {
        id: "led-01",
        debit: "shopper_account (Priya Sharma)",
        credit: "platform_escrow_pool",
        amountCents: 1840000,
        type: "order_payment",
        description: "Customer checkout authorization and escrow hold",
      },
      {
        id: "led-02",
        debit: "platform_escrow_pool",
        credit: "platform_revenue",
        amountCents: 166000,
        type: "commission_fee",
        description: "Platform take-rate commission withholdings across 2 workshops",
      },
      {
        id: "led-03",
        debit: "platform_escrow_pool",
        credit: "vendor_payable (Jaipur Blue Pottery)",
        amountCents: 846000,
        type: "vendor_credit",
        description: "Escrow payable allocation for shipment shp-8831-01",
      },
      {
        id: "led-04",
        debit: "platform_escrow_pool",
        credit: "vendor_payable (Varanasi Weaves)",
        amountCents: 828000,
        type: "vendor_credit",
        description: "Escrow payable allocation for shipment shp-8831-02",
      },
    ],
  };

  const handleCancelOrder = () => {
    setOrderStatus("cancelled");
  };

  const handleIssueRefund = () => {
    setRefundIssued(true);
    setTimeout(() => setRefundIssued(false), 4000);
  };

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title={`Order Investigation: ${order.orderNumber}`}
        subtitle={`Placed on ${formatDate(order.createdAt)} • Total: ${formatCurrency(order.totalCents)}`}
        badge={order.status.toUpperCase()}
      />

      <div className="p-6 space-y-6 flex-1 max-w-6xl">
        <Link
          href="/orders"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Global Orders
        </Link>

        {/* Customer & Payment Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Customer Destination */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <User className="w-4 h-4 text-amber-400" />
              Customer Information
            </h3>
            <div className="text-xs space-y-1.5">
              <div className="text-white font-bold">{order.customer.name}</div>
              <div className="text-slate-300 font-mono text-[11px]">{order.customer.email}</div>
              <div className="text-slate-400">{order.customer.phone}</div>
              <div className="pt-2 text-slate-300 flex items-start gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <span>{order.customer.shippingAddress}</span>
              </div>
            </div>
          </div>

          {/* Payment Gateway */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <CreditCard className="w-4 h-4 text-emerald-400" />
              Payment Gateway Capture
            </h3>
            <div className="text-xs space-y-1.5">
              <div className="text-emerald-400 font-mono font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                PAYMENT_SUCCESS
              </div>
              <div className="text-slate-300">{order.payment.method}</div>
              <div className="text-slate-400 font-mono text-[11px]">
                Ref: {order.payment.paymentId}
              </div>
              <div className="text-slate-400">Gateway: {order.payment.provider}</div>
            </div>
          </div>

          {/* Order Actions */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 flex flex-col justify-between">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-sky-400" />
              Operator Control Actions
            </h3>
            <div className="space-y-2">
              <button
                type="button"
                onClick={handleIssueRefund}
                className="w-full py-2 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/30 text-amber-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Issue Escrow Refund to Buyer
              </button>
              <button
                type="button"
                onClick={handleCancelOrder}
                className="w-full py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <Ban className="w-3.5 h-3.5" />
                Cancel Entire Split Order
              </button>
            </div>
            {refundIssued && (
              <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Full refund entry posted to double-entry ledger.
              </div>
            )}
          </div>
        </div>

        {/* Split Shipments Breakdown */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Truck className="w-4 h-4 text-amber-400" />
              Independent Vendor Consignments ({order.shipments.length} Ateliers)
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Fulfillment state machine operates autonomously per vendor
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {order.shipments.map((shp) => (
              <div
                key={shp.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Store className="w-4 h-4 text-amber-400" />
                    <span className="font-bold text-white text-xs">{shp.shopName}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono text-[10px] font-semibold">
                    {shp.status.toUpperCase()}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1 font-mono">
                  <div className="text-slate-400">Consignment: {shp.id}</div>
                  <div className="text-slate-200">Carrier: {shp.courierName}</div>
                  <div className="text-amber-400">AWB: {shp.trackingNumber}</div>
                </div>

                <div className="space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Consignment Items
                  </div>
                  {shp.items.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs py-1 border-b border-slate-800/80 last:border-0"
                    >
                      <span className="text-slate-200">
                        {item.quantity}x {item.title}
                      </span>
                      <span className="font-mono text-white">
                        {formatCurrency(item.unitPriceCents * item.quantity)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Artisan Payout Net:</span>
                  <span className="font-mono font-bold text-emerald-400">
                    {formatCurrency(shp.vendorPayoutCents)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Double-Entry Ledger Audit Trail for this Order */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Receipt className="w-4 h-4 text-emerald-400" />
              Double-Entry Ledger Audit Journal Trail
            </h3>
            <span className="text-xs text-emerald-400 font-mono font-semibold">
              Σ Debits = Σ Credits (Balanced)
            </span>
          </div>

          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Debit Account</th>
                <th className="px-4 py-3">Credit Account</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Entry Type</th>
                <th className="px-4 py-3">Journal Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {order.ledgerEntries.map((led) => (
                <tr key={led.id} className="hover:bg-slate-800/40 transition">
                  <td className="px-4 py-3 font-mono text-slate-300">{led.debit}</td>
                  <td className="px-4 py-3 font-mono text-slate-300">{led.credit}</td>
                  <td className="px-4 py-3 font-mono font-bold text-amber-400">
                    {formatCurrency(led.amountCents)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                      {led.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{led.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
