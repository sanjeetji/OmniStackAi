"use client";

import { useState } from "react";
import { SellerHeader } from "@/components/seller-header";
import { ShieldCheck, CheckCircle2, Building2, MapPin } from "lucide-react";

export default function SellerSettingsPage() {
  const [saved, setSaved] = useState(false);
  const [shopName, setShopName] = useState("Jaipur Blue Art Pottery");
  const [tagline, setTagline] = useState(
    "Authentic UNESCO Heritage GI-tagged Blue Pottery Handcrafted in Rajasthan"
  );
  const [description, setDescription] = useState(
    "Preserving the classical 19th-century Jaipur blue pottery technique pioneered by Kripal Singh Shekhawat. Every item is molded by hand using quartz powder, Fuller's earth, and katira gond, without using clay."
  );
  const [bankName, setBankName] = useState("HDFC Bank Ltd");
  const [accountNumber, setAccountNumber] = useState("50100294109412");
  const [ifsc, setIfsc] = useState("HDFC0001248");

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 4000);
  }

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title="Workshop & Atelier Settings"
        description="Verify artisan credentials, bank settlement details, and public craft profile."
      />

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {saved && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center gap-2 shadow-2xs">
            <CheckCircle2 className="w-4 h-4 text-emerald-700" />
            <span>Workshop settings and bank settlement credentials updated!</span>
          </div>
        )}

        {/* KYC Verification Card */}
        <div className="bg-emerald-900 text-white p-6 rounded-2xl shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-800 text-emerald-200 flex items-center justify-center text-2xl font-bold flex-shrink-0">
              <ShieldCheck className="w-6 h-6 text-emerald-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold">Government Certified Master Artisan</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-700 text-white uppercase">
                  KYC Verified
                </span>
              </div>
              <p className="text-xs text-emerald-100/80 mt-1 max-w-lg">
                GI Tag Registration #39 (Jaipur Blue Pottery). Fully verified by the Crafts Council of
                India. Standard platform commission capped at 10.00%.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          {/* Atelier Brand Profile */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500">
              Workshop Brand Profile
            </h3>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Atelier Workshop Name
              </label>
              <input
                type="text"
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Storefront Headline & Tagline
              </label>
              <input
                type="text"
                value={tagline}
                onChange={(e) => setTagline(e.target.value)}
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Heritage Story & Studio Bio
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                required
                className="w-full text-sm rounded-xl border border-stone-300 p-3"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Studio Workshop Address
              </label>
              <div className="p-3 bg-stone-50 rounded-xl border border-stone-200 text-xs text-stone-700 flex items-start gap-2">
                <MapPin className="w-4 h-4 text-amber-800 flex-shrink-0 mt-0.5" />
                <span>Kripal Kumbh Studio, B-18 Shiv Marg, Bani Park, Jaipur, Rajasthan 302016</span>
              </div>
            </div>
          </div>

          {/* Direct Bank Settlement Credentials */}
          <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-4">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-amber-800" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500">
                Direct NEFT / RTGS Bank Account
              </h3>
            </div>
            <p className="text-xs text-stone-500">
              Escrow payouts are settled automatically to this bank account upon your withdrawal requests.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Bank Name
                </label>
                <input
                  type="text"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  required
                  className="w-full text-sm rounded-xl border border-stone-300 p-3"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  Account Number
                </label>
                <input
                  type="text"
                  value={accountNumber}
                  onChange={(e) => setAccountNumber(e.target.value)}
                  required
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                  IFSC Code
                </label>
                <input
                  type="text"
                  value={ifsc}
                  onChange={(e) => setIfsc(e.target.value)}
                  required
                  className="w-full text-sm rounded-xl border border-stone-300 p-3 font-mono"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="px-6 py-2.5 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold transition shadow-sm"
            >
              Save Workshop Profile
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
