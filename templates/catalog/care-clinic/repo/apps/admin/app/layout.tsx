import "./globals.css";
import type { Metadata } from "next";
import { AdminSessionProvider } from "../lib/session";

export const metadata: Metadata = {
  title: {
    default: "CareClinic Ops",
    template: "%s · CareClinic Ops",
  },
  description:
    "Front desk reception, doctor rostering, diagnostics, cashier and practice operations for CareClinic Indiranagar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {/* Every page is a client page behind the staff guard; the provider owns the session and
            the one event-stream connection the whole console shares. */}
        <AdminSessionProvider>{children}</AdminSessionProvider>
      </body>
    </html>
  );
}
