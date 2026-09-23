"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft, Star, ShieldCheck, MapPin, Award, CheckCircle2 } from "lucide-react";
import { api, type Shop, type Product } from "@bazaar/shared";
import { ProductCard } from "../../../components/product-card.tsx";

export default function ShopProfilePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const [shop, setShop] = useState<Shop | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, pRes] = await Promise.all([
          api.getShop(slug),
          api.getProducts({ shop: slug, limit: 30 }),
        ]);
        setShop(s);
        setProducts(pRes.products);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-48 bg-stone-200 rounded-3xl" />
        <div className="h-8 bg-stone-200 rounded-md w-1/3" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-72 bg-stone-200 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!shop) {
    return (
      <div className="py-20 text-center">
        <h2 className="text-xl font-bold text-stone-900">Artisan Shop Not Found</h2>
        <Link href="/" className="inline-block mt-4 px-4 py-2 bg-amber-700 text-white rounded-full text-xs font-semibold">
          Return to Marketplace
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-10 animate-fade-in">
      {/* Shop Header Banner */}
      <div className="relative rounded-3xl overflow-hidden bg-stone-900 border border-stone-200 shadow-md">
        <div className="h-44 sm:h-56 w-full overflow-hidden opacity-75">
          <img
            src={shop.banner_url || "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=1200&auto=format&fit=crop"}
            alt={shop.name}
            className="w-full h-full object-cover"
          />
        </div>

        <div className="relative -mt-16 px-6 pb-6 sm:px-10 sm:pb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="flex items-end gap-4">
            <div className="w-24 h-24 rounded-2xl overflow-hidden bg-white p-1 shadow-lg border-2 border-white shrink-0">
              <img
                src={shop.logo_url || "https://images.unsplash.com/photo-1544816155-12df9643f363?w=200&auto=format&fit=crop"}
                alt={shop.name}
                className="w-full h-full object-cover rounded-xl"
              />
            </div>
            <div className="text-white pb-1">
              <div className="flex items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-serif font-black">{shop.name}</h1>
                <span className="inline-flex items-center gap-1 bg-emerald-500/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-xs">
                  <CheckCircle2 className="w-3 h-3" />
                  Verified
                </span>
              </div>
              <p className="text-xs text-amber-200 mt-1 max-w-md">{shop.tagline}</p>
            </div>
          </div>

          <div className="bg-white/95 backdrop-blur-sm rounded-2xl p-3 border border-stone-200 flex items-center gap-4 text-xs shrink-0 shadow-sm">
            <div className="flex items-center gap-1.5 pr-3 border-r border-stone-200">
              <Star className="w-4 h-4 text-amber-500 fill-current" />
              <span className="font-bold text-stone-900">{Number(shop.rating_avg || 5.0).toFixed(1)}</span>
              <span className="text-stone-400">({shop.rating_count} reviews)</span>
            </div>
            <div className="text-stone-700 font-medium">
              Direct Payouts • Fair Trade
            </div>
          </div>
        </div>
      </div>

      {/* About & Craft Story */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200">
        <h2 className="text-base font-bold text-stone-900 mb-2">About the Artisan Studio</h2>
        <p className="text-xs sm:text-sm text-stone-600 leading-relaxed max-w-3xl">
          {shop.description || "Dedicated to preserving heritage Indian craft techniques and empowering local artisan families."}
        </p>
      </div>

      {/* Shop Products Catalog */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-serif font-bold text-stone-900">
            Products by {shop.name} ({products.length})
          </h2>
        </div>

        {products.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 text-center border border-stone-200">
            <p className="text-sm font-semibold text-stone-600">No active products listed in this shop right now.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
