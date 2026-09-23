import type { Metadata } from "next";
import "./globals.css";
import { AdminShell } from "@/components/admin-shell";

export const metadata: Metadata = {
  title: "Bazaar Marketplace Operations Console",
  description: "Marketplace operator supervisor console for multi-vendor onboarding, KYC, ledger audit, and order fulfillment.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-950 text-slate-100">
        <AdminShell>{children}</AdminShell>
      </body>
    </html>
  );
}
