"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronRight, Wallet } from "lucide-react";
import { inr, km, minutes } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Notice, Panel, Stat, cx } from "@/components/ui";
import { api } from "@/lib/api";

type Range = "today" | "week" | "month";

interface Earnings {
  range: Range;
  trips: number;
  earnings: number;
  cash_collected: number;
  distance_km: number;
  minutes_driving: number;
  cancelled_by_me: number;
  five_star_ratings: number;
  series: { day: string; earnings: number; trips: number }[];
}

const RANGES: { id: Range; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "week", label: "7 days" },
  { id: "month", label: "30 days" },
];

export default function EarningsPage() {
  const [range, setRange] = useState<Range>("week");
  const [data, setData] = useState<Earnings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setData(null);
    setError(null);
    api.get<Earnings>(`/driver/earnings?range=${range}`)
      .then((r) => live && setData(r))
      .catch(() => live && setError("Couldn't load your earnings."));
    return () => {
      live = false;
    };
  }, [range]);

  const perHour = data && data.minutes_driving > 0 ? data.earnings / (data.minutes_driving / 60) : 0;

  return (
    <Shell title="Earnings">
      <div className="grid gap-4">
        <div role="tablist" aria-label="Period" className="grid grid-cols-3 gap-1 rounded-2xl bg-surface p-1">
          {RANGES.map((r) => (
            <button key={r.id} role="tab" aria-selected={range === r.id} onClick={() => setRange(r.id)} className={cx("h-10 rounded-xl text-sm font-bold transition", range === r.id ? "bg-raised text-fg" : "text-fg-muted")}>{r.label}</button>
          ))}
        </div>

        {error ? <Notice>{error}</Notice> : null}

        <Panel className="p-5">
          <p className="text-sm font-semibold text-fg-muted">You earned</p>
          <p className="mt-1 text-4xl font-extrabold tabular-nums text-go">{data ? inr(data.earnings) : "—"}</p>
          <p className="mt-1 text-sm text-fg-muted">{data ? `${data.trips} trip${data.trips === 1 ? "" : "s"} · ${km(data.distance_km)} · ${minutes(data.minutes_driving)} driving` : "Loading…"}</p>
          {data && data.series.length > 1 ? <BarChart series={data.series} /> : null}
        </Panel>

        <div className="grid grid-cols-2 gap-3">
          <Stat label="Per hour driving" value={data ? inr(Math.round(perHour)) : "—"} />
          <Stat label="Cash collected" value={data ? inr(data.cash_collected) : "—"} sub="Already in your pocket" />
          <Stat label="5-star ratings" value={data ? data.five_star_ratings : "—"} />
          <Stat label="You cancelled" value={data ? data.cancelled_by_me : "—"} sub={data && data.cancelled_by_me > 2 ? "Try to keep this low" : undefined} />
        </div>

        <Link href="/wallet" className="flex items-center gap-3 rounded-[var(--radius-card)] border border-line/60 bg-surface p-4">
          <span className="grid size-11 place-items-center rounded-2xl bg-go-soft text-go"><Wallet className="size-5" aria-hidden="true" /></span>
          <span className="flex-1">
            <span className="block font-bold">Wallet & payouts</span>
            <span className="block text-sm text-fg-muted">Online fares land here. Withdraw to your bank any day.</span>
          </span>
          <ChevronRight className="size-5 text-fg-muted" aria-hidden="true" />
        </Link>
        <p className="px-1 text-xs text-fg-muted">Earnings are shown after RideNow's commission. Cash trips: you keep the cash and the commission is taken from your wallet.</p>
      </div>
    </Shell>
  );
}

/** Earnings per day as bars. Plain SVG so it works offline and themes with CSS variables. */
function BarChart({ series }: { series: Earnings["series"] }) {
  const max = Math.max(1, ...series.map((s) => s.earnings));
  const width = 320;
  const height = 120;
  const gap = series.length > 14 ? 2 : 6;
  const bar = (width - gap * (series.length - 1)) / series.length;
  const best = series.reduce((a, b) => (b.earnings > a.earnings ? b : a), series[0]);
  const label = (day: string) => new Date(`${day}T00:00:00`).toLocaleDateString("en-IN", series.length > 7 ? { day: "numeric" } : { weekday: "short" });

  return (
    <figure className="mt-5">
      <svg viewBox={`0 0 ${width} ${height + 18}`} className="w-full" role="img" aria-label={`Daily earnings. Best day ${label(best.day)} with ${inr(best.earnings)}.`}>
        {series.map((s, i) => {
          const h = Math.max(3, (s.earnings / max) * height);
          const x = i * (bar + gap);
          return (
            <g key={s.day}>
              <rect x={x} y={height - h} width={bar} height={h} rx={Math.min(6, bar / 2)} className={s.day === best.day ? "fill-go" : "fill-go/35"}>
                <title>{`${label(s.day)}: ${inr(s.earnings)} · ${s.trips} trips`}</title>
              </rect>
              {series.length <= 7 || i % 5 === 0 ? (
                <text x={x + bar / 2} y={height + 14} textAnchor="middle" className="fill-fg-muted text-[9px] font-semibold">{label(s.day)}</text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <figcaption className="sr-only">Earnings for each day in the selected period.</figcaption>
    </figure>
  );
}
