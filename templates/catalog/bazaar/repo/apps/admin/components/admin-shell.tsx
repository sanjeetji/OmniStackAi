"use client";

import { usePathname } from "next/navigation";
import { AdminSidebar } from "./admin-sidebar";
import { DemoBanner } from "./demo-banner";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col">
        <DemoBanner />
        <main className="flex-1 flex items-center justify-center p-4">
          {children}
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <DemoBanner />
      <div className="flex flex-1 min-h-[calc(100vh-37px)]">
        <AdminSidebar />
        <main className="flex-1 flex flex-col min-w-0 bg-slate-900/40">
          {children}
        </main>
      </div>
    </div>
  );
}
