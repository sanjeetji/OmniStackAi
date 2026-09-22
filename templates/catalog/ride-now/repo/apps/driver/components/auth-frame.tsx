import Link from "next/link";

/** Signed-out frame for sign-in and sign-up: brand mark, a heading and the form. */
export function AuthFrame({ title, subtitle, children, footer }: { title: string; subtitle: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <main className="mx-auto grid min-h-dvh max-w-md content-start gap-7 px-5 pb-10 pt-[max(2.5rem,env(safe-area-inset-top))]">
      <Link href="/" className="flex items-center gap-2.5 font-extrabold" aria-label="RideNow Driver home">
        <span className="grid size-10 place-items-center rounded-2xl bg-go text-bg">
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M5 17h14M6 17l1.6-5.2A2 2 0 0 1 9.5 10.4h5a2 2 0 0 1 1.9 1.4L18 17" />
            <circle cx="8" cy="18" r="1.4" />
            <circle cx="16" cy="18" r="1.4" />
          </svg>
        </span>
        <span>RideNow <span className="text-go">Driver</span></span>
      </Link>
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">{title}</h1>
        <p className="mt-2 text-fg-muted">{subtitle}</p>
      </div>
      {children}
      <div className="text-center text-sm text-fg-muted">{footer}</div>
    </main>
  );
}
