import { redirect } from "next/navigation";
import Link from "next/link";
import { getCurrentUser } from "@/lib/session";
import LogoutButton from "./logout-button";

export default async function HomePage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <main className="wrap">
      <header className="masthead">
        <div>
          <p className="eyebrow">OmniStackAI</p>
          <h1>Welcome back, {user.name}</h1>
          <p className="lede">{user.email}</p>
        </div>
        <LogoutButton />
      </header>

      <section className="panel">
        <h2>Your account</h2>
        <div className="grid">
          <div className="stat">
            <div className="label">Role</div>
            <div className="value">{user.role}</div>
          </div>
          <div className="stat">
            <div className="label">Plan</div>
            <div className="value">{user.plan}</div>
          </div>
          <div className="stat">
            <div className="label">Credit balance</div>
            <div className="value">{user.credit_balance}</div>
          </div>
          <div className="stat">
            <div className="label">Bring your own key</div>
            <div className="value">
              <span className={`badge ${user.byok_enabled ? "on" : "off"}`}>
                {user.byok_enabled ? "Enabled" : "Not enabled"}
              </span>
            </div>
          </div>
        </div>
      </section>

      <p className="muted" style={{ marginTop: 20 }}>
        <Link href="/studio">Open the Studio to build an app →</Link>
      </p>
      <p className="muted" style={{ marginTop: 8 }}>
        <Link href="/fabric">View the model fabric &amp; cost overview →</Link>
      </p>
    </main>
  );
}
