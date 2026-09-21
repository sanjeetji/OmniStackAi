"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronRight, History } from "lucide-react";
import { STATUS_LABEL, dateTimeLabel, inr, type Trip, type TripStatus } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Badge, ButtonLink, Card, EmptyState, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";

const FILTERS: { value: TripStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];
const PAGE = 15;
const EMOJI: Record<string, string> = { bike: "🛵", auto: "🛺", mini: "🚗", sedan: "🚘", xl: "🚙" };

export default function TripsPage() {
  const [filter, setFilter] = useState<TripStatus | "">("");
  const [trips, setTrips] = useState<Trip[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setTrips(null);
    api.get<{ trips: Trip[]; total: number }>(`/rider/trips?limit=${PAGE}${filter ? `&status=${filter}` : ""}`).then((r) => {
      setTrips(r.trips);
      setTotal(r.total);
    }).catch(() => setTrips([]));
  }, [filter]);

  async function more() {
    if (!trips) return;
    setLoadingMore(true);
    const r = await api.get<{ trips: Trip[]; total: number }>(`/rider/trips?limit=${PAGE}&offset=${trips.length}${filter ? `&status=${filter}` : ""}`);
    setTrips([...trips, ...r.trips]);
    setLoadingMore(false);
  }

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Your trips</h1>
          <p className="mt-1 text-muted">{total ? `${total} trip${total === 1 ? "" : "s"}` : "Receipts and ride history"}</p>
        </div>
        <div role="tablist" aria-label="Filter trips" className="flex rounded-full bg-black/5 p-1">
          {FILTERS.map((f) => (
            <button key={f.label} role="tab" aria-selected={filter === f.value} onClick={() => setFilter(f.value)} className={cx("rounded-full px-4 py-1.5 text-sm font-semibold", filter === f.value ? "bg-white shadow-sm" : "text-muted")}>
              {f.label}
            </button>
          ))}
        </div>
      </div>
      {trips === null ? (
        <div className="grid gap-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : trips.length === 0 ? (
        <Card><EmptyState icon={<History className="size-6" />} title="No trips yet" body="Your rides and receipts will show up here." action={<ButtonLink href="/ride">Book a ride</ButtonLink>} /></Card>
      ) : (
        <div className="grid gap-3">
          {trips.map((trip) => (
            <Link key={trip.id} href={["completed", "cancelled", "no_driver"].includes(trip.status) ? `/trips/${trip.id}` : `/trip/${trip.id}`} className="rn-rise flex items-center gap-4 rounded-[var(--radius-card)] bg-card p-4 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5">
              <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-canvas text-2xl" aria-hidden="true">{EMOJI[trip.vehicle_type] ?? "🚗"}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-bold">{trip.drop.name}</p>
                <p className="truncate text-sm text-muted">from {trip.pickup.name}</p>
                <p className="mt-1 text-xs text-muted">{dateTimeLabel(trip.requested_at)} · {trip.vehicle_type_name}</p>
              </div>
              <div className="grid justify-items-end gap-1">
                <span className="font-extrabold">{trip.status === "completed" ? inr(trip.fare_final) : trip.fare_final ? inr(trip.fare_final) : "—"}</span>
                <Badge tone={trip.status === "completed" ? "success" : trip.status === "cancelled" || trip.status === "no_driver" ? "neutral" : "amber"}>{STATUS_LABEL[trip.status]}</Badge>
              </div>
              <ChevronRight className="size-5 shrink-0 text-muted" aria-hidden="true" />
            </Link>
          ))}
          {trips.length < total ? (
            <button type="button" onClick={more} disabled={loadingMore} className="mx-auto mt-2 rounded-full px-5 py-2 text-sm font-semibold text-teal hover:bg-teal-soft">
              {loadingMore ? "Loading…" : "Show more"}
            </button>
          ) : null}
        </div>
      )}
    </AppShell>
  );
}
