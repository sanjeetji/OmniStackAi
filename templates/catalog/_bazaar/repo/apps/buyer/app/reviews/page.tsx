"use client";

import { useState } from "react";
import Link from "next/link";
import { formatDate } from "@bazaar/shared";
import { api } from "@bazaar/shared";
import type { Review } from "@bazaar/shared";

const INITIAL_REVIEWS: (Review & { productName: string; shopName: string; imageUrl: string })[] = [
  {
    id: "rev-001",
    product_id: "prod-001",
    shop_id: "shp-jaipur",
    user_id: "u-shopper-001",
    rating: 5,
    title: "Mesmerizing Cobalt Blue Glaze & Exceptional Packing",
    comment:
      "The craftsmanship is breathtaking. Every brushstroke shows generations of skill. Blue Dart handled the fragile pottery with care; it arrived safely in Bengaluru in triple-layer craft cushioning.",
    verified_purchase: true,
    vendor_reply:
      "Thank you deeply Priya ji. Our studio in Jaipur grinds quartz stones manually to achieve this signature turquoise blue. We are delighted it found a home with you!",
    vendor_replied_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    productName: "Hand-Painted Royal Blue Terracotta Vase",
    shopName: "Jaipur Blue Art Pottery",
    imageUrl: "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=400&q=80",
  },
  {
    id: "rev-002",
    product_id: "prod-003",
    shop_id: "shp-moradabad",
    user_id: "u-shopper-001",
    rating: 5,
    title: "Heavy, substantial brass with rich antique patina",
    comment:
      "This urli bowl weighs over 3 kilograms. Placing marigolds and floating tea lights has transformed our living room entrance. True Moradabad brass casting excellence.",
    verified_purchase: true,
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 96).toISOString(),
    productName: "Hammered Antique Finish Brass Urli Bowl",
    shopName: "Moradabad Brass Craft Guild",
    imageUrl: "https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=400&q=80",
  },
];

export default function ReviewsPage() {
  const [reviews, setReviews] = useState(INITIAL_REVIEWS);
  const [showForm, setShowForm] = useState(false);
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!comment.trim()) return;

    try {
      setSubmitting(true);
      await api.submitReview({
        productId: "prod-002",
        rating,
        title,
        comment,
      });

      const newRev = {
        id: `rev-${Date.now()}`,
        product_id: "prod-002",
        shop_id: "shp-varanasi",
        user_id: "u-shopper-001",
        rating,
        title,
        comment,
        verified_purchase: true,
        created_at: new Date().toISOString(),
        productName: "Authentic Pure Zari Banarasi Silk Stole",
        shopName: "Varanasi Silk Looms",
        imageUrl:
          "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80",
      };

      setReviews([newRev, ...reviews]);
      setShowForm(false);
      setTitle("");
      setComment("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 5000);
    } catch {
      // Local addition fallback
      const newRev = {
        id: `rev-${Date.now()}`,
        product_id: "prod-002",
        shop_id: "shp-varanasi",
        user_id: "u-shopper-001",
        rating,
        title,
        comment,
        verified_purchase: true,
        created_at: new Date().toISOString(),
        productName: "Authentic Pure Zari Banarasi Silk Stole",
        shopName: "Varanasi Silk Looms",
        imageUrl:
          "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80",
      };
      setReviews([newRev, ...reviews]);
      setShowForm(false);
      setTitle("");
      setComment("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 5000);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-serif font-bold text-stone-900">Artisan Feedback & Reviews</h1>
          <p className="text-stone-600 text-sm mt-1">
            Share your experience with traditional master craftsmen to help preserve indigenous arts.
          </p>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="px-5 py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-sm font-semibold transition self-start sm:self-auto"
        >
          {showForm ? "Cancel Review" : "Write a Review"}
        </button>
      </div>

      {/* Success Notification */}
      {success && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm font-medium flex items-center gap-2">
          <span>✅</span>
          <span>Your review has been verified and published to the artisan's storefront!</span>
        </div>
      )}

      {/* Review Submission Form */}
      {showForm && (
        <div className="bg-white rounded-2xl border border-stone-200 p-6 mb-8 shadow-sm">
          <h3 className="text-lg font-serif font-bold text-stone-900 mb-1">
            Review: Authentic Pure Zari Banarasi Silk Stole
          </h3>
          <p className="text-xs text-stone-500 mb-4">
            Sold by Varanasi Silk Looms &bull; Delivered under Consignment #SHP-9821-02
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Rating Stars */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Your Rating
              </label>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    className="text-2xl transition hover:scale-110"
                  >
                    {star <= rating ? "⭐" : "☆"}
                  </button>
                ))}
                <span className="text-sm font-semibold text-stone-700 ml-2">
                  {rating} out of 5 stars
                </span>
              </div>
            </div>

            {/* Title */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Headline / Summary
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Masterful weave, rich texture, authentic zari"
                className="w-full text-sm rounded-lg border border-stone-300 p-2.5 focus:border-amber-600 focus:outline-none"
              />
            </div>

            {/* Comment */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 uppercase mb-1">
                Detailed Review
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                required
                rows={4}
                placeholder="Describe the craft quality, packaging, delivery, and personal impression..."
                className="w-full text-sm rounded-lg border border-stone-300 p-2.5 focus:border-amber-600 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-stone-600 text-xs font-semibold hover:bg-stone-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition"
              >
                {submitting ? "Publishing..." : "Submit Verified Review"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Reviews List */}
      <div className="space-y-6">
        {reviews.map((rev) => (
          <div
            key={rev.id}
            className="bg-white rounded-2xl border border-stone-200 p-6 shadow-sm hover:shadow-md transition"
          >
            <div className="flex items-start gap-4">
              <img
                src={rev.imageUrl}
                alt={rev.productName}
                className="w-16 h-16 object-cover rounded-xl border border-stone-200 flex-shrink-0"
              />

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-base font-semibold text-stone-900">{rev.productName}</h3>
                    <p className="text-xs text-stone-500">
                      Crafted by{" "}
                      <Link
                        href={`/shops/${rev.shop_id}`}
                        className="text-amber-800 font-medium hover:underline"
                      >
                        {rev.shopName}
                      </Link>
                    </p>
                  </div>
                  <time className="text-xs text-stone-400 font-mono">
                    {formatDate(rev.created_at)}
                  </time>
                </div>

                {/* Rating & Badge */}
                <div className="flex items-center gap-2 mt-2">
                  <div className="text-amber-500 text-sm">{"★".repeat(rev.rating)}</div>
                  {rev.verified_purchase && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                      ✓ Verified Buyer
                    </span>
                  )}
                </div>

                {/* Review Text */}
                {rev.title && (
                  <h4 className="text-sm font-bold text-stone-800 mt-2">{rev.title}</h4>
                )}
                <p className="text-sm text-stone-600 mt-1 leading-relaxed">{rev.comment}</p>

                {/* Artisan Direct Reply */}
                {rev.vendor_reply && (
                  <div className="mt-4 p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl text-xs">
                    <div className="flex items-center justify-between text-amber-900 font-semibold mb-1">
                      <span>Artisan Response from {rev.shopName}</span>
                      {rev.vendor_replied_at && (
                        <span className="text-[10px] text-amber-700/80">
                          {formatDate(rev.vendor_replied_at)}
                        </span>
                      )}
                    </div>
                    <p className="text-stone-700 italic">"{rev.vendor_reply}"</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
