import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { AdminConsole } from "@/components/admin-console";

export const metadata: Metadata = { title: "Admin console" };

// PC-011: the super_admin console. Anyone else gets the same "not found" as the API gives them.
export default async function AdminPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/admin");
  if (user.role !== "super_admin") notFound();
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">Admin console</h1>
      <p className="mt-1 text-sm text-muted-foreground">Accounts, credits, plans and platform spending. Every change is recorded.</p>
      <AdminConsole selfId={user.id} />
    </main>
  );
}
