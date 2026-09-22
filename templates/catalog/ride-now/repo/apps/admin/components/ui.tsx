"use client";

import Link from "next/link";
import {
  forwardRef,
  useEffect,
  useId,
  useRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { AlertTriangle, ArrowLeft, ChevronLeft, ChevronRight, LoaderCircle, RotateCcw, Search, X } from "lucide-react";
import { initials } from "@ridenow/shared";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// --- buttons ------------------------------------------------------------------------------------

type Variant = "primary" | "secondary" | "ghost" | "danger" | "ok";
const VARIANT: Record<Variant, string> = {
  primary: "bg-signal text-white hover:bg-signal-deep",
  secondary: "border border-line-strong bg-panel text-ink hover:border-ink-2/40 hover:bg-sunken",
  ghost: "text-ink-2 hover:bg-ink/5",
  danger: "border border-bad/30 bg-bad-soft text-bad hover:border-bad/60",
  ok: "bg-ok text-white hover:brightness-110",
};
const SIZE = { sm: "h-8 px-2.5 text-[13px]", md: "h-9 px-3.5 text-sm" } as const;
const BUTTON_BASE =
  "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-box font-semibold outline-none transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-3 focus-visible:ring-signal/35";

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: keyof typeof SIZE; busy?: boolean }
>(function Button({ variant = "primary", size = "md", busy, className, children, disabled, type = "button", ...rest }, ref) {
  return (
    <button ref={ref} type={type} disabled={disabled || busy} className={cx(BUTTON_BASE, SIZE[size], VARIANT[variant], className)} {...rest}>
      {busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
      {children}
    </button>
  );
});

export function LinkButton({ href, variant = "secondary", size = "md", className, children }: { href: string; variant?: Variant; size?: keyof typeof SIZE; className?: string; children: ReactNode }) {
  return (
    <Link href={href} className={cx(BUTTON_BASE, SIZE[size], VARIANT[variant], className)}>
      {children}
    </Link>
  );
}

// --- layout -------------------------------------------------------------------------------------

export function PageHeader({ title, description, actions, back }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; back?: { href: string; label: string } }) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {back ? (
          <Link href={back.href} className="mb-1.5 inline-flex items-center gap-1 text-[13px] font-medium text-muted hover:text-ink">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            {back.label}
          </Link>
        ) : null}
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">{title}</h1>
        {description ? <p className="mt-0.5 max-w-2xl text-[13px] text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Panel({ title, description, actions, className, bodyClassName, children }: { title?: ReactNode; description?: ReactNode; actions?: ReactNode; className?: string; bodyClassName?: string; children: ReactNode }) {
  return (
    <section className={cx("rounded-box border border-line bg-panel shadow-panel", className)}>
      {title ? (
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-ink">{title}</h2>
            {description ? <p className="text-xs text-muted">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

export function KeyValues({ items, className }: { items: [ReactNode, ReactNode][]; className?: string }) {
  return (
    <dl className={cx("grid gap-x-4 gap-y-2.5 text-[13px] sm:grid-cols-[auto_1fr]", className)}>
      {items.map(([key, value], index) => (
        <div key={index} className="contents">
          <dt className="text-muted">{key}</dt>
          <dd className="min-w-0 font-medium text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

// --- data display -------------------------------------------------------------------------------

export type Tone = "neutral" | "ok" | "warn" | "bad" | "info" | "signal";
const TONE: Record<Tone, string> = {
  neutral: "bg-ink/6 text-ink-2",
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  info: "bg-info-soft text-info",
  signal: "bg-signal-soft text-signal",
};
const DOT: Record<Tone, string> = { neutral: "bg-muted", ok: "bg-ok", warn: "bg-warn", bad: "bg-bad", info: "bg-info", signal: "bg-signal" };

export function Badge({ tone = "neutral", dot, children, className }: { tone?: Tone; dot?: boolean; children: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold", TONE[tone], className)}>
      {dot ? <span className={cx("size-1.5 rounded-full", DOT[tone])} aria-hidden="true" /> : null}
      {children}
    </span>
  );
}

export function Avatar({ name, color, size = 28 }: { name: string; color: string; size?: number }) {
  return (
    <span aria-hidden="true" className="inline-grid shrink-0 place-items-center rounded-md font-semibold text-white" style={{ background: color, width: size, height: size, fontSize: Math.round(size * 0.4) }}>
      {initials(name)}
    </span>
  );
}

export function Person({ name, color, sub }: { name: string; color: string; sub?: ReactNode }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <Avatar name={name} color={color} />
      <span className="min-w-0">
        <span className="block truncate font-medium text-ink">{name}</span>
        {sub ? <span className="block truncate text-xs text-muted">{sub}</span> : null}
      </span>
    </span>
  );
}

export function Stat({ label, value, delta, hint, icon }: { label: string; value: ReactNode; delta?: { value: number; label: string } | null; hint?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="rounded-box border border-line bg-panel p-4 shadow-panel">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[13px] font-medium text-muted">{label}</p>
        {icon ? <span className="text-muted">{icon}</span> : null}
      </div>
      <p className="num mt-1.5 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted">
        {delta ? (
          <span className={cx("num font-semibold", delta.value > 0 ? "text-ok" : delta.value < 0 ? "text-bad" : "text-muted")}>
            {delta.value > 0 ? "▲" : delta.value < 0 ? "▼" : "•"} {Math.abs(delta.value).toFixed(1)}%
          </span>
        ) : null}
        {delta ? <span>{delta.label}</span> : null}
        {hint ? <span>{hint}</span> : null}
      </div>
    </div>
  );
}

/** Percentage change from `previous` to `current`, or null when there is no base. */
export function change(current: number, previous: number): number | null {
  if (!previous) return null;
  return ((current - previous) / previous) * 100;
}

// --- tables -------------------------------------------------------------------------------------

export const th = "whitespace-nowrap border-b border-line bg-sunken px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted first:pl-4 last:pr-4";
export const td = "border-b border-line px-3 py-2.5 align-middle text-[13px] first:pl-4 last:pr-4";

export function Table({ children, label, className }: { children: ReactNode; label: string; className?: string }) {
  return (
    <div className={cx("overflow-x-auto", className)}>
      <table className="w-full border-collapse" aria-label={label}>
        {children}
      </table>
    </div>
  );
}

export function Pager({ offset, limit, total, onChange }: { offset: number; limit: number; total: number; onChange: (offset: number) => void }) {
  if (total <= limit) {
    return <p className="num px-4 py-3 text-xs text-muted">{total} {total === 1 ? "result" : "results"}</p>;
  }
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(total, offset + limit);
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <p className="num text-xs text-muted">
        {from}–{to} of {total}
      </p>
      <div className="flex gap-1.5">
        <Button variant="secondary" size="sm" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))} aria-label="Previous page">
          <ChevronLeft className="size-4" aria-hidden="true" />
        </Button>
        <Button variant="secondary" size="sm" disabled={to >= total} onClick={() => onChange(offset + limit)} aria-label="Next page">
          <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

// --- states -------------------------------------------------------------------------------------

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-md bg-ink/6", className)} />;
}

export function LoadingRows({ rows = 6, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="grid gap-2 p-4">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-9" />
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

export function LoadingPage({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="grid gap-4">
      <Skeleton className="h-8 w-56" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-72" />
      <span className="sr-only">{label}…</span>
    </div>
  );
}

export function Empty({ icon, title, body, action }: { icon: ReactNode; title: string; body: string; action?: ReactNode }) {
  return (
    <div className="grid justify-items-center gap-1.5 px-6 py-12 text-center">
      <span className="grid size-11 place-items-center rounded-box bg-sunken text-muted">{icon}</span>
      <p className="mt-1.5 font-semibold text-ink">{title}</p>
      <p className="max-w-sm text-[13px] text-muted">{body}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-box border border-bad/25 bg-bad-soft px-4 py-3 text-[13px] text-bad">
      <span className="flex items-center gap-2">
        <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
        {message}
      </span>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RotateCcw className="size-3.5" aria-hidden="true" />
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div role={tone === "bad" ? "alert" : "status"} className={cx("rounded-box px-3.5 py-2.5 text-[13px]", TONE[tone])}>
      {children}
    </div>
  );
}

// --- forms --------------------------------------------------------------------------------------

const CONTROL =
  "w-full rounded-box border border-line-strong bg-panel px-3 text-[13px] text-ink outline-none transition placeholder:text-muted/70 focus:border-signal focus:ring-3 focus:ring-signal/20 aria-invalid:border-bad";

export const Field = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: ReactNode; error?: string | null; suffix?: ReactNode }>(
  function Field({ label, hint, error, suffix, className, id, ...rest }, ref) {
    const auto = useId();
    const inputId = id ?? auto;
    return (
      <div className={cx("grid gap-1", className)}>
        <label htmlFor={inputId} className="text-xs font-semibold text-ink-2">{label}</label>
        <div className="relative">
          <input ref={ref} id={inputId} aria-invalid={error ? true : undefined} aria-describedby={hint || error ? `${inputId}-hint` : undefined} className={cx(CONTROL, "h-9", suffix ? "pr-10" : "")} {...rest} />
          {suffix ? <span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted">{suffix}</span> : null}
        </div>
        {error ? (
          <p id={`${inputId}-hint`} role="alert" className="text-xs text-bad">{error}</p>
        ) : hint ? (
          <p id={`${inputId}-hint`} className="text-xs text-muted">{hint}</p>
        ) : null}
      </div>
    );
  },
);

export function TextArea({ label, className, id, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  const auto = useId();
  return (
    <div className={cx("grid gap-1", className)}>
      <label htmlFor={id ?? auto} className="text-xs font-semibold text-ink-2">{label}</label>
      <textarea id={id ?? auto} className={cx(CONTROL, "min-h-24 py-2 leading-relaxed")} {...rest} />
    </div>
  );
}

export function Select({ label, options, className, id, hideLabel, ...rest }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; options: { value: string; label: string }[]; hideLabel?: boolean }) {
  const auto = useId();
  return (
    <div className={cx("grid gap-1", className)}>
      <label htmlFor={id ?? auto} className={hideLabel ? "sr-only" : "text-xs font-semibold text-ink-2"}>{label}</label>
      <select id={id ?? auto} className={cx(CONTROL, "h-9 pr-8")} {...rest}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </div>
  );
}

export function Toggle({ checked, onChange, label, disabled }: { checked: boolean; onChange: (next: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx("relative h-5 w-9 shrink-0 rounded-full outline-none transition focus-visible:ring-3 focus-visible:ring-signal/35 disabled:opacity-50", checked ? "bg-ok" : "bg-line-strong")}
    >
      <span className={cx("absolute top-0.5 size-4 rounded-full bg-white shadow transition-all", checked ? "left-[18px]" : "left-0.5")} />
    </button>
  );
}

export function SearchBox({ value, onChange, placeholder, label }: { value: string; onChange: (value: string) => void; placeholder: string; label: string }) {
  return (
    <div className="relative w-full sm:w-72">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
      <input type="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={label} className={cx(CONTROL, "h-9 pl-8")} />
    </div>
  );
}

export function Segmented<T extends string>({ value, onChange, options, label }: { value: T; onChange: (value: T) => void; options: { value: T; label: string; count?: number }[]; label: string }) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap rounded-box border border-line-strong bg-panel p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
          className={cx(
            "inline-flex h-7 items-center gap-1.5 rounded-[5px] px-2.5 text-[13px] font-medium outline-none transition focus-visible:ring-3 focus-visible:ring-signal/35",
            value === option.value ? "bg-ink text-white" : "text-ink-2 hover:bg-ink/5",
          )}
        >
          {option.label}
          {option.count !== undefined ? <span className={cx("num text-xs", value === option.value ? "text-white/70" : "text-muted")}>{option.count}</span> : null}
        </button>
      ))}
    </div>
  );
}

// --- dialog -------------------------------------------------------------------------------------

export function Modal({ open, title, description, onClose, children, footer, width = "max-w-md" }: { open: boolean; title: string; description?: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode; width?: string }) {
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  // Callers pass a new onClose on every render; keep the latest without re-running the focus effect.
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const first = panel.current?.querySelector<HTMLElement>("input, textarea, select, button:not([data-close])");
    first?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close.current();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [open]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/45 p-4" onMouseDown={onClose}>
      <div ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId} onMouseDown={(e) => e.stopPropagation()} className={cx("ops-in w-full rounded-box border border-line bg-panel shadow-pop", width)}>
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <h2 id={titleId} className="font-semibold text-ink">{title}</h2>
            {description ? <p className="mt-0.5 text-[13px] text-muted">{description}</p> : null}
          </div>
          <button type="button" data-close onClick={onClose} aria-label="Close" className="grid size-7 place-items-center rounded-md text-muted hover:bg-ink/5 hover:text-ink">
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer ? <div className="flex justify-end gap-2 border-t border-line bg-sunken px-5 py-3">{footer}</div> : null}
      </div>
    </div>
  );
}
