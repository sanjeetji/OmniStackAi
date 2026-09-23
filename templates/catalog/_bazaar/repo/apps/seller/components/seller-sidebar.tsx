"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PackageCheck,
  Palette,
  BadgeIndianRupee,
  Star,
  Settings,
  Store,
  CheckCircle,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/shipments", label: "Orders & Fulfillment", icon: PackageCheck },
  { href: "/products", label: "Product Catalog", icon: Palette },
  { href: "/payouts", label: "Escrow & Payouts", icon: BadgeIndianRupee },
  { href: "/reviews", label: "Customer Reviews", icon: Star },
  { href: "/settings", label: "Workshop Settings", icon: Settings },
];

export function SellerSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-stone-900 text-stone-300 flex flex-col justify-between min-h-[calc(100vh-37px)] p-4 border-r border-stone-800 flex-shrink-0">
      <div>
        {/* Brand Atelier */}
        <div className="pb-6 border-b border-stone-800 mb-6 px-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-800 text-amber-200 flex items-center justify-center text-xl font-bold shadow-md">
              🏺
            </div>
            <div>
              <h2 className="text-sm font-bold text-white font-serif tracking-wide">
                Jaipur Blue Art
              </h2>
              <div className="flex items-center gap-1.5 mt-0.5">
                <CheckCircle className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] text-emerald-400 font-medium">KYC Verified Atelier</span>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? "bg-amber-800/90 text-white shadow-sm"
                    : "text-stone-400 hover:bg-stone-800/70 hover:text-stone-200"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-amber-200" : "text-stone-500"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="pt-6 border-t border-stone-800 space-y-3 px-2">
        <div className="p-3 bg-stone-800/60 rounded-xl border border-stone-700/50 text-[11px]">
          <span className="text-stone-400 block text-[10px] uppercase font-bold tracking-wider">
            Live Settlement Escrow
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-base font-bold text-amber-300">₹43,200.00</span>
            <Link
              href="/payouts"
              className="text-[10px] text-amber-400 hover:underline font-medium"
            >
              Withdraw &rarr;
            </Link>
          </div>
        </div>

        <a
          href="http://localhost:3000/shops/jaipur-pottery"
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-xl bg-stone-800 hover:bg-stone-700 text-stone-300 text-xs font-medium transition"
        >
          <span className="flex items-center gap-2">
            <Store className="w-3.5 h-3.5 text-stone-400" />
            <span>Public Storefront</span>
          </span>
          <span className="text-stone-500">&rarr;</span>
        </a>
      </div>
    </aside>
  );
}
