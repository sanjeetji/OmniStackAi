"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  ShoppingBag,
  Store,
  Star,
  Layers,
  ChevronRight,
} from "lucide-react";
import { api, type Product, type Shop, type Category } from "@bazaar/shared";
import { ProductCard } from "../components/product-card.tsx";

export default function HomePage() {
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([]);
  const [shops, setShops] = useState<Shop[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [prods, shps, cats] = await Promise.all([
          api.getFeatured(),
          api.getShops(),
          api.getCategories(),
        ]);
        setFeaturedProducts(prods);
        setShops(shps);
        setCategories(cats);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-16 animate-fade-in">
      {/* Hero Showcase Section */}
      <section className="relative rounded-3xl overflow-hidden bg-gradient-to-r from-stone-900 via-stone-800 to-amber-950 text-white shadow-xl">
        <div className="absolute inset-0 opacity-25 mix-blend-overlay bg-[radial-gradient(#d97706_1px,transparent_1px)] [background-size:16px_16px]" />
        <div className="relative px-6 py-16 sm:px-12 sm:py-20 lg:py-24 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-semibold mb-6 border border-amber-500/30 backdrop-blur-xs">
            <Sparkles className="w-3.5 h-3.5" />
            Direct from 1,200+ Master Weavers & Craft Clusters
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-serif font-black tracking-tight leading-tight sm:leading-none">
            Authentic Indian Crafts,{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-amber-200 to-amber-400">
              Direct to Your Home.
            </span>
          </h1>

          <p className="mt-6 text-sm sm:text-base text-stone-300 leading-relaxed max-w-xl">
            Experience hand-spun Chanderi silks, studio ceramics, engraved brassware, and single-origin Malabar spices. Buy from multiple artisan workshops in a single seamless order.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/category/apparel-ethnic"
              className="px-6 py-3 rounded-full bg-amber-600 hover:bg-amber-500 text-white text-sm font-semibold shadow-md transition-all flex items-center gap-2"
            >
              <ShoppingBag className="w-4 h-4" />
              Explore Handlooms
            </Link>
            <Link
              href="/category/home-decor"
              className="px-6 py-3 rounded-full bg-white/10 hover:bg-white/20 text-white text-sm font-semibold border border-white/20 backdrop-blur-xs transition-all flex items-center gap-2"
            >
              Artisanal Decor
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Category Pills Strip */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-serif font-bold text-stone-900">Explore by Category</h2>
            <p className="text-xs text-stone-500 mt-0.5">Handpicked collections across Indian craft regions</p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {categories.map((cat) => (
            <Link
              key={cat.id}
              href={`/category/${cat.slug}`}
              className="group p-4 bg-white rounded-2xl border border-stone-200/80 hover:border-amber-400 hover:shadow-md transition-all flex flex-col items-center text-center"
            >
              <div className="w-16 h-16 rounded-full overflow-hidden bg-stone-100 mb-3 shadow-inner group-hover:scale-105 transition-transform">
                <img
                  src={cat.image_url || "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=200&auto=format&fit=crop"}
                  alt={cat.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <h3 className="text-xs font-bold text-stone-900 group-hover:text-amber-800 transition-colors line-clamp-1">
                {cat.name}
              </h3>
              <span className="text-[11px] text-stone-400 mt-1 flex items-center gap-0.5">
                Explore <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* Featured Products */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-serif font-bold text-stone-900">Curated Masterpieces</h2>
            <p className="text-xs text-stone-500 mt-0.5">High-craft items celebrating traditional Indian techniques</p>
          </div>
          <Link
            href="/category/all"
            className="text-xs font-semibold text-amber-800 hover:text-amber-950 flex items-center gap-1"
          >
            View all products <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-72 bg-stone-100 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredProducts.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}
      </section>

      {/* Verified Artisan Shops Showcase */}
      <section className="bg-amber-50/60 rounded-3xl p-6 sm:p-10 border border-amber-200/60">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <span className="text-[11px] uppercase tracking-wider font-bold text-amber-800">
              Direct from Workshops
            </span>
            <h2 className="text-2xl font-serif font-bold text-stone-900 mt-1">
              Meet Our Verified Artisan Creators
            </h2>
            <p className="text-xs text-stone-600 mt-1">
              Every shop is independently verified for fair wages, craft marks, and authentic origins.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-900 bg-white px-3 py-1.5 rounded-full border border-amber-200 shrink-0">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            100% Certified KYC
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {shops.slice(0, 6).map((shop) => (
            <Link
              key={shop.id}
              href={`/shops/${shop.slug}`}
              className="group bg-white rounded-2xl p-5 border border-stone-200/80 hover:shadow-lg hover:border-amber-400 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 rounded-xl overflow-hidden bg-stone-100 shrink-0 border border-stone-100">
                    <img
                      src={shop.logo_url || "https://images.unsplash.com/photo-1544816155-12df9643f363?w=100&auto=format&fit=crop"}
                      alt={shop.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-stone-900 group-hover:text-amber-800 transition-colors">
                      {shop.name}
                    </h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <Star className="w-3 h-3 text-amber-500 fill-current" />
                      <span className="text-xs font-bold text-stone-800">
                        {Number(shop.rating_avg || 5.0).toFixed(1)}
                      </span>
                      <span className="text-[10px] text-stone-400">
                        ({shop.rating_count} reviews)
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-stone-600 line-clamp-2 leading-relaxed italic">
                  "{shop.tagline || shop.description}"
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-xs font-semibold text-amber-800">
                <span>View Artisan Workshop</span>
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* How Multi-Vendor Marketplace Works */}
      <section className="bg-white rounded-3xl p-6 sm:p-10 border border-stone-200">
        <h2 className="text-xl font-serif font-bold text-stone-900 text-center mb-2">
          How Bazaar Multi-Vendor Commerce Works
        </h2>
        <p className="text-xs text-stone-500 text-center max-w-lg mx-auto mb-10">
          Seamless multi-store shopping backed by automated per-vendor fulfillment and double-entry accounting.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/60 text-center">
            <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 font-bold flex items-center justify-center mx-auto mb-3 text-sm">
              1
            </div>
            <h4 className="text-xs font-bold text-stone-900">One Shared Cart</h4>
            <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
              Add products from multiple independent artisan shops and pay once with Card, UPI, or COD.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/60 text-center">
            <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 font-bold flex items-center justify-center mx-auto mb-3 text-sm">
              2
            </div>
            <h4 className="text-xs font-bold text-stone-900">Automated Split Orders</h4>
            <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
              The platform partitions your order into independent shipments assigned directly to each seller workshop.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/60 text-center">
            <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 font-bold flex items-center justify-center mx-auto mb-3 text-sm">
              3
            </div>
            <h4 className="text-xs font-bold text-stone-900">5-Stage State Machine</h4>
            <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
              Each vendor accepts, packs, labels, and dispatches via Delhivery or BlueDart with live tracking.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/60 text-center">
            <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-800 font-bold flex items-center justify-center mx-auto mb-3 text-sm">
              4
            </div>
            <h4 className="text-xs font-bold text-stone-900">Automated Settlements</h4>
            <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
              The double-entry ledger deducts platform commission and settles net earnings directly to vendor banks.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
