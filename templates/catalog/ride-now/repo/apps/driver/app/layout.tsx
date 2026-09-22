import type { Metadata, Viewport } from "next";
import { Sora } from "next/font/google";
import { DriverProvider } from "@/lib/driver";
import "./globals.css";

const sora = Sora({ subsets: ["latin"], variable: "--font-sora", display: "swap" });

export const metadata: Metadata = {
  title: { default: "RideNow Driver", template: "%s · RideNow Driver" },
  description: "Go online, accept rides and track your earnings.",
  appleWebApp: { capable: true, title: "RideNow Driver", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: "#0b0e13",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={sora.variable}>
      <body className="min-h-dvh font-sans">
        <DriverProvider>{children}</DriverProvider>
      </body>
    </html>
  );
}
