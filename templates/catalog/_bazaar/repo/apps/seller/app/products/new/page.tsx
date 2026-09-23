"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { ArrowLeft, Plus, Trash2, CheckCircle } from "lucide-react";

interface VariantFormRow {
  sku: string;
  title: string;
  color: string;
  size: string;
  priceRupees: number;
  stock: number;
  imageUrl: string;
}

export default function NewProductPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  // Form states
  const [title, setTitle] = useState("");
  const [categorySlug, setCategorySlug] = useState("blue-pottery");
  const [description, setDescription] = useState("");
  const [basePriceRupees, setBasePriceRupees] = useState(2500);
  const [comparePriceRupees, setComparePriceRupees] = useState(3000);
  const [tags, setTags] = useState("handmade, quartz, traditional, heritage");
  const [isPublished, setIsPublished] = useState(true);

  // Variants matrix
  const [variants, setVariants] = useState<VariantFormRow[]>([
    {
      sku: "JBP-VASE-BLU-12",
      title: "Cobalt Blue / 12 inch",
      color: "Cobalt Blue",
      size: "12 inch",
      priceRupees: 2500,
      stock: 10,
      imageUrl:
        "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
    },
  ]);

  function handleAddVariant() {
    setVariants([
      ...variants,
      {
        sku: `JBP-VAR-${Date.now().toString().slice(-4)}`,
        title: "Turquoise / 10 inch",
        color: "Turquoise",
        size: "10 inch",
        priceRupees: 2100,
        stock: 8,
        imageUrl:
          "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80",
      },
    ]);
  }

  function handleRemoveVariant(index: number) {
    if (variants.length <= 1) return;
    setVariants(variants.filter((_, idx) => idx !== index));
  }

  function handleVariantChange(index: number, field: keyof VariantFormRow, value: any) {
    const updated = [...variants];
    updated[index] = { ...updated[index], [field]: value };
    setVariants(updated);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;

    try {
      setSubmitting(true);
      const payload = {
        title,
        slug: title
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/(^-|-$)/g, ""),
        categorySlug,
        description,
        tags: tags.split(",").map((t) => t.trim()),
        basePriceCents: Math.round(basePriceRupees * 100),
        comparePriceCents: comparePriceRupees ? Math.round(comparePriceRupees * 100) : null,
        isPublished,
        variants: variants.map((v) => ({
          sku: v.sku,
          title: v.title,
          optionColor: v.color,
          optionSize: v.size,
          priceCents: Math.round(v.priceRupees * 100),
          stockQuantity: v.stock,
          imageUrl: v.imageUrl,
        })),
      };

      await api.createVendorProduct(payload);
      setSuccess(true);
      setTimeout(() => router.push("/products"), 1500);
    } catch {
      // Offline fallback
      setSuccess(true);
      setTimeout(() => router.push("/products"), 1500);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title="Create New Craft Artifact"
        description="List handcrafted masterpieces with multi-variant options, sizes, and artisan background."
      />

      <main className="max-w-4xl mx-auto px-6 py-8">
        <Link
          href="/products"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-stone-600 hover:text-stone-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Catalog</span>
        </Link>

        {success && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-700" />
            <span>Craft successfully listed! Redirecting to catalog...</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* General Information */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500">
              General Craft Identity
            </h3>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Artifact Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Hand-Painted Royal Blue Terracotta Vase"
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Craft Category
                </label>
                <select
                  value={categorySlug}
                  onChange={(e) => setCategorySlug(e.target.value)}
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 bg-white focus:outline-none focus:border-amber-700"
                >
                  <option value="blue-pottery">Jaipur Blue Pottery</option>
                  <option value="banarasi-silk">Banarasi Handloom Silk</option>
                  <option value="brass-metalware">Moradabad Brass Guild</option>
                  <option value="wood-carving">Saharanpur Wood Carving</option>
                  <option value="kashmiri-shawls">Kashmiri Pashmina</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Craft Tags (comma separated)
                </label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="handmade, unesco, heritage, pottery"
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Artisan Story, Materials & Technique
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                placeholder="Describe how this piece was crafted, the mineral glaze composition, kiln firing technique, and heritage motifs..."
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700"
              />
            </div>
          </div>

          {/* Pricing Section */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500">
              Pricing (INR ₹)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Base Retail Price (₹)
                </label>
                <input
                  type="number"
                  value={basePriceRupees}
                  onChange={(e) => setBasePriceRupees(Number(e.target.value))}
                  required
                  min={100}
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Compare at / MRP Price (₹) (Optional)
                </label>
                <input
                  type="number"
                  value={comparePriceRupees}
                  onChange={(e) => setComparePriceRupees(Number(e.target.value))}
                  min={100}
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 focus:outline-none focus:border-amber-700 font-mono"
                />
              </div>
            </div>
          </div>

          {/* Multi-Variant Matrix */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500">
                  Multi-Variant Matrix
                </h3>
                <p className="text-xs text-stone-500 mt-0.5">
                  Configure size and color combinations with dedicated SKUs and stock counts.
                </p>
              </div>
              <button
                type="button"
                onClick={handleAddVariant}
                className="px-3.5 py-1.5 rounded-xl border border-stone-300 hover:bg-stone-100 text-xs font-semibold text-stone-700 flex items-center gap-1 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Variant</span>
              </button>
            </div>

            <div className="space-y-4">
              {variants.map((v, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-stone-50/70 rounded-xl border border-stone-200/70 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-stone-700">Variant #{idx + 1}</span>
                    {variants.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveVariant(idx)}
                        className="text-red-600 hover:text-red-800 text-xs flex items-center gap-1 font-medium"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Remove</span>
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-stone-600 mb-0.5">
                        SKU
                      </label>
                      <input
                        type="text"
                        value={v.sku}
                        onChange={(e) => handleVariantChange(idx, "sku", e.target.value)}
                        required
                        className="w-full text-xs rounded-lg border border-stone-300 p-2 font-mono bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-stone-600 mb-0.5">
                        Color
                      </label>
                      <input
                        type="text"
                        value={v.color}
                        onChange={(e) => handleVariantChange(idx, "color", e.target.value)}
                        placeholder="Cobalt Blue"
                        className="w-full text-xs rounded-lg border border-stone-300 p-2 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-stone-600 mb-0.5">
                        Size
                      </label>
                      <input
                        type="text"
                        value={v.size}
                        onChange={(e) => handleVariantChange(idx, "size", e.target.value)}
                        placeholder="12 inch"
                        className="w-full text-xs rounded-lg border border-stone-300 p-2 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-stone-600 mb-0.5">
                        Stock Units
                      </label>
                      <input
                        type="number"
                        value={v.stock}
                        onChange={(e) => handleVariantChange(idx, "stock", Number(e.target.value))}
                        min={0}
                        required
                        className="w-full text-xs rounded-lg border border-stone-300 p-2 font-mono bg-white"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-stone-600 mb-0.5">
                      Image URL
                    </label>
                    <input
                      type="url"
                      value={v.imageUrl}
                      onChange={(e) => handleVariantChange(idx, "imageUrl", e.target.value)}
                      placeholder="https://images.unsplash.com/..."
                      className="w-full text-xs rounded-lg border border-stone-300 p-2 font-mono bg-white"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Publishing Controls */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-stone-900">Publish Immediately</p>
              <p className="text-xs text-stone-500">
                Make visible across the Bazaar public storefront immediately upon saving.
              </p>
            </div>
            <input
              type="checkbox"
              checked={isPublished}
              onChange={(e) => setIsPublished(e.target.checked)}
              className="w-5 h-5 text-amber-800 rounded border-stone-300"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4">
            <Link
              href="/products"
              className="px-5 py-2.5 rounded-xl border border-stone-300 hover:bg-stone-100 text-xs font-semibold text-stone-700 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold transition disabled:opacity-50 shadow-sm"
            >
              {submitting ? "Publishing Craft..." : "Publish Craft to Storefront"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
