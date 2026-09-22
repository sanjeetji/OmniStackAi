"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Download, Route } from "lucide-react";
import { dateTimeLabel, inr, km, type Trip } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { PaymentBadge, TripStatusBadge } from "@/components/status";
import { Button, Empty, ErrorState, LoadingRows, PageHeader, Pager, Panel, SearchBox, Segmented, Select, Table, td, th } from "@/components/ui";
import type { Live, VehicleTypeRow } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const LIMIT = 25;
const STATUSES = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "no_driver", label: "No driver" },
] as const;
type StatusFilter = (typeof STATUSES)[number]["value"];

export default function TripsPage() {
  return (
    <Shell>
      <Suspense fallback={<LoadingRows />}>
        <TripsView />
      </Suspense>
    </Shell>
  );
}

function TripsView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const status = (STATUSES.find((s) => s.value === params.get("status"))?.value ?? "all") as StatusFilter;
  const vehicle = params.get("vehicle_type") ?? "";
  const offset = Math.max(0, Number(params.get("offset") ?? 0) || 0);
  const q = params.get("q") ?? "";
  const [search, setSearch] = useState(q);

  const update = (next: Record<string, string | number | null>) => {
    const merged = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(next)) {
      if (value === null || value === "" || value === "all" || value === 0) merged.delete(key);
      else merged.set(key, String(value));
    }
    const query = merged.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  useEffect(() => setSearch(q), [q]);
  useEffect(() => {
    if (search.trim() === q) return;
    const timer = setTimeout(() => update({ q: search.trim(), offset: 0 }), 350);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to typing
  }, [search]);

  const listPath = status === "active" ? null : `/admin/trips?${new URLSearchParams({
    limit: String(LIMIT),
    offset: String(offset),
    ...(status !== "all" ? { status } : {}),
    ...(vehicle ? { vehicle_type: vehicle } : {}),
    ...(q ? { q } : {}),
  }).toString()}`;
  const list = useApi<{ trips: Trip[]; total: number }>(listPath);
  const live = useApi<Live>(status === "active" ? "/admin/live" : null);
  const types = useApi<{ vehicle_types: VehicleTypeRow[] }>("/admin/vehicle-types");

  const activeTrips = (live.data?.trips ?? []).filter((t) => (!vehicle || t.vehicle_type === vehicle) && matches(t, q));
  const rows = status === "active" ? activeTrips : list.data?.trips ?? null;
  const total = status === "active" ? activeTrips.length : list.data?.total ?? 0;
  const error = status === "active" ? live.error : list.error;
  const loading = status === "active" ? !live.data : !list.data || list.loading;

  return (
    <>
      <PageHeader
        title="Trips"
        description="Every ride request in the city, newest first."
        actions={
          <Button variant="secondary" disabled={!rows?.length} onClick={() => rows && downloadCsv(rows)}>
            <Download className="size-4" aria-hidden="true" />
            Export this page
          </Button>
        }
      />
      <Panel>
        <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
          <Segmented label="Status" value={status} onChange={(value) => update({ status: value, offset: 0 })} options={STATUSES.map((s) => ({ value: s.value, label: s.label }))} />
          <Select
            label="Vehicle type"
            hideLabel
            className="w-40"
            value={vehicle}
            onChange={(e) => update({ vehicle_type: e.target.value, offset: 0 })}
            options={[{ value: "", label: "All vehicles" }, ...(types.data?.vehicle_types ?? []).map((v) => ({ value: v.id, label: v.name }))]}
          />
          <div className="ml-auto w-full sm:w-auto">
            <SearchBox value={search} onChange={setSearch} placeholder="Code, rider, driver or place" label="Search trips" />
          </div>
        </div>
        {error && !rows ? (
          <div className="p-4"><ErrorState message={error} onRetry={status === "active" ? live.reload : list.reload} /></div>
        ) : rows === null || (loading && rows.length === 0) ? (
          <LoadingRows label="Loading trips" />
        ) : rows.length === 0 ? (
          <Empty
            icon={<Route className="size-5" />}
            title={q || vehicle || status !== "all" ? "No trips match these filters" : "No trips yet"}
            body={q || vehicle || status !== "all" ? "Try another status, vehicle type or search." : "Trips appear here as soon as riders book."}
            action={q || vehicle || status !== "all" ? <Button variant="secondary" size="sm" onClick={() => { setSearch(""); update({ status: null, vehicle_type: null, q: null, offset: 0 }); }}>Clear filters</Button> : undefined}
          />
        ) : (
          <>
            <Table label="Trips" className={loading ? "opacity-60 transition-opacity" : undefined}>
              <thead>
                <tr>
                  <th className={th}>Trip</th>
                  <th className={th}>Requested</th>
                  <th className={th}>Rider</th>
                  <th className={th}>Driver</th>
                  <th className={th}>Route</th>
                  <th className={th}>Status</th>
                  <th className={th}>Payment</th>
                  <th className={`${th} text-right`}>Fare</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((trip) => (
                  <tr key={trip.id} className="hover:bg-sunken">
                    <td className={td}><Link href={`/trips/${trip.id}`} className="font-mono text-xs font-semibold text-signal hover:underline">{trip.code}</Link></td>
                    <td className={`${td} whitespace-nowrap text-ink-2`}>{dateTimeLabel(trip.requested_at)}</td>
                    <td className={`${td} whitespace-nowrap`}>{trip.rider ? <Link href={`/riders/${trip.rider.id}`} className="hover:underline">{trip.rider.name}</Link> : "–"}</td>
                    <td className={`${td} whitespace-nowrap`}>{trip.driver ? <Link href={`/drivers/${trip.driver.id}`} className="hover:underline">{trip.driver.name}</Link> : <span className="text-muted">–</span>}</td>
                    <td className={`${td} max-w-64`}>
                      <span className="block truncate">{trip.pickup.name} → {trip.drop.name}</span>
                      <span className="block text-xs text-muted">{trip.vehicle_type_name} · {km(trip.distance_km)}{trip.surge > 1 ? ` · ${trip.surge.toFixed(2)}× surge` : ""}</span>
                    </td>
                    <td className={td}><TripStatusBadge status={trip.status} /></td>
                    <td className={td}><PaymentBadge method={trip.payment_method} status={trip.payment_status} /></td>
                    <td className={`${td} num text-right font-medium`}>{inr(trip.fare_final ?? trip.fare_estimate)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
            {status === "active" ? (
              <p className="num px-4 py-3 text-xs text-muted">{total} active {total === 1 ? "trip" : "trips"}</p>
            ) : (
              <Pager offset={offset} limit={LIMIT} total={total} onChange={(next) => update({ offset: next })} />
            )}
          </>
        )}
      </Panel>
    </>
  );
}

function matches(trip: Trip, q: string): boolean {
  if (!q) return true;
  const hay = [trip.code, trip.rider?.name, trip.driver?.name, trip.pickup.name, trip.drop.name].join(" ").toLowerCase();
  return hay.includes(q.toLowerCase());
}

function downloadCsv(trips: Trip[]) {
  const header = ["code", "requested_at", "status", "rider", "driver", "pickup", "drop", "vehicle", "distance_km", "payment_method", "payment_status", "fare"];
  const cell = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const lines = trips.map((t) =>
    [t.code, t.requested_at, t.status, t.rider?.name, t.driver?.name, t.pickup.name, t.drop.name, t.vehicle_type_name, t.distance_km, t.payment_method, t.payment_status, t.fare_final ?? t.fare_estimate].map(cell).join(","),
  );
  const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ridenow-trips-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
