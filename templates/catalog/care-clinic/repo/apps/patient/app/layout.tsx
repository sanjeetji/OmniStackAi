import type { Metadata } from "next";
import "./globals.css";
import { DemoBanner } from "@/components/demo-banner";
import { PatientHeader } from "@/components/patient-header";
import { PatientFooter } from "@/components/patient-footer";

export const metadata: Metadata = {
  title: "CareClinic — Patient Healthcare & Telemedicine Portal",
  description:
    "Comprehensive patient health portal for in-clinic appointment booking, high-definition telehealth consultations, digital prescriptions, and longitudinal electronic medical records.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased selection:bg-teal-100 selection:text-teal-900">
        <DemoBanner />
        <PatientHeader />
        <main className="flex-1 pb-16">{children}</main>
        <PatientFooter />
      </body>
    </html>
  );
}
