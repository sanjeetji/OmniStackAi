"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Layers, Settings2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/studio", label: "Studio", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings2 },
  { href: "/fabric", label: "Fabric", icon: Layers },
] as const;

function isCurrent(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Primary navigation. The current section is marked with `aria-current="page"` (and styled
 * from it) so both keyboard/screen-reader users and sighted users know where they are. */
export default function AppNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex items-center gap-0.5">
      {ITEMS.map(({ href, label, icon: Icon }) => {
        const current = isCurrent(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium outline-none transition-colors select-none",
              "focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px",
              current
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            <span className="hidden sm:inline">{label}</span>
            <span className="sr-only sm:hidden">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
