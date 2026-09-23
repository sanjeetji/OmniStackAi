"use client";

import { useState } from "react";
import { formatDate } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { MessageSquare, Star, Send, Check } from "lucide-react";

interface ReviewItem {
  id: string;
  customerName: string;
  productTitle: string;
  rating: number;
  title: string;
  comment: string;
  createdAt: string;
  vendorReply?: string | null;
}

const DEMO_REVIEWS: ReviewItem[] = [
  {
    id: "rev-001",
    customerName: "Priya Sharma",
    productTitle: "Hand-Painted Royal Blue Terracotta Vase",
    rating: 5,
    title: "Mesmerizing Cobalt Blue Glaze & Exceptional Packing",
    comment:
      "The craftsmanship is breathtaking. Every brushstroke shows generations of skill. Blue Dart handled the fragile pottery with care; it arrived safely in Bengaluru in triple-layer craft cushioning.",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    vendorReply:
      "Thank you deeply Priya ji. Our studio in Jaipur grinds quartz stones manually to achieve this signature turquoise blue. We are delighted it found a home with you!",
  },
  {
    id: "rev-002",
    customerName: "Ananya Iyer",
    productTitle: "Traditional Floral Jaipur Blue Glazed Plate",
    rating: 5,
    title: "A stunning centerpiece for Diwali festivities",
    comment:
      "The intricate Persian arabesque pattern is even more vivid in person. The glaze has that authentic soft sheen characteristic of true Jaipur pottery.",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
  },
  {
    id: "rev-003",
    customerName: "Rohan Deshmukh",
    productTitle: "Miniature Jaipur Pottery Coasters Set of 6",
    rating: 5,
    title: "Heavy, well made and functional art",
    comment:
      "Waterproof and durable. Guests constantly ask where we bought them. Excellent gift set.",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 120).toISOString(),
  },
];

export default function SellerReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>(DEMO_REVIEWS);
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  function handleSendReply(id: string) {
    if (!replyText.trim()) return;
    setReviews((prev) =>
      prev.map((r) => (r.id === id ? { ...r, vendorReply: replyText } : r))
    );
    setReplyingTo(null);
    setReplyText("");
    setSuccessNotice("Artisan response published directly to your storefront!");
    setTimeout(() => setSuccessNotice(null), 4000);
  }

  return (
    <div className="flex-1 pb-16">
      <SellerHeader
        title="Customer Reviews & Patron Feedback"
        description="Interact directly with verified patrons and share the heritage stories behind your crafts."
      />

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Rating Overview Banner */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-800 flex items-center justify-center text-3xl font-serif font-bold border border-amber-200/80">
              4.9
            </div>
            <div>
              <div className="flex items-center gap-1 text-amber-500">
                {"★".repeat(5)}
              </div>
              <h2 className="text-sm font-bold text-stone-900 mt-0.5">
                Outstanding Craft Heritage Rating
              </h2>
              <p className="text-xs text-stone-500">Based on 84 verified buyer purchases across India</p>
            </div>
          </div>

          <div className="text-xs text-stone-500 bg-stone-50 p-3 rounded-xl border border-stone-200/60 sm:text-right">
            <span>Response Rate: <strong className="text-emerald-700">98%</strong></span>
            <span className="block mt-0.5">Average Response Time: <strong className="text-stone-800">4 hours</strong></span>
          </div>
        </div>

        {/* Success Notice */}
        {successNotice && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center gap-2 shadow-2xs">
            <Check className="w-4 h-4 text-emerald-700" />
            <span>{successNotice}</span>
          </div>
        )}

        {/* Reviews List */}
        <div className="space-y-4">
          {reviews.map((rev) => (
            <div
              key={rev.id}
              className="bg-white p-6 rounded-2xl border border-stone-200/80 shadow-2xs space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
                <div>
                  <span className="font-bold text-stone-900 text-sm">{rev.customerName}</span>
                  <span className="text-xs text-stone-400 ml-2">
                    reviewed <strong className="text-stone-700">{rev.productTitle}</strong>
                  </span>
                </div>
                <time className="text-xs text-stone-400 font-mono">
                  {formatDate(rev.createdAt)}
                </time>
              </div>

              <div className="flex items-center gap-1 text-amber-500 text-xs">
                {"★".repeat(rev.rating)}
              </div>

              {rev.title && <h3 className="text-xs font-bold text-stone-800">{rev.title}</h3>}
              <p className="text-xs text-stone-600 leading-relaxed">{rev.comment}</p>

              {/* Vendor Reply */}
              {rev.vendorReply ? (
                <div className="mt-3 p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl text-xs">
                  <span className="font-bold text-amber-900 block mb-1">
                    Your Artisan Response (Jaipur Blue Pottery):
                  </span>
                  <p className="text-stone-700 italic">"{rev.vendorReply}"</p>
                </div>
              ) : replyingTo === rev.id ? (
                <div className="mt-3 p-4 bg-stone-50 rounded-xl border border-stone-200 space-y-3">
                  <label className="block text-xs font-semibold text-stone-700">
                    Write Artisan Response to {rev.customerName}:
                  </label>
                  <textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    rows={3}
                    placeholder="Thank the customer, explain the craft history, or offer maintenance tips..."
                    className="w-full text-xs rounded-lg border border-stone-300 p-2.5 bg-white focus:outline-none focus:border-amber-700"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setReplyingTo(null)}
                      className="px-3 py-1.5 rounded-lg border border-stone-300 text-stone-600 text-xs font-semibold hover:bg-stone-100"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleSendReply(rev.id)}
                      className="px-4 py-1.5 bg-amber-800 hover:bg-amber-900 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5"
                    >
                      <Send className="w-3 h-3" />
                      <span>Publish Reply</span>
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setReplyingTo(rev.id);
                    setReplyText("");
                  }}
                  className="mt-2 text-xs font-semibold text-amber-800 hover:text-amber-900 flex items-center gap-1.5"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Reply to Patron</span>
                </button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
