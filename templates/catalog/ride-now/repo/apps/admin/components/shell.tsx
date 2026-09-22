"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  BadgePercent,
  Banknote,
  Car,
  CircleCheck,
  CircleX,
  Gauge,
  Info,
  LifeBuoy,
  LogOut,
  Map as MapIcon,
  Menu,
  Radar,
  Route,
  ScrollText,
  Search,
  Settings,
  Tags,
  Users,
  Wallet,
  X,
  type LucideIcon,
} from "lucide-react";
import { useRequireAdmin, type Queues } from "@/lib/session";
import { Avatar, Skeleton, cx } from "./ui";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: (q: Queues) => number;
}

const NAV: { heading: string; items: NavItem[] }[] = [
  { heading: "Overview", items: [
    { href: "/", label: "Dashboard", icon: Gauge },
    { href: "/live", label: "Live map", icon: Radar },
  ] },
  { heading: "Operations", items: [
    { href: "/trips", label: "Trips", icon: Route },
    { href: "/riders", label: "Riders", icon: Users },
    { href: "/drivers", label: "Drivers", icon: Car, badge: (q) => q.driversPending },
    { href: "/tickets", label: "Support", icon: LifeBuoy, badge: (q) => q.openTickets },
  ] },
  { heading: "Money", items: [
    { href: "/payouts", label: "Payouts", icon: Banknote, badge: (q) => q.payoutsDue },
    { href: "/finance", label: "Finance", icon: Wallet },
    { href: "/promos", label: "Promo codes", icon: BadgePercent },
  ] },
  { heading: "City setup", items: [
    { href: "/pricing", label: "Pricing", icon: Tags },
    { href: "/zones", label: "Surge zones", icon: MapIcon },
  ] },
  { heading: "Admin", items: [
    { href: "/audit", label: "Audit log", icon: ScrollText },
    { href: "/settings", label: "Settings", icon: Settings },
  ] },
];

function isCurrent(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 px-2 py-1 outline-none focus-visible:ring-3 focus-visible:ring-signal/40 rounded-md">
      <span className="relative grid size-8 place-items-center rounded-lg bg-white text-[15px] font-bold text-side">
        R
        <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full bg-brand ring-2 ring-side" aria-hidden="true" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold text-white">RideNow Ops</span>
        <span className="block text-[11px] text-side-muted">Bengaluru · operations</span>
      </span>
    </Link>
  );
}

function Nav({ queues, onNavigate }: { queues: Queues | null; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Operations" className="grid gap-5">
      {NAV.map((group) => (
        <div key={group.heading}>
          <p className="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-wider text-side-muted">{group.heading}</p>
          <ul className="grid gap-0.5">
            {group.items.map(({ href, label, icon: Icon, badge }) => {
              const current = isCurrent(pathname, href);
              const count = queues && badge ? badge(queues) : 0;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={current ? "page" : undefined}
                    className={cx(
                      "flex h-8 items-center gap-2.5 rounded-md px-2.5 text-[13px] font-medium outline-none transition focus-visible:ring-3 focus-visible:ring-signal/40",
                      current ? "bg-side-2 text-white" : "text-side-fg hover:bg-side-2/60 hover:text-white",
                    )}
                  >
                    <Icon className={cx("size-4 shrink-0", current ? "text-brand" : "text-side-muted")} aria-hidden="true" />
                    <span className="flex-1">{label}</span>
                    {count > 0 ? (
                      <span className="num rounded-full bg-brand px-1.5 text-[11px] font-bold leading-[18px] text-side" aria-label={`${count} waiting`}>
                        {count}
                      </span>
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

/** The operations frame: sidebar, top bar with live counts and trip search, toasts. */
export function Shell({ children }: { children: ReactNode }) {
  const { user, queues, signOut, toasts, dismissToast } = useRequireAdmin();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => setMenuOpen(false), [pathname]);

  if (!user) {
    return (
      <div role="status" className="grid min-h-dvh place-items-center">
        <div className="grid w-64 gap-2">
          <Skeleton className="h-3" />
          <Skeleton className="h-3 w-2/3" />
          <span className="sr-only">Checking your session…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[232px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-md focus:bg-panel focus:px-3 focus:py-2 focus:text-sm focus:shadow-pop">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-dvh flex-col gap-6 overflow-y-auto border-r border-side-line bg-side px-3 py-4 lg:flex">
        <Brand />
        <Nav queues={queues} />
        <div className="mt-auto rounded-md border border-side-line bg-side-2/60 p-3 text-[11px] leading-relaxed text-side-muted">
          Demo city. Payments, SMS and maps are mocks, so nothing here moves real money.
        </div>
      </aside>

      {menuOpen ? (
        <div className="fixed inset-0 z-50 bg-ink/50 lg:hidden" onClick={() => setMenuOpen(false)}>
          <div role="dialog" aria-modal="true" aria-label="Menu" onClick={(e) => e.stopPropagation()} className="ops-in flex h-full w-72 flex-col gap-6 overflow-y-auto bg-side px-3 py-4">
            <div className="flex items-center justify-between">
              <Brand />
              <button type="button" onClick={() => setMenuOpen(false)} aria-label="Close menu" className="grid size-8 place-items-center rounded-md text-side-fg hover:bg-side-2">
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
            <Nav queues={queues} onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      ) : null}

      <div className="min-w-0">
        <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-line bg-panel/90 px-4 backdrop-blur lg:px-6">
          <button type="button" onClick={() => setMenuOpen(true)} aria-label="Open menu" className="grid size-8 place-items-center rounded-md text-ink-2 hover:bg-ink/5 lg:hidden">
            <Menu className="size-5" aria-hidden="true" />
          </button>
          <form
            role="search"
            className="relative hidden max-w-sm flex-1 sm:block"
            onSubmit={(event) => {
              event.preventDefault();
              const q = query.trim();
              router.push(q ? `/trips?q=${encodeURIComponent(q)}` : "/trips");
            }}
          >
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Find a trip by code, rider, driver or place"
              aria-label="Find a trip"
              className="h-9 w-full rounded-md border border-line bg-sunken pl-8 pr-3 text-[13px] outline-none focus:border-signal focus:bg-panel focus:ring-3 focus:ring-signal/20"
            />
          </form>
          <div className="ml-auto flex items-center gap-2 text-[13px]">
            <Link href="/live" className="hidden items-center gap-1.5 rounded-full border border-line px-2.5 py-1 font-medium text-ink-2 hover:border-line-strong md:inline-flex">
              <span className="ops-pulse size-2 rounded-full bg-ok" aria-hidden="true" />
              <span className="num">{queues ? queues.driversOnline : "–"}</span> drivers online
            </Link>
            <Link href="/trips?status=active" className="hidden items-center gap-1.5 rounded-full border border-line px-2.5 py-1 font-medium text-ink-2 hover:border-line-strong md:inline-flex">
              <span className="size-2 rounded-full bg-signal" aria-hidden="true" />
              <span className="num">{queues ? queues.activeTrips : "–"}</span> active trips
            </Link>
            <span className="mx-1 hidden h-6 w-px bg-line md:block" aria-hidden="true" />
            <Link href="/settings" className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-ink/5" title="Settings">
              <Avatar name={user.full_name} color={user.avatar_color} size={26} />
              <span className="hidden font-medium text-ink xl:inline">{user.full_name}</span>
            </Link>
            <button
              type="button"
              onClick={async () => {
                await signOut();
                router.replace("/login");
              }}
              aria-label="Sign out"
              title="Sign out"
              className="grid size-8 place-items-center rounded-md text-muted hover:bg-ink/5 hover:text-ink"
            >
              <LogOut className="size-4" aria-hidden="true" />
            </button>
          </div>
        </header>
        <main id="main" className="ops-in mx-auto max-w-[1400px] px-4 py-6 lg:px-6">
          {children}
        </main>
      </div>

      <div aria-live="polite" className="fixed bottom-4 right-4 z-[70] grid w-80 gap-2">
        {toasts.map((t) => (
          <div key={t.id} className="ops-in flex items-start gap-2.5 rounded-box border border-line bg-panel px-3.5 py-3 text-[13px] text-ink shadow-pop">
            {t.tone === "ok" ? (
              <CircleCheck className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden="true" />
            ) : t.tone === "bad" ? (
              <CircleX className="mt-0.5 size-4 shrink-0 text-bad" aria-hidden="true" />
            ) : (
              <Info className="mt-0.5 size-4 shrink-0 text-info" aria-hidden="true" />
            )}
            <p className="flex-1">{t.text}</p>
            <button type="button" onClick={() => dismissToast(t.id)} aria-label="Dismiss" className="text-muted hover:text-ink">
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
