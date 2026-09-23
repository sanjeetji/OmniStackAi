import "./globals.css";
import type { Metadata } from "next";
import { DoctorSessionProvider } from "../lib/session";

export const metadata: Metadata = {
  title: {
    default: "CareClinic Workstation",
    template: "%s · CareClinic Workstation",
  },
  description:
    "The physician's clinical workstation: today's queue, consultations, SOAP notes, e-prescriptions, lab orders and the patient chart.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {/* Every screen is a client screen behind the doctor guard; the provider owns the session
            and the one event-stream connection the whole workstation shares. */}
        <DoctorSessionProvider>{children}</DoctorSessionProvider>
      </body>
    </html>
  );
}
