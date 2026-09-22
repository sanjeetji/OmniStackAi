import type { Metadata, Viewport } from "next";
import { Instrument_Sans } from "next/font/google";
import { AdminProvider } from "@/lib/session";
import "./globals.css";

const instrument = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument", display: "swap" });

export const metadata: Metadata = {
  title: { default: "RideNow Ops", template: "%s · RideNow Ops" },
  description: "Run the RideNow city: live trips, drivers, pricing, payouts and support.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: "#0b1320",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={instrument.variable}>
      <body className="min-h-dvh font-sans">
        <AdminProvider>{children}</AdminProvider>
      </body>
    </html>
  );
}
