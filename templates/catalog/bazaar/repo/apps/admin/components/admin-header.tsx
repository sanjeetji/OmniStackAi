"use client";

import Link from "next/link";
import { Search, Bell, ExternalLink, ShieldCheck } from "lucide-react";

interface AdminHeaderProps {
  title: string;
  subtitle?: string;
  badge?: string;
  actionText?: string;
  actionHref?: string;
  actionIcon?: any;
}

export function AdminHeader({
  title,
  subtitle,
  badge,
  actionText,
  actionHref,
  actionIcon: ActionIcon,
}: AdminHeaderProps) {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white tracking-tight">{title}</h1>
          {badge && (
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
              {badge}
            </span>
          )}
        </div>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Quick link to buyer storefront */}
        <a
          href="http://localhost:3001"
          target="_blank"
          rel="noreferrer"
          className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-800 text-xs text-slate-300 hover:text-white hover:bg-slate-900 transition"
        >
          <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
          Storefront Preview
        </a>

        {actionText && actionHref && (
          <Link
            href={actionHref}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-sm transition"
          >
            {ActionIcon && <ActionIcon className="w-3.5 h-3.5" />}
            {actionText}
          </Link>
        )}
      </div>
    </header>
  );
}
