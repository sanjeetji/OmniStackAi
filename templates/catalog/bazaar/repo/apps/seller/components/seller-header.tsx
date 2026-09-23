"use client";

import Link from "next/link";
import { Plus, Bell } from "lucide-react";

export function SellerHeader({ title, description }: { title: string; description?: string }) {
  return (
    <header className="bg-white border-b border-stone-200 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 className="text-xl sm:text-2xl font-serif font-bold text-stone-900">{title}</h1>
        {description && <p className="text-xs text-stone-500 mt-0.5">{description}</p>}
      </div>

      <div className="flex items-center gap-3">
        <button
          className="p-2 rounded-xl text-stone-500 hover:text-stone-800 hover:bg-stone-100 transition relative"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-amber-600 absolute top-1.5 right-1.5 ring-2 ring-white"></span>
        </button>

        <Link
          href="/products/new"
          className="px-4 py-2 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Craft Listing</span>
        </Link>
      </div>
    </header>
  );
}
