"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CircleUserRound, History, House, IndianRupee } from "lucide-react";
import { ACTIVE_STATUSES } from "@ridenow/shared";
import { useRequireDriver } from "@/lib/driver";
import { OfferSheet } from "./offer-sheet";
import { Loading, cx } from "./ui";

const TABS = [
  { href: "/", label: "Home", icon: House },
  { href: "/earnings", label: "Earnings", icon: IndianRupee },
  { href: "/trips", label: "Trips", icon: History },
  { href: "/account", label: "Account", icon: CircleUserRound },
];

/** Phone-first frame: content, the incoming-request sheet, and a bottom tab bar. */
export function Shell({ children, title, action }: { children: React.ReactNode; title?: string; action?: React.ReactNode }) {
  const { user, profile, online, trip } = useRequireDriver();
  const pathname = usePathname();
  if (!user || !profile) return <Loading label="Starting your shift" />;
  const activeTrip = trip && ACTIVE_STATUSES.includes(trip.status);
  const current = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <div className="mx-auto min-h-dvh max-w-md pb-24">
      {title ? (
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line/60 bg-bg/90 px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur">
          <h1 className="text-xl font-extrabold">{title}</h1>
          {action ?? (
            <span className={cx("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold", online ? "bg-go-soft text-go" : "bg-white/8 text-fg-muted")}>
              <span className={cx("size-2 rounded-full", online ? "bg-go" : "bg-fg-muted")} aria-hidden="true" />
              {online ? "Online" : "Offline"}
            </span>
          )}
        </header>
      ) : null}
      {activeTrip && pathname !== "/trip" ? (
        <Link href="/trip" className="mx-4 mt-3 flex items-center justify-between rounded-2xl bg-go px-4 py-3 text-sm font-bold text-bg">
          <span>Trip in progress · {trip.code}</span>
          <span>Open →</span>
        </Link>
      ) : null}
      <main className="px-4 pt-4">{children}</main>
      <OfferSheet />
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 border-t border-line/70 bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur">
        <div className="mx-auto grid max-w-md grid-cols-4">
          {TABS.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} aria-current={current(href) ? "page" : undefined} className={cx("flex flex-col items-center gap-1 py-2.5 text-[11px] font-bold", current(href) ? "text-go" : "text-fg-muted")}>
              <Icon className="size-5" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
