import Link from "next/link";
import { CircleCheck } from "lucide-react";
import BrandMark from "./brand-mark";

/* Three statements about what the product does today - each one true of the shipped code, not
 * aspirational copy. */
const POINTS = [
  "Real Next.js, Python and Go code you can read, run and export",
  "A live preview and multi-turn edits in one workspace",
  "Your own local model stays free to run; cloud models spend credits",
];

/** Split-screen frame for the sign-in and create-account pages: a brand panel on wide screens,
 * a compact brand row on small ones, and the form card. Server component. */
export default function AuthScreen({
  title,
  description,
  footer,
  children,
}: Readonly<{
  title: string;
  description?: string;
  footer: React.ReactNode;
  children: React.ReactNode;
}>) {
  return (
    <div className="grid min-h-dvh bg-background lg:grid-cols-[1.1fr_1fr]">
      <section
        aria-label="About OmniStackAI"
        className="grain relative hidden overflow-hidden border-r border-border/60 bg-card lg:flex lg:flex-col lg:justify-between lg:p-10"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-40 -left-32 size-[520px] rounded-full bg-brand/15 blur-3xl"
        />
        <Link
          href="/"
          aria-label="OmniStackAI home"
          className="relative flex w-fit items-center gap-2 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <BrandMark className="size-7" />
          <span className="text-sm font-semibold tracking-tight">OmniStackAI</span>
        </Link>
        <div className="relative max-w-md">
          <p className="text-balance text-4xl font-semibold tracking-tight leading-[1.05]">
            Describe the app. Get the codebase.
          </p>
          <p className="mt-4 text-pretty text-muted-foreground">
            OmniStackAI turns a plain-language description into a real, multi-service project you
            own, with a live preview and a chat to keep changing it.
          </p>
          <ul className="mt-8 grid gap-3 text-sm">
            {POINTS.map((point) => (
              <li key={point} className="flex gap-2.5">
                <CircleCheck className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-muted-foreground">Founder Stage 0 · local-first</p>
      </section>

      <section className="flex flex-col px-6 py-6 sm:px-10">
        <Link
          href="/"
          aria-label="OmniStackAI home"
          className="flex w-fit items-center gap-2 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50 lg:hidden"
        >
          <BrandMark className="size-6" />
          <span className="text-sm font-semibold tracking-tight">OmniStackAI</span>
        </Link>
        <div className="reveal my-auto w-full max-w-sm self-center py-10">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description ? (
            <p className="mt-1.5 text-pretty text-sm text-muted-foreground">{description}</p>
          ) : null}
          <div className="mt-8">{children}</div>
          <p className="mt-6 text-sm text-muted-foreground">{footer}</p>
        </div>
      </section>
    </div>
  );
}
