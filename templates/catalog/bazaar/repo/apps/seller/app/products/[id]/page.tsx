"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Eye, EyeOff, Package, Save, Star } from "lucide-react";
import { api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { useApi, useAction } from "@/lib/use-api";
import { count, day, inr, num } from "@/lib/format";

export default function EditListing({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const listing = useApi(() => api.getVendorProduct(id), [id]);
  const { run, busy, error } = useAction();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", price: "", comparePrice: "", tags: "" });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!listing.data || loaded) return;
    const p = listing.data.product;
    setForm({
      title: p.title ?? "",
      description: p.description ?? "",
      price: String(num(p.base_price_cents) / 100),
      comparePrice: p.compare_price_cents ? String(num(p.compare_price_cents) / 100) : "",
      tags: (p.tags ?? []).join(", "),
    });
    setLoaded(true);
  }, [listing.data, loaded]);

  async function save(patch?: { isPublished?: boolean }) {
    const ok = await run(() =>
      api.updateVendorProduct(id, {
        title: form.title.trim(),
        description: form.description.trim(),
        basePriceCents: Math.round(Number(form.price) * 100),
        comparePriceCents: form.comparePrice ? Math.round(Number(form.comparePrice) * 100) : undefined,
        tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        ...patch,
      })
    );
    if (ok) {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      listing.refresh();
    }
  }

  const field = "w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500";
  const label = "mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-400";

  return (
    <>
      <SellerHeader title="Edit listing" description="What shoppers see, and what you have in stock" />

      <div className="p-6">
        <Link href="/products" className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200">
          <ArrowLeft className="h-3.5 w-3.5" /> Catalogue
        </Link>

        {error && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
            {error}
          </div>
        )}
        {saved && (
          <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-300">
            Saved.
          </div>
        )}

        {listing.error && !listing.data ? (
          <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            {listing.error}
          </p>
        ) : !listing.data ? (
          <p aria-busy="true" className="text-sm text-slate-400">Loading the listing…</p>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <div>
                <label className={label}>Title</label>
                <input className={field} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              </div>
              <div>
                <label className={label}>About this piece</label>
                <textarea className={`${field} min-h-32`} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={label}>Price (₹)</label>
                  <input className={field} type="number" min="1" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
                </div>
                <div>
                  <label className={label}>Was (₹)</label>
                  <input className={field} type="number" min="0" value={form.comparePrice} onChange={(e) => setForm({ ...form, comparePrice: e.target.value })} />
                </div>
              </div>
              <div>
                <label className={label}>Tags</label>
                <input className={field} value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
              </div>

              <div className="flex flex-wrap gap-2 border-t border-slate-800 pt-4">
                <button
                  onClick={() => void save()}
                  disabled={busy}
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" /> {busy ? "Saving" : "Save"}
                </button>
                <button
                  onClick={() => void save({ isPublished: !listing.data!.product.is_published })}
                  disabled={busy}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
                >
                  {listing.data.product.is_published ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  {listing.data.product.is_published ? "Hide from the shop" : "Put it back on sale"}
                </button>
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-100">
                  <Package className="h-4 w-4 text-amber-400" /> Variants and stock
                </h2>
                {listing.data.variants.length === 0 ? (
                  <p className="text-sm text-slate-400">No variant on this listing.</p>
                ) : (
                  <ul className="space-y-2">
                    {listing.data.variants.map((variant: any) => (
                      <li key={variant.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 px-3 py-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm text-slate-200">{variant.title}</p>
                          <p className="truncate text-[11px] text-slate-500">
                            {variant.sku}
                            {variant.option_color ? ` · ${variant.option_color}` : ""}
                            {variant.option_size ? ` · ${variant.option_size}` : ""}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-sm font-semibold text-slate-200">{inr(variant.price_cents)}</p>
                          <p
                            className={
                              num(variant.stock_quantity) === 0
                                ? "text-[11px] font-semibold text-rose-400"
                                : num(variant.stock_quantity) < 5
                                  ? "text-[11px] font-semibold text-amber-400"
                                  : "text-[11px] text-slate-500"
                            }
                          >
                            {count(variant.stock_quantity)} in stock
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm">
                <h2 className="mb-3 text-sm font-bold text-slate-100">How it is doing</h2>
                <dl className="space-y-2 text-slate-400">
                  <div className="flex justify-between">
                    <dt>Rating</dt>
                    <dd className="inline-flex items-center gap-1 font-semibold text-slate-200">
                      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                      {Number(listing.data.product.rating_avg).toFixed(1)} · {listing.data.product.rating_count}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>On sale</dt>
                    <dd className="font-semibold text-slate-200">
                      {listing.data.product.is_published ? "Yes" : "Hidden"}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Listed</dt>
                    <dd className="font-semibold text-slate-200">{day(listing.data.product.created_at)}</dd>
                  </div>
                </dl>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  );
}
