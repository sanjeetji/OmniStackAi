"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function classes(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function Panel({
  title,
  subtitle,
  actions,
  children,
  padded = true,
  className,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  padded?: boolean;
  className?: string;
}) {
  return (
    <section className={classes("rounded-lg border border-[var(--color-border)] bg-[var(--color-card)]", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
          <div>
            {title && <h2 className="text-[13px] font-semibold tracking-tight text-[var(--color-ink)]">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[12px] text-[var(--color-ink-muted)]">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={padded ? "p-4" : undefined}>{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "plain",
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "plain" | "good" | "alert" | "danger" | "signal";
  icon?: ReactNode;
}) {
  const accent = {
    plain: "text-[var(--color-ink)]",
    good: "text-[var(--color-good)]",
    alert: "text-[var(--color-alert)]",
    danger: "text-[var(--color-danger)]",
    signal: "text-[var(--color-signal)]",
  }[tone];

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">{label}</p>
        {icon && <span className="text-[var(--color-ink-subtle)]">{icon}</span>}
      </div>
      <p className={classes("tabular mt-2 text-[26px] font-semibold leading-none", accent)}>{value}</p>
      {hint && <p className="mt-1.5 text-[12px] text-[var(--color-ink-muted)]">{hint}</p>}
    </div>
  );
}

const BADGE_TONES: Record<string, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  good: "bg-[var(--color-good-soft)] text-[var(--color-good)] ring-emerald-200",
  alert: "bg-[var(--color-alert-soft)] text-[var(--color-alert)] ring-amber-200",
  danger: "bg-[var(--color-danger-soft)] text-[var(--color-danger)] ring-red-200",
  signal: "bg-[var(--color-signal-soft)] text-[var(--color-signal)] ring-cyan-200",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: keyof typeof BADGE_TONES | string;
}) {
  return (
    <span
      className={classes(
        "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
        BADGE_TONES[tone] ?? BADGE_TONES.neutral
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  href,
  variant = "primary",
  size = "md",
  disabled,
  type = "button",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: "primary" | "quiet" | "danger" | "ghost";
  size?: "sm" | "md";
  disabled?: boolean;
  type?: "button" | "submit";
  title?: string;
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-md font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";
  const sizing = size === "sm" ? "px-2.5 py-1 text-[12px]" : "px-3 py-1.5 text-[13px]";
  const look = {
    primary: "bg-[var(--color-signal)] text-white hover:bg-[#0c6178]",
    quiet: "border border-[var(--color-border-strong)] bg-white text-[var(--color-ink)] hover:bg-slate-50",
    danger: "bg-[var(--color-danger)] text-white hover:bg-red-800",
    ghost: "text-[var(--color-signal)] hover:bg-[var(--color-signal-soft)]",
  }[variant];

  if (href) {
    return (
      <Link href={href} className={classes(base, sizing, look)} title={title}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={classes(base, sizing, look)} title={title}>
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-[var(--color-ink-muted)]">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "w-full rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1.5 text-[13px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-ink-subtle)] focus:border-[var(--color-signal)] focus:ring-2 focus:ring-cyan-100";

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-[var(--color-border)] text-left">
            {head.map((cell, index) => (
              <th
                key={index}
                className="whitespace-nowrap px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]"
              >
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Row({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <tr
      onClick={onClick}
      className={classes(
        "border-b border-[var(--color-border)] last:border-0",
        onClick && "cursor-pointer hover:bg-slate-50"
      )}
    >
      {children}
    </tr>
  );
}

export function Cell({
  children,
  align = "left",
  muted,
  mono,
}: {
  children: ReactNode;
  align?: "left" | "right" | "center";
  muted?: boolean;
  mono?: boolean;
}) {
  return (
    <td
      className={classes(
        "px-3 py-2 align-middle",
        align === "right" && "text-right tabular",
        align === "center" && "text-center",
        muted && "text-[var(--color-ink-muted)]",
        mono && "tabular"
      )}
    >
      {children}
    </td>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div aria-busy="true" className="flex items-center gap-2 px-3 py-10 text-[13px] text-[var(--color-ink-muted)]">
      <Loader2 size={15} className="animate-spin" />
      {label}…
    </div>
  );
}

export function Empty({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5 px-3 py-12 text-center">
      <Inbox size={20} className="text-[var(--color-ink-subtle)]" />
      <p className="text-[13px] font-semibold text-[var(--color-ink)]">{title}</p>
      {detail && <p className="max-w-sm text-[12px] text-[var(--color-ink-muted)]">{detail}</p>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-red-200 bg-[var(--color-danger-soft)] px-3 py-2 text-[12px] text-[var(--color-danger)]">
      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

/** Data, loading and empty in one place, so every screen behaves the same way. */
export function DataState<T>({
  state,
  empty,
  children,
}: {
  state: { data: T | null; loading: boolean; error: string | null };
  empty?: { title: string; detail?: string };
  children: (data: T) => ReactNode;
}) {
  if (state.error && !state.data) return <div className="p-4"><ErrorNote message={state.error} /></div>;
  if (!state.data) return <Loading />;
  if (empty && Array.isArray(state.data) && state.data.length === 0) {
    return <Empty title={empty.title} detail={empty.detail} />;
  }
  return <>{children(state.data)}</>;
}
