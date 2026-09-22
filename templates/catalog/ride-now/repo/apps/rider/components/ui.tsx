"use client";

import Link from "next/link";
import { forwardRef, useEffect, useId, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";
import { LoaderCircle, Star, X } from "lucide-react";
import { initials } from "@ridenow/shared";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

type ButtonVariant = "primary" | "dark" | "outline" | "ghost" | "danger";

const BUTTON: Record<ButtonVariant, string> = {
  primary: "bg-amber text-ink hover:bg-amber-deep shadow-[0_6px_18px_-8px_rgb(229_148_0/0.8)]",
  dark: "bg-ink text-white hover:bg-ink-soft",
  outline: "border border-line bg-white text-ink hover:border-ink/30",
  ghost: "text-ink-soft hover:bg-black/5",
  danger: "bg-danger text-white hover:bg-danger/90",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; busy?: boolean; size?: "md" | "lg" | "sm" }
>(function Button({ variant = "primary", busy, size = "md", className, children, disabled, ...rest }, ref) {
  return (
    <button
      ref={ref}
      disabled={disabled || busy}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold outline-none transition active:translate-y-px disabled:cursor-not-allowed disabled:opacity-55 focus-visible:ring-4 focus-visible:ring-amber/40",
        size === "lg" ? "h-13 px-7 text-base" : size === "sm" ? "h-9 px-4 text-sm" : "h-11 px-5 text-sm",
        BUTTON[variant],
        className,
      )}
      {...rest}
    >
      {busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
      {children}
    </button>
  );
});

export function ButtonLink({ href, variant = "primary", size = "md", className, children }: { href: string; variant?: ButtonVariant; size?: "md" | "lg" | "sm"; className?: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold outline-none transition active:translate-y-px focus-visible:ring-4 focus-visible:ring-amber/40",
        size === "lg" ? "h-13 px-7 text-base" : size === "sm" ? "h-9 px-4 text-sm" : "h-11 px-5 text-sm",
        BUTTON[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function Card({ className, children, as: Tag = "section" }: { className?: string; children: ReactNode; as?: "section" | "div" | "article" }) {
  return <Tag className={cx("rounded-[var(--radius-card)] bg-card shadow-[var(--shadow-card)]", className)}>{children}</Tag>;
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string; error?: string | null; leading?: ReactNode }>(
  function Input({ label, hint, error, leading, className, id, ...rest }, ref) {
    const auto = useId();
    const inputId = id ?? auto;
    return (
      <div className={cx("grid gap-1.5", className)}>
        {label ? <label htmlFor={inputId} className="text-sm font-semibold text-ink-soft">{label}</label> : null}
        <div className={cx("flex h-12 items-center gap-2 rounded-2xl border bg-white px-4 transition focus-within:border-ink focus-within:ring-4 focus-within:ring-amber/25", error ? "border-danger" : "border-line")}>
          {leading}
          <input ref={ref} id={inputId} aria-invalid={Boolean(error)} className="h-full min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted/70" {...rest} />
        </div>
        {error ? <p role="alert" className="text-sm text-danger">{error}</p> : hint ? <p className="text-xs text-muted">{hint}</p> : null}
      </div>
    );
  },
);

export function Badge({ tone = "neutral", children, className }: { tone?: "neutral" | "amber" | "teal" | "success" | "danger" | "dark"; children: ReactNode; className?: string }) {
  const tones = {
    neutral: "bg-black/5 text-ink-soft",
    amber: "bg-amber-soft text-amber-deep",
    teal: "bg-teal-soft text-teal",
    success: "bg-success-soft text-success",
    danger: "bg-danger-soft text-danger",
    dark: "bg-ink text-white",
  } as const;
  return <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold", tones[tone], className)}>{children}</span>;
}

export function Avatar({ name, color, size = 40 }: { name: string; color: string; size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="inline-grid shrink-0 place-items-center rounded-full font-bold text-white"
      style={{ background: color, width: size, height: size, fontSize: size * 0.36 }}
    >
      {initials(name)}
    </span>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="grid place-items-center gap-2 py-16 text-muted">
      <LoaderCircle className="size-6 animate-spin" aria-hidden="true" />
      <span className="text-sm">{label}…</span>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-2xl bg-black/[0.06]", className)} />;
}

export function EmptyState({ icon, title, body, action }: { icon: ReactNode; title: string; body: string; action?: ReactNode }) {
  return (
    <div className="grid justify-items-center gap-2 px-6 py-14 text-center">
      <span className="grid size-14 place-items-center rounded-full bg-amber-soft text-amber-deep">{icon}</span>
      <p className="mt-2 text-lg font-bold">{title}</p>
      <p className="max-w-sm text-pretty text-sm text-muted">{body}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

export function Alert({ tone = "danger", children }: { tone?: "danger" | "success" | "info"; children: ReactNode }) {
  const tones = { danger: "bg-danger-soft text-danger", success: "bg-success-soft text-success", info: "bg-teal-soft text-teal" } as const;
  return <div role={tone === "danger" ? "alert" : "status"} className={cx("rounded-2xl px-4 py-3 text-sm font-medium", tones[tone])}>{children}</div>;
}

/** A bottom sheet on phones, a centred dialog on larger screens. */
export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid items-end bg-ink/40 backdrop-blur-[2px] sm:place-items-center" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        className="rn-rise w-full rounded-t-[28px] bg-white p-6 shadow-[var(--shadow-float)] sm:max-w-md sm:rounded-[28px]"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={onClose} className="grid size-9 place-items-center rounded-full hover:bg-black/5" aria-label="Close">
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Stars({ value, onChange, size = 28 }: { value: number; onChange?: (value: number) => void; size?: number }) {
  return (
    <div role={onChange ? "radiogroup" : "img"} aria-label={`${value} out of 5 stars`} className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) =>
        onChange ? (
          <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} star${n > 1 ? "s" : ""}`} onClick={() => onChange(n)} className="rounded-md outline-none focus-visible:ring-4 focus-visible:ring-amber/40">
            <Star style={{ width: size, height: size }} className={n <= value ? "fill-amber text-amber" : "text-line"} aria-hidden="true" />
          </button>
        ) : (
          <Star key={n} style={{ width: size, height: size }} className={n <= Math.round(value) ? "fill-amber text-amber" : "text-line"} aria-hidden="true" />
        ),
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-balance text-3xl font-extrabold tracking-tight">{title}</h1>
        {subtitle ? <p className="mt-1 text-pretty text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}
