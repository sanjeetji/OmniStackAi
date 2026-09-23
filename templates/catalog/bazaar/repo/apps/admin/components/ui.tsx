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
    <section
      className={classes(
        "rounded-xl border border-[var(--surface-border)] bg-[var(--surface)]",
        className
      )}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--surface-border)] px-4 py-3">
          <div>
            {title && <h2 className="text-[13px] font-semibold tracking-tight text-slate-100">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[12px] text-[var(--muted-light)]">{subtitle}</p>}
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
    plain: "text-slate-100",
    good: "text-[var(--emerald)]",
    alert: "text-[var(--accent-light)]",
    danger: "text-[var(--rose)]",
    signal: "text-sky-400",
  }[tone];

  return (
    <div className="rounded-xl border border-[var(--surface-border)] bg-[var(--surface)] p-4">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">{label}</p>
        {icon && <span className="text-[var(--muted)]">{icon}</span>}
      </div>
      <p className={classes("tabular mt-2 text-[26px] font-semibold leading-none", accent)}>{value}</p>
      {hint && <p className="mt-1.5 text-[12px] text-[var(--muted-light)]">{hint}</p>}
    </div>
  );
}

const BADGE_TONES: Record<string, string> = {
  neutral: "bg-slate-800 text-slate-300 ring-slate-700",
  good: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/30",
  alert: "bg-amber-500/10 text-amber-400 ring-amber-500/30",
  danger: "bg-rose-500/10 text-rose-400 ring-rose-500/30",
  signal: "bg-sky-500/10 text-sky-400 ring-sky-500/30",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
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
    "inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";
  const sizing = size === "sm" ? "px-2.5 py-1 text-[12px]" : "px-3 py-1.5 text-[13px]";
  const look = {
    primary: "bg-[var(--accent)] text-slate-950 hover:bg-[var(--accent-light)]",
    quiet: "border border-[var(--surface-border)] bg-[var(--surface-elevated)] text-slate-200 hover:bg-slate-700",
    danger: "bg-[var(--rose)] text-white hover:bg-rose-600",
    ghost: "text-[var(--accent-light)] hover:bg-amber-500/10",
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

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-[var(--muted-light)]">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-[var(--surface-border)] bg-[var(--background)] px-2.5 py-1.5 text-[13px] text-slate-100 outline-none placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-amber-500/20";

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left">
            {head.map((cell, index) => (
              <th
                key={index}
                className="whitespace-nowrap px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]"
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
        "border-b border-[var(--surface-border)] last:border-0",
        onClick && "cursor-pointer hover:bg-slate-800/50"
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
        "px-3 py-2 align-middle text-slate-200",
        align === "right" && "text-right tabular",
        align === "center" && "text-center",
        muted && "text-[var(--muted-light)]",
        mono && "tabular"
      )}
    >
      {children}
    </td>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div aria-busy="true" className="flex items-center gap-2 px-3 py-10 text-[13px] text-[var(--muted-light)]">
      <Loader2 size={15} className="animate-spin" />
      {label}…
    </div>
  );
}

export function Empty({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5 px-3 py-12 text-center">
      <Inbox size={20} className="text-[var(--muted)]" />
      <p className="text-[13px] font-semibold text-slate-200">{title}</p>
      {detail && <p className="max-w-sm text-[12px] text-[var(--muted-light)]">{detail}</p>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[12px] text-rose-300">
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
