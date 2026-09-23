"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShoppingBag,
  Trash2,
  ArrowRight,
  Store,
  Tag,
  ShieldCheck,
  Truck,
  CheckCircle2,
} from "lucide-react";
import { formatPrice, api, type Cart, type CartItem } from "@bazaar/shared";

export default function CartPage() {
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [couponCode, setCouponCode] = useState("");
  const [couponDiscount, setCouponDiscount] = useState(0);
  const [couponMessage, setCouponMessage] = useState("");
  const [applyingCoupon, setApplyingCoupon] = useState(false);

  const loadCart = async () => {
    try {
      const c = await api.getCart();
      setCart(c);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCart();
  }, []);

  const handleUpdateQty = async (itemId: string, newQty: number) => {
    try {
      await api.updateCartItem(itemId, newQty);
      loadCart();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemove = async (itemId: string) => {
    try {
      await api.removeCartItem(itemId);
      loadCart();
    } catch (err) {
      console.error(err);
    }
  };

  const handleApplyCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!couponCode.trim() || !cart) return;

    try {
      setApplyingCoupon(true);
      const res = await api.validateCoupon(couponCode, cart.subtotal_cents);
      if (res.valid) {
        setCouponDiscount(res.discountCents);
        setCouponMessage(`Coupon applied: Save ${formatPrice(res.discountCents)}!`);
      } else {
        setCouponDiscount(0);
        setCouponMessage("Invalid coupon code or minimum order spend not met.");
      }
    } catch (err) {
      setCouponMessage("Failed to apply coupon.");
    } finally {
      setApplyingCoupon(false);
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
  const isEmpty = items.length === 0;

  // Group items by vendor shop
  const groupedByShop = new Map<string, { shopName: string; shopSlug: string; items: CartItem[] }>();
  for (const item of items) {
    if (!groupedByShop.has(item.shop_id)) {
      groupedByShop.set(item.shop_id, {
        shopName: item.shop_name,
        shopSlug: item.shop_slug,
        items: [],
      });
    }
    groupedByShop.get(item.shop_id)!.items.push(item);
  }

  const subtotal = cart?.subtotal_cents || 0;
  const freeShippingThreshold = 100000; // ₹1,000
  const shippingFee = subtotal >= freeShippingThreshold || subtotal === 0 ? 0 : 9900;
  const tax = Math.round((subtotal * 5) / 100);
  const total = Math.max(0, subtotal - couponDiscount + shippingFee + tax);

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900">
          Shopping Cart ({items.reduce((acc, i) => acc + i.quantity, 0)} items)
        </h1>
        <Link
          href="/"
          className="text-xs font-semibold text-amber-800 hover:text-amber-950 flex items-center gap-1"
        >
          Continue Shopping <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {isEmpty ? (
        <div className="bg-white rounded-3xl p-16 text-center border border-stone-200 space-y-4">
          <div className="w-16 h-16 rounded-full bg-amber-50 text-amber-800 flex items-center justify-center mx-auto">
            <ShoppingBag className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-stone-900">Your shopping cart is empty</h3>
          <p className="text-xs text-stone-500 max-w-sm mx-auto">
            Explore our curated craft catalog and support authentic Indian artisans with fair-share purchases.
          </p>
          <Link
            href="/"
            className="inline-block mt-2 px-6 py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-full text-xs font-bold shadow-md transition-colors"
          >
            Explore Catalog
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          {/* Left Column: Multi-Vendor Partitioned Items */}
          <div className="lg:col-span-2 space-y-6">
            {/* Free Shipping Meter */}
            <div className="bg-amber-50 rounded-2xl p-4 border border-amber-200/80 text-xs flex items-center gap-3">
              <Truck className="w-5 h-5 text-amber-700 shrink-0" />
              <div className="flex-1">
                {subtotal >= freeShippingThreshold ? (
                  <span className="font-bold text-emerald-800">
                    🎉 You qualify for FREE shipping across all artisan orders!
                  </span>
                ) : (
                  <span>
                    Add <strong className="text-stone-900">{formatPrice(freeShippingThreshold - subtotal)}</strong> more of handcrafted goods to get <strong>FREE delivery</strong>.
                  </span>
                )}
              </div>
            </div>

            {/* Vendor Groups */}
            {Array.from(groupedByShop.entries()).map(([shopId, group]) => {
              const shopSubtotal = group.items.reduce(
                (acc, it) => acc + it.price_cents * it.quantity,
                0
              );

              return (
                <div
                  key={shopId}
                  className="bg-white rounded-3xl border border-stone-200 overflow-hidden shadow-xs"
                >
                  {/* Shop Partition Header */}
                  <div className="bg-stone-50/80 px-6 py-3.5 border-b border-stone-200 flex items-center justify-between">
                    <Link
                      href={`/shops/${group.shopSlug}`}
                      className="inline-flex items-center gap-2 text-xs font-bold text-stone-900 hover:text-amber-800 transition-colors"
                    >
                      <Store className="w-4 h-4 text-amber-700" />
                      <span>{group.shopName}</span>
                      <span className="text-[10px] text-stone-400 font-normal">
                        ({group.items.length} items)
                      </span>
                    </Link>
                    <span className="text-xs font-bold text-stone-700">
                      Subtotal: {formatPrice(shopSubtotal)}
                    </span>
                  </div>

                  {/* Items in this shop */}
                  <div className="divide-y divide-stone-100 p-6 space-y-6">
                    {group.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-start gap-4 pt-4 first:pt-0"
                      >
                        <div className="w-20 h-20 rounded-2xl overflow-hidden bg-stone-100 shrink-0 border border-stone-200">
                          <img
                            src={
                              item.image_url ||
                              "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=200&auto=format&fit=crop"
                            }
                            alt={item.product_title}
                            className="w-full h-full object-cover"
                          />
                        </div>

                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-bold text-stone-900 truncate">
                            {item.product_title}
                          </h4>
                          <p className="text-xs text-stone-500 mt-0.5">
                            {item.variant_title} • SKU: {item.sku}
                          </p>

                          <div className="flex items-center justify-between mt-3">
                            <div className="flex items-center border border-stone-200 rounded-lg bg-white">
                              <button
                                onClick={() => handleUpdateQty(item.id, item.quantity - 1)}
                                className="px-2.5 py-1 text-xs font-bold text-stone-600 hover:text-stone-900"
                              >
                                -
                              </button>
                              <span className="px-2 text-xs font-bold text-stone-900">
                                {item.quantity}
                              </span>
                              <button
                                onClick={() => handleUpdateQty(item.id, item.quantity + 1)}
                                className="px-2.5 py-1 text-xs font-bold text-stone-600 hover:text-stone-900"
                              >
                                +
                              </button>
                            </div>

                            <div className="flex items-center gap-4">
                              <span className="text-sm font-bold text-stone-900">
                                {formatPrice(item.price_cents * item.quantity)}
                              </span>
                              <button
                                onClick={() => handleRemove(item.id)}
                                className="text-stone-400 hover:text-rose-600 transition-colors p-1"
                                title="Remove item"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Order Summary & Checkout */}
          <div className="space-y-6">
            <div className="bg-white rounded-3xl p-6 border border-stone-200 shadow-sm space-y-6">
              <h3 className="text-base font-bold text-stone-900">Order Summary</h3>

              {/* Promo Coupon Form */}
              <form onSubmit={handleApplyCoupon} className="space-y-2">
                <label className="block text-[11px] uppercase font-bold text-stone-600 tracking-wider">
                  Discount Coupon
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Tag className="w-3.5 h-3.5 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={couponCode}
                      onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                      placeholder="e.g. WELCOME10"
                      className="w-full pl-9 pr-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs font-bold uppercase placeholder:normal-case placeholder:font-normal focus:bg-white focus:border-amber-600 focus:outline-none"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={applyingCoupon || !couponCode.trim()}
                    className="px-3.5 py-2 bg-stone-900 hover:bg-stone-800 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-colors"
                  >
                    Apply
                  </button>
                </div>
                {couponMessage && (
                  <p
                    className={`text-[11px] font-medium ${
                      couponDiscount > 0 ? "text-emerald-700" : "text-rose-600"
                    }`}
                  >
                    {couponMessage}
                  </p>
                )}
              </form>

              {/* Price Calculation Lines */}
              <div className="space-y-3 pt-3 border-t border-stone-100 text-xs">
                <div className="flex justify-between text-stone-600">
                  <span>Items Subtotal</span>
                  <span className="font-semibold text-stone-900">{formatPrice(subtotal)}</span>
                </div>

                {couponDiscount > 0 && (
                  <div className="flex justify-between text-emerald-700 font-medium">
                    <span>Coupon Savings</span>
                    <span>-{formatPrice(couponDiscount)}</span>
                  </div>
                )}

                <div className="flex justify-between text-stone-600">
                  <span>Estimated Shipping</span>
                  <span className="font-semibold text-stone-900">
                    {shippingFee === 0 ? "FREE" : formatPrice(shippingFee)}
                  </span>
                </div>

                <div className="flex justify-between text-stone-600">
                  <span>Estimated GST (5%)</span>
                  <span className="font-semibold text-stone-900">{formatPrice(tax)}</span>
                </div>

                <div className="flex justify-between text-base font-bold text-stone-900 pt-3 border-t border-stone-200">
                  <span>Grand Total</span>
                  <span className="text-xl font-serif font-black">{formatPrice(total)}</span>
                </div>
              </div>

              {/* Split Order Notice */}
              <div className="p-3 bg-amber-50 rounded-xl border border-amber-200/60 text-[11px] text-amber-900 leading-relaxed">
                <strong>Multi-Vendor Notice:</strong> Your cart contains items from <strong>{groupedByShop.size} artisan workshops</strong>. They will dispatch independently with separate tracking numbers.
              </div>

              {/* Checkout Button */}
              <Link
                href={`/checkout${couponCode && couponDiscount > 0 ? `?coupon=${encodeURIComponent(couponCode)}` : ""}`}
                className="w-full py-3.5 px-6 rounded-2xl bg-amber-700 hover:bg-amber-600 text-white font-bold text-sm text-center shadow-md transition-all flex items-center justify-center gap-2"
              >
                Proceed to Checkout
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
