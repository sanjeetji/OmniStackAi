import { redirect } from "next/navigation";
import Link from "next/link";
import { getCurrentUser } from "@/lib/session";
import StudioForm from "./studio-form";

export const metadata = {
  title: "Studio — OmniStackAI Console",
};

export default async function StudioPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <main className="wrap wrap--wide">
      <header className="masthead">
        <div>
          <p className="eyebrow">OmniStackAI</p>
          <h1>Studio</h1>
          <p className="lede">
            Describe an app in plain English. It becomes a real, owned Git repository.
          </p>
        </div>
        <Link href="/" className="button button--secondary">
          ← Back
        </Link>
      </header>

      <StudioForm initialCreditBalance={user.credit_balance} />
    </main>
  );
}
