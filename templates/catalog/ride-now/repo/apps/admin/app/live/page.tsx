"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { Car, Crosshair, Route } from "lucide-react";
import { inr, relativeTime } from "@ridenow/shared";
import { CityMap, type MapMarker, type MapZone } from "@ridenow/shared/map";
import { Shell } from "@/components/shell";
import { TripStatusBadge } from "@/components/status";
import { Badge, Empty, ErrorState, PageHeader, Panel, Segmented, Skeleton, Toggle, cx } from "@/components/ui";
import { useAdminEvent } from "@/lib/session";
import type { Live, LiveDriver } from "@/lib/types";
import { useApi, useInterval } from "@/lib/use-api";

export default function LivePage() {
  return (
    <Shell>
      <LiveView />
    </Shell>
  );
}

type Selection = { kind: "trip" | "driver"; id: string } | null;

function LiveView() {
  const { data, error, reload, setData } = useApi<Live>("/admin/live");
  const [tab, setTab] = useState<"trips" | "drivers">("trips");
  const [selected, setSelected] = useState<Selection>(null);
  const [showZones, setShowZones] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(() => new Date());
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);

  const soon = () => {
    if (pending.current) clearTimeout(pending.current);
    pending.current = setTimeout(() => {
      reload();
      setUpdatedAt(new Date());
    }, 800);
  };
  useInterval(() => {
    reload();
    setUpdatedAt(new Date());
  }, 10_000);
  useAdminEvent(["trip.updated", "driver.status", "zone.updated"], soon);
  // Move cars as they report, without refetching everything.
  useAdminEvent(["driver.location"], (_type, point: { driver_id: string; lat: number; lng: number; heading: number }) => {
    setData((current) => {
      if (!current) return current;
      const known = current.drivers.some((d) => d.id === point.driver_id);
      if (!known) return current;
      return { ...current, drivers: current.drivers.map((d) => (d.id === point.driver_id ? { ...d, lat: point.lat, lng: point.lng, heading: point.heading } : d)) };
    });
  });

  const view = useMemo(() => {
    if (!data) return null;
    const trip = selected?.kind === "trip" ? data.trips.find((t) => t.id === selected.id) ?? null : null;
    const driver = selected?.kind === "driver" ? data.drivers.find((d) => d.id === selected.id) ?? null : null;
    const markers: MapMarker[] = data.drivers.map((d) => ({
      id: d.id,
      kind: "car",
      lat: d.lat,
      lng: d.lng,
      heading: d.heading,
      tone: d.trip_status ? "busy" : "default",
      label: driver?.id === d.id || (trip?.driver?.id === d.id) ? d.name : undefined,
    }));
    for (const t of data.trips) {
      if (t.status === "requested" || trip?.id === t.id) {
        markers.push({ id: `p-${t.id}`, kind: "pickup", lat: t.pickup.lat, lng: t.pickup.lng, label: trip?.id === t.id ? t.pickup.name : undefined });
      }
    }
    if (trip) markers.push({ id: `d-${trip.id}`, kind: "drop", lat: trip.drop.lat, lng: trip.drop.lng, label: trip.drop.name });
    const zones: MapZone[] = showZones
      ? data.zones.filter((z) => z.active).map((z) => ({ id: z.id, lat: z.center_lat, lng: z.center_lng, radiusKm: z.radius_km, label: z.name, surge: z.surge }))
      : [];
    const focus = trip
      ? [trip.pickup, trip.drop, ...(trip.driver?.location ? [trip.driver.location] : [])]
      : driver
        ? [{ lat: driver.lat - 0.02, lng: driver.lng - 0.02 }, { lat: driver.lat + 0.02, lng: driver.lng + 0.02 }]
        : undefined;
    return { markers, zones, focus, route: trip ? ([trip.pickup, trip.drop] as [typeof trip.pickup, typeof trip.drop]) : null };
  }, [data, selected, showZones]);

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;

  const busy = data?.drivers.filter((d) => d.trip_status).length ?? 0;
  const free = (data?.drivers.length ?? 0) - busy;

  return (
    <>
      <PageHeader
        title="Live map"
        description={`Updates as drivers report their position. Last refreshed ${updatedAt.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", second: "2-digit" })}.`}
        actions={
          <label className="flex items-center gap-2 text-[13px] text-ink-2">
            <Toggle checked={showZones} onChange={setShowZones} label="Show surge zones" />
            Surge zones
          </label>
        }
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Panel className="overflow-hidden" bodyClassName="relative">
          <div className="h-[62vh] min-h-[420px]">
            {view ? (
              <CityMap markers={view.markers} zones={view.zones} focus={view.focus} route={view.route} ariaLabel={`Map of ${data?.drivers.length ?? 0} online drivers and ${data?.trips.length ?? 0} active trips`} />
            ) : (
              <Skeleton className="size-full rounded-none" />
            )}
          </div>
          <div className="absolute left-3 top-3 flex flex-wrap gap-2 text-xs">
            <Legend color="var(--map-car)" label={`${free} free`} />
            <Legend color="var(--map-car-busy)" label={`${busy} on a trip`} />
            <Legend color="var(--map-pickup)" label="Waiting pickup" round />
          </div>
          {selected ? (
            <button type="button" onClick={() => setSelected(null)} className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-md border border-line bg-panel px-2.5 py-1.5 text-xs font-medium shadow-panel hover:bg-sunken">
              <Crosshair className="size-3.5" aria-hidden="true" />
              Show the whole city
            </button>
          ) : null}
        </Panel>

        <Panel bodyClassName="max-h-[62vh] overflow-y-auto">
          <div className="sticky top-0 z-10 border-b border-line bg-panel px-4 py-3">
            <Segmented
              label="List"
              value={tab}
              onChange={setTab}
              options={[
                { value: "trips", label: "Active trips", count: data?.trips.length ?? 0 },
                { value: "drivers", label: "Online drivers", count: data?.drivers.length ?? 0 },
              ]}
            />
          </div>
          {!data ? (
            <div className="grid gap-2 p-4">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : tab === "trips" ? (
            data.trips.length === 0 ? (
              <Empty icon={<Route className="size-5" />} title="No trips right now" body="Book a ride in the rider app and it appears here within seconds." />
            ) : (
              <ul className="divide-y divide-line">
                {data.trips.map((t) => (
                  <li key={t.id}>
                    <button
                      type="button"
                      onClick={() => setSelected({ kind: "trip", id: t.id })}
                      aria-pressed={selected?.kind === "trip" && selected.id === t.id}
                      className={cx("grid w-full gap-1 px-4 py-3 text-left hover:bg-sunken", selected?.kind === "trip" && selected.id === t.id && "bg-signal-soft")}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-semibold">{t.code}</span>
                        <TripStatusBadge status={t.status} />
                      </span>
                      <span className="truncate text-[13px]">{t.pickup.name} → {t.drop.name}</span>
                      <span className="flex justify-between gap-2 text-xs text-muted">
                        <span className="truncate">{t.rider?.name} · {t.driver ? t.driver.name : "finding a driver"}</span>
                        <span className="num shrink-0">{inr(t.fare_estimate)} · {relativeTime(t.requested_at)}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )
          ) : data.drivers.length === 0 ? (
            <Empty icon={<Car className="size-5" />} title="No drivers online" body="Drivers appear here when they go online in the driver app." />
          ) : (
            <ul className="divide-y divide-line">
              {[...data.drivers].sort(byBusy).map((d) => (
                <li key={d.id} className={cx("flex items-center gap-3 px-4 py-2.5", selected?.kind === "driver" && selected.id === d.id && "bg-signal-soft")}>
                  <button type="button" onClick={() => setSelected({ kind: "driver", id: d.id })} className="min-w-0 flex-1 text-left">
                    <span className="block truncate text-[13px] font-medium">{d.name}</span>
                    <span className="block text-xs text-muted">{d.vehicle_type}{d.simulated ? " · simulated" : ""}</span>
                  </button>
                  {d.trip_status ? <Badge tone="signal" dot>On trip</Badge> : <Badge tone="ok" dot>Free</Badge>}
                  <Link href={`/drivers/${d.id}`} className="text-xs font-medium text-signal hover:underline">Profile</Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  );
}

function byBusy(a: LiveDriver, b: LiveDriver): number {
  return Number(Boolean(b.trip_status)) - Number(Boolean(a.trip_status)) || a.name.localeCompare(b.name);
}

function Legend({ color, label, round }: { color: string; label: string; round?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-line bg-panel/95 px-2 py-1 font-medium shadow-panel">
      <span className={round ? "size-2.5 rounded-full" : "h-3 w-2 rounded-[2px]"} style={{ background: color }} aria-hidden="true" />
      {label}
    </span>
  );
}
