import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center px-6">
      <div className="max-w-sm text-center">
        <p className="font-mono text-sm font-semibold text-signal">404</p>
        <h1 className="mt-2 text-xl font-semibold">This page does not exist</h1>
        <p className="mt-1 text-[13px] text-muted">The link may be old, or the record was removed.</p>
        <Link href="/" className="mt-5 inline-flex h-9 items-center rounded-box bg-signal px-3.5 text-sm font-semibold text-white hover:bg-signal-deep">
          Back to the dashboard
        </Link>
      </div>
    </main>
  );
}
