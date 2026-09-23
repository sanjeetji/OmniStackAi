"use client";

import { Building2, Clock, CreditCard, Video } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Badge, Button, DataState } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { clock } from "../../lib/format";

export default function Settings() {
  const { prefs, setPrefs, user, signOut } = useSession();
  const settings = useApi(() => defaultApiClient.getClinicSettings(), []);

  return (
    <Shell title="Settings" subtitle="The clinic record, the booking rules, and what runs on a mock provider">
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="This clinic">
          <DataState state={settings}>
            {(data) => (
              <dl className="space-y-2.5 text-[13px]">
                {[
                  ["Name", data.clinic?.name ?? "—"],
                  ["Code", data.clinic?.code ?? "—"],
                  ["Address", `${data.clinic?.address ?? ""}${data.clinic?.city ? `, ${data.clinic.city}` : ""}`],
                  ["Pincode", data.clinic?.pincode ?? "—"],
                  ["Phone", data.clinic?.phone ?? "—"],
                  ["Email", data.clinic?.email ?? "—"],
                  [
                    "Opening hours",
                    data.clinic ? `${clock(data.clinic.opening_time)} – ${clock(data.clinic.closing_time)}` : "—",
                  ],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-start justify-between gap-6">
                    <dt className="shrink-0 text-[var(--color-ink-muted)]">{label}</dt>
                    <dd className="text-right font-medium text-[var(--color-ink)]">{value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </DataState>
        </Panel>

        <Panel title="Booking rules" subtitle="Enforced by the API, not by this screen">
          <DataState state={settings}>
            {(data) => (
              <ul className="space-y-3 text-[12.5px]">
                <li className="flex items-start gap-2.5">
                  <Clock size={15} className="mt-0.5 shrink-0 text-[var(--color-ink-subtle)]" />
                  <div>
                    <p className="font-medium text-[var(--color-ink)]">
                      {data.settings.defaultSlotDurationMins}-minute consultation slots
                    </p>
                    <p className="text-[var(--color-ink-muted)]">
                      Generated from each doctor's weekly rule; a booked slot cannot be taken twice, which the
                      database enforces.
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <CreditCard size={15} className="mt-0.5 shrink-0 text-[var(--color-ink-subtle)]" />
                  <div>
                    <p className="font-medium text-[var(--color-ink)]">Cancellation policy</p>
                    <p className="text-[var(--color-ink-muted)]">{data.settings.cancellationPolicy}</p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <Building2 size={15} className="mt-0.5 shrink-0 text-[var(--color-ink-subtle)]" />
                  <div>
                    <p className="font-medium text-[var(--color-ink)]">Queue tokens</p>
                    <p className="text-[var(--color-ink-muted)]">
                      {data.settings.autoAssignQueueTokens
                        ? "Issued automatically, per doctor per day, at check-in."
                        : "Issued by hand at the desk."}
                    </p>
                  </div>
                </li>
              </ul>
            )}
          </DataState>
        </Panel>

        <Panel title="Providers" subtitle="What is simulated in this deployment, and where the real one plugs in">
          <DataState state={settings}>
            {(data) => (
              <ul className="space-y-2.5 text-[12.5px]">
                {[
                  {
                    icon: <Video size={15} />,
                    name: "Telehealth video",
                    mock: data.settings.mockTelehealthProvider,
                    file: "services/api/src/services/telehealth.ts",
                  },
                  {
                    icon: <CreditCard size={15} />,
                    name: "Payment gateway",
                    mock: data.settings.mockPaymentGateway,
                    file: "services/api/src/services/billing.ts",
                  },
                ].map((provider) => (
                  <li key={provider.name} className="flex items-start justify-between gap-3 rounded-md border border-[var(--color-border)] p-3">
                    <div className="flex items-start gap-2.5">
                      <span className="mt-0.5 text-[var(--color-ink-subtle)]">{provider.icon}</span>
                      <div>
                        <p className="font-medium text-[var(--color-ink)]">{provider.name}</p>
                        <p className="tabular text-[11px] text-[var(--color-ink-muted)]">{provider.file}</p>
                      </div>
                    </div>
                    <Badge tone={provider.mock ? "alert" : "good"}>{provider.mock ? "Simulated" : "Live"}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </DataState>
        </Panel>

        <Panel title="This workstation" subtitle="Saved in this browser only">
          <div className="space-y-3 text-[12.5px]">
            <label className="flex items-center justify-between gap-4">
              <span>
                <span className="block font-medium text-[var(--color-ink)]">Chime when a token is called</span>
                <span className="text-[var(--color-ink-muted)]">Useful at a busy counter; silent on shared screens.</span>
              </span>
              <input
                type="checkbox"
                className="h-4 w-4 accent-[var(--color-signal)]"
                checked={prefs.sound}
                onChange={(event) => setPrefs({ ...prefs, sound: event.target.checked })}
              />
            </label>

            <label className="flex items-center justify-between gap-4">
              <span>
                <span className="block font-medium text-[var(--color-ink)]">Show money columns</span>
                <span className="text-[var(--color-ink-muted)]">Hide fees on a screen the waiting room can see.</span>
              </span>
              <input
                type="checkbox"
                className="h-4 w-4 accent-[var(--color-signal)]"
                checked={prefs.showMoney}
                onChange={(event) => setPrefs({ ...prefs, showMoney: event.target.checked })}
              />
            </label>

            <label className="flex items-center justify-between gap-4">
              <span>
                <span className="block font-medium text-[var(--color-ink)]">Fallback refresh</span>
                <span className="text-[var(--color-ink-muted)]">
                  How often a screen reloads when the live stream is unavailable.
                </span>
              </span>
              <select
                className="rounded-md border border-[var(--color-border-strong)] bg-white px-2 py-1 text-[12px]"
                value={prefs.refreshSeconds}
                onChange={(event) => setPrefs({ ...prefs, refreshSeconds: Number(event.target.value) })}
              >
                {[10, 20, 60, 120].map((seconds) => (
                  <option key={seconds} value={seconds}>
                    {seconds}s
                  </option>
                ))}
              </select>
            </label>

            <div className="border-t border-[var(--color-border)] pt-3">
              <p className="text-[12px] text-[var(--color-ink-muted)]">
                Signed in as <span className="font-medium text-[var(--color-ink)]">{user?.full_name}</span> ({user?.role})
              </p>
              <div className="mt-2">
                <Button variant="quiet" size="sm" onClick={signOut}>
                  Sign out
                </Button>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </Shell>
  );
}
