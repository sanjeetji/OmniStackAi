"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MapPin,
  ShoppingBag,
  Truck,
  Store,
  Wallet,
  Receipt,
  FileCheck2,
  Tag,
  Star,
  ShieldAlert,
  Settings,
  Activity,
  Layers,
  Sparkles,
} from "lucide-react";

interface NavItem {
  title: string;
  href: string;
  icon: any;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export function AdminSidebar() {
  const pathname = usePathname();

  const sections: NavSection[] = [
    {
      title: "Overview",
      items: [
        { title: "Marketplace Dashboard", href: "/", icon: LayoutDashboard },
        { title: "Live Logistics Map", href: "/live-map", icon: MapPin, badge: "Live" },
      ],
    },
    {
      title: "Commerce & Logistics",
      items: [
        { title: "Global Orders", href: "/orders", icon: ShoppingBag },
        { title: "Shipments Monitor", href: "/shipments", icon: Truck },
      ],
    },
    {
      title: "Vendors & KYC",
      items: [
        { title: "Artisan Workshops", href: "/shops", icon: Store, badge: "KYC" },
      ],
    },
    {
      title: "Accounting & Escrow",
      items: [
        { title: "Platform Financials", href: "/finance", icon: Wallet },
        { title: "Double-Entry Ledger", href: "/finance/ledger", icon: Receipt },
        { title: "Settlement Batches", href: "/settlements", icon: FileCheck2 },
      ],
    },
    {
      title: "Governance & Tools",
      items: [
        { title: "Promotions & Coupons", href: "/coupons", icon: Tag },
        { title: "Review Moderation", href: "/reviews", icon: Star },
        { title: "Audit Trail", href: "/audit", icon: ShieldAlert },
        { title: "Platform Settings", href: "/settings", icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 min-h-screen">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-white shadow-md shadow-amber-900/30">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-tight flex items-center gap-1.5">
              Bazaar <span className="text-amber-400 font-mono text-xs px-1.5 py-0.5 rounded bg-amber-400/10 border border-amber-400/20">OPS</span>
            </span>
            <p className="text-[11px] text-slate-400">Marketplace Supervisor</p>
          </div>
        </Link>
      </div>

      {/* System Status Pill */}
      <div className="px-4 py-2.5 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>PostgreSQL & SSE Active</span>
        </div>
        <span className="text-slate-400 font-mono">v1.0.0</span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-3 space-y-4 overflow-y-auto">
        {sections.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {section.title}
            </div>
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? "text-amber-400" : "text-slate-400"}`} />
                    <span>{item.title}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${
                        item.badge === "Live"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Escrow Pool Quick Stat */}
      <div className="p-3 m-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="flex items-center gap-1.5 text-[11px]">
            <Activity className="w-3.5 h-3.5 text-amber-400" />
            Escrow Liability Pool
          </span>
          <span className="text-[10px] text-emerald-400 font-mono">100% BALANCED</span>
        </div>
        <div className="text-base font-bold text-white font-mono">₹4,28,450.00</div>
        <p className="text-[10px] text-slate-400 mt-1">Multi-party double-entry verified</p>
      </div>

      {/* Operator User Card */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/50 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-amber-400 text-xs">
            VM
          </div>
          <div>
            <div className="font-semibold text-slate-200">Vikram Malhotra</div>
            <div className="text-[10px] text-slate-400">Chief Market Operator</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
