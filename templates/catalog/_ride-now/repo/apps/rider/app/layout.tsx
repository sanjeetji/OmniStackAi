import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { SessionProvider } from "@/lib/session";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta", display: "swap" });

export const metadata: Metadata = {
  title: { default: "RideNow · Rides across Bengaluru", template: "%s · RideNow" },
  description: "Book bikes, autos and cabs in seconds. Upfront fares, live tracking and verified drivers.",
};

export const viewport: Viewport = { themeColor: "#0b1b2b", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={jakarta.variable}>
      <body className="min-h-dvh font-sans">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
