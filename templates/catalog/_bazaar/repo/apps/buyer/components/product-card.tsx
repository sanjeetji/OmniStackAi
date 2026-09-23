"use client";

import { useState } from "react";
import Link from "next/link";
import { Star, ShoppingBag, Check, Store } from "lucide-react";
import { formatPrice, api, type Product } from "@bazaar/shared";

export function ProductCard({ product }: { product: Product }) {
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);

  const primaryVariant = product.variants?.[0];
  const price = primaryVariant?.price_cents ?? product.base_price_cents;
  const comparePrice = primaryVariant?.compare_price_cents ?? product.compare_price_cents;
  const discountPercent =
    comparePrice && comparePrice > price
      ? Math.round(((comparePrice - price) / comparePrice) * 100)
      : null;

  const imageUrl =
    primaryVariant?.image_url ||
    "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop";

  const handleQuickAdd = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!primaryVariant) return;

    try {
      setAdding(true);
      await api.addToCart(primaryVariant.id, 1);
      setAdded(true);
      setTimeout(() => setAdded(false), 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="group relative bg-white rounded-2xl border border-stone-200/80 overflow-hidden hover:shadow-lg hover:border-amber-400/50 transition-all flex flex-col h-full">
      {/* Product Image */}
      <Link
        href={`/products/${product.shop_slug || "shop"}/${product.slug}`}
        className="block relative aspect-4/3 bg-stone-100 overflow-hidden"
      >
        <img
          src={imageUrl}
          alt={product.title}
          className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        {discountPercent && (
          <span className="absolute top-2.5 left-2.5 bg-rose-600 text-white font-bold text-[10px] px-2 py-0.5 rounded-full shadow-xs">
            {discountPercent}% OFF
          </span>
        )}
        {product.is_featured && (
          <span className="absolute top-2.5 right-2.5 bg-amber-600/90 text-white font-semibold text-[10px] px-2 py-0.5 rounded-full backdrop-blur-xs shadow-xs">
            Curated
          </span>
        )}
      </Link>

      {/* Product Info */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          {/* Shop Pill */}
          <Link
            href={`/shops/${product.shop_slug}`}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 hover:text-amber-950 transition-colors mb-1.5"
          >
            <Store className="w-3 h-3 text-amber-600" />
            <span>{product.shop_name || "Artisan Shop"}</span>
          </Link>

          {/* Title */}
          <Link
            href={`/products/${product.shop_slug || "shop"}/${product.slug}`}
            className="block font-medium text-stone-900 text-sm hover:text-amber-800 transition-colors line-clamp-2 leading-snug"
          >
            {product.title}
          </Link>

          {/* Rating */}
          <div className="flex items-center gap-1.5 mt-2">
            <div className="flex items-center text-amber-500">
              <Star className="w-3.5 h-3.5 fill-current" />
            </div>
            <span className="text-xs font-bold text-stone-800">
              {Number(product.rating_avg || 5.0).toFixed(1)}
            </span>
            <span className="text-stone-400 text-xs">
              ({product.rating_count || 1})
            </span>
          </div>
        </div>

        {/* Price & Add to Cart button */}
        <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between gap-2">
          <div>
            <div className="text-base font-bold text-stone-900 leading-tight">
              {formatPrice(price)}
            </div>
            {comparePrice && comparePrice > price && (
              <div className="text-xs text-stone-400 line-through">
                {formatPrice(comparePrice)}
              </div>
            )}
          </div>

          <button
            onClick={handleQuickAdd}
            disabled={adding}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-xs ${
              added
                ? "bg-emerald-600 text-white"
                : "bg-stone-900 hover:bg-amber-700 text-white"
            }`}
          >
            {added ? (
              <>
                <Check className="w-3.5 h-3.5" />
                Added
              </>
            ) : (
              <>
                <ShoppingBag className="w-3.5 h-3.5" />
                {adding ? "Adding..." : "Add"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
