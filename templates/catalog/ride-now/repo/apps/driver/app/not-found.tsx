import Link from "next/link";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <main className="mx-auto grid min-h-dvh max-w-md place-content-center gap-4 px-6 text-center">
      <p className="text-6xl font-extrabold text-go">404</p>
      <h1 className="text-2xl font-extrabold">Wrong turn</h1>
      <p className="text-fg-muted">This page doesn't exist. Head back to Home to go online.</p>
      <Link href="/" className="mx-auto inline-flex h-12 items-center rounded-2xl bg-go px-6 text-sm font-bold text-bg">Back to Home</Link>
    </main>
  );
}
