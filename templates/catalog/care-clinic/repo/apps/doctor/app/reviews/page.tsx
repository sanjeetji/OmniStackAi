"use client";

import { useMemo, useState } from "react";
import { Star } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Badge, DataState, Stat } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { count, day, percent } from "../../lib/format";

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${rating} out of 5`}>
      {[1, 2, 3, 4, 5].map((value) => (
        <Star
          key={value}
          size={13}
          className={value <= rating ? "fill-amber-400 text-amber-400" : "text-slate-300"}
        />
      ))}
    </span>
  );
}

export default function Reviews() {
  const [filter, setFilter] = useState<number | "all">("all");
  const reviews = useApi(() => defaultApiClient.getDoctorReviews(), []);

  const rows = reviews.data?.reviews ?? [];
  const shown = useMemo(
    () => (filter === "all" ? rows : rows.filter((review) => review.rating === filter)),
    [rows, filter]
  );

  const average = rows.length > 0 ? rows.reduce((sum, r) => sum + r.rating, 0) / rows.length : 0;
  const distribution = [5, 4, 3, 2, 1].map((rating) => ({
    rating,
    n: rows.filter((review) => review.rating === rating).length,
  }));

  return (
    <Shell title="Reviews" subtitle="What your patients said after their visit">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat
          label="Average"
          value={rows.length > 0 ? average.toFixed(2) : "—"}
          tone="good"
          hint={`${count(rows.length)} review${rows.length === 1 ? "" : "s"}`}
          icon={<Star size={15} />}
        />
        <Stat
          label="Four or five stars"
          value={percent(rows.filter((r) => r.rating >= 4).length, rows.length)}
          hint="Of reviews left"
        />
        <Stat
          label="Left anonymously"
          value={count(rows.filter((r) => r.is_anonymous).length)}
          hint="The name is hidden from you"
        />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1.8fr]">
        <Panel title="How they rate" subtitle="Across every review">
          <ul className="space-y-2">
            {distribution.map((bucket) => (
              <li key={bucket.rating}>
                <button
                  onClick={() => setFilter(filter === bucket.rating ? "all" : bucket.rating)}
                  className="w-full text-left"
                >
                  <div className="flex items-baseline justify-between gap-2 text-[12.5px]">
                    <span className="flex items-center gap-1.5">
                      <Stars rating={bucket.rating} />
                    </span>
                    <span className="tabular text-[var(--color-ink-muted)]">
                      {bucket.n} · {percent(bucket.n, rows.length)}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-amber-400"
                      style={{ width: `${rows.length ? Math.max((bucket.n / rows.length) * 100, 2) : 0}%` }}
                    />
                  </div>
                </button>
              </li>
            ))}
          </ul>
          {filter !== "all" && (
            <button
              onClick={() => setFilter("all")}
              className="mt-3 text-[12px] font-semibold text-[var(--color-emerald-brand)] hover:underline"
            >
              Show every review
            </button>
          )}
        </Panel>

        <Panel
          title={filter === "all" ? "Every review" : `${filter}-star reviews`}
          subtitle={`${shown.length} shown`}
          padded={false}
        >
          <DataState state={reviews}>
            {() =>
              shown.length === 0 ? (
                <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                  {rows.length === 0
                    ? "No patient has left a review yet."
                    : "No review with that rating."}
                </p>
              ) : (
                <ul className="divide-y divide-[var(--color-border)]">
                  {shown.map((review) => (
                    <li key={review.id} className="px-4 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Stars rating={review.rating} />
                          <span className="text-[12.5px] font-medium text-[var(--color-ink)]">
                            {review.is_anonymous ? "Anonymous patient" : review.patient_name}
                          </span>
                          {review.is_anonymous && <Badge>Anonymous</Badge>}
                        </div>
                        <span className="tabular text-[11.5px] text-[var(--color-ink-subtle)]">
                          {day(String(review.created_at))}
                        </span>
                      </div>
                      <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--color-ink)]">{review.feedback}</p>
                    </li>
                  ))}
                </ul>
              )
            }
          </DataState>
        </Panel>
      </div>
    </Shell>
  );
}
