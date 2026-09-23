"use client";

/** Small chart primitives drawn with plain SVG and divs, so the console ships no chart library. */

export function TrendChart({
  series,
  height = 160,
  format = (value: number) => String(Math.round(value)),
}: {
  series: { label: string; value: number; secondary?: number }[];
  height?: number;
  format?: (value: number) => string;
}) {
  if (series.length === 0) {
    return <p className="px-3 py-8 text-center text-[12px] text-[var(--color-ink-muted)]">Nothing to chart yet.</p>;
  }

  const peak = Math.max(1, ...series.map((point) => Math.max(point.value, point.secondary ?? 0)));
  const width = Math.max(series.length * 26, 320);
  const step = width / series.length;

  return (
    <div className="overflow-x-auto">
      <svg width={width} height={height} role="img" aria-label="Daily trend" className="block">
        {[0.25, 0.5, 0.75, 1].map((fraction) => (
          <line
            key={fraction}
            x1={0}
            x2={width}
            y1={height - height * fraction + 12}
            y2={height - height * fraction + 12}
            stroke="var(--color-border)"
            strokeDasharray="3 3"
          />
        ))}
        {series.map((point, index) => {
          const barHeight = ((height - 26) * point.value) / peak;
          const x = index * step + step * 0.22;
          const barWidth = step * 0.56;
          return (
            <g key={point.label}>
              <rect
                x={x}
                y={height - 14 - barHeight}
                width={barWidth}
                height={Math.max(barHeight, 1)}
                rx={2}
                fill="var(--color-signal)"
                opacity={0.85}
              >
                <title>{`${point.label}: ${format(point.value)}`}</title>
              </rect>
              {point.secondary !== undefined && (
                <rect
                  x={x}
                  y={height - 14 - ((height - 26) * point.secondary) / peak}
                  width={barWidth}
                  height={2}
                  fill="var(--color-alert)"
                >
                  <title>{`${point.label}: ${format(point.secondary)}`}</title>
                </rect>
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-[var(--color-ink-subtle)]">
        <span>{series[0]?.label}</span>
        <span>{series[series.length - 1]?.label}</span>
      </div>
    </div>
  );
}

export function ShareBars({
  rows,
  format = (value: number) => String(value),
}: {
  rows: { label: string; value: number; note?: string }[];
  format?: (value: number) => string;
}) {
  const total = Math.max(1, rows.reduce((sum, row) => sum + row.value, 0));

  return (
    <ul className="space-y-2.5">
      {rows.map((row) => {
        const share = Math.round((row.value / total) * 100);
        return (
          <li key={row.label}>
            <div className="flex items-baseline justify-between gap-2 text-[12.5px]">
              <span className="truncate font-medium text-[var(--color-ink)]">{row.label}</span>
              <span className="tabular shrink-0 text-[var(--color-ink-muted)]">
                {format(row.value)} · {share}%
              </span>
            </div>
            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-[var(--color-signal)]" style={{ width: `${Math.max(share, 2)}%` }} />
            </div>
            {row.note && <p className="mt-0.5 text-[11px] text-[var(--color-ink-subtle)]">{row.note}</p>}
          </li>
        );
      })}
    </ul>
  );
}
