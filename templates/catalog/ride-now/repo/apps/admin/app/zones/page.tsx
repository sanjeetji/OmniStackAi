"use client";

import { useEffect, useState } from "react";
import { Crosshair, Save } from "lucide-react";
import { CityMap, type MapZone } from "@ridenow/shared/map";
import { Shell } from "@/components/shell";
import { Badge, Button, ErrorState, LoadingRows, PageHeader, Panel, Skeleton, Toggle, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin, useAdminEvent } from "@/lib/session";
import type { Zone } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

export default function ZonesPage() {
  return (
    <Shell>
      <ZonesView />
    </Shell>
  );
}

function ZonesView() {
  const { data, error, reload } = useApi<{ zones: Zone[] }>("/admin/zones");
  const [focus, setFocus] = useState<string | null>(null);
  useAdminEvent(["zone.updated"], reload);

  const zones = data?.zones ?? [];
  const mapZones: MapZone[] = zones.map((z) => ({ id: z.id, lat: z.center_lat, lng: z.center_lng, radiusKm: z.radius_km, label: z.name, surge: z.active ? z.surge : 1 }));
  const focused = zones.find((z) => z.id === focus);

  return (
    <>
      <PageHeader
        title="Surge zones"
        description="Pickups inside an active zone are priced with its multiplier (1.00× to 3.00×). Riders see the surge before they book; changes apply to new bookings at once."
      />
      {error && !data ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
          <Panel className="overflow-hidden" bodyClassName="relative">
            <div className="h-[60vh] min-h-[400px]">
              {data ? (
                <CityMap
                  zones={mapZones}
                  focus={focused ? [{ lat: focused.center_lat - 0.03, lng: focused.center_lng - 0.03 }, { lat: focused.center_lat + 0.03, lng: focused.center_lng + 0.03 }] : mapZones.map((z) => ({ lat: z.lat, lng: z.lng }))}
                  ariaLabel={`Map of ${zones.length} surge zones`}
                />
              ) : (
                <Skeleton className="size-full rounded-none" />
              )}
            </div>
            {focused ? (
              <button type="button" onClick={() => setFocus(null)} className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-medium shadow-panel hover:bg-sunken">
                <Crosshair className="size-3.5" aria-hidden="true" />
                Show all zones
              </button>
            ) : null}
          </Panel>
          <Panel title="Zones" description={`${zones.filter((z) => z.active && z.surge > 1).length} surging now`}>
            {!data ? (
              <LoadingRows rows={6} label="Loading zones" />
            ) : (
              <ul className="divide-y divide-line">
                {zones.map((zone) => (
                  <ZoneRow key={zone.id} zone={zone} selected={focus === zone.id} onSelect={() => setFocus(zone.id)} onSaved={reload} />
                ))}
              </ul>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}

function ZoneRow({ zone, selected, onSelect, onSaved }: { zone: Zone; selected: boolean; onSelect: () => void; onSaved: () => void }) {
  const { toast } = useAdmin();
  const [surge, setSurge] = useState(zone.surge);
  const [active, setActive] = useState(zone.active);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setSurge(zone.surge);
    setActive(zone.active);
  }, [zone]);
  const dirty = surge !== zone.surge || active !== zone.active;

  async function save() {
    setBusy(true);
    try {
      await api.patch(`/admin/zones/${zone.id}`, { surge, active });
      toast(`${zone.name}: ${active ? `${surge.toFixed(2)}× surge` : "switched off"}`);
      onSaved();
    } catch (err) {
      toast(errorText(err), "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className={cx("grid gap-2.5 px-4 py-3", selected && "bg-signal-soft/60")}>
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={onSelect} className="text-left">
          <span className="block text-[13px] font-semibold hover:underline">{zone.name}</span>
          <span className="num block text-xs text-muted">{zone.radius_km} km radius</span>
        </button>
        <div className="flex items-center gap-2">
          {active && surge > 1 ? <Badge tone="warn">{surge.toFixed(2)}×</Badge> : <Badge>{active ? "Normal" : "Off"}</Badge>}
          <Toggle checked={active} onChange={setActive} label={`${zone.name} zone active`} />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label htmlFor={`surge-${zone.id}`} className="sr-only">Surge multiplier for {zone.name}</label>
        <input
          id={`surge-${zone.id}`}
          type="range"
          min={1}
          max={3}
          step={0.05}
          value={surge}
          disabled={!active}
          onChange={(e) => setSurge(Math.round(Number(e.target.value) * 100) / 100)}
          className="h-1.5 flex-1 accent-signal disabled:opacity-40"
        />
        <span className="num w-12 text-right text-[13px] font-semibold">{surge.toFixed(2)}×</span>
        <Button size="sm" busy={busy} disabled={!dirty} onClick={() => void save()}>
          <Save className="size-3.5" aria-hidden="true" />
          Save
        </Button>
      </div>
    </li>
  );
}
