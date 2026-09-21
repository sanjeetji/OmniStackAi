"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Flame, Hourglass, Power, ShieldAlert, Star, Wallet } from "lucide-react";
import { inr } from "@ridenow/shared";
import { CityMap, type MapMarker, type MapZone } from "@ridenow/shared/map";
import { Shell } from "@/components/shell";
import { Notice, Panel, Stat, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useDriver } from "@/lib/driver";

interface Earnings { trips: number; earnings: number; cash_collected: number; minutes_driving: number }
interface Zone { id: string; name: string; center_lat: number; center_lng: number; radius_km: number; surge: number; active: boolean }

export default function Home() {
  return (
    <Shell title="RideNow Driver">
      <HomeScreen />
    </Shell>
  );
}

function HomeScreen() {
  const { profile, online, goOnline, position, error, clearError, mode } = useDriver();
  const [today, setToday] = useState<Earnings | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Earnings>("/driver/earnings?range=today").then(setToday).catch(() => undefined);
    api.get<{ balance: number }>("/driver/wallet?limit=1").then((r) => setBalance(r.balance)).catch(() => undefined);
  }, [online]);

  useEffect(() => {
    api.get<{ zones: Zone[] }>("/driver/zones").then((r) => setZones(r.zones)).catch(() => setZones([]));
  }, []);

  const markers = useMemo<MapMarker[]>(() => (position ? [{ id: "me", kind: "car", ...position, heading: position.heading, tone: online ? "default" : "muted" }] : []), [position, online]);
  const mapZones = useMemo<MapZone[]>(() => zones.filter((z) => z.active && z.surge > 1).map((z) => ({ id: z.id, lat: z.center_lat, lng: z.center_lng, radiusKm: z.radius_km, surge: z.surge, label: z.name })), [zones]);
  if (!profile) return null;
  const pending = profile.status !== "approved";

  return (
    <div className="grid gap-4">
      <div className="relative h-72 overflow-hidden rounded-[var(--radius-card)] border border-line/60">
        <CityMap markers={markers} zones={mapZones} focus={position ? [position, ...mapZones.slice(0, 2)] : undefined} ariaLabel="Your position and busy areas" />
        {mapZones.length ? (
          <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-bg/85 px-3 py-1 text-xs font-bold text-warn backdrop-blur">
            <Flame className="size-3.5" aria-hidden="true" /> {mapZones.length} surge zone{mapZones.length > 1 ? "s" : ""}
          </span>
        ) : null}
        {mode === "simulated" ? (
          <span className="absolute bottom-3 left-3 rounded-full bg-bg/85 px-3 py-1 text-[11px] font-semibold text-fg-muted backdrop-blur">Simulated location · change in Account</span>
        ) : null}
      </div>

      {pending ? (
        <Notice tone={profile.status === "suspended" ? "danger" : "warn"}>
          {profile.status === "pending" ? (
            <span className="flex gap-2"><Hourglass className="size-4 shrink-0" aria-hidden="true" /> Your documents are being reviewed. You can go online once you're approved.</span>
          ) : (
            <span className="flex gap-2"><ShieldAlert className="size-4 shrink-0" aria-hidden="true" /> Driving is paused on your account. Contact support.</span>
          )}
        </Notice>
      ) : null}
      {error ? <Notice><button type="button" onClick={clearError} className="text-left">{error}</button></Notice> : null}

      <button
        type="button"
        disabled={pending || busy}
        onClick={async () => { setBusy(true); await goOnline(!online); setBusy(false); }}
        aria-pressed={online}
        className={cx(
          "flex h-20 items-center justify-center gap-3 rounded-[var(--radius-card)] text-xl font-extrabold transition active:scale-[0.99] disabled:opacity-50",
          online ? "border border-line bg-raised text-fg" : "drv-glow bg-go text-bg",
        )}
      >
        <Power className="size-6" aria-hidden="true" />
        {busy ? "…" : online ? "Go offline" : "Go online"}
      </button>
      <p className="-mt-2 text-center text-xs text-fg-muted">{online ? "You're receiving ride requests nearby." : "Go online to start receiving ride requests."}</p>

      <div className="grid grid-cols-2 gap-3">
        <Stat label="Today's earnings" value={today ? inr(today.earnings) : "…"} sub={today ? `${today.trips} trip${today.trips === 1 ? "" : "s"}` : undefined} />
        <Stat label="Rating" value={<span className="inline-flex items-center gap-1">{profile.rating.toFixed(2)}<Star className="size-5 fill-warn text-warn" aria-hidden="true" /></span>} sub={`${profile.rating_count} ratings`} />
        <Stat label="Acceptance" value={`${profile.acceptance_rate}%`} sub="Last 30 days" />
        <Stat label="Cash collected" value={today ? inr(today.cash_collected) : "…"} sub="Today" />
      </div>

      {balance !== null && balance >= 100 ? (
        <Panel className="flex items-center gap-3 p-4">
          <span className="grid size-11 place-items-center rounded-2xl bg-go-soft text-go"><Wallet className="size-5" aria-hidden="true" /></span>
          <div className="flex-1">
            <p className="font-bold">{inr(balance)} available</p>
            <p className="text-xs text-fg-muted">Withdraw to your bank any day.</p>
          </div>
          <Link href="/wallet" className="rounded-xl bg-raised px-4 py-2 text-sm font-bold">Withdraw</Link>
        </Panel>
      ) : null}

      <Panel className="flex items-center justify-between p-4 text-sm">
        <span className="text-fg-muted">{profile.vehicle.color} {profile.vehicle.make} {profile.vehicle.model}</span>
        <span className="rounded-lg border border-line px-2 py-1 font-mono font-bold">{profile.vehicle.plate}</span>
      </Panel>
    </div>
  );
}
