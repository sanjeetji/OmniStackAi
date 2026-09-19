import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { ThemeProvider } from "./theme-provider";

// Self-hosted via next/font (Next 16's own font guide): no external request, no layout shift.
// Geist Mono covers every code/monospace surface - file viewer, problems, usage numbers.
const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

const DESCRIPTION =
  "Describe an app in plain English and get a real, owned codebase - web, backend, and database - with verification built in.";

/** Absolute base for metadata URLs (og:image etc.). Production sets the optional
 * OMNISTACKAI_CONSOLE_PUBLIC_URL (see .env.example); local dev falls back to the console's real
 * address rather than an invented domain. An unparsable value falls back the same way. */
function resolveMetadataBase(): URL {
  const configured = process.env.OMNISTACKAI_CONSOLE_PUBLIC_URL?.trim();
  const fallback = `http://127.0.0.1:${process.env.OMNISTACKAI_CONSOLE_PORT?.trim() || "4321"}`;
  try {
    return new URL(configured || fallback);
  } catch {
    return new URL(fallback);
  }
}

export const metadata: Metadata = {
  metadataBase: resolveMetadataBase(),
  title: { default: "OmniStackAI", template: "%s · OmniStackAI" },
  description: DESCRIPTION,
  applicationName: "OmniStackAI",
  openGraph: {
    type: "website",
    siteName: "OmniStackAI",
    title: "OmniStackAI",
    description: DESCRIPTION,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "OmniStackAI",
    description: DESCRIPTION,
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    // suppressHydrationWarning: next-themes sets the theme class on <html> before hydration.
    <html lang="en" className={cn("font-sans", geist.variable, geistMono.variable)} suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <TooltipProvider>{children}</TooltipProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
