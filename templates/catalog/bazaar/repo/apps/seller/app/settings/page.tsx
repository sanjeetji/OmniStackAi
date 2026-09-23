"use client";

import { useEffect, useState } from "react";
import { Landmark, Save, ShieldCheck, Store } from "lucide-react";
import { api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { useApi, useAction } from "@/lib/use-api";
import { day, titleCase } from "@/lib/format";

export default function AtelierSettings() {
  const shop = useApi(() => api.getVendorShop(), []);
  const { run, busy, error } = useAction();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    name: "",
    tagline: "",
    description: "",
    bankName: "",
    bankAccountLast4: "",
    bankIfscCode: "",
  });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!shop.data || loaded) return;
    setForm({
      name: shop.data.name ?? "",
      tagline: shop.data.tagline ?? "",
      description: shop.data.description ?? "",
      bankName: shop.data.bank_name ?? "",
      bankAccountLast4: shop.data.bank_account_last4 ?? "",
      bankIfscCode: shop.data.bank_ifsc_code ?? "",
    });
    setLoaded(true);
  }, [shop.data, loaded]);

  async function save() {
    const ok = await run(() => api.updateShop(form));
    if (ok) {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      shop.refresh();
    }
  }

  const field = "w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500";
  const label = "mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-400";

  return (
    <>
      <SellerHeader title="Atelier settings" description="Your workshop as shoppers see it, and where you are paid" />

      <div className="p-6">
        {error && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
            {error}
          </div>
        )}
        {saved && (
          <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-300">
            Saved. Shoppers see the change immediately.
          </div>
        )}

        {shop.error && !shop.data ? (
          <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            {shop.error}
          </p>
        ) : !shop.data ? (
          <p aria-busy="true" className="text-sm text-slate-400">Loading your workshop…</p>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-100">
                <Store className="h-4 w-4 text-amber-400" /> Your workshop
              </h2>
              <div className="space-y-4">
                <div>
                  <label className={label}>Name</label>
                  <input className={field} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div>
                  <label className={label}>Tagline</label>
                  <input className={field} value={form.tagline} onChange={(e) => setForm({ ...form, tagline: e.target.value })} />
                </div>
                <div>
                  <label className={label}>About the craft</label>
                  <textarea
                    className={`${field} min-h-28`}
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                  />
                </div>

                <h3 className="flex items-center gap-2 border-t border-slate-800 pt-4 text-sm font-bold text-slate-100">
                  <Landmark className="h-4 w-4 text-amber-400" /> Where you are settled
                </h3>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="sm:col-span-2">
                    <label className={label}>Bank</label>
                    <input className={field} value={form.bankName} onChange={(e) => setForm({ ...form, bankName: e.target.value })} />
                  </div>
                  <div>
                    <label className={label}>Last 4</label>
                    <input
                      className={field}
                      maxLength={4}
                      value={form.bankAccountLast4}
                      onChange={(e) => setForm({ ...form, bankAccountLast4: e.target.value })}
                    />
                  </div>
                </div>
                <div>
                  <label className={label}>IFSC</label>
                  <input
                    className={`${field} uppercase`}
                    value={form.bankIfscCode}
                    onChange={(e) => setForm({ ...form, bankIfscCode: e.target.value.toUpperCase() })}
                  />
                </div>

                <button
                  onClick={() => void save()}
                  disabled={busy}
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" /> {busy ? "Saving" : "Save"}
                </button>
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-100">
                  <ShieldCheck className="h-4 w-4 text-amber-400" /> Verification
                </h2>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">KYC status</span>
                  <span
                    className={
                      shop.data.kyc_status === "verified"
                        ? "rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-400 ring-1 ring-inset ring-emerald-500/30"
                        : "rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-400 ring-1 ring-inset ring-amber-500/30"
                    }
                  >
                    {titleCase(shop.data.kyc_status)}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">
                  {shop.data.kyc_status === "verified"
                    ? "You are verified and may list and sell."
                    : "A marketplace operator reviews your documents before you can sell. You will be told either way."}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm">
                <h2 className="mb-3 text-sm font-bold text-slate-100">Your terms</h2>
                <dl className="space-y-2 text-slate-400">
                  <div className="flex justify-between">
                    <dt>Commission</dt>
                    <dd className="font-semibold text-slate-200">
                      {(shop.data.commission_rate_basis_points / 100).toFixed(1)}%
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Rating</dt>
                    <dd className="font-semibold text-slate-200">
                      {Number(shop.data.rating_avg).toFixed(1)} · {shop.data.rating_count}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Joined</dt>
                    <dd className="font-semibold text-slate-200">{day(shop.data.created_at)}</dd>
                  </div>
                </dl>
                <p className="mt-3 border-t border-slate-800 pt-3 text-xs text-slate-500">
                  Your commission is set by the marketplace. Ask an operator to change it.
                </p>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  );
}
