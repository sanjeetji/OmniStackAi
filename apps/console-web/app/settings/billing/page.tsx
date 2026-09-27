import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { BillingPanel } from "@/components/billing-panel";

export const metadata: Metadata = { title: "Plan and billing" };

export default async function BillingPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/settings/billing");
  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Plan and billing</h1>
      <p className="mt-1 text-sm text-muted-foreground">What your plan includes, and credits for building.</p>
      <BillingPanel />
    </main>
  );
}
