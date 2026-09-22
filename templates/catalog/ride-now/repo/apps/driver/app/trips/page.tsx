"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronRight, History, Star } from "lucide-react";
import { dateLabel, inr, km, timeLabel, type Trip } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Button, Empty, Loading, Notice, Panel, Tag } from "@/components/ui";
import { api } from "@/lib/api";

const PAGE = 20;

type Filter = "all" | "completed" | "cancelled";

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[] | null>(null);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ trips: Trip[]; total: number }>(`/driver/trips?limit=${PAGE}`)
      .then((r) => {
        setTrips(r.trips);
        setTotal(r.total);
      })
      .catch(() => setError("Couldn't load your trips."));
  }, []);

  async function more() {
    if (!trips) return;
    setLoadingMore(true);
    try {
      const r = await api.get<{ trips: Trip[]; total: number }>(`/driver/trips?limit=${PAGE}&offset=${trips.length}`);
      setTrips([...trips, ...r.trips]);
      setTotal(r.total);
    } finally {
      setLoadingMore(false);
    }
  }

  const shown = trips?.filter((t) => filter === "all" || (filter === "completed" ? t.status === "completed" : t.status === "cancelled" || t.status === "no_driver")) ?? [];
  const groups = new Map<string, Trip[]>();
  for (const trip of shown) {
    const day = dateLabel(trip.requested_at);
    groups.set(day, [...(groups.get(day) ?? []), trip]);
  }

  return (
    <Shell title="Trips">
      <div className="grid gap-4">
        <div className="flex gap-2" role="group" aria-label="Filter trips">
          {(["all", "completed", "cancelled"] as const).map((f) => (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)} className={filter === f ? "rounded-full bg-fg px-4 py-1.5 text-sm font-bold text-bg" : "rounded-full border border-line px-4 py-1.5 text-sm font-semibold text-fg-muted"}>
              {f === "all" ? "All" : f === "completed" ? "Completed" : "Cancelled"}
            </button>
          ))}
        </div>
        {error ? <Notice>{error}</Notice> : trips === null ? <Loading label="Loading trips" /> : shown.length === 0 ? (
          <Panel><Empty icon={<History className="size-6" />} title="No trips here yet" body="Go online from Home. Every ride you take will be listed here with its fare and rating." /></Panel>
        ) : (
          [...groups.entries()].map(([day, list]) => (
            <section key={day}>
              <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">{day}</h2>
              <Panel className="divide-y divide-line/60">
                {list.map((trip) => (
                  <Link key={trip.id} href={`/trips/${trip.id}`} className="flex items-center gap-3 px-4 py-3.5 hover:bg-white/3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{trip.pickup.name} → {trip.drop.name}</p>
                      <p className="flex items-center gap-1.5 truncate text-xs text-fg-muted">
                        {timeLabel(trip.requested_at)} · {trip.vehicle_type_name} · {km(trip.distance_km)}
                        {trip.my_rating ? <><span aria-hidden="true">·</span><Star className="size-3 fill-warn text-warn" aria-hidden="true" />{trip.my_rating} given</> : null}
                      </p>
                    </div>
                    <div className="text-right">
                      {trip.status === "completed" ? (
                        <p className="font-bold tabular-nums text-go">{inr(trip.driver_earning ?? 0)}</p>
                      ) : (
                        <Tag tone={trip.status === "cancelled" ? "danger" : "muted"}>{trip.status === "cancelled" ? "Cancelled" : trip.status === "no_driver" ? "Missed" : "Active"}</Tag>
                      )}
                      <p className="text-xs text-fg-muted">{trip.payment_method === "cash" ? "Cash" : "Wallet"}</p>
                    </div>
                    <ChevronRight className="size-4 text-fg-muted" aria-hidden="true" />
                  </Link>
                ))}
              </Panel>
            </section>
          ))
        )}
        {trips && trips.length < total ? (
          <Button variant="outline" busy={loadingMore} onClick={() => void more()}>Show older trips</Button>
        ) : null}
      </div>
    </Shell>
  );
}
