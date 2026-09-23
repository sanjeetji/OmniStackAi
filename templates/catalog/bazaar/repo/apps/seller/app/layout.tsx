import type { Metadata } from "next";
import "./globals.css";
import { SellerDemoBanner } from "@/components/demo-banner";
import { SellerSidebar } from "@/components/seller-sidebar";

export const metadata: Metadata = {
  title: "Bazaar Artisan Atelier Portal",
  description: "Merchant workshop fulfillment, inventory, and ledger console for master Indian craftspeople.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-stone-100/70 text-stone-900">
        <SellerDemoBanner />
        <div className="flex">
          <SellerSidebar />
          <div className="flex-1 flex flex-col min-w-0 min-h-[calc(100vh-37px)]">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
