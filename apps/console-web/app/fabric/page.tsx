import overview from "@/data/overview.json";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";

export const metadata = {
  title: "Model Fabric",
};

export default async function FabricPage() {
  const { routingLadder, providers, priceBook, resilience, usage, builderShowcase } = overview;

  // This page is public (it renders a static overview); the shell just needs to know whether to
  // show the account menu or the sign-in actions, and must not break if the control-plane is down.
  let user = null;
  try {
    user = await getCurrentUser();
  } catch {
    user = null;
  }

  return (
    <AppShell user={user}>
      <header className="masthead">
        <div>
          <p className="eyebrow">Founder Stage 0 · local-first</p>
          <h1>Model Fabric &amp; Cost Overview</h1>
          <p className="lede">{overview.note}</p>
        </div>
      </header>

      <section className="panel">
        <h2>Routing ladder ({overview.routingMode})</h2>
        <ul className="ladder" style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {routingLadder.map((step) => (
            <li
              key={step.level}
              style={{
                display: "flex",
                gap: 12,
                alignItems: "baseline",
                padding: "7px 0",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <span style={{ fontWeight: 700, width: 34, color: "var(--brand)" }}>
                {step.level}
              </span>
              <span>{step.action}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Providers</h2>
        <div className="overflow">
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Tier</th>
                <th>Default model</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.providerId}>
                  <td>{provider.providerId}</td>
                  <td>
                    <span className={`badge ${provider.tier === "local" ? "on" : "off"}`}>
                      {provider.tier}
                    </span>
                  </td>
                  <td className="mono">{provider.defaultModel}</td>
                  <td>
                    <span className={`badge ${provider.active ? "on" : "off"}`}>
                      {provider.active ? "Active" : "Needs key"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Price book</h2>
        <div className="overflow">
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Model</th>
                <th className="num">Input $/M tok</th>
                <th className="num">Output $/M tok</th>
              </tr>
            </thead>
            <tbody>
              {priceBook.map((entry) => (
                <tr key={`${entry.providerId}:${entry.modelId}`}>
                  <td>{entry.providerId}</td>
                  <td className="mono">{entry.modelId}</td>
                  <td className="num">{entry.inputPerMTokUsd}</td>
                  <td className="num">{entry.outputPerMTokUsd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Usage &amp; resilience</h2>
        <div className="grid">
          <div className="stat">
            <div className="label">Total calls</div>
            <div className="value">{usage.totalCalls}</div>
          </div>
          <div className="stat">
            <div className="label">Successful calls</div>
            <div className="value">{usage.successfulCalls}</div>
          </div>
          <div className="stat">
            <div className="label">Total cost (USD)</div>
            <div className="value">{usage.totalCostUsd}</div>
          </div>
          <div className="stat">
            <div className="label">Circuit breaker</div>
            <div className="value">
              <span className={`badge ${resilience.circuitBreaker.enabled ? "on" : "off"}`}>
                {resilience.circuitBreaker.enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Builder showcase</h2>
        <p className="muted">{builderShowcase.note}</p>
        <h3 style={{ marginTop: 16, fontSize: 15 }}>
          {builderShowcase.projectPlan.appName}
        </h3>
        <div className="grid" style={{ marginTop: 8 }}>
          {builderShowcase.projectPlan.apps.map((app) => (
            <div key={app.appDir} className="stat">
              <div className="label">{app.label}</div>
              <div className="value mono" style={{ fontSize: 13 }}>
                {app.appDir}
              </div>
              <p className="muted" style={{ margin: "6px 0 0", fontSize: 12 }}>
                {app.verify.gates.join(" → ")}
              </p>
            </div>
          ))}
        </div>

        <h3 style={{ marginTop: 20, fontSize: 15 }}>
          Edit preview — {builderShowcase.editPreview.baseExample}
        </h3>
        <p className="muted">{builderShowcase.editPreview.requestedChange}</p>
        <pre className="mono overflow" style={{ background: "var(--bg)", padding: 16, borderRadius: 12 }}>
          {builderShowcase.editPreview.unifiedPatch}
        </pre>
      </section>
    </AppShell>
  );
}
