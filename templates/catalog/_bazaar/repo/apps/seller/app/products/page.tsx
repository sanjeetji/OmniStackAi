"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatPrice, api, type Product } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { Search, Plus, Filter, Edit, Eye, AlertCircle } from "lucide-react";

const DEMO_PRODUCTS: (Product & { totalStock: number })[] = [
  {
    id: "prod-001",
    shop_id: "shp-jaipur",
    category_id: "cat-pottery",
    title: "Hand-Painted Royal Blue Terracotta Vase",
    slug: "royal-blue-terracotta-vase",
    description: "Traditional Jaipur blue pottery vase handcrafted using ground quartz and copper oxide.",
    tags: ["unesco", "handmade", "heritage", "quartz"],
    base_price_cents: 240000,
    compare_price_cents: 280000,
    is_published: true,
    is_featured: true,
    rating_avg: 4.9,
    rating_count: 42,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
    updated_at: new Date().toISOString(),
    category_name: "Blue Pottery",
    totalStock: 14,
    variants: [
      {
        id: "var-001",
        product_id: "prod-001",
        sku: "JBP-VASE-BLU-12",
        title: "Cobalt Blue / 12 inch",
        option_color: "Cobalt Blue",
        option_size: "12 inch",
        price_cents: 240000,
        compare_price_cents: 280000,
        stock_quantity: 8,
        reserved_quantity: 2,
        is_active: true,
        image_url:
          "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
      },
      {
        id: "var-002",
        product_id: "prod-001",
        sku: "JBP-VASE-TRQ-10",
        title: "Turquoise / 10 inch",
        option_color: "Turquoise",
        option_size: "10 inch",
        price_cents: 195000,
        stock_quantity: 6,
        reserved_quantity: 0,
        is_active: true,
        image_url:
          "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
      },
    ],
  },
  {
    id: "prod-002",
    shop_id: "shp-jaipur",
    category_id: "cat-pottery",
    title: "Traditional Floral Jaipur Blue Glazed Plate",
    slug: "floral-blue-glazed-plate",
    description: "Signature decorative wall hanging or serving plate with Persian arabesque motifs.",
    tags: ["decorative", "persian", "wall-plate"],
    base_price_cents: 260000,
    is_published: true,
    is_featured: false,
    rating_avg: 4.8,
    rating_count: 28,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(),
    updated_at: new Date().toISOString(),
    category_name: "Blue Pottery",
    totalStock: 3,
    variants: [
      {
        id: "var-003",
        product_id: "prod-002",
        sku: "JBP-PLT-10",
        title: "10 inch / Turquoise & Indigo",
        option_color: "Turquoise & Indigo",
        option_size: "10 inch",
        price_cents: 260000,
        stock_quantity: 3,
        reserved_quantity: 1,
        is_active: true,
        image_url:
          "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=600&q=80",
      },
    ],
  },
  {
    id: "prod-003",
    shop_id: "shp-jaipur",
    category_id: "cat-pottery",
    title: "Miniature Jaipur Pottery Coasters Set of 6",
    slug: "miniature-pottery-coasters-set",
    description: "Set of 6 handcrafted ceramic coasters with cork backing and waterproof glaze.",
    tags: ["tableware", "set-of-6", "gift"],
    base_price_cents: 140000,
    is_published: true,
    is_featured: false,
    rating_avg: 5.0,
    rating_count: 14,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
    updated_at: new Date().toISOString(),
    category_name: "Blue Pottery",
    totalStock: 22,
    variants: [
      {
        id: "var-004",
        product_id: "prod-003",
        sku: "JBP-CST-6",
        title: "Multicolor / Set of 6",
        price_cents: 140000,
        stock_quantity: 22,
        reserved_quantity: 0,
        is_active: true,
        image_url:
          "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
      },
    ],
  },
];

export default function SellerProductsPage() {
  const [products, setProducts] = useState(DEMO_PRODUCTS);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getVendorProducts();
        if (res.products && res.products.length > 0) {
          const withStock = res.products.map((p) => ({
            ...p,
            totalStock:
              p.variants?.reduce((sum, v) => sum + (v.stock_quantity - v.reserved_quantity), 0) ||
              10,
          }));
          setProducts(withStock as any);
        }
      } catch {
        // Fallback demo products
      }
    }
    load();
  }, []);

  const filtered = products.filter((p) => {
    const matchSearch =
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.slug.toLowerCase().includes(search.toLowerCase());
    if (!matchSearch) return false;
    if (filter === "published") return p.is_published;
    if (filter === "low_stock") return p.totalStock < 5;
    return true;
  });

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title="Artisan Craft Catalog"
        description="Manage active listings, multi-variant inventory, prices, and stock allocations."
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Top Controls Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search crafts by title, motif, or SKU..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-stone-300 text-xs bg-white focus:outline-none focus:border-amber-700"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex rounded-xl bg-stone-200/60 p-1 text-xs font-semibold">
              <button
                onClick={() => setFilter("all")}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filter === "all" ? "bg-white text-stone-900 shadow-2xs" : "text-stone-600"
                }`}
              >
                All ({products.length})
              </button>
              <button
                onClick={() => setFilter("published")}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filter === "published" ? "bg-white text-stone-900 shadow-2xs" : "text-stone-600"
                }`}
              >
                Published
              </button>
              <button
                onClick={() => setFilter("low_stock")}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filter === "low_stock" ? "bg-white text-stone-900 shadow-2xs" : "text-stone-600"
                }`}
              >
                Low Stock
              </button>
            </div>

            <Link
              href="/products/new"
              className="px-4 py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Listing</span>
            </Link>
          </div>
        </div>

        {/* Product Catalog Table */}
        <div className="bg-white rounded-2xl border border-stone-200/80 overflow-hidden shadow-2xs">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-500 uppercase tracking-wider font-semibold border-b border-stone-200/60">
              <tr>
                <th className="py-3 px-6">Craft Artifact</th>
                <th className="py-3 px-6">Category</th>
                <th className="py-3 px-6">Variants</th>
                <th className="py-3 px-6">Base Price</th>
                <th className="py-3 px-6">Available Stock</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filtered.map((p) => {
                const img =
                  p.variants?.[0]?.image_url ||
                  "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80";
                const isLow = p.totalStock < 5;

                return (
                  <tr key={p.id} className="hover:bg-stone-50/50 transition">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <img
                          src={img}
                          alt={p.title}
                          className="w-12 h-12 object-cover rounded-xl border border-stone-200 flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <p className="font-bold text-stone-900 truncate max-w-xs">{p.title}</p>
                          <p className="text-[11px] text-stone-400 font-mono mt-0.5">/{p.slug}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-stone-600 font-medium">
                      {p.category_name || "Artisan Craft"}
                    </td>
                    <td className="py-4 px-6 text-stone-600">
                      {p.variants?.length || 1} variant(s)
                    </td>
                    <td className="py-4 px-6 font-bold text-stone-900">
                      {formatPrice(p.base_price_cents)}
                      {p.compare_price_cents && (
                        <span className="block text-[10px] text-stone-400 line-through">
                          {formatPrice(p.compare_price_cents)}
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                          isLow
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        }`}
                      >
                        {isLow && <AlertCircle className="w-3 h-3 text-rose-600" />}
                        <span>{p.totalStock} in stock</span>
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                          p.is_published
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-stone-100 text-stone-600"
                        }`}
                      >
                        {p.is_published ? "Live" : "Draft"}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/products/${p.id}`}
                          className="p-1.5 rounded-lg border border-stone-300 hover:bg-stone-100 text-stone-700 transition"
                          title="Edit Product"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </Link>
                        <a
                          href={`http://localhost:3000/products/jaipur-pottery/${p.slug}`}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded-lg border border-stone-300 hover:bg-stone-100 text-stone-700 transition"
                          title="View on Storefront"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
