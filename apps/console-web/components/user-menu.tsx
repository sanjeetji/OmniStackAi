"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, Coins, Layers, Loader2, LogOut, Settings2 } from "lucide-react";
import { toast } from "sonner";
import type { ControlPlaneUser } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function initialsFor(name: string, email: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  if (parts.length === 1 && parts[0].length > 0) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

/** The signed-in account menu. Built on the vendored shadcn DropdownMenu (Radix) so it is a real
 * menu: keyboard-navigable, focus-managed, dismissed on Escape/outside click. Sign-out keeps the
 * exact behavior the old LogoutButton had: POST /api/auth/logout (idempotent, always clears the
 * cookie), then go to /login and refresh the server components. */
export default function UserMenu({ user }: Readonly<{ user: ControlPlaneUser }>) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      toast.success("Signed out");
    } catch {
      toast.error("The sign-out request failed. Sending you to the sign-in page.");
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`Account menu for ${user.name}`}
          className="group inline-flex h-8 items-center gap-2 rounded-lg pr-2 pl-1 text-sm outline-none transition-colors select-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:bg-muted active:translate-y-px"
        >
          <span
            aria-hidden="true"
            className="flex size-6 items-center justify-center rounded-md bg-primary text-[11px] font-semibold text-primary-foreground"
          >
            {initialsFor(user.name, user.email)}
          </span>
          <span className="hidden max-w-32 truncate font-medium sm:inline">{user.name}</span>
          <ChevronDown
            aria-hidden="true"
            className="size-3.5 text-muted-foreground transition-transform group-aria-expanded:rotate-180"
          />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="grid gap-0.5">
          <span className="truncate text-sm font-medium text-foreground">{user.name}</span>
          <span className="truncate font-normal">{user.email}</span>
        </DropdownMenuLabel>
        <div className="flex items-center justify-between gap-2 px-1.5 py-1.5 text-xs">
          <Badge variant="secondary" className="capitalize">
            {user.plan} plan
          </Badge>
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <Coins className="size-3.5" aria-hidden="true" />
            <span className="font-mono tabular-nums text-foreground">
              {user.credit_balance.toLocaleString("en-US")}
            </span>
            credits
          </span>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild>
            <Link href="/settings">
              <Settings2 aria-hidden="true" />
              Settings
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/fabric">
              <Layers aria-hidden="true" />
              Model fabric
            </Link>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          disabled={signingOut}
          onSelect={(event) => {
            event.preventDefault();
            void handleSignOut();
          }}
        >
          {signingOut ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <LogOut aria-hidden="true" />
          )}
          {signingOut ? "Signing out…" : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
