import Link from "next/link";
import type { ControlPlaneUser } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import AppNav from "./app-nav";
import BrandMark from "./brand-mark";
import UserMenu from "./user-menu";
import WorkspaceSwitcher from "./workspace-switcher";

/** The application shell every signed-in screen (and the public /fabric page) renders inside:
 * a skip-to-content link, a sticky header with the brand, primary navigation and the account
 * menu (or sign-in actions when signed out), and the `<main>` landmark. Server component; the
 * only client pieces are the nav (needs the pathname) and the menu (needs state).
 *
 * `layout="contained"` (default) centers content in a 1180px column with page padding;
 * `layout="full"` hands the whole viewport width to the page as a flex column - the Studio
 * (R-493) lays out its own chat rail + workspace grid against the full width. */
export default function AppShell({
  user,
  layout = "contained",
  children,
}: Readonly<{
  user: ControlPlaneUser | null;
  layout?: "contained" | "full";
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-lg focus:outline-none"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div
          className={cn(
            "flex h-14 w-full items-center gap-4",
            layout === "contained" ? "mx-auto max-w-[1180px] px-6" : "px-4",
          )}
        >
          <div className="flex items-center gap-3">
            <Link
              href="/"
              aria-label="OmniStackAI home"
              className="flex items-center gap-2 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <BrandMark className="size-6" />
              <span className="text-sm font-semibold tracking-tight">OmniStackAI</span>
            </Link>
            {user && (
              <>
                <span className="text-border/60 font-light select-none">/</span>
                <WorkspaceSwitcher />
              </>
            )}
          </div>
          <AppNav />
          <div className="ml-auto flex items-center gap-2">
            {user ? (
              <UserMenu user={user} />
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link href="/login">Sign in</Link>
                </Button>
                <Button asChild size="sm">
                  <Link href="/register">Create account</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>
      <main
        id="main"
        tabIndex={-1}
        className={cn(
          "flex-1 outline-none",
          layout === "contained"
            ? "mx-auto w-full max-w-[1180px] px-6 pt-8 pb-18"
            : "flex min-h-0 flex-col",
        )}
      >
        {children}
      </main>
    </div>
  );
}
