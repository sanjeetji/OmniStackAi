import type { Metadata } from "next";
import "./globals.css";
import { OperatorSessionProvider } from "../lib/session";

export const metadata: Metadata = {
  title: {
    default: "Bazaar Ops",
    template: "%s · Bazaar Ops",
  },
  description:
    "Marketplace operations: vendor onboarding and KYC, orders and consignments, the double-entry ledger, settlements, coupons, reviews and the audit trail.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased bg-[var(--background)] text-slate-100">
        {/* Every screen is a client screen behind the operator guard; the provider owns the session
            and the one event-stream connection the whole console shares. */}
        <OperatorSessionProvider>{children}</OperatorSessionProvider>
      </body>
    </html>
  );
}
