"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Star } from "lucide-react";
import { relativeTime } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Empty, Loading, Notice, Panel, Stars, Tag } from "@/components/ui";
import { api } from "@/lib/api";

interface Ratings {
  average: number;
  count: number;
  breakdown: { stars: number; count: number }[];
  top_tags: { tag: string; count: number }[];
  recent: { stars: number; tags: string[]; comment: string; created_at: string; code: string }[];
}

/** Coaching for the tags riders pick on a low rating (see the rider app's rate screen). */
const TIPS: Record<string, string> = {
  "Late pickup": "Head to pickup as soon as you accept. Riders watch your car move live.",
  "Rash driving": "Stay within speed limits and brake early. Safety reports are reviewed by our team.",
  "Took a longer route": "Follow the suggested route unless the rider asks otherwise.",
  "AC not working": "Get the AC checked. Riders on Mini, Sedan and XL expect it.",
  "Unprofessional": "Greet the rider, confirm the drop and keep calls short while driving.",
};

export default function RatingsPage() {
  const [data, setData] = useState<Ratings | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<Ratings>("/driver/ratings").then(setData).catch(() => setError("Couldn't load your ratings."));
  }, []);

  const negative = data?.top_tags.filter((t) => TIPS[t.tag]) ?? [];

  return (
    <Shell title="Ratings">
      <Link href="/account" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-fg-muted hover:text-fg"><ArrowLeft className="size-4" aria-hidden="true" /> Account</Link>
      {error ? <Notice>{error}</Notice> : !data ? <Loading label="Loading ratings" /> : (
        <div className="grid gap-4">
          <Panel className="grid grid-cols-[auto_1fr] items-center gap-5 p-5">
            <div className="text-center">
              <p className="text-5xl font-extrabold tabular-nums">{data.average.toFixed(2)}</p>
              <Stars value={data.average} size={16} />
              <p className="mt-1 text-xs text-fg-muted">{data.count} ratings</p>
            </div>
            <ul className="grid gap-1.5" aria-label="Ratings by stars">
              {data.breakdown.map((b) => {
                const share = data.count > 0 ? (b.count / data.count) * 100 : 0;
                return (
                  <li key={b.stars} className="flex items-center gap-2 text-xs">
                    <span className="w-3 font-bold">{b.stars}</span>
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-raised">
                      <span className="block h-full rounded-full bg-warn" style={{ width: `${share}%` }} />
                    </span>
                    <span className="w-8 text-right tabular-nums text-fg-muted">{b.count}</span>
                  </li>
                );
              })}
            </ul>
          </Panel>

          {data.top_tags.length > 0 ? (
            <section>
              <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">What riders say</h2>
              <div className="flex flex-wrap gap-2">
                {data.top_tags.map((t) => <Tag key={t.tag} tone={TIPS[t.tag] ? "warn" : "go"}>{t.tag} · {t.count}</Tag>)}
              </div>
            </section>
          ) : null}

          {negative.length > 0 ? (
            <Panel className="grid gap-2 p-4">
              <p className="font-bold">How to improve</p>
              {negative.map((t) => <p key={t.tag} className="text-sm text-fg-muted"><b className="text-fg">{t.tag}:</b> {TIPS[t.tag]}</p>)}
            </Panel>
          ) : null}

          <section>
            <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">Recent feedback</h2>
            {data.recent.length === 0 ? (
              <Panel><Empty icon={<Star className="size-6" />} title="No ratings yet" body="Riders rate you after each completed trip." /></Panel>
            ) : (
              <Panel className="divide-y divide-line/60">
                {data.recent.map((r, i) => (
                  <div key={`${r.code}-${i}`} className="grid gap-1 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <Stars value={r.stars} size={14} />
                      <span className="text-xs text-fg-muted">{r.code} · {relativeTime(r.created_at)}</span>
                    </div>
                    {r.tags.length ? <p className="text-sm">{r.tags.join(" · ")}</p> : null}
                    {r.comment ? <p className="text-sm text-fg-muted">“{r.comment}”</p> : null}
                  </div>
                ))}
              </Panel>
            )}
          </section>
        </div>
      )}
    </Shell>
  );
}
