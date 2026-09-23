"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  Activity,
  BarChart3,
  Calendar,
  CheckCircle2,
  DollarSign,
  DoorOpen,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  RotateCcw,
  Settings,
  ShieldAlert,
  Stethoscope,
  Tv,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { useSession, useRequireStaff } from "../lib/session";
import { classes } from "./ui";

const SECTIONS = [
  {
    title: "Command centre",
    items: [
      { href: "/", label: "Operations dashboard", icon: LayoutDashboard },
      { href: "/front-desk", label: "Front desk", icon: Users },
      { href: "/check-in", label: "Patient check-in", icon: CheckCircle2 },
      { href: "/walk-in", label: "Walk-in booking", icon: UserPlus },
      { href: "/queue-display", label: "Waiting-room board", icon: Tv },
    ],
  },
  {
    title: "Clinic and rosters",
    items: [
      { href: "/appointments", label: "Appointments", icon: Calendar },
      { href: "/doctors", label: "Doctors", icon: Stethoscope },
      { href: "/rooms", label: "Rooms", icon: DoorOpen },
      { href: "/labs", label: "Diagnostics", icon: FlaskConical },
    ],
  },
  {
    title: "Cashier",
    items: [
      { href: "/billing", label: "Billing", icon: DollarSign },
      { href: "/refunds", label: "Refunds", icon: RotateCcw },
    ],
  },
  {
    title: "Governance",
    items: [
      { href: "/reports", label: "Reports", icon: BarChart3 },
      { href: "/audit", label: "Chart access audit", icon: ShieldAlert },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
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
            "rise-in pointer-events-auto flex items-start gap-2 rounded-lg border bg-white px-3 py-2 shadow-lg",
            toast.tone === "good" && "border-emerald-200",
            toast.tone === "alert" && "border-amber-200",
            toast.tone === "info" && "border-[var(--color-border)]"
          )}
        >
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-semibold text-[var(--color-ink)]">{toast.title}</p>
            {toast.detail && <p className="text-[11px] text-[var(--color-ink-muted)]">{toast.detail}</p>}
          </div>
          <button onClick={() => dismiss(toast.id)} aria-label="Dismiss" className="text-[var(--color-ink-subtle)] hover:text-[var(--color-ink)]">
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

/**
 * The console chrome, and the guard: nothing renders until there is a staff session, so a page
 * never briefly shows clinic data to a signed-out browser.
 */
export function Shell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const { user, checking } = useRequireStaff();
  const { connected, signOut } = useSession();

  if (checking || !user) {
    return (
      <div aria-busy="true" className="flex min-h-screen items-center justify-center text-[13px] text-[var(--color-ink-muted)]">
        Checking your clinic session…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-[var(--color-rail-edge)] bg-[var(--color-rail)] lg:flex">
        <div className="flex items-center gap-2 border-b border-[var(--color-rail-edge)] px-4 py-4">
          <span className="grid h-8 w-8 place-items-center rounded-md bg-[var(--color-signal-bright)] text-[13px] font-bold text-[#04232b]">
            CC
          </span>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-semibold text-white">CareClinic Ops</p>
            <p className="truncate text-[11px] text-slate-400">Indiranagar branch</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {SECTIONS.map((section) => (
            <div key={section.title} className="mb-4">
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                {section.title}
              </p>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={classes(
                      "mb-0.5 flex items-center gap-2 rounded-md px-2 py-1.5 text-[12.5px] transition",
                      active
                        ? "bg-[var(--color-signal-bright)]/15 font-semibold text-[var(--color-signal-bright)]"
                        : "text-slate-300 hover:bg-[var(--color-rail-hover)] hover:text-white"
                    )}
                  >
                    <Icon size={15} className="shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="border-t border-[var(--color-rail-edge)] px-3 py-3">
          <p className="truncate text-[12px] font-semibold text-white">{user.full_name}</p>
          <p className="mb-2 truncate text-[11px] capitalize text-slate-400">{user.role}</p>
          <button
            onClick={signOut}
            className="flex w-full items-center justify-center gap-1.5 rounded-md border border-[var(--color-rail-edge)] py-1.5 text-[12px] text-slate-300 transition hover:bg-[var(--color-rail-hover)] hover:text-white"
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3">
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-[var(--color-ink)]">{title}</h1>
            {subtitle && <p className="truncate text-[12px] text-[var(--color-ink-muted)]">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            {actions}
            <span
              className="flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-2 py-1 text-[11px] font-semibold text-[var(--color-ink-muted)]"
              title={connected ? "Receiving live clinic events" : "Live stream reconnecting; screens still refresh on a timer"}
            >
              <Activity size={12} className={connected ? "live-dot text-[var(--color-good)]" : "text-[var(--color-ink-subtle)]"} />
              {connected ? "Live" : "Polling"}
            </span>
          </div>
        </header>

        <main className="flex-1 bg-[var(--color-canvas)] p-4">{children}</main>
      </div>

      <Toasts />
    </div>
  );
}
