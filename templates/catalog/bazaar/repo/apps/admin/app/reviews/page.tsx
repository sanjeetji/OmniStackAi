"use client";

import { useState } from "react";
import { AdminHeader } from "@/components/admin-header";
import {
  Star,
  ShieldCheck,
  Search,
  Filter,
  Trash2,
  EyeOff,
  CheckCircle2,
  Store,
  MessageSquare,
} from "lucide-react";
import { formatDate } from "@bazaar/shared";

interface ReviewItem {
  id: string;
  productName: string;
  shopName: string;
  customerName: string;
  rating: number;
  comment: string;
  verifiedPurchase: boolean;
  vendorReply?: string;
  createdAt: string;
  flagged: boolean;
}

export default function AdminReviewsPage() {
  const [search, setSearch] = useState("");
  const [reviews, setReviews] = useState<ReviewItem[]>([
    {
      id: "rev-01",
      productName: "Royal Mughal Cobalt Floral Vase (12\")",
      shopName: "Jaipur Blue Art Pottery",
      customerName: "Priya Sharma",
      rating: 5,
      comment:
        "The hand-painted quartz glaze is breathtaking. The cobalt and turquoise pigments are vivid and the double packing ensured it arrived in Bengaluru without a scratch.",
      verifiedPurchase: true,
      vendorReply:
        "Dhanyawad Priya Ji! Honored that our Bani Park studio vase found a home in your living room.",
      createdAt: "2026-09-21T14:30:00Z",
      flagged: false,
    },
    {
      id: "rev-02",
      productName: "Traditional Floral Tile Coasters (Set of 6)",
      shopName: "Jaipur Blue Art Pottery",
      customerName: "Arjun Mehta",
      rating: 5,
      comment:
        "Authentic craft. You can see the subtle artisan brush strokes. Worth every rupee compared to machine-made tiles.",
      verifiedPurchase: true,
      createdAt: "2026-09-20T11:15:00Z",
      flagged: false,
    },
    {
      id: "rev-03",
      productName: "Pure Katan Silk Banarasi Saree",
      shopName: "Varanasi Heritage Weaves",
      customerName: "Ananya Deshmukh",
      rating: 5,
      comment:
        "True heirloom piece. The zari gold border is so supple and genuine. The GI accreditation certificate was included in the box.",
      verifiedPurchase: true,
      vendorReply:
        "Pranam Ananya Ji! Our Ansari family looms take over 22 days per saree. Wear it in health!",
      createdAt: "2026-09-19T09:40:00Z",
      flagged: false,
    },
    {
      id: "rev-04",
      productName: "Dhokra Lost-Wax Bell Metal Nandi Bull",
      shopName: "Bastar Tribal Bell Metal",
      customerName: "Rajesh Kannan",
      rating: 4,
      comment:
        "Impressive tribal sculpture. Slightly smaller than envisioned but the primitive wax casting texture is 100% authentic.",
      verifiedPurchase: true,
      createdAt: "2026-09-18T16:20:00Z",
      flagged: false,
    },
  ]);

  const toggleFlag = (id: string) => {
    setReviews((prev) =>
      prev.map((r) => (r.id === id ? { ...r, flagged: !r.flagged } : r))
    );
  };

  const deleteReview = (id: string) => {
    setReviews((prev) => prev.filter((r) => r.id !== id));
  };

  const filtered = reviews.filter(
    (r) =>
      r.productName.toLowerCase().includes(search.toLowerCase()) ||
      r.shopName.toLowerCase().includes(search.toLowerCase()) ||
      r.customerName.toLowerCase().includes(search.toLowerCase()) ||
      r.comment.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Review Moderation"
        subtitle="Audit verified patron ratings, craft testimonials, and artisan workshop replies across all products."
        badge="Quality Moderation"
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Rating Overview Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="text-3xl font-extrabold font-mono text-white flex items-center gap-2">
              4.9 <Star className="w-6 h-6 fill-amber-400 text-amber-400" />
            </div>
            <div>
              <div className="text-xs font-bold text-white">Marketplace Quality Average</div>
              <p className="text-xs text-slate-400">
                100% Verified Purchase Reviews across 8 artisan workshops
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="text-slate-400">
              <span className="text-white font-bold font-mono">142</span> Total Reviews
            </div>
            <span className="text-slate-700">•</span>
            <div className="text-slate-400">
              <span className="text-emerald-400 font-bold font-mono">98.4%</span> Positive (4 &amp; 5 Stars)
            </div>
            <span className="text-slate-700">•</span>
            <div className="text-slate-400">
              <span className="text-amber-400 font-bold font-mono">0</span> Flagged for Policy
            </div>
          </div>
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search reviews by product name, artisan workshop, customer, or content..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
          />
        </div>

        {/* Reviews List */}
        <div className="space-y-4">
          {filtered.map((rev) => (
            <div
              key={rev.id}
              className={`bg-slate-900 border rounded-xl p-5 space-y-3 transition ${
                rev.flagged ? "border-rose-500/40 bg-rose-950/10" : "border-slate-800"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-xs">{rev.productName}</span>
                    <span className="text-slate-500">•</span>
                    <span className="text-xs text-amber-400 flex items-center gap-1">
                      <Store className="w-3 h-3" /> {rev.shopName}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                    <span>By {rev.customerName}</span>
                    <span>•</span>
                    <span className="font-mono">{formatDate(rev.createdAt)}</span>
                    {rev.verifiedPurchase && (
                      <span className="text-emerald-400 font-medium inline-flex items-center gap-1 text-[10px]">
                        <CheckCircle2 className="w-3 h-3" /> Verified Purchase
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* Star Rating */}
                  <div className="flex items-center gap-0.5 text-amber-400">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star
                        key={i}
                        className={`w-3.5 h-3.5 ${
                          i < rev.rating
                            ? "fill-amber-400 text-amber-400"
                            : "text-slate-700"
                        }`}
                      />
                    ))}
                  </div>

                  {/* Actions */}
                  <button
                    type="button"
                    onClick={() => toggleFlag(rev.id)}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition cursor-pointer flex items-center gap-1 ${
                      rev.flagged
                        ? "bg-rose-500/20 text-rose-300 hover:bg-rose-500/30"
                        : "bg-slate-800 hover:bg-slate-700 text-slate-300"
                    }`}
                  >
                    <EyeOff className="w-3 h-3" />
                    {rev.flagged ? "Unflag" : "Flag"}
                  </button>

                  <button
                    type="button"
                    onClick={() => deleteReview(rev.id)}
                    className="p-1 rounded text-slate-500 hover:text-rose-400 transition cursor-pointer"
                    title="Delete review"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Review Text */}
              <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                "{rev.comment}"
              </p>

              {/* Vendor Reply */}
              {rev.vendorReply && (
                <div className="ml-4 pl-3 border-l-2 border-amber-500/50 text-xs space-y-1">
                  <div className="text-[11px] font-semibold text-amber-400 flex items-center gap-1.5">
                    <MessageSquare className="w-3 h-3" />
                    Artisan Workshop Direct Reply
                  </div>
                  <p className="text-slate-300 text-[11px]">
                    "{rev.vendorReply}"
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
