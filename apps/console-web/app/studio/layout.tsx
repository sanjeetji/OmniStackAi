import { redirect } from "next/navigation";
import Link from "next/link";
import { getCurrentUser } from "@/lib/session";
import LogoutButton from "../logout-button";
import { BackArrowIcon } from "./studio-icons";

export default async function StudioLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <div className="studio-shell">
      <header className="studio-topbar">
        <Link href="/" className="studio-topbar-back" aria-label="Back to home">
          <BackArrowIcon />
          <span className="studio-topbar-brand">OmniStackAI Studio</span>
        </Link>
        <LogoutButton />
      </header>
      <main className="studio-main">{children}</main>
    </div>
  );
}
