import Link from "next/link";
import type { ControlPlaneUser } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
import AppNav from "./app-nav";
import BrandMark from "./brand-mark";
import UserMenu from "./user-menu";

/** The application shell every signed-in screen (and the public /fabric page) renders inside:
 * a skip-to-content link, a sticky header with the brand, primary navigation and the account
 * menu (or sign-in actions when signed out), and the `<main>` landmark. Server component; the
 * only client pieces are the nav (needs the pathname) and the menu (needs state).
 *
 * `<main>` keeps the legacy `.studio-main` geometry (1180px, 32/24/72px padding) on purpose: the
 * Studio workspace's own CSS still sizes its chat rail against it until R-493 rebuilds that. */
export default function AppShell({
  user,
  children,
}: Readonly<{ user: ControlPlaneUser | null; children: React.ReactNode }>) {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-lg focus:outline-none"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex h-14 w-full max-w-[1180px] items-center gap-4 px-6">
          <Link
            href="/"
            aria-label="OmniStackAI home"
            className="flex items-center gap-2 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <BrandMark className="size-6" />
            <span className="text-sm font-semibold tracking-tight">OmniStackAI</span>
          </Link>
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
        className="mx-auto w-full max-w-[1180px] flex-1 px-6 pt-8 pb-18 outline-none"
      >
        {children}
      </main>
    </div>
  );
}
