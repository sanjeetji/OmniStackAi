"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  Activity,
  FileCheck2,
  LayoutDashboard,
  LogOut,
  MapPin,
  Receipt,
  Settings,
  ShieldAlert,
  ShoppingBag,
  Star,
  Store,
  Tag,
  Truck,
  Wallet,
  X,
} from "lucide-react";
import { api } from "@bazaar/shared";
import { useRequireOperator, useSession } from "../lib/session";
import { useApi } from "../lib/use-api";
import { classes } from "./ui";
import { inr } from "../lib/format";

const SECTIONS = [
  {
    title: "Marketplace",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Live logistics", href: "/live-map", icon: MapPin },
    ],
  },
  {
    title: "Trade",
    items: [
      { label: "Orders", href: "/orders", icon: ShoppingBag },
      { label: "Consignments", href: "/shipments", icon: Truck },
      { label: "Workshops", href: "/shops", icon: Store },
    ],
  },
  {
    title: "Money",
    items: [
      { label: "Financials", href: "/finance", icon: Wallet },
      { label: "Ledger", href: "/finance/ledger", icon: Receipt },
      { label: "Settlements", href: "/settlements", icon: FileCheck2 },
    ],
  },
  {
    title: "Governance",
    items: [
      { label: "Coupons", href: "/coupons", icon: Tag },
      { label: "Reviews", href: "/reviews", icon: Star },
      { label: "Audit trail", href: "/audit", icon: ShieldAlert },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/finance") return pathname === "/finance";
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
            "pointer-events-auto flex items-start gap-2 rounded-lg border bg-[var(--surface)] px-3 py-2 shadow-xl",
            toast.tone === "good" && "border-emerald-500/30",
            toast.tone === "alert" && "border-amber-500/30",
            toast.tone === "info" && "border-[var(--surface-border)]"
          )}
        >
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-semibold text-slate-100">{toast.title}</p>
            {toast.detail && <p className="text-[11px] text-[var(--muted-light)]">{toast.detail}</p>}
          </div>
          <button onClick={() => dismiss(toast.id)} aria-label="Dismiss" className="text-[var(--muted)] hover:text-slate-200">
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

/** The escrow pool the marketplace is holding, read live rather than asserted. */
function EscrowPool() {
  const { pulse } = useSession();
  const finance = useApi(() => api.getAdminFinance(), [pulse]);
  const held = finance.data?.summary?.totalVendorPayablesCents;

  return (
    <div className="mx-3 mb-3 rounded-lg border border-[var(--surface-border)] bg-[var(--background)] p-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[11px] text-[var(--muted-light)]">
          <Activity size={13} className="text-[var(--accent-light)]" />
          Escrow held for vendors
        </span>
      </div>
      <div className="tabular mt-1 text-[15px] font-bold text-white">
        {finance.data ? inr(held) : "—"}
      </div>
      <p className="mt-0.5 text-[10px] text-[var(--muted)]">Owed out of the double-entry ledger</p>
    </div>
  );
}

/**
 * The console chrome, and the guard: nothing renders until there is an operator session, so
 * marketplace data is never briefly shown to a signed-out browser.
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
  const { operator, checking } = useRequireOperator();
  const { connected, signOut } = useSession();

  if (checking || !operator) {
    return (
      <div aria-busy="true" className="flex min-h-screen items-center justify-center text-[13px] text-[var(--muted-light)]">
        Checking your operator session…
      </div>
    );
  }

  const initials = (operator.name || operator.email)
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="flex min-h-screen bg-[var(--background)]">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-[var(--surface-border)] bg-[var(--surface)] lg:flex">
        <div className="flex items-center gap-2.5 border-b border-[var(--surface-border)] px-4 py-4">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--accent)] text-[14px] font-bold text-slate-950">
            BZ
          </span>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-semibold text-white">Bazaar Ops</p>
            <p className="truncate text-[11px] text-[var(--muted)]">Marketplace control</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {SECTIONS.map((section) => (
            <div key={section.title} className="mb-4">
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
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
                      "mb-0.5 flex items-center gap-2 rounded-lg px-2 py-1.5 text-[12.5px] transition",
                      active
                        ? "bg-amber-500/15 font-semibold text-[var(--accent-light)]"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
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

        <EscrowPool />

        <div className="border-t border-[var(--surface-border)] p-3">
          <div className="mb-2 flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-full border border-[var(--surface-border)] bg-[var(--background)] text-[11px] font-bold text-[var(--accent-light)]">
              {initials}
            </div>
            <div className="min-w-0">
              <div className="truncate text-[12px] font-semibold text-slate-200">{operator.name || operator.email}</div>
              <div className="truncate text-[10px] capitalize text-[var(--muted)]">{operator.role}</div>
            </div>
          </div>
          <button
            onClick={signOut}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[var(--surface-border)] py-1.5 text-[12px] text-slate-300 transition hover:bg-slate-800 hover:text-white"
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--surface-border)] bg-[var(--surface)]/90 px-4 py-3 backdrop-blur">
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-slate-100">{title}</h1>
            {subtitle && <p className="truncate text-[12px] text-[var(--muted-light)]">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            {actions}
            <span
              className="flex items-center gap-1.5 rounded-lg border border-[var(--surface-border)] px-2 py-1 text-[11px] font-semibold text-[var(--muted-light)]"
              title={connected ? "Receiving live marketplace events" : "Live stream reconnecting; screens still refresh on a timer"}
            >
              <Activity size={12} className={connected ? "animate-pulse text-[var(--emerald)]" : "text-[var(--muted)]"} />
              {connected ? "Live" : "Polling"}
            </span>
          </div>
        </header>

        <main className="flex-1 p-4">{children}</main>
      </div>

      <Toasts />
    </div>
  );
}
