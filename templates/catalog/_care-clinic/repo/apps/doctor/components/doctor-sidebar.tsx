"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Stethoscope,
  LayoutDashboard,
  Users,
  Calendar,
  CalendarDays,
  DollarSign,
  Star,
  ShieldCheck,
  Video,
  LogOut,
  Clock,
} from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";

export function DoctorSidebar() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Clinical Dashboard", icon: LayoutDashboard },
    { href: "/queue", label: "Today's Queue", icon: Users, badge: "6 Active" },
    { href: "/patients", label: "Patient Directory", icon: Users },
    { href: "/schedule", label: "Schedule Matrix", icon: Calendar },
    { href: "/schedule/rules", label: "Availability Rules", icon: CalendarDays },
    { href: "/earnings", label: "Billing & Earnings", icon: DollarSign },
    { href: "/reviews", label: "Patient Reviews", icon: Star },
  ];

  const handleLogout = () => {
    defaultApiClient.clearSession();
    window.location.reload();
  };

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-screen border-r border-slate-800">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold shadow-sm shrink-0">
          <Stethoscope className="w-6 h-6 text-white" />
        </div>
        <div>
          <span className="text-white font-extrabold text-base block tracking-tight">CareClinic</span>
          <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider block -mt-0.5">
            Physician Workstation
          </span>
        </div>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? "bg-emerald-600 text-white shadow-xs"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className="w-4 h-4" />
                <span>{link.label}</span>
              </div>
              {link.badge && (
                <span className="bg-emerald-500/20 text-emerald-300 text-[10px] px-2 py-0.5 rounded-md font-bold">
                  {link.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Doctor Status Card */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-800/80 text-teal-200 font-bold flex items-center justify-center text-sm shrink-0">
            RV
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-xs font-bold text-white block truncate">Dr. Rajesh Varma, MD</span>
            <span className="text-[10px] text-emerald-400 block truncate">OPD 101 • First Floor</span>
            <span className="text-[10px] text-slate-400 block">KMC Reg: 48291</span>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>OPD In-Session</span>
          </span>
          <button
            onClick={handleLogout}
            className="text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
