import Link from "next/link";

export function Logo({ href = "/", light = false }: { href?: string; light?: boolean }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2 rounded-lg outline-none focus-visible:ring-4 focus-visible:ring-amber/40" aria-label="RideNow home">
      <span className="grid size-9 place-items-center rounded-xl bg-amber text-ink shadow-[0_6px_16px_-8px_rgb(229_148_0/0.9)]">
        <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
          <path d="M5 16.5 7.2 9.8A2.5 2.5 0 0 1 9.6 8h4.8a2.5 2.5 0 0 1 2.4 1.8L19 16.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          <circle cx="8" cy="17" r="1.9" fill="currentColor" />
          <circle cx="16" cy="17" r="1.9" fill="currentColor" />
        </svg>
      </span>
      <span className={`text-xl font-extrabold tracking-tight ${light ? "text-white" : "text-ink"}`}>
        Ride<span className="text-amber-deep">Now</span>
      </span>
    </Link>
  );
}
