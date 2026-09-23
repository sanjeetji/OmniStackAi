"use client";

import { useMemo, useState } from "react";
import { Star, Trash2 } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote, Stat } from "../../components/ui";
import { useApi, useAction } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, day, percent } from "../../lib/format";

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${rating} out of 5`}>
      {[1, 2, 3, 4, 5].map((value) => (
        <Star key={value} size={12} className={value <= rating ? "fill-amber-400 text-amber-400" : "text-slate-600"} />
      ))}
    </span>
  );
}

export default function ReviewModeration() {
  const { pulse, notify } = useSession();
  const [filter, setFilter] = useState<number | "all" | "low">("all");
  const reviews = useApi(() => api.getAdminReviews(), [pulse]);
  const { run, busy, error } = useAction();

  const rows = reviews.data?.reviews ?? [];
  const shown = useMemo(() => {
    if (filter === "all") return rows;
    if (filter === "low") return rows.filter((review: any) => review.rating <= 2);
    return rows.filter((review: any) => review.rating === filter);
  }, [rows, filter]);

  const lowRated = rows.filter((review: any) => review.rating <= 2).length;
  const average = rows.length
    ? rows.reduce((sum: number, review: any) => sum + review.rating, 0) / rows.length
    : 0;

  async function remove(id: string) {
    const ok = await run(() => api.deleteAdminReview(id));
    if (ok) {
      notify({ title: "Review removed", detail: "It no longer appears on the storefront", tone: "alert" });
      reviews.refresh();
    }
  }

  return (
    <Shell title="Reviews" subtitle="What shoppers said, and what an operator may take down">
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Reviews" value={count(rows.length)} icon={<Star size={15} />} />
        <Stat label="Average" value={rows.length ? average.toFixed(2) : "—"} tone="good" />
        <Stat
          label="One or two stars"
          value={count(lowRated)}
          tone={lowRated > 0 ? "alert" : "plain"}
          hint={`${percent(lowRated, rows.length)} of all reviews`}
        />
      </div>

      <Panel
        className="mt-3"
        padded={false}
        title="Moderation queue"
        subtitle="Removing a review is recorded in the audit trail"
        actions={
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: "all" as const, label: "All" },
              { id: "low" as const, label: "1–2 stars" },
              { id: 5 as const, label: "5" },
              { id: 4 as const, label: "4" },
              { id: 3 as const, label: "3" },
            ].map((option) => (
              <button
                key={String(option.id)}
                onClick={() => setFilter(option.id)}
                className={
                  filter === option.id
                    ? "rounded-lg bg-[var(--accent)] px-2.5 py-1 text-[12px] font-semibold text-slate-950"
                    : "rounded-lg border border-[var(--surface-border)] bg-[var(--surface-elevated)] px-2.5 py-1 text-[12px] font-medium text-[var(--muted-light)] hover:bg-slate-700"
                }
              >
                {option.label}
              </button>
            ))}
          </div>
        }
      >
        <DataState state={reviews}>
          {() =>
            shown.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                {rows.length === 0 ? "No review yet." : "No review with that rating."}
              </p>
            ) : (
              <ul className="divide-y divide-[var(--surface-border)]">
                {shown.map((review: any) => (
                  <li key={review.id} className="px-4 py-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <Stars rating={review.rating} />
                          <span className="text-[12.5px] font-medium text-slate-200">
                            {review.shopper_name ?? "Shopper"}
                          </span>
                          {review.is_verified_purchase && <Badge tone="good">Verified purchase</Badge>}
                        </div>
                        <p className="text-[11.5px] text-[var(--muted)]">
                          on {review.product_title ?? review.shop_name ?? "a listing"} · {day(review.created_at)}
                        </p>
                      </div>
                      <Button size="sm" variant="quiet" disabled={busy} onClick={() => void remove(review.id)}>
                        <Trash2 size={13} /> Remove
                      </Button>
                    </div>
                    {review.title && (
                      <p className="mt-1.5 text-[13px] font-semibold text-slate-100">{review.title}</p>
                    )}
                    {review.body && (
                      <p className="mt-0.5 text-[12.5px] leading-relaxed text-[var(--muted-light)]">{review.body}</p>
                    )}
                    {review.vendor_reply && (
                      <p className="mt-2 rounded-lg border-l-2 border-[var(--accent)] bg-[var(--background)] px-2.5 py-1.5 text-[12px] text-[var(--muted-light)]">
                        <span className="font-semibold text-slate-300">Workshop replied: </span>
                        {review.vendor_reply}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )
          }
        </DataState>
      </Panel>
    </Shell>
  );
}
