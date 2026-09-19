import Link from "next/link";
import { ArrowLeft, Sparkles } from "lucide-react";
import BrandMark from "@/components/brand-mark";
import { Button } from "@/components/ui/button";

/** Root not-found: per Next 16's `not-found.js` convention this also serves every URL that
 * matches no route at all. It renders inside the root layout but outside the app shell, because
 * the sign-in state is unknown here and a wrong shell would be worse than none. */
export default function NotFound() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-background px-6 text-center">
      <BrandMark className="size-10" title="OmniStackAI" />
      <p className="mt-8 font-mono text-sm tabular-nums text-muted-foreground">404</p>
      <h1 className="mt-2 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
        This page doesn&rsquo;t exist
      </h1>
      <p className="mt-3 max-w-md text-pretty text-muted-foreground">
        The link may be out of date, or the address was typed wrong. Nothing on your account has
        changed.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <Button asChild>
          <Link href="/">
            <ArrowLeft aria-hidden="true" />
            Go home
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/studio">
            <Sparkles aria-hidden="true" />
            Open Studio
          </Link>
        </Button>
      </div>
    </main>
  );
}
