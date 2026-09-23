import type { Metadata } from "next";
import "./globals.css";
import { DoctorSidebar } from "@/components/doctor-sidebar";
import { DoctorHeader } from "@/components/doctor-header";

export const metadata: Metadata = {
  title: "CareClinic — Doctor Telehealth & Clinical Workstation",
  description:
    "High-efficiency clinical workstation for outpatient queue management, SOAP clinical documentation, ICD-10 coding, digital prescriptions, and telemedicine calls.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-100 text-slate-900 flex min-h-screen font-sans antialiased selection:bg-emerald-100 selection:text-emerald-900">
        <DoctorSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <DoctorHeader />
          <main className="flex-1 p-6 lg:p-8 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
