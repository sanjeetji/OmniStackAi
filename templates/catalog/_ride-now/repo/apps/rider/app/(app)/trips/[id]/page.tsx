"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Star } from "lucide-react";
import Link from "next/link";
import { STATUS_LABEL, dateTimeLabel, timeLabel, type Trip } from "@ridenow/shared";
import { CityMap } from "@ridenow/shared/map";
import { AppShell } from "@/components/app-shell";
import { RateTrip } from "@/components/rate-trip";
import { Receipt } from "@/components/receipt";
import { Alert, Avatar, Badge, ButtonLink, Card, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

const EVENT_LABEL: Record<string, string> = {
  requested: "You requested the ride",
  offer_sent: "Offered to a driver",
  driver_assigned: "Driver accepted",
  driver_arrived: "Driver arrived at pickup",
  started: "Ride started",
  completed: "Arrived at drop",
  cancelled: "Ride cancelled",
  no_driver: "No driver found",
  refunded: "Refund issued",
};

export default function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<Trip>(`/rider/trips/${id}`).then(setTrip).catch(() => setError("This trip was not found."));
  }, [id]);

  return (
    <AppShell>
      <Link href="/trips" className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden="true" /> All trips
      </Link>
      {error ? <Alert>{error}</Alert> : !trip ? <Spinner /> : (
        <div className="grid gap-5 md:grid-cols-[1.1fr_1fr]">
          <div className="grid content-start gap-5">
            <Card className="overflow-hidden">
              <div className="h-60"><CityMap markers={[{ id: "p", kind: "pickup", ...trip.pickup }, { id: "d", kind: "drop", ...trip.drop }]} route={[trip.pickup, trip.drop]} showLabels={false} ariaLabel="Trip route" /></div>
              <div className="grid gap-2 p-5 text-sm">
                <div className="flex items-center justify-between">
                  <h1 className="text-xl font-extrabold">{trip.drop.name}</h1>
                  <Badge tone={trip.status === "completed" ? "success" : "neutral"}>{STATUS_LABEL[trip.status]}</Badge>
                </div>
                <p className="text-muted">{dateTimeLabel(trip.requested_at)} · from {trip.pickup.name}</p>
              </div>
            </Card>
            {trip.events?.length ? (
              <Card className="p-5">
                <p className="mb-3 font-bold">Timeline</p>
                <ol className="grid gap-3 border-l-2 border-line pl-4">
                  {trip.events.filter((e) => e.kind !== "offer_sent").map((event, index) => (
                    <li key={index} className="relative text-sm">
                      <span className="absolute -left-[23px] top-1 size-3 rounded-full border-2 border-white bg-amber" aria-hidden="true" />
                      <span className="font-semibold">{EVENT_LABEL[event.kind] ?? event.kind}</span>
                      <span className="ml-2 text-muted">{timeLabel(event.at)}</span>
                    </li>
                  ))}
                </ol>
              </Card>
            ) : null}
          </div>
          <div className="grid content-start gap-5">
            {trip.driver ? (
              <Card className="flex items-center gap-3 p-5">
                <Avatar name={trip.driver.name} color={trip.driver.avatar_color} size={48} />
                <div className="flex-1">
                  <p className="font-bold">{trip.driver.name}</p>
                  <p className="text-sm text-muted">{trip.driver.vehicle} · {trip.driver.plate}</p>
                </div>
                {trip.my_rating ? <span className="flex items-center gap-1 font-bold"><Star className="size-4 fill-amber text-amber" aria-hidden="true" />{trip.my_rating}</span> : null}
              </Card>
            ) : null}
            {trip.status === "completed" || trip.fare_final ? <Card className="p-5"><Receipt trip={trip} /></Card> : <Card className="p-5 text-sm text-muted">{trip.cancel_reason} You were not charged.</Card>}
            {trip.status === "completed" && trip.driver && trip.my_rating === null ? (
              <Card className="p-5"><RateTrip tripId={trip.id} driverName={trip.driver.name} onRated={(stars) => setTrip({ ...trip, my_rating: stars })} /></Card>
            ) : null}
            <div className="grid grid-cols-2 gap-2">
              <ButtonLink href="/ride" variant="dark">Ride again</ButtonLink>
              <ButtonLink href={`/help?trip=${trip.id}`} variant="outline">Get help</ButtonLink>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
