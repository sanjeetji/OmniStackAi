"use client";

import { CreditCard, Percent, Receipt, Truck } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Badge, Button, DataState } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { useSession } from "../../lib/session";

export default function Settings() {
  const { operator, signOut } = useSession();
  const settings = useApi(() => api.getAdminSettings(), []);

  return (
    <Shell title="Settings" subtitle="The rules the marketplace runs on, and what is simulated here">
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Marketplace rules" subtitle="Enforced by the API, not by this screen">
          <DataState state={settings}>
            {(data) => (
              <ul className="space-y-3 text-[12.5px]">
                <li className="flex items-start gap-2.5">
                  <Percent size={15} className="mt-0.5 shrink-0 text-[var(--muted)]" />
                  <div>
                    <p className="font-medium text-slate-200">
                      {(data.settings.defaultCommissionBasisPoints / 100).toFixed(1)}% default commission
                    </p>
                    <p className="text-[var(--muted-light)]">
                      Taken from each consignment when it is delivered. A workshop can be given its own
                      rate on its profile.
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <Receipt size={15} className="mt-0.5 shrink-0 text-[var(--muted)]" />
                  <div>
                    <p className="font-medium text-slate-200">{data.settings.escrowHoldDays}-day escrow hold</p>
                    <p className="text-[var(--muted-light)]">
                      Money is held by the platform until a consignment is delivered and the hold has
                      passed, then it can be settled.
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <Receipt size={15} className="mt-0.5 shrink-0 text-[var(--muted)]" />
                  <div>
                    <p className="font-medium text-slate-200">
                      GST {(data.settings.taxRateBasisPoints / 100).toFixed(0)}% · {data.settings.gstin}
                    </p>
                    <p className="text-[var(--muted-light)]">Printed on every shopper invoice.</p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <Truck size={15} className="mt-0.5 shrink-0 text-[var(--muted)]" />
                  <div>
                    <p className="font-medium text-slate-200">Carriers</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {(data.settings.supportedCarriers ?? []).map((carrier: string) => (
                        <Badge key={carrier}>{carrier}</Badge>
                      ))}
                    </div>
                  </div>
                </li>
              </ul>
            )}
          </DataState>
        </Panel>

        <Panel title="Providers" subtitle="What is simulated here, and where the real one plugs in">
          <DataState state={settings}>
            {(data) => (
              <ul className="space-y-2.5 text-[12.5px]">
                {[
                  {
                    icon: <CreditCard size={15} />,
                    name: "Payments",
                    mock: data.settings.mockPayments,
                    file: "services/api/src/providers/payments.ts",
                  },
                  {
                    icon: <Truck size={15} />,
                    name: "Logistics and tracking",
                    mock: data.settings.mockLogistics,
                    file: "services/api/src/providers/logistics.ts",
                  },
                ].map((provider) => (
                  <li
                    key={provider.name}
                    className="flex items-start justify-between gap-3 rounded-lg border border-[var(--surface-border)] p-3"
                  >
                    <div className="flex items-start gap-2.5">
                      <span className="mt-0.5 text-[var(--muted)]">{provider.icon}</span>
                      <div>
                        <p className="font-medium text-slate-200">{provider.name}</p>
                        <p className="tabular text-[11px] text-[var(--muted)]">{provider.file}</p>
                      </div>
                    </div>
                    <Badge tone={provider.mock ? "alert" : "good"}>{provider.mock ? "Simulated" : "Live"}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </DataState>

          <div className="mt-4 border-t border-[var(--surface-border)] pt-3">
            <p className="text-[12px] text-[var(--muted-light)]">
              Signed in as <span className="font-medium text-slate-200">{operator?.name || operator?.email}</span> ({operator?.role})
            </p>
            <div className="mt-2">
              <Button variant="quiet" size="sm" onClick={signOut}>
                Sign out
              </Button>
            </div>
          </div>
        </Panel>
      </div>

      <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--muted)]">
        These values come from the API. Changing them in a real deployment is a settings write that
        is recorded in the audit trail.
      </p>
    </Shell>
  );
}
