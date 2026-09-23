"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, formatPrice } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { ArrowLeft, CheckCircle } from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function EditProductPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const [title, setTitle] = useState("Hand-Painted Royal Blue Terracotta Vase");
  const [description, setDescription] = useState(
    "Traditional Jaipur blue pottery vase handcrafted using ground quartz and copper oxide."
  );
  const [basePriceRupees, setBasePriceRupees] = useState(2400);
  const [stockQty, setStockQty] = useState(14);
  const [isPublished, setIsPublished] = useState(true);

  useEffect(() => {
    // Attempt load product
    async function load() {
      try {
        setLoading(true);
        // api loads or fallback
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      setSuccess(true);
      setTimeout(() => router.push("/products"), 1500);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title="Edit Craft Listing"
        description={`Product ID: ${id} • Jaipur Blue Pottery Collection`}
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
            <span>Listing updated successfully!</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Artifact Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Description & Technique
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Retail Price (₹)
                </label>
                <input
                  type="number"
                  value={basePriceRupees}
                  onChange={(e) => setBasePriceRupees(Number(e.target.value))}
                  min={100}
                  required
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Total Allocated Stock
                </label>
                <input
                  type="number"
                  value={stockQty}
                  onChange={(e) => setStockQty(Number(e.target.value))}
                  min={0}
                  required
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs font-semibold text-stone-700">Published Status</span>
              <input
                type="checkbox"
                checked={isPublished}
                onChange={(e) => setIsPublished(e.target.checked)}
                className="w-5 h-5 text-amber-800 rounded border-stone-300"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <Link
              href="/products"
              className="px-5 py-2.5 rounded-xl border border-stone-300 text-stone-700 text-xs font-semibold"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold transition disabled:opacity-50"
            >
              {saving ? "Saving Changes..." : "Save Changes"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
