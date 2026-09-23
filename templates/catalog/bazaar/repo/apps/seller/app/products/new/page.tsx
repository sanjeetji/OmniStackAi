"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { useApi, useAction } from "@/lib/use-api";
import { inr } from "@/lib/format";

interface VariantDraft {
  sku: string;
  title: string;
  optionColor: string;
  optionSize: string;
  price: string;
  stock: string;
}

const EMPTY: VariantDraft = { sku: "", title: "", optionColor: "", optionSize: "", price: "", stock: "0" };

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 200);
}

export default function NewListing() {
  const router = useRouter();
  const categories = useApi(() => api.getCategories(), []);
  const { run, busy, error } = useAction();

  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [comparePrice, setComparePrice] = useState("");
  const [variants, setVariants] = useState<VariantDraft[]>([{ ...EMPTY, title: "Standard" }]);

  const field = "w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500";
  const label = "mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-400";

  function updateVariant(index: number, patch: Partial<VariantDraft>) {
    setVariants((current) => current.map((variant, i) => (i === index ? { ...variant, ...patch } : variant)));
  }

  async function create() {
    const ok = await run(async () => {
      const product = await api.createVendorProduct({
        categoryId,
        title: title.trim(),
        slug: slugify(title),
        description: description.trim(),
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        basePriceCents: Math.round(Number(basePrice) * 100),
        comparePriceCents: comparePrice ? Math.round(Number(comparePrice) * 100) : undefined,
        variants: variants.map((variant, index) => ({
          sku: variant.sku.trim() || `${slugify(title).slice(0, 12).toUpperCase()}-${index + 1}`,
          title: variant.title.trim() || "Standard",
          optionColor: variant.optionColor.trim() || undefined,
          optionSize: variant.optionSize.trim() || undefined,
          priceCents: Math.round(Number(variant.price || basePrice) * 100),
          stockQuantity: Number(variant.stock) || 0,
        })),
      });
      router.push(`/products/${product.product.id}`);
    });
    return ok;
  }

  const valid = title.trim() && categoryId && description.trim() && Number(basePrice) > 0;

  return (
    <>
      <SellerHeader title="New listing" description="One craft, with every size or colour you make it in" />

      <div className="p-6">
        <Link href="/products" className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200">
          <ArrowLeft className="h-3.5 w-3.5" /> Catalogue
        </Link>

        {error && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
            {error}
          </div>
        )}

        <form
          className="grid gap-5 lg:grid-cols-[1.4fr_1fr]"
          onSubmit={(event) => {
            event.preventDefault();
            void create();
          }}
        >
          <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div>
              <label className={label}>Title</label>
              <input className={field} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Hand-painted blue pottery vase" required />
              {title && <p className="mt-1 text-[11px] text-slate-500">Address: /{slugify(title)}</p>}
            </div>

            <div>
              <label className={label}>Craft category</label>
              <select className={field} value={categoryId} onChange={(e) => setCategoryId(e.target.value)} required>
                <option value="">Choose a category</option>
                {(categories.data ?? []).map((category: any) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={label}>About this piece</label>
              <textarea
                className={`${field} min-h-32`}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="The technique, the materials, how long it takes to make, how to care for it."
                required
              />
            </div>

            <div>
              <label className={label}>Tags</label>
              <input className={field} value={tags} onChange={(e) => setTags(e.target.value)} placeholder="handmade, heritage, gi-tag" />
              <p className="mt-1 text-[11px] text-slate-500">Comma separated. Shoppers search these.</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={label}>Price (₹)</label>
                <input className={field} type="number" min="1" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} required />
              </div>
              <div>
                <label className={label}>Was (₹)</label>
                <input className={field} type="number" min="0" value={comparePrice} onChange={(e) => setComparePrice(e.target.value)} />
                <p className="mt-1 text-[11px] text-slate-500">Shown struck through. Leave blank if not on offer.</p>
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-bold text-slate-100">Variants</h2>
                <button
                  type="button"
                  onClick={() => setVariants((current) => [...current, { ...EMPTY }])}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-2 py-1 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  <Plus className="h-3 w-3" /> Add
                </button>
              </div>

              <div className="space-y-3">
                {variants.map((variant, index) => (
                  <div key={index} className="rounded-xl border border-slate-800 p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        Variant {index + 1}
                      </span>
                      {variants.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setVariants((current) => current.filter((_, i) => i !== index))}
                          className="text-slate-500 hover:text-rose-400"
                          aria-label="Remove variant"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="space-y-2">
                      <input className={field} value={variant.title} onChange={(e) => updateVariant(index, { title: e.target.value })} placeholder="Name, e.g. Large" />
                      <div className="grid grid-cols-2 gap-2">
                        <input className={field} value={variant.optionColor} onChange={(e) => updateVariant(index, { optionColor: e.target.value })} placeholder="Colour" />
                        <input className={field} value={variant.optionSize} onChange={(e) => updateVariant(index, { optionSize: e.target.value })} placeholder="Size" />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <input className={field} type="number" value={variant.price} onChange={(e) => updateVariant(index, { price: e.target.value })} placeholder={basePrice || "Price"} />
                        <input className={field} type="number" min="0" value={variant.stock} onChange={(e) => updateVariant(index, { stock: e.target.value })} placeholder="Stock" />
                      </div>
                      <input className={field} value={variant.sku} onChange={(e) => updateVariant(index, { sku: e.target.value })} placeholder="SKU (generated if blank)" />
                    </div>
                  </div>
                ))}
              </div>

              <p className="mt-3 border-t border-slate-800 pt-3 text-[11px] text-slate-500">
                Stock is held the moment a shopper checks out, so it cannot be oversold.
              </p>
            </div>

            <button
              type="submit"
              disabled={busy || !valid}
              className="w-full rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50"
            >
              {busy ? "Publishing" : `Publish for ${basePrice ? inr(Number(basePrice) * 100) : "—"}`}
            </button>
          </section>
        </form>
      </div>
    </>
  );
}
