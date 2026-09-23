"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  MapPin,
  CreditCard,
  Smartphone,
  Banknote,
  ShieldCheck,
  CheckCircle2,
  Lock,
  ArrowRight,
  Store,
} from "lucide-react";
import { formatPrice, api, type Cart, type UserAddress } from "@bazaar/shared";

function CheckoutForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const couponParam = searchParams.get("coupon") || "";

  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<UserAddress[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState<string>("");
  const [paymentMethod, setPaymentMethod] = useState<"mock_card" | "mock_upi" | "cod">("mock_card");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // New address form state
  const [showNewAddress, setShowNewAddress] = useState(false);
  const [newRecipientName, setNewRecipientName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newStreet, setNewStreet] = useState("");
  const [newCity, setNewCity] = useState("Bengaluru");
  const [newState, setNewState] = useState("Karnataka");
  const [newPostalCode, setNewPostalCode] = useState("560038");

  useEffect(() => {
    async function init() {
      try {
        const c = await api.getCart();
        setCart(c);

        try {
          const addrs = await api.getAddresses();
          setAddresses(addrs);
          if (addrs.length > 0) {
            const def = addrs.find((a) => a.is_default) || addrs[0];
            setSelectedAddressId(def.id);
          } else {
            setShowNewAddress(true);
          }
        } catch {
          // If not logged in, prompt address entry
          setShowNewAddress(true);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const handlePlaceOrder = async () => {
    setError("");

    let shippingAddress: any = null;
    if (showNewAddress) {
      if (!newRecipientName || !newPhone || !newStreet || !newCity || !newPostalCode) {
        setError("Please complete all shipping address fields.");
        return;
      }
      shippingAddress = {
        recipientName: newRecipientName,
        phone: newPhone,
        street: newStreet,
        city: newCity,
        state: newState,
        postalCode: newPostalCode,
        country: "India",
      };
    } else {
      const addr = addresses.find((a) => a.id === selectedAddressId);
      if (!addr) {
        setError("Please select or enter a shipping delivery address.");
        return;
      }
      shippingAddress = {
        recipientName: addr.recipient_name,
        phone: addr.phone,
        street: addr.street,
        city: addr.city,
        state: addr.state,
        postalCode: addr.postal_code,
        country: addr.country,
      };
    }

    try {
      setSubmitting(true);
      const res = await api.checkout({
        shippingAddress,
        paymentMethod,
        couponCode: couponParam || undefined,
      });

      router.push(`/orders/${res.order.id}/confirmation`);
    } catch (err: any) {
      setError(err?.message || "Failed to place order. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 animate-pulse space-y-6">
        <div className="h-8 bg-stone-200 rounded-md w-1/4" />
        <div className="h-64 bg-stone-200 rounded-3xl" />
      </div>
    );
  }

  const items = cart?.items || [];
  const subtotal = cart?.subtotal_cents || 0;
  const shippingFee = subtotal >= 100000 ? 0 : 9900;
  const tax = Math.round((subtotal * 5) / 100);
  const total = subtotal + shippingFee + tax;

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900">
          Secure Checkout
        </h1>
        <p className="text-xs text-stone-500 mt-1">
          Review shipping destination, payment options, and multi-vendor sub-orders.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold rounded-2xl">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column: Delivery Address & Payment Method */}
        <div className="lg:col-span-2 space-y-8">
          {/* Step 1: Delivery Address */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-amber-700 text-white text-xs font-bold flex items-center justify-center">
                  1
                </div>
                <h3 className="text-base font-bold text-stone-900">Shipping Address</h3>
              </div>
              {addresses.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowNewAddress(!showNewAddress)}
                  className="text-xs font-bold text-amber-800 hover:text-amber-950"
                >
                  {showNewAddress ? "Use Saved Address" : "+ Add New Address"}
                </button>
              )}
            </div>

            {!showNewAddress && addresses.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {addresses.map((a) => (
                  <label
                    key={a.id}
                    className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex flex-col justify-between ${
                      selectedAddressId === a.id
                        ? "border-amber-600 bg-amber-50/50 ring-1 ring-amber-600"
                        : "border-stone-200 hover:border-stone-300"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-amber-800 bg-amber-100/60 px-2 py-0.5 rounded-full">
                          {a.label}
                        </span>
                        <input
                          type="radio"
                          name="address"
                          checked={selectedAddressId === a.id}
                          onChange={() => setSelectedAddressId(a.id)}
                          className="accent-amber-600"
                        />
                      </div>
                      <div className="font-bold text-xs text-stone-900">{a.recipient_name}</div>
                      <div className="text-xs text-stone-600 mt-1 leading-relaxed">
                        {a.street}, {a.city}, {a.state} - {a.postal_code}
                      </div>
                    </div>
                    <div className="text-[11px] text-stone-500 mt-3 pt-2 border-t border-stone-100">
                      Phone: {a.phone}
                    </div>
                  </label>
                ))}
              </div>
            ) : (
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-bold text-stone-700 mb-1">
                      Recipient Full Name
                    </label>
                    <input
                      type="text"
                      value={newRecipientName}
                      onChange={(e) => setNewRecipientName(e.target.value)}
                      placeholder="e.g. Priya Sharma"
                      className="w-full px-3.5 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:bg-white focus:border-amber-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-stone-700 mb-1">
                      Contact Phone Number
                    </label>
                    <input
                      type="tel"
                      value={newPhone}
                      onChange={(e) => setNewPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full px-3.5 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:bg-white focus:border-amber-600 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-stone-700 mb-1">
                    Street Address, Flat, Building
                  </label>
                  <input
                    type="text"
                    value={newStreet}
                    onChange={(e) => setNewStreet(e.target.value)}
                    placeholder="e.g. Flat 402, Lotus Greens, Indiranagar"
                    className="w-full px-3.5 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:bg-white focus:border-amber-600 focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-stone-700 mb-1">City</label>
                    <input
                      type="text"
                      value={newCity}
                      onChange={(e) => setNewCity(e.target.value)}
                      className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:bg-white focus:border-amber-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-stone-700 mb-1">State</label>
                    <input
                      type="text"
                      value={newState}
                      onChange={(e) => setNewState(e.target.value)}
                      className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:bg-white focus:border-amber-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-stone-700 mb-1">Postal Code</label>
                    <input
                      type="text"
                      value={newPostalCode}
                      onChange={(e) => setNewPostalCode(e.target.value)}
                      className="w-full px-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs focus:bg-white focus:border-amber-600 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Step 2: Payment Method */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200 space-y-6">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-amber-700 text-white text-xs font-bold flex items-center justify-center">
                2
              </div>
              <h3 className="text-base font-bold text-stone-900">Payment Method</h3>
            </div>

            <div className="space-y-3">
              <label
                className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-center justify-between ${
                  paymentMethod === "mock_card"
                    ? "border-amber-600 bg-amber-50/50 ring-1 ring-amber-600"
                    : "border-stone-200 hover:border-stone-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <CreditCard className="w-5 h-5 text-amber-700" />
                  <div>
                    <div className="text-xs font-bold text-stone-900">
                      Credit / Debit Card (Instant Simulation)
                    </div>
                    <div className="text-[11px] text-stone-500">
                      Visa, Mastercard, RuPay & Amex supported
                    </div>
                  </div>
                </div>
                <input
                  type="radio"
                  name="payment"
                  checked={paymentMethod === "mock_card"}
                  onChange={() => setPaymentMethod("mock_card")}
                  className="accent-amber-600"
                />
              </label>

              <label
                className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-center justify-between ${
                  paymentMethod === "mock_upi"
                    ? "border-amber-600 bg-amber-50/50 ring-1 ring-amber-600"
                    : "border-stone-200 hover:border-stone-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Smartphone className="w-5 h-5 text-amber-700" />
                  <div>
                    <div className="text-xs font-bold text-stone-900">UPI / QR Code</div>
                    <div className="text-[11px] text-stone-500">
                      Google Pay, PhonePe, Paytm, or BHIM
                    </div>
                  </div>
                </div>
                <input
                  type="radio"
                  name="payment"
                  checked={paymentMethod === "mock_upi"}
                  onChange={() => setPaymentMethod("mock_upi")}
                  className="accent-amber-600"
                />
              </label>

              <label
                className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-center justify-between ${
                  paymentMethod === "cod"
                    ? "border-amber-600 bg-amber-50/50 ring-1 ring-amber-600"
                    : "border-stone-200 hover:border-stone-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Banknote className="w-5 h-5 text-amber-700" />
                  <div>
                    <div className="text-xs font-bold text-stone-900">Cash on Delivery (COD)</div>
                    <div className="text-[11px] text-stone-500">Pay cash or UPI upon delivery</div>
                  </div>
                </div>
                <input
                  type="radio"
                  name="payment"
                  checked={paymentMethod === "cod"}
                  onChange={() => setPaymentMethod("cod")}
                  className="accent-amber-600"
                />
              </label>
            </div>
          </div>
        </div>

        {/* Right Column: Order Confirmation Box */}
        <div className="space-y-6">
          <div className="bg-white rounded-3xl p-6 border border-stone-200 shadow-sm space-y-6">
            <h3 className="text-base font-bold text-stone-900">Order Summary</h3>

            {/* Line items preview */}
            <div className="space-y-3 divide-y divide-stone-100 max-h-60 overflow-y-auto pr-1">
              {items.map((it) => (
                <div key={it.id} className="pt-3 first:pt-0 flex items-center justify-between text-xs">
                  <div className="truncate pr-2">
                    <span className="font-bold text-stone-900">{it.quantity}x</span>{" "}
                    <span className="text-stone-700">{it.product_title}</span>
                  </div>
                  <span className="font-bold text-stone-900 shrink-0">
                    {formatPrice(it.price_cents * it.quantity)}
                  </span>
                </div>
              ))}
            </div>

            {/* Price Calculations */}
            <div className="space-y-2.5 pt-3 border-t border-stone-100 text-xs">
              <div className="flex justify-between text-stone-600">
                <span>Subtotal</span>
                <span className="font-semibold text-stone-900">{formatPrice(subtotal)}</span>
              </div>
              <div className="flex justify-between text-stone-600">
                <span>Shipping</span>
                <span className="font-semibold text-stone-900">
                  {shippingFee === 0 ? "FREE" : formatPrice(shippingFee)}
                </span>
              </div>
              <div className="flex justify-between text-stone-600">
                <span>Taxes & GST (5%)</span>
                <span className="font-semibold text-stone-900">{formatPrice(tax)}</span>
              </div>
              <div className="flex justify-between text-base font-bold text-stone-900 pt-3 border-t border-stone-200">
                <span>Total Amount</span>
                <span className="text-xl font-serif font-black">{formatPrice(total)}</span>
              </div>
            </div>

            {/* Pay Button */}
            <button
              onClick={handlePlaceOrder}
              disabled={submitting}
              className="w-full py-4 px-6 rounded-2xl bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-bold text-sm shadow-md transition-all flex items-center justify-center gap-2"
            >
              <Lock className="w-4 h-4" />
              {submitting ? "Placing Order..." : `Pay ${formatPrice(total)}`}
            </button>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-stone-400 text-center">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Encrypted Mock Payment • 100% Buyer Protection</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto py-24 px-4 text-center">
          <div className="w-12 h-12 border-4 border-amber-700 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-stone-600 text-sm font-medium">Preparing artisan checkout...</p>
        </div>
      }
    >
      <CheckoutForm />
    </Suspense>
  );
}
