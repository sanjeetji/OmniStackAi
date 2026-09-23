"use client";

import { useMemo, useState } from "react";
import { MessageSquare, Send, Star } from "lucide-react";
import { api } from "@bazaar/shared";
import { SellerHeader } from "@/components/seller-header";
import { useApi, useAction } from "@/lib/use-api";
import { day, percent } from "@/lib/format";

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${rating} out of 5`}>
      {[1, 2, 3, 4, 5].map((value) => (
        <Star key={value} className={value <= rating ? "h-3.5 w-3.5 fill-amber-400 text-amber-400" : "h-3.5 w-3.5 text-slate-600"} />
      ))}
    </span>
  );
}

export default function Reviews() {
  const reviews = useApi(() => api.getVendorReviews(), []);
  const { run, busy, error } = useAction();
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [reply, setReply] = useState("");

  const rows = reviews.data?.reviews ?? [];
  const unanswered = useMemo(() => rows.filter((r: any) => !r.vendor_reply), [rows]);
  const average = rows.length ? rows.reduce((sum: number, r: any) => sum + r.rating, 0) / rows.length : 0;

  async function send(reviewId: string) {
    const ok = await run(() => api.replyToReview(reviewId, reply.trim()));
    if (ok) {
      setReplyTo(null);
      setReply("");
      reviews.refresh();
    }
  }

  return (
    <>
      <SellerHeader title="Reviews" description="What shoppers said about your craft, and your replies" />

      <div className="p-6">
        {error && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
            {error}
          </div>
        )}

        <div className="mb-5 grid gap-4 sm:grid-cols-3">
          {[
            { label: "Reviews", value: rows.length, tone: "text-slate-100" },
            { label: "Average", value: rows.length ? average.toFixed(2) : "—", tone: "text-amber-400" },
            { label: "Awaiting a reply", value: unanswered.length, tone: unanswered.length ? "text-rose-400" : "text-emerald-400" },
          ].map((tile) => (
            <div key={tile.label} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{tile.label}</p>
              <p className={`mt-1 text-2xl font-bold ${tile.tone}`}>{tile.value}</p>
            </div>
          ))}
        </div>

        {reviews.error && !reviews.data ? (
          <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            {reviews.error}
          </p>
        ) : !reviews.data ? (
          <p aria-busy="true" className="text-sm text-slate-400">Loading your reviews…</p>
        ) : rows.length === 0 ? (
          <p className="rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-12 text-center text-sm text-slate-400">
            No shopper has reviewed your work yet.
          </p>
        ) : (
          <ul className="space-y-3">
            {rows.map((review: any) => (
              <li key={review.id} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Stars rating={review.rating} />
                      <span className="text-sm font-semibold text-slate-200">{review.shopper_name ?? "Shopper"}</span>
                      {review.verified_purchase && (
                        <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 ring-1 ring-inset ring-emerald-500/30">
                          Verified purchase
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500">
                      on {review.product_title ?? "a listing"} · {day(review.created_at)}
                    </p>
                  </div>
                  {!review.vendor_reply && replyTo !== review.id && (
                    <button
                      onClick={() => {
                        setReplyTo(review.id);
                        setReply("");
                      }}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-slate-800"
                    >
                      <MessageSquare className="h-3.5 w-3.5" /> Reply
                    </button>
                  )}
                </div>

                {review.title && <p className="mt-2 text-sm font-bold text-slate-100">{review.title}</p>}
                {review.comment && <p className="mt-1 text-sm leading-relaxed text-slate-400">{review.comment}</p>}

                {review.vendor_reply && (
                  <div className="mt-3 rounded-xl border-l-2 border-amber-500 bg-slate-950/60 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">You replied</p>
                    <p className="mt-0.5 text-sm text-slate-300">{review.vendor_reply}</p>
                    {review.vendor_replied_at && (
                      <p className="mt-0.5 text-[11px] text-slate-500">{day(review.vendor_replied_at)}</p>
                    )}
                  </div>
                )}

                {replyTo === review.id && (
                  <div className="mt-3 space-y-2">
                    <textarea
                      className="min-h-20 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
                      value={reply}
                      onChange={(event) => setReply(event.target.value)}
                      placeholder="Thank them, or explain what you will do about it. Shoppers see this on the listing."
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => void send(review.id)}
                        disabled={busy || !reply.trim()}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50"
                      >
                        <Send className="h-3.5 w-3.5" /> Post the reply
                      </button>
                      <button
                        onClick={() => setReplyTo(null)}
                        className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
