"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft, SlidersHorizontal, Search } from "lucide-react";
import { api, type Product, type Category } from "@bazaar/shared";
import { ProductCard } from "../../../components/product-card.tsx";

export default function CategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [category, setCategory] = useState<Category | null>(null);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<string>("popular");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const cats = await api.getCategories();
        setCategories(cats);

        const currentCat = cats.find((c) => c.slug === slug);
        setCategory(currentCat || null);

        const res = await api.getProducts({
          category: slug === "all" ? undefined : slug,
          sort: sort as any,
          limit: 40,
        });
        setProducts(res.products);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug, sort]);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Category Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-stone-500 hover:text-stone-900 transition-colors mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to all categories
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900">
              {slug === "all" ? "All Products" : category?.name || slug}
            </h1>
            <p className="text-xs text-stone-500 mt-1 max-w-xl">
              {category?.description || "Browse handcrafted artisan items directly from creator studios."}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-stone-500 font-medium">Sort by:</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="bg-stone-50 border border-stone-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-stone-800 focus:outline-none focus:border-amber-600"
            >
              <option value="popular">Popular & Rating</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="newest">Newest Arrivals</option>
            </select>
          </div>
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="h-72 bg-stone-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 text-center border border-stone-200">
          <p className="text-sm font-semibold text-stone-700">No products found in this category.</p>
          <p className="text-xs text-stone-400 mt-1">Try exploring other categories or view all products.</p>
          <Link
            href="/category/all"
            className="inline-block mt-4 px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-full text-xs font-semibold"
          >
            Browse All Products
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  );
}
