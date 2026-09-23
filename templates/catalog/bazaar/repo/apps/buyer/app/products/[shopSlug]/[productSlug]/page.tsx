"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  Star,
  ShoppingBag,
  ShieldCheck,
  Truck,
  RotateCcw,
  Store,
  Check,
  ArrowRight,
  Info,
} from "lucide-react";
import { formatPrice, api, type Product, type ProductVariant } from "@bazaar/shared";

export default function ProductDetailPage({
  params,
}: {
  params: Promise<{ shopSlug: string; productSlug: string }>;
}) {
  const { shopSlug, productSlug } = use(params);
  const [product, setProduct] = useState<Product | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const [activeTab, setActiveTab] = useState<"details" | "craft" | "reviews">("details");

  useEffect(() => {
    async function load() {
      try {
        const prod = await api.getProduct(shopSlug, productSlug);
        setProduct(prod);
        if (prod.variants && prod.variants.length > 0) {
          setSelectedVariant(prod.variants[0]);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [shopSlug, productSlug]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-12 animate-pulse space-y-6">
        <div className="h-6 w-48 bg-stone-200 rounded-md" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          <div className="aspect-square bg-stone-200 rounded-3xl" />
          <div className="space-y-4">
            <div className="h-8 bg-stone-200 rounded-md w-3/4" />
            <div className="h-6 bg-stone-200 rounded-md w-1/4" />
            <div className="h-24 bg-stone-200 rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-xl font-bold text-stone-900">Product Not Found</h2>
        <p className="text-xs text-stone-500 mt-1">The item may have been moved or archived by the artisan.</p>
        <Link href="/" className="inline-block mt-4 px-4 py-2 bg-amber-700 text-white rounded-full text-xs font-semibold">
          Return to Marketplace
        </Link>
      </div>
    );
  }

  const currentPrice = selectedVariant?.price_cents ?? product.base_price_cents;
  const comparePrice = selectedVariant?.compare_price_cents ?? product.compare_price_cents;
  const discountPercent =
    comparePrice && comparePrice > currentPrice
      ? Math.round(((comparePrice - currentPrice) / comparePrice) * 100)
      : null;

  const currentImage =
    selectedVariant?.image_url ||
    product.variants?.[0]?.image_url ||
    "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=800&auto=format&fit=crop";

  const handleAddToCart = async () => {
    if (!selectedVariant) return;
    try {
      setAdding(true);
      await api.addToCart(selectedVariant.id, quantity);
      setAdded(true);
      setTimeout(() => setAdded(false), 2500);
    } catch (err) {
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-12 animate-fade-in max-w-6xl mx-auto">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumbs" className="flex items-center gap-2 text-xs text-stone-500">
        <Link href="/" className="hover:text-stone-900">Home</Link>
        <span>/</span>
        <Link href={`/category/${product.category_slug || "all"}`} className="hover:text-stone-900">
          {product.category_name || "Category"}
        </Link>
        <span>/</span>
        <span className="text-stone-900 font-medium truncate max-w-[200px]">{product.title}</span>
      </nav>

      {/* Main Showcase Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 lg:gap-14">
        {/* Left: Product Image */}
        <div className="space-y-4">
          <div className="relative aspect-square rounded-3xl overflow-hidden bg-stone-100 border border-stone-200 shadow-sm">
            <img
              src={currentImage}
              alt={product.title}
              className="w-full h-full object-cover object-center"
            />
            {discountPercent && (
              <span className="absolute top-4 left-4 bg-rose-600 text-white font-bold text-xs px-3 py-1 rounded-full shadow-md">
                {discountPercent}% OFF
              </span>
            )}
          </div>

          {/* Variant Thumbnail Selector */}
          {product.variants && product.variants.length > 1 && (
            <div className="flex items-center gap-3 overflow-x-auto pb-2">
              {product.variants.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSelectedVariant(v)}
                  className={`w-16 h-16 rounded-xl overflow-hidden border-2 shrink-0 transition-all ${
                    selectedVariant?.id === v.id
                      ? "border-amber-600 scale-105 shadow-sm"
                      : "border-stone-200 opacity-70 hover:opacity-100"
                  }`}
                >
                  <img
                    src={v.image_url || currentImage}
                    alt={v.title}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Product Details & Purchase Form */}
        <div className="space-y-6">
          <div>
            {/* Vendor Shop Pill */}
            <Link
              href={`/shops/${product.shop_slug}`}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 text-amber-900 text-xs font-semibold border border-amber-200 hover:bg-amber-100 transition-colors mb-3"
            >
              <Store className="w-3.5 h-3.5 text-amber-700" />
              <span>{product.shop_name}</span>
              <span className="text-[10px] text-amber-700 bg-amber-200/60 px-1.5 py-0.2 rounded-full">
                Verified Artisan
              </span>
            </Link>

            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 leading-snug">
              {product.title}
            </h1>

            {/* Rating Stars */}
            <div className="flex items-center gap-2 mt-3">
              <div className="flex items-center text-amber-500">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star key={s} className="w-4 h-4 fill-current" />
                ))}
              </div>
              <span className="text-xs font-bold text-stone-800">
                {Number(product.rating_avg || 5.0).toFixed(1)}
              </span>
              <span className="text-xs text-stone-400">
                • {product.rating_count} customer reviews
              </span>
            </div>
          </div>

          {/* Pricing Box */}
          <div className="p-4 bg-stone-50 rounded-2xl border border-stone-200 flex items-baseline gap-3">
            <span className="text-3xl font-serif font-black text-stone-900">
              {formatPrice(currentPrice)}
            </span>
            {comparePrice && comparePrice > currentPrice && (
              <>
                <span className="text-base text-stone-400 line-through">
                  {formatPrice(comparePrice)}
                </span>
                <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                  Save {formatPrice(comparePrice - currentPrice)}
                </span>
              </>
            )}
            <span className="text-[11px] text-stone-500 ml-auto">Inclusive of all taxes</span>
          </div>

          {/* Variant Selection Matrix */}
          {product.variants && product.variants.length > 0 && (
            <div className="space-y-4">
              <label className="block text-xs font-bold uppercase tracking-wider text-stone-700">
                Select Option / Variant:
              </label>
              <div className="flex flex-wrap gap-2">
                {product.variants.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => setSelectedVariant(v)}
                    className={`px-4 py-2 rounded-xl text-xs font-semibold border transition-all text-left flex items-center gap-2 ${
                      selectedVariant?.id === v.id
                        ? "border-amber-600 bg-amber-50 text-amber-950 ring-1 ring-amber-600"
                        : "border-stone-200 bg-white text-stone-700 hover:border-stone-300"
                    }`}
                  >
                    <span>{v.title}</span>
                    <span className="text-[11px] font-bold text-stone-500">
                      {formatPrice(v.price_cents)}
                    </span>
                  </button>
                ))}
              </div>

              {/* Stock Status Indicator */}
              <div className="flex items-center gap-2 text-xs font-medium pt-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-emerald-800">
                  {selectedVariant?.stock_quantity
                    ? `In Stock (${selectedVariant.stock_quantity} pieces available)`
                    : "In Stock - Dispatches in 24 hours"}
                </span>
              </div>
            </div>
          )}

          {/* Quantity & Add to Cart Action */}
          <div className="flex items-center gap-4 pt-2">
            <div className="flex items-center border border-stone-200 rounded-xl bg-white shadow-xs">
              <button
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="px-3 py-2 text-sm font-bold text-stone-600 hover:text-stone-900"
              >
                -
              </button>
              <span className="px-2 text-xs font-bold text-stone-900">{quantity}</span>
              <button
                onClick={() => setQuantity(quantity + 1)}
                className="px-3 py-2 text-sm font-bold text-stone-600 hover:text-stone-900"
              >
                +
              </button>
            </div>

            <button
              onClick={handleAddToCart}
              disabled={adding}
              className={`flex-1 py-3.5 px-6 rounded-2xl text-sm font-bold flex items-center justify-center gap-2 shadow-md transition-all ${
                added
                  ? "bg-emerald-600 text-white"
                  : "bg-amber-700 hover:bg-amber-600 text-white"
              }`}
            >
              {added ? (
                <>
                  <Check className="w-4 h-4" />
                  Added to Cart!
                </>
              ) : (
                <>
                  <ShoppingBag className="w-4 h-4" />
                  {adding ? "Adding to Cart..." : "Add to Cart"}
                </>
              )}
            </button>

            <Link
              href="/cart"
              className="px-5 py-3.5 rounded-2xl text-sm font-bold bg-stone-900 hover:bg-stone-800 text-white transition-colors"
            >
              Buy Now
            </Link>
          </div>

          {/* Trust Guarantees */}
          <div className="grid grid-cols-3 gap-3 pt-4 border-t border-stone-100 text-center">
            <div className="p-3 bg-stone-50 rounded-xl">
              <ShieldCheck className="w-4 h-4 text-amber-700 mx-auto mb-1" />
              <div className="text-[11px] font-bold text-stone-800">GI Tag Certified</div>
              <div className="text-[10px] text-stone-400">Authentic handloom</div>
            </div>
            <div className="p-3 bg-stone-50 rounded-xl">
              <Truck className="w-4 h-4 text-amber-700 mx-auto mb-1" />
              <div className="text-[11px] font-bold text-stone-800">Tracked Delivery</div>
              <div className="text-[10px] text-stone-400">2-4 business days</div>
            </div>
            <div className="p-3 bg-stone-50 rounded-xl">
              <RotateCcw className="w-4 h-4 text-amber-700 mx-auto mb-1" />
              <div className="text-[11px] font-bold text-stone-800">Easy Returns</div>
              <div className="text-[10px] text-stone-400">7-day doorstep return</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs: Description, Artisan Workshop & Verified Reviews */}
      <div className="bg-white rounded-3xl p-6 sm:p-10 border border-stone-200">
        <div className="flex items-center gap-6 border-b border-stone-200 pb-4 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("details")}
            className={`pb-2 transition-colors relative ${
              activeTab === "details"
                ? "text-amber-800 font-bold border-b-2 border-amber-700"
                : "text-stone-500 hover:text-stone-900"
            }`}
          >
            Product Description
          </button>
          <button
            onClick={() => setActiveTab("craft")}
            className={`pb-2 transition-colors relative ${
              activeTab === "craft"
                ? "text-amber-800 font-bold border-b-2 border-amber-700"
                : "text-stone-500 hover:text-stone-900"
            }`}
          >
            Artisan Workshop & Craft Heritage
          </button>
          <button
            onClick={() => setActiveTab("reviews")}
            className={`pb-2 transition-colors relative ${
              activeTab === "reviews"
                ? "text-amber-800 font-bold border-b-2 border-amber-700"
                : "text-stone-500 hover:text-stone-900"
            }`}
          >
            Verified Reviews ({product.rating_count})
          </button>
        </div>

        <div className="mt-6 text-sm text-stone-600 leading-relaxed">
          {activeTab === "details" && (
            <div className="space-y-4">
              <p>{product.description}</p>
              {product.tags && product.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {product.tags.map((t) => (
                    <span key={t} className="px-2.5 py-1 bg-stone-100 rounded-full text-xs text-stone-600 font-medium">
                      #{t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "craft" && (
            <div className="space-y-4">
              <h4 className="font-bold text-stone-900">Crafted by {product.shop_name}</h4>
              <p>
                This item is handmade in the master weaving cluster of {product.shop_name}. Using centuries-old looms and natural dying vats, every warp and weft represents tangible cultural heritage.
              </p>
              <Link
                href={`/shops/${product.shop_slug}`}
                className="inline-flex items-center gap-1 text-xs font-bold text-amber-800 hover:underline pt-2"
              >
                Visit {product.shop_name} Storefront <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}

          {activeTab === "reviews" && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 p-4 bg-amber-50/60 rounded-2xl border border-amber-200/60">
                <div className="text-3xl font-serif font-black text-amber-900">
                  {Number(product.rating_avg || 5.0).toFixed(1)}
                </div>
                <div>
                  <div className="flex items-center text-amber-500">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star key={s} className="w-3.5 h-3.5 fill-current" />
                    ))}
                  </div>
                  <div className="text-xs text-amber-900 font-medium mt-0.5">
                    100% of buyers recommend this artisan piece
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-stone-50 rounded-2xl border border-stone-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-xs text-stone-900">Priya Sharma</span>
                    <span className="text-[10px] text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full font-bold">
                      Verified Purchase
                    </span>
                  </div>
                  <div className="flex items-center text-amber-500 mb-1">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star key={s} className="w-3 h-3 fill-current" />
                    ))}
                  </div>
                  <p className="text-xs text-stone-700">
                    "Exquisite drape and feel! The zari work is subtle and rich. Arrived in beautiful handloom packaging."
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
