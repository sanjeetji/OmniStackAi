import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";

/** The /studio auth gate lives here (R-475) so every Studio view inherits it; the visible chrome
 * is the shared AppShell (R-492), in its full-width layout so the Studio's own chat-rail +
 * workspace grid (R-493) can use the whole viewport. */
export default async function StudioLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <AppShell user={user} layout="full">
      {children}
    </AppShell>
  );
}
