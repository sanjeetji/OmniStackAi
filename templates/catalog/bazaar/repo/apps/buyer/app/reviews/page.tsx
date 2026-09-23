"use client";

import { useState } from "react";
import Link from "next/link";
import { Star } from "lucide-react";
import { api } from "@bazaar/shared";
import { useApi, useAction } from "@/lib/use-api";
import { day } from "@/lib/format";

function Stars({ rating, onPick }: { rating: number; onPick?: (value: number) => void }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((value) => {
        const filled = value <= rating;
        const cls = filled ? "h-4 w-4 fill-amber-500 text-amber-500" : "h-4 w-4 text-stone-300";
        return onPick ? (
          <button key={value} type="button" onClick={() => onPick(value)} aria-label={`${value} star`}>
            <Star className={cls} />
          </button>
        ) : (
          <Star key={value} className={cls} />
        );
      })}
    </span>
  );
}

export default function MyReviews() {
  const reviews = useApi(() => api.getMyReviews(), []);
  const { run, busy, error } = useAction();
  const [writing, setWriting] = useState<string | null>(null);
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [comment, setComment] = useState("");

  const mine = reviews.data?.reviews ?? [];
  const awaiting = reviews.data?.awaitingReview ?? [];

  async function submit(productId: string) {
    const ok = await run(() =>
      api.submitReview({ productId, rating, title: title.trim() || undefined, comment: comment.trim() })
    );
    if (ok) {
      setWriting(null);
      setTitle("");
      setComment("");
      setRating(5);
      reviews.refresh();
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8">
        <h1 className="font-serif text-3xl font-bold text-stone-900">Your reviews</h1>
        <p className="mt-1 text-sm text-stone-600">
          Tell other shoppers what the craft was really like. Artisans read and reply to these.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {reviews.error && !reviews.data ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{reviews.error}</p>
      ) : !reviews.data ? (
        <p aria-busy="true" className="text-sm text-stone-500">Loading your reviews…</p>
      ) : (
        <>
          {awaiting.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
                Delivered, not yet reviewed
              </h2>
              <ul className="space-y-3">
                {awaiting.map((item: any) => (
                  <li key={item.product_id} className="rounded-2xl border border-stone-200 bg-white p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-stone-900">{item.product_title}</p>
                        <p className="text-xs text-stone-500">
                          {item.shop_name}
                          {item.delivered_at ? ` · delivered ${day(item.delivered_at)}` : ""}
                        </p>
                      </div>
                      {writing !== item.product_id && (
                        <button
                          onClick={() => setWriting(item.product_id)}
                          className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-800"
                        >
                          Write a review
                        </button>
                      )}
                    </div>

                    {writing === item.product_id && (
                      <div className="mt-4 space-y-3 border-t border-stone-100 pt-4">
                        <div className="flex items-center gap-3">
                          <span className="text-sm text-stone-600">Your rating</span>
                          <Stars rating={rating} onPick={setRating} />
                        </div>
                        <input
                          className="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:border-amber-600"
                          value={title}
                          onChange={(event) => setTitle(event.target.value)}
                          placeholder="Sum it up in a few words"
                        />
                        <textarea
                          className="min-h-24 w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:border-amber-600"
                          value={comment}
                          onChange={(event) => setComment(event.target.value)}
                          placeholder="How does it look and feel? Was it as described? Would you buy from this workshop again?"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => void submit(item.product_id)}
                            disabled={busy || !comment.trim()}
                            className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-800 disabled:opacity-50"
                          >
                            {busy ? "Posting" : "Post the review"}
                          </button>
                          <button
                            onClick={() => setWriting(null)}
                            className="rounded-xl border border-stone-200 px-4 py-2 text-sm font-semibold text-stone-600 hover:bg-stone-50"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
              {mine.length > 0 ? "What you have written" : "Your reviews"}
            </h2>
            {mine.length === 0 ? (
              <p className="rounded-2xl border border-stone-200 bg-white px-4 py-12 text-center text-sm text-stone-500">
                You have not reviewed anything yet.{" "}
                <Link href="/orders" className="font-semibold text-amber-700 hover:underline">
                  See your orders
                </Link>
                .
              </p>
            ) : (
              <ul className="space-y-3">
                {mine.map((review: any) => (
                  <li key={review.id} className="rounded-2xl border border-stone-200 bg-white p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-stone-900">{review.product_title}</p>
                        <p className="text-xs text-stone-500">
                          {review.shop_name} · {day(review.created_at)}
                        </p>
                      </div>
                      <Stars rating={review.rating} />
                    </div>
                    {review.title && <p className="mt-2 font-semibold text-stone-800">{review.title}</p>}
                    {review.comment && <p className="mt-1 text-sm leading-relaxed text-stone-600">{review.comment}</p>}
                    {review.vendor_reply && (
                      <div className="mt-3 rounded-xl border-l-2 border-amber-600 bg-stone-50 px-3 py-2">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
                          {review.shop_name} replied
                        </p>
                        <p className="mt-0.5 text-sm text-stone-700">{review.vendor_reply}</p>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
