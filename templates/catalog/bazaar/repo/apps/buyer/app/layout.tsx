import type { Metadata } from "next";
import "./globals.css";
import { Header } from "../components/header.tsx";
import { Footer } from "../components/footer.tsx";
import { DemoBanner } from "../components/demo-banner.tsx";

export const metadata: Metadata = {
  title: "Bazaar — Handcrafted & Artisanal Multi-Vendor Marketplace",
  description:
    "Explore authentic handloom sarees, terracotta pottery, brassware, single-origin spices, and fine silver jewelry from master artisans across India.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-stone-50/50 text-stone-900 antialiased selection:bg-amber-200">
        <DemoBanner />
        <Header />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
