import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center px-6 text-center">
      <div>
        <p className="text-6xl" aria-hidden="true">🛺</p>
        <h1 className="mt-4 text-3xl font-extrabold">Wrong turn</h1>
        <p className="mt-2 text-muted">This page doesn't exist. Let's get you back on the road.</p>
        <Link href="/ride" className="mt-6 inline-flex h-11 items-center rounded-full bg-amber px-6 font-semibold text-ink">Book a ride</Link>
      </div>
    </main>
  );
}
