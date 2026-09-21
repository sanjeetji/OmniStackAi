"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, LifeBuoy } from "lucide-react";
import { STATUS_LABEL, dateTimeLabel, inr, km, minutes, timeLabel, type Trip } from "@ridenow/shared";
import { CityMap, type MapMarker } from "@ridenow/shared/map";
import { Shell } from "@/components/shell";
import { Avatar, LinkButton, Loading, Notice, Panel, Stars, Tag } from "@/components/ui";
import { api } from "@/lib/api";

type Detail = Trip & { rating_received: { stars: number; tags: string[]; comment: string } | null };

const EVENT_LABEL: Record<string, string> = {
  requested: "Ride requested",
  offer_sent: "Offered to you",
  driver_assigned: "You accepted",
  driver_arrived: "You arrived at pickup",
  started: "Ride started",
  completed: "Ride completed",
  cancelled: "Ride cancelled",
  no_driver: "No driver found",
  refunded: "Rider refunded",
};

export default function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [trip, setTrip] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<Detail>(`/driver/trips/${id}`).then(setTrip).catch(() => setError("This trip was not found."));
  }, [id]);

  const markers = useMemo<MapMarker[]>(() => (trip ? [
    { id: "pickup", kind: "pickup", ...trip.pickup, label: "Pickup" },
    { id: "drop", kind: "drop", ...trip.drop, label: "Drop" },
  ] : []), [trip]);

  return (
    <Shell title="Trip details">
      <Link href="/trips" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-fg-muted hover:text-fg"><ArrowLeft className="size-4" aria-hidden="true" /> All trips</Link>
      {error ? <Notice>{error}</Notice> : !trip ? <Loading label="Loading trip" /> : (
        <div className="grid gap-4">
          <div className="h-48 overflow-hidden rounded-[var(--radius-card)] border border-line/60">
            <CityMap markers={markers} route={[trip.pickup, trip.drop]} ariaLabel="Trip route" />
          </div>

          <Panel className="grid gap-3 p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-fg-muted">{trip.code} · {dateTimeLabel(trip.requested_at)}</p>
              <Tag tone={trip.status === "completed" ? "go" : trip.status === "cancelled" ? "danger" : "muted"}>{STATUS_LABEL[trip.status]}</Tag>
            </div>
            <ol className="grid gap-2">
              <li className="flex gap-3"><span className="mt-1.5 size-2.5 shrink-0 rounded-full bg-go" aria-hidden="true" /><span><span className="block font-semibold">{trip.pickup.name}</span>{trip.started_at ? <span className="text-xs text-fg-muted">Picked up {timeLabel(trip.started_at)}</span> : null}</span></li>
              <li className="flex gap-3"><span className="mt-1.5 size-2.5 shrink-0 rounded-sm bg-warn" aria-hidden="true" /><span><span className="block font-semibold">{trip.drop.name}</span>{trip.completed_at ? <span className="text-xs text-fg-muted">Dropped {timeLabel(trip.completed_at)}</span> : null}</span></li>
            </ol>
            <p className="text-sm text-fg-muted">{trip.vehicle_type_name} · {km(trip.distance_km)} · {minutes(trip.duration_min)}{trip.surge > 1 ? ` · ${trip.surge}× surge` : ""}</p>
          </Panel>

          {trip.status === "completed" ? (
            <Panel className="p-5">
              <h2 className="mb-3 font-bold">Your earning</h2>
              <dl className="grid gap-2 text-sm">
                <Row label="Fare paid by rider" value={inr(trip.fare_final)} />
                {trip.discount > 0 ? <Row label={`Promo ${trip.promo_code ?? ""} (paid by RideNow)`} value={inr(trip.discount)} /> : null}
                <Row label="RideNow commission" value={`− ${inr(trip.commission ?? 0)}`} />
                <div className="my-1 border-t border-line/60" />
                <Row label="You earned" value={<span className="text-lg font-extrabold text-go">{inr(trip.driver_earning ?? 0)}</span>} />
                <Row label="Payment" value={trip.payment_method === "cash" ? "Cash collected by you" : "Rider's wallet"} />
              </dl>
            </Panel>
          ) : trip.cancel_reason ? (
            <Notice tone="warn">Cancelled{trip.cancelled_by ? ` by the ${trip.cancelled_by}` : ""}: {trip.cancel_reason}</Notice>
          ) : null}

          {trip.rider ? (
            <Panel className="grid gap-3 p-5">
              <div className="flex items-center gap-3">
                <Avatar name={trip.rider.name} color={trip.rider.avatar_color} />
                <div className="flex-1">
                  <p className="font-bold">{trip.rider.name}</p>
                  <p className="text-xs text-fg-muted">Rider</p>
                </div>
              </div>
              {trip.rating_received ? (
                <div className="rounded-2xl bg-raised p-3">
                  <p className="mb-1 text-xs font-semibold text-fg-muted">Rated you</p>
                  <Stars value={trip.rating_received.stars} size={18} />
                  {trip.rating_received.tags.length ? <p className="mt-2 text-sm">{trip.rating_received.tags.join(" · ")}</p> : null}
                  {trip.rating_received.comment ? <p className="mt-1 text-sm text-fg-muted">“{trip.rating_received.comment}”</p> : null}
                </div>
              ) : trip.status === "completed" ? <p className="text-sm text-fg-muted">The rider hasn't rated this trip.</p> : null}
              {trip.my_rating ? <p className="text-sm text-fg-muted">You gave {trip.my_rating} star{trip.my_rating > 1 ? "s" : ""}.</p> : null}
            </Panel>
          ) : null}

          {trip.events?.length ? (
            <Panel className="p-5">
              <h2 className="mb-3 font-bold">Timeline</h2>
              <ol className="grid gap-3 border-l border-line pl-4">
                {trip.events.map((event, index) => (
                  <li key={`${event.kind}-${index}`} className="relative text-sm">
                    <span className="absolute -left-[21px] top-1.5 size-2.5 rounded-full bg-fg-muted" aria-hidden="true" />
                    <span className="font-semibold">{EVENT_LABEL[event.kind] ?? event.kind}</span>
                    <span className="block text-xs text-fg-muted">{timeLabel(event.at)} · by {event.actor}</span>
                  </li>
                ))}
              </ol>
            </Panel>
          ) : null}

          <LinkButton href={`/help?trip=${trip.id}`}><LifeBuoy className="size-4" aria-hidden="true" /> Report a problem with this trip</LinkButton>
        </div>
      )}
    </Shell>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-fg-muted">{label}</dt>
      <dd className="font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
