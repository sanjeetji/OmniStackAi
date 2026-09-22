"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Plug } from "lucide-react";
import { Shell } from "@/components/shell";
import { Avatar, Badge, Button, KeyValues, PageHeader, Panel, Toggle } from "@/components/ui";
import { api } from "@/lib/api";
import { readPrefs, useAdmin, writePrefs } from "@/lib/session";

export default function SettingsPage() {
  return (
    <Shell>
      <SettingsView />
    </Shell>
  );
}

// Each provider is a mock behind an interface in services/api/src/providers; swap the
// implementation to go live. Provider keys belong in the API's environment, never in the apps.
const PROVIDERS = [
  { name: "Payments", mock: "Mock card payments. Card 4000 0000 0000 0002 is declined, so failure paths can be tried.", real: "Stripe or Razorpay", file: "services/api/src/providers/payments.ts" },
  { name: "SMS (OTP)", mock: "Codes are written to the API log. In the preview, 123456 is also accepted.", real: "Twilio or MSG91", file: "services/api/src/providers/sms.ts" },
  { name: "Maps and routing", mock: "Straight-line distance × 1.3 at an average city speed, drawn on the built-in city map.", real: "Google Maps or Mapbox", file: "services/api/src/providers/maps.ts" },
];

function SettingsView() {
  const router = useRouter();
  const { user, signOut, toast } = useAdmin();
  const [sound, setSound] = useState(false);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const saved = readPrefs();
    setSound(saved.sound);
    setCompact(saved.compact);
  }, []);

  const savePrefs = (next: { sound: boolean; compact: boolean }) => {
    setSound(next.sound);
    setCompact(next.compact);
    toast(writePrefs(next) ? "Saved on this device" : "This browser blocks local storage, so the setting lasts for this visit only", "info");
  };

  if (!user) return null;
  return (
    <>
      <PageHeader title="Settings" description="Your operator account, this device's preferences, and how this RideNow deployment is wired." />
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Your account" bodyClassName="grid gap-4 p-4">
          <div className="flex items-center gap-3">
            <Avatar name={user.full_name} color={user.avatar_color} size={44} />
            <div>
              <p className="font-semibold">{user.full_name}</p>
              <p className="text-[13px] text-muted">Operations · full access</p>
            </div>
          </div>
          <KeyValues items={[["Email", user.email ?? "–"], ["Phone", user.phone ?? "–"], ["Role", "Admin"], ["Session", "Signed in on this browser; access tokens refresh every 15 minutes"]]} />
          <div>
            <Button
              variant="secondary"
              onClick={async () => {
                await signOut();
                router.replace("/login");
              }}
            >
              <LogOut className="size-4" aria-hidden="true" />
              Sign out
            </Button>
          </div>
        </Panel>

        <Panel title="This device" description="Stored in this browser only" bodyClassName="grid gap-4 p-4">
          <label className="flex items-start justify-between gap-4">
            <span>
              <span className="block text-[13px] font-medium">Sound for urgent tickets</span>
              <span className="block text-xs text-muted">Play a chime when a safety ticket arrives while this tab is open.</span>
            </span>
            <Toggle checked={sound} onChange={(v) => savePrefs({ sound: v, compact })} label="Sound for urgent tickets" />
          </label>
          <label className="flex items-start justify-between gap-4">
            <span>
              <span className="block text-[13px] font-medium">Compact tables</span>
              <span className="block text-xs text-muted">Fit more rows on screen on small laptops.</span>
            </span>
            <Toggle checked={compact} onChange={(v) => savePrefs({ sound, compact: v })} label="Compact tables" />
          </label>
        </Panel>

        <Panel title="Integrations" description="Everything runs without credentials. Each provider is a mock behind an interface in the API." className="xl:col-span-2">
          <ul className="divide-y divide-line">
            {PROVIDERS.map((p) => (
              <li key={p.name} className="grid gap-1 px-4 py-3 sm:grid-cols-[180px_1fr_auto] sm:items-center sm:gap-4">
                <p className="flex items-center gap-2 text-[13px] font-semibold"><Plug className="size-4 text-muted" aria-hidden="true" />{p.name}</p>
                <div className="text-[13px]">
                  <p className="text-ink-2">{p.mock}</p>
                  <p className="text-xs text-muted">
                    Go live with {p.real}: implement <span className="font-mono">{p.file}</span> and add its keys to the API&apos;s <span className="font-mono">.env</span>.
                  </p>
                </div>
                <Badge tone="warn">Mock</Badge>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="API" className="xl:col-span-2" bodyClassName="p-4">
          <KeyValues
            items={[
              ["Base URL", <span key="b" className="font-mono text-xs">{api.baseUrl}</span>],
              ["Reference", <a key="o" href={`${api.baseUrl}/openapi.json`} target="_blank" rel="noreferrer" className="text-signal hover:underline">OpenAPI document</a>],
              ["Realtime", "Server-sent events on /stream (trip, driver, ticket, payout and zone updates)"],
            ]}
          />
        </Panel>
      </div>
    </>
  );
}
