"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  CalendarDays,
  ClipboardList,
  IndianRupee,
  LayoutDashboard,
  LogOut,
  SlidersHorizontal,
  Star,
  Stethoscope,
  Users,
  X,
} from "lucide-react";
import { useRequireDoctor, useSession } from "../lib/session";
import { classes } from "./ui";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/queue", label: "Today's queue", icon: ClipboardList },
  { href: "/patients", label: "My patients", icon: Users },
  { href: "/schedule", label: "OPD hours", icon: CalendarDays },
  { href: "/schedule/rules", label: "Leave and changes", icon: SlidersHorizontal },
  { href: "/earnings", label: "Earnings", icon: IndianRupee },
  { href: "/reviews", label: "Reviews", icon: Star },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/schedule") return pathname === "/schedule";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Toasts() {
  const { toasts, dismiss } = useSession();
  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-72 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={classes(
            "pointer-events-auto flex items-start gap-2 rounded-xl border bg-white px-3 py-2 shadow-lg",
            toast.tone === "good" && "border-emerald-200",
            toast.tone === "alert" && "border-amber-200",
            toast.tone === "info" && "border-[var(--color-border)]"
          )}
        >
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-semibold text-[var(--color-ink)]">{toast.title}</p>
            {toast.detail && <p className="text-[11px] text-[var(--color-ink-muted)]">{toast.detail}</p>}
          </div>
          <button onClick={() => dismiss(toast.id)} aria-label="Dismiss" className="text-slate-400 hover:text-slate-700">
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

function ClinicClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="tabular hidden text-[12px] text-[var(--color-ink-muted)] sm:inline">
      {now
        ? now.toLocaleString("en-IN", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true })
        : ""}
    </span>
  );
}

/**
 * The workstation chrome, and the guard: nothing renders until there is a doctor session, so a
 * chart is never briefly shown to a signed-out browser.
 */
export function Shell({
  title,
  subtitle,
  actions,
  children,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  const pathname = usePathname();
  const { doctor, checking } = useRequireDoctor();
  const { connected, signOut } = useSession();

  if (checking || !doctor) {
    return (
      <div aria-busy="true" className="flex min-h-screen items-center justify-center text-[13px] text-[var(--color-ink-muted)]">
        Checking your clinic session…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-slate-800 bg-[var(--color-sidebar)] lg:flex">
        <div className="flex items-center gap-2.5 border-b border-slate-800 px-4 py-4">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-[var(--color-emerald-brand)] text-white">
            <Stethoscope size={17} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-semibold text-white">Workstation</p>
            <p className="truncate text-[11px] text-slate-400">CareClinic Indiranagar</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={classes(
                  "mb-0.5 flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-[13px] transition",
                  active
                    ? "bg-[var(--color-emerald-brand)]/15 font-semibold text-emerald-300"
                    : "text-slate-300 hover:bg-[var(--color-sidebar-hover)] hover:text-white"
                )}
              >
                <Icon size={16} className="shrink-0" />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-800 px-3 py-3">
          <p className="truncate text-[12px] font-semibold text-white">{doctor.full_name}</p>
          <p className="mb-2 truncate text-[11px] text-slate-400">{doctor.email}</p>
          <button
            onClick={signOut}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-700 py-1.5 text-[12px] text-slate-300 transition hover:bg-[var(--color-sidebar-hover)] hover:text-white"
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] bg-white px-4 py-3">
          <div className="min-w-0">
            <h1 className="truncate text-[16px] font-semibold tracking-tight text-[var(--color-ink)]">{title}</h1>
            {subtitle && <p className="truncate text-[12px] text-[var(--color-ink-muted)]">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            <ClinicClock />
            {actions}
            <span
              className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-2 py-1 text-[11px] font-semibold text-[var(--color-ink-muted)]"
              title={connected ? "Receiving live clinic events" : "Live stream reconnecting; screens still refresh on a timer"}
            >
              <Activity size={12} className={connected ? "animate-pulse-subtle text-emerald-600" : "text-slate-400"} />
              {connected ? "Live" : "Polling"}
            </span>
          </div>
        </header>

        <main className={classes("flex-1 bg-[var(--color-canvas)] p-4", !wide && "mx-auto w-full max-w-[1400px]")}>
          {children}
        </main>
      </div>

      <Toasts />
    </div>
  );
}
