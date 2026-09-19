import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";

export default async function SettingsLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return <AppShell user={user}>{children}</AppShell>;
}
