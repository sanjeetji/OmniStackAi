"use client";

import Link from "next/link";
import { ArrowLeft, RefreshCw, TriangleAlert } from "lucide-react";
import BrandMark from "@/components/brand-mark";
import { Button } from "@/components/ui/button";

/** Route error boundary (Next `error.js` - must be a client component). In production Next
 * replaces a server error's message with a generic one and gives `digest`, which matches the
 * server log - so the digest is shown as a reference, never a raw message. `retry()` re-fetches
 * and re-renders the boundary's children (Next 16's documented recovery path). */
export default function ErrorPage({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <main className="reveal flex min-h-dvh flex-col items-center justify-center bg-background px-6 text-center">
      <BrandMark className="size-10" title="OmniStackAI" />
      <p className="mt-8 inline-flex items-center gap-1.5 text-sm text-destructive">
        <TriangleAlert className="size-4" aria-hidden="true" />
        Something went wrong
      </p>
      <h1 className="mt-2 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
        This page hit an error
      </h1>
      <p className="mt-3 max-w-md text-pretty text-muted-foreground">
        It was logged on the server. Try again; if it keeps happening, start from the home page.
      </p>
      {error.digest ? (
        <p className="mt-3 font-mono text-xs text-muted-foreground">Reference {error.digest}</p>
      ) : null}
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <Button type="button" onClick={() => retry()}>
          <RefreshCw aria-hidden="true" />
          Try again
        </Button>
        <Button asChild variant="outline">
          <Link href="/">
            <ArrowLeft aria-hidden="true" />
            Go home
          </Link>
        </Button>
      </div>
    </main>
  );
}
