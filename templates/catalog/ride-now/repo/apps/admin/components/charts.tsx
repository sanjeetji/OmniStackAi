"use client";

import { useState } from "react";
import { cx } from "./ui";

/** A short day label ("12 Sep") from "YYYY-MM-DD", without time-zone shifts. */
export function dayLabel(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y!, m! - 1, d!)).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "UTC" });
}

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const exponent = 10 ** Math.floor(Math.log10(value));
  const fraction = value / exponent;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10;
  return nice * exponent;
}

export interface Series {
  name: string;
  color: string;
  values: number[];
}

/**
 * Daily bars (first series) with optional lines (other series, on their own scale). Hovering or
 * focusing a day shows every value for it. The table fallback keeps the numbers accessible.
 */
export function DailyChart({ labels, bars, lines = [], format, lineFormat, height = 220, caption }: {
  labels: string[];
  bars: Series;
  lines?: Series[];
  format: (value: number) => string;
  lineFormat?: (value: number) => string;
  height?: number;
  caption: string;
}) {
  const [active, setActive] = useState<number | null>(null);
  const W = 720;
  const H = height;
  const pad = { l: 44, r: lines.length ? 56 : 12, t: 12, b: 26 };
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const n = labels.length;
  const barMax = niceMax(Math.max(...bars.values, 0));
  const lineMax = niceMax(Math.max(0, ...lines.flatMap((s) => s.values)));
  const step = innerW / Math.max(1, n);
  const barW = Math.min(28, step * 0.62);
  const x = (i: number) => pad.l + step * i + step / 2;
  const yBar = (v: number) => pad.t + innerH - (v / barMax) * innerH;
  const yLine = (v: number) => pad.t + innerH - (v / lineMax) * innerH;
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const fmtLine = lineFormat ?? format;

  return (
    <figure className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={caption}>
        {ticks.map((t) => {
          const y = pad.t + innerH - t * innerH;
          return (
            <g key={t}>
              <line x1={pad.l} x2={W - pad.r} y1={y} y2={y} stroke="var(--color-line)" strokeDasharray={t === 0 ? undefined : "3 4"} />
              <text x={pad.l - 8} y={y + 4} textAnchor="end" fontSize="11" fill="var(--color-muted)" className="num">
                {format(barMax * t)}
              </text>
              {lines.length ? (
                <text x={W - pad.r + 8} y={y + 4} fontSize="11" fill="var(--color-muted)" className="num">
                  {fmtLine(lineMax * t)}
                </text>
              ) : null}
            </g>
          );
        })}
        {bars.values.map((v, i) => (
          <rect key={i} x={x(i) - barW / 2} y={yBar(v)} width={barW} height={Math.max(0, pad.t + innerH - yBar(v))} rx={3} fill={bars.color} opacity={active === null || active === i ? 1 : 0.45} />
        ))}
        {lines.map((s) => (
          <g key={s.name}>
            <polyline fill="none" stroke={s.color} strokeWidth={2.2} strokeLinejoin="round" strokeLinecap="round" points={s.values.map((v, i) => `${x(i)},${yLine(v)}`).join(" ")} />
            {s.values.map((v, i) => (
              <circle key={i} cx={x(i)} cy={yLine(v)} r={active === i ? 4 : 2.5} fill="#fff" stroke={s.color} strokeWidth={2} />
            ))}
          </g>
        ))}
        {labels.map((label, i) =>
          i % Math.ceil(n / 7) === 0 || i === n - 1 ? (
            <text key={label} x={x(i)} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--color-muted)">
              {dayLabel(label)}
            </text>
          ) : null,
        )}
        {labels.map((label, i) => (
          <rect
            key={`hit-${label}`}
            x={pad.l + step * i}
            y={pad.t}
            width={step}
            height={innerH}
            fill="transparent"
            tabIndex={0}
            aria-label={`${dayLabel(label)}: ${bars.name} ${format(bars.values[i] ?? 0)}${lines.map((s) => `, ${s.name} ${fmtLine(s.values[i] ?? 0)}`).join("")}`}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
            onFocus={() => setActive(i)}
            onBlur={() => setActive(null)}
            style={{ outline: "none" }}
          />
        ))}
      </svg>
      {active !== null ? (
        <div
          className="pointer-events-none absolute top-2 rounded-md border border-line bg-panel px-3 py-2 text-xs shadow-pop"
          style={{ left: `${Math.min(78, Math.max(4, (x(active) / W) * 100 - 8))}%` }}
        >
          <p className="font-semibold text-ink">{dayLabel(labels[active]!)}</p>
          <p className="num mt-1 flex items-center gap-1.5 text-ink-2">
            <span className="size-2 rounded-sm" style={{ background: bars.color }} />
            {bars.name}: {format(bars.values[active] ?? 0)}
          </p>
          {lines.map((s) => (
            <p key={s.name} className="num flex items-center gap-1.5 text-ink-2">
              <span className="size-2 rounded-full" style={{ background: s.color }} />
              {s.name}: {fmtLine(s.values[active] ?? 0)}
            </p>
          ))}
        </div>
      ) : null}
      <figcaption className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: bars.color }} />
          {bars.name}
        </span>
        {lines.map((s) => (
          <span key={s.name} className="inline-flex items-center gap-1.5">
            <span className="h-0.5 w-3 rounded" style={{ background: s.color }} />
            {s.name} (right axis)
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

/** Horizontal share bars, e.g. trips per vehicle type. */
export function ShareBars({ items, format, className }: { items: { id: string; label: string; value: number; sub?: string }[]; format: (value: number) => string; className?: string }) {
  const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <ul className={cx("grid gap-3", className)}>
      {items.map((item) => (
        <li key={item.id}>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-[13px]">
            <span className="font-medium text-ink">{item.label}</span>
            <span className="num text-muted">
              {format(item.value)} · {Math.round((item.value / total) * 100)}%
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-ink/6" aria-hidden="true">
            <div className="h-full rounded-full bg-signal" style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
          {item.sub ? <p className="num mt-1 text-xs text-muted">{item.sub}</p> : null}
        </li>
      ))}
    </ul>
  );
}
