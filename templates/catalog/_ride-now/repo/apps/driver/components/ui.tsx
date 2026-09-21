"use client";

import Link from "next/link";
import { forwardRef, useEffect, useId, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";
import { LoaderCircle, Star, X } from "lucide-react";
import { initials } from "@ridenow/shared";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

type Variant = "go" | "light" | "ghost" | "outline" | "danger" | "warn";
const VARIANT: Record<Variant, string> = {
  go: "bg-go text-bg hover:bg-go-deep",
  warn: "bg-warn text-bg hover:brightness-95",
  light: "bg-fg text-bg hover:bg-white",
  outline: "border border-line bg-raised text-fg hover:border-fg-muted",
  ghost: "text-fg-muted hover:bg-white/5 hover:text-fg",
  danger: "bg-danger text-white hover:brightness-95",
};

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean; size?: "sm" | "md" | "lg" | "xl" }>(
  function Button({ variant = "go", busy, size = "md", className, children, disabled, ...rest }, ref) {
    return (
      <button
        ref={ref}
        disabled={disabled || busy}
        className={cx(
          "inline-flex items-center justify-center gap-2 rounded-2xl font-bold outline-none transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-4 focus-visible:ring-go/40",
          { sm: "h-9 px-3 text-sm", md: "h-12 px-5 text-sm", lg: "h-14 px-6 text-base", xl: "h-16 px-8 text-lg" }[size],
          VARIANT[variant],
          className,
        )}
        {...rest}
      >
        {busy ? <LoaderCircle className="size-5 animate-spin" aria-hidden="true" /> : null}
        {children}
      </button>
    );
  },
);

export function LinkButton({ href, variant = "outline", className, children }: { href: string; variant?: Variant; className?: string; children: ReactNode }) {
  return (
    <Link href={href} className={cx("inline-flex h-12 items-center justify-center gap-2 rounded-2xl px-5 text-sm font-bold outline-none transition focus-visible:ring-4 focus-visible:ring-go/40", VARIANT[variant], className)}>
      {children}
    </Link>
  );
}

export function Panel({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cx("rounded-[var(--radius-card)] border border-line/60 bg-surface", className)}>{children}</section>;
}

export const Field = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string | null }>(
  function Field({ label, hint, error, className, id, ...rest }, ref) {
    const auto = useId();
    return (
      <div className={cx("grid gap-1.5", className)}>
        <label htmlFor={id ?? auto} className="text-sm font-semibold text-fg-muted">{label}</label>
        <input ref={ref} id={id ?? auto} aria-invalid={Boolean(error)} className={cx("h-13 rounded-2xl border bg-raised px-4 text-base outline-none transition focus:border-go focus:ring-4 focus:ring-go/20", error ? "border-danger" : "border-line")} {...rest} />
        {error ? <p role="alert" className="text-sm text-danger">{error}</p> : hint ? <p className="text-xs text-fg-muted">{hint}</p> : null}
      </div>
    );
  },
);

export function Tag({ tone = "muted", children }: { tone?: "muted" | "go" | "warn" | "danger" | "info"; children: ReactNode }) {
  const tones = { muted: "bg-white/8 text-fg-muted", go: "bg-go-soft text-go", warn: "bg-warn-soft text-warn", danger: "bg-danger-soft text-danger", info: "bg-info/15 text-info" } as const;
  return <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold", tones[tone])}>{children}</span>;
}

export function Avatar({ name, color, size = 44 }: { name: string; color: string; size?: number }) {
  return (
    <span aria-hidden="true" className="inline-grid shrink-0 place-items-center rounded-2xl font-bold text-white" style={{ background: color, width: size, height: size, fontSize: size * 0.36 }}>
      {initials(name)}
    </span>
  );
}

export function Notice({ tone = "danger", children }: { tone?: "danger" | "go" | "warn" | "info"; children: ReactNode }) {
  const tones = { danger: "bg-danger-soft text-danger", go: "bg-go-soft text-go", warn: "bg-warn-soft text-warn", info: "bg-info/12 text-info" } as const;
  return <div role={tone === "danger" ? "alert" : "status"} className={cx("rounded-2xl px-4 py-3 text-sm font-semibold", tones[tone])}>{children}</div>;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="grid place-items-center gap-2 py-20 text-fg-muted">
      <LoaderCircle className="size-6 animate-spin" aria-hidden="true" />
      <span className="text-sm">{label}…</span>
    </div>
  );
}

export function Empty({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="grid justify-items-center gap-2 px-6 py-14 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-raised text-fg-muted">{icon}</span>
      <p className="mt-2 font-bold">{title}</p>
      <p className="max-w-xs text-sm text-fg-muted">{body}</p>
    </div>
  );
}

export function Stars({ value, onChange, size = 30 }: { value: number; onChange?: (n: number) => void; size?: number }) {
  return (
    <div role={onChange ? "radiogroup" : "img"} aria-label={`${value} out of 5 stars`} className="flex gap-1.5">
      {[1, 2, 3, 4, 5].map((n) =>
        onChange ? (
          <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} star${n > 1 ? "s" : ""}`} onClick={() => onChange(n)}>
            <Star style={{ width: size, height: size }} className={n <= value ? "fill-warn text-warn" : "text-line"} aria-hidden="true" />
          </button>
        ) : (
          <Star key={n} style={{ width: size, height: size }} className={n <= Math.round(value) ? "fill-warn text-warn" : "text-line"} aria-hidden="true" />
        ),
      )}
    </div>
  );
}

export function Sheet({ open, onClose, title, children }: { open: boolean; onClose?: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open || !onClose) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid items-end bg-black/60" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()} className="drv-rise mx-auto w-full max-w-md rounded-t-[28px] border-t border-line bg-surface p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          {onClose ? (
            <button type="button" onClick={onClose} aria-label="Close" className="grid size-9 place-items-center rounded-full hover:bg-white/5"><X className="size-5" aria-hidden="true" /></button>
          ) : null}
        </div>
        {children}
      </div>
    </div>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-2xl bg-raised p-4">
      <p className="text-xs font-semibold text-fg-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold tabular-nums">{value}</p>
      {sub ? <p className="mt-0.5 text-xs text-fg-muted">{sub}</p> : null}
    </div>
  );
}
