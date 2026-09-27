import Link from "next/link";
import BrandMark from "./brand-mark";

/** PC-012: the frame for the Terms of Service and Privacy Policy. Public; readable signed out. */
export default function LegalPage({
  title,
  version,
  children,
}: Readonly<{ title: string; version: string; children: React.ReactNode }>) {
  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border/60">
        <div className="mx-auto flex h-14 max-w-[760px] items-center gap-2 px-6">
          <Link href="/" aria-label="OmniStackAI home" className="flex items-center gap-2">
            <BrandMark className="size-6" />
            <span className="text-sm font-semibold tracking-tight">OmniStackAI</span>
          </Link>
          <nav className="ml-auto flex gap-4 text-sm text-muted-foreground">
            <Link href="/terms" className="hover:text-foreground">Terms</Link>
            <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-[760px] px-6 pt-10 pb-20">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Version {version}</p>
        <p className="mt-4 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
          Beta draft. This text is pending review by counsel and may change before general availability;
          you will be asked to accept any new version.
        </p>
        <div className="legal mt-8 grid gap-6 text-sm leading-relaxed [&_h2]:mt-2 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-foreground [&_li]:ml-5 [&_li]:list-disc [&_p]:text-muted-foreground [&_ul]:grid [&_ul]:gap-1.5 [&_ul]:text-muted-foreground">
          {children}
        </div>
      </main>
    </div>
  );
}
