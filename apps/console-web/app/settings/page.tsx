import { getProviderStatus, type ProviderStatus } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export const metadata = {
  title: "Settings",
};

export default async function SettingsPage() {
  const token = await getSessionToken();
  let status: ProviderStatus | null = null;
  let error: string | null = null;
  if (token) {
    try {
      status = await getProviderStatus(token);
    } catch {
      error = "Could not reach the model provider status service.";
    }
  }

  return (
    <section className="panel">
      <h2>Model Providers</h2>
      <p className="studio-intro muted">
        Live status of the model fabric — which providers are configured, and which one would
        actually run your next build or edit right now.
      </p>
      {error ? <div className="error-banner">{error}</div> : null}

      {status ? (
        <>
          <div className="settings-active-now">
            {status.activeNow ? (
              <>
                <span className="badge on">Ready</span>
                <span>
                  Your next build will use <strong>{status.activeNow.providerId}</strong> (
                  <span className="mono">{status.activeNow.modelId}</span>)
                </span>
              </>
            ) : (
              <>
                <span className="badge off">Not ready</span>
                <span>{status.activeNowError ?? "No provider is currently available."}</span>
              </>
            )}
          </div>

          <div className="overflow" style={{ marginTop: 20 }}>
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
                {status.providers.map((provider) => (
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
        </>
      ) : null}
    </section>
  );
}
