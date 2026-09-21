"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Bell, CarFront, CircleUserRound, History, LifeBuoy, LogOut, MapPin, Tag, Wallet } from "lucide-react";
import { useStream } from "@ridenow/shared";
import { api } from "@/lib/api";
import { useRequireRider, useSession } from "@/lib/session";
import { Avatar, Spinner, cx } from "./ui";
import { Logo } from "./logo";

const NAV = [
  { href: "/ride", label: "Ride", icon: CarFront },
  { href: "/trips", label: "Trips", icon: History },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/help", label: "Help", icon: LifeBuoy },
];

export function AppShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const user = useRequireRider();
  const { signOut } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const [unread, setUnread] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    api.get<{ unread: number }>("/support/notifications?limit=1").then((r) => setUnread(r.unread)).catch(() => undefined);
  }, [user, pathname]);

  useStream(api, { notification: () => setUnread((n) => n + 1) }, Boolean(user));

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpen]);

  if (!user) return <Spinner label="Checking your account" />;

  const current = (href: string) => pathname === href || pathname.startsWith(`${href}/`) || (href === "/trips" && pathname.startsWith("/trip/"));

  return (
    <div className="min-h-dvh pb-20 sm:pb-0">
      <header className="sticky top-0 z-40 border-b border-line/70 bg-canvas/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <Logo href="/ride" />
          <nav aria-label="Main" className="ml-4 hidden items-center gap-1 sm:flex">
            {NAV.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                aria-current={current(href) ? "page" : undefined}
                className={cx("rounded-full px-4 py-2 text-sm font-semibold transition", current(href) ? "bg-ink text-white" : "text-ink-soft hover:bg-black/5")}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/notifications" className="relative grid size-10 place-items-center rounded-full hover:bg-black/5" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}>
              <Bell className="size-5" aria-hidden="true" />
              {unread > 0 ? <span className="absolute right-1.5 top-1.5 grid min-w-4 place-items-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">{unread > 9 ? "9+" : unread}</span> : null}
            </Link>
            <div className="relative" ref={menuRef}>
              <button type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-haspopup="menu" className="rounded-full outline-none focus-visible:ring-4 focus-visible:ring-amber/40">
                <Avatar name={user.full_name} color={user.avatar_color} size={38} />
                <span className="sr-only">Account menu</span>
              </button>
              {menuOpen ? (
                <div role="menu" className="rn-rise absolute right-0 mt-2 w-60 overflow-hidden rounded-2xl border border-line bg-white p-1.5 shadow-[var(--shadow-float)]">
                  <div className="px-3 py-2">
                    <p className="truncate font-semibold">{user.full_name}</p>
                    <p className="truncate text-xs text-muted">{user.email ?? user.phone}</p>
                  </div>
                  {[
                    { href: "/account", label: "Account", icon: CircleUserRound },
                    { href: "/places", label: "Saved places", icon: MapPin },
                    { href: "/promos", label: "Promotions", icon: Tag },
                  ].map(({ href, label, icon: Icon }) => (
                    <Link key={href} role="menuitem" href={href} onClick={() => setMenuOpen(false)} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium hover:bg-black/5">
                      <Icon className="size-4 text-muted" aria-hidden="true" />
                      {label}
                    </Link>
                  ))}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={async () => {
                      await signOut();
                      router.replace("/login");
                    }}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-danger hover:bg-danger-soft"
                  >
                    <LogOut className="size-4" aria-hidden="true" />
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </header>
      <main className={cx("mx-auto px-4 py-8", wide ? "max-w-6xl" : "max-w-4xl")}>{children}</main>
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-line bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur sm:hidden">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href} aria-current={current(href) ? "page" : undefined} className={cx("flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold", current(href) ? "text-ink" : "text-muted")}>
            <Icon className={cx("size-5", current(href) && "text-amber-deep")} aria-hidden="true" />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
