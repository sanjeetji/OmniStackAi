import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";

export default async function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/admin");
  return <AppShell user={user}>{children}</AppShell>;
}
