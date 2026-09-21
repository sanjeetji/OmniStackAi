"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Copy, Phone, Search, ShieldCheck, Star, XCircle } from "lucide-react";
import { ACTIVE_STATUSES, ApiError, STATUS_LABEL, inr, minutes, timeLabel, useStream, type Trip, type TripStatus } from "@ridenow/shared";
import { CityMap, type MapMarker } from "@ridenow/shared/map";
import { AppShell } from "@/components/app-shell";
import { RateTrip } from "@/components/rate-trip";
import { Receipt } from "@/components/receipt";
import { Alert, Avatar, Button, ButtonLink, Card, Sheet, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";

const STEPS: { status: TripStatus; label: string }[] = [
  { status: "requested", label: "Requested" },
  { status: "driver_assigned", label: "Driver on the way" },
  { status: "driver_arrived", label: "Driver arrived" },
  { status: "in_progress", label: "On trip" },
  { status: "completed", label: "Arrived" },
];
const CANCEL_REASONS = ["Changed my plans", "Driver is taking too long", "Driver asked me to cancel", "Booked by mistake", "Found another ride"];

export default function TripPage() {
  return (
    <AppShell wide>
      <LiveTrip />
    </AppShell>
  );
}

function LiveTrip() {
  const { id } = useParams<{ id: string }>();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState(CANCEL_REASONS[0]);
  const [cancelling, setCancelling] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    api.get<Trip>(`/rider/trips/${id}`).then(setTrip).catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load the trip."));
  }, [id]);

  useEffect(() => load(), [load]);

  const live = trip ? ACTIVE_STATUSES.includes(trip.status) : false;
  useStream(api, {
    "trip.updated": (updated: Trip) => {
      if (updated.id === id) setTrip((current) => ({ ...current, ...updated, events: current?.events }));
    },
    "driver.location": (update: { trip_id: string; lat: number; lng: number; heading: number }) => {
      if (update.trip_id !== id) return;
      setTrip((current) => current?.driver ? { ...current, driver: { ...current.driver, location: { lat: update.lat, lng: update.lng, heading: update.heading } } } : current);
    },
  }, live);

  // A slow poll keeps the page right even if the realtime connection is blocked.
  useEffect(() => {
    if (!live) return;
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  }, [live, load]);

  const markers = useMemo<MapMarker[]>(() => {
    if (!trip) return [];
    const list: MapMarker[] = [];
    if (trip.status !== "in_progress" && trip.status !== "completed") list.push({ id: "pickup", kind: "pickup", ...trip.pickup, label: "Pickup" });
    list.push({ id: "drop", kind: "drop", ...trip.drop, label: trip.status === "completed" ? "Dropped here" : "Drop" });
    if (trip.driver?.location && live) list.push({ id: "car", kind: "car", ...trip.driver.location, heading: trip.driver.location.heading });
    return list;
  }, [trip, live]);

  if (error) return <Alert>{error}</Alert>;
  if (!trip) return <Spinner label="Loading your ride" />;

  const stepIndex = STEPS.findIndex((s) => s.status === trip.status);
  const waitedMinutes = trip.arrived_at ? (Date.now() - new Date(trip.arrived_at).getTime()) / 60000 : 0;
  const cancelFee = trip.status === "driver_arrived" && waitedMinutes > 3;

  async function cancel() {
    setCancelling(true);
    try {
      const updated = await api.post<Trip & { cancellation_fee: number }>(`/rider/trips/${id}/cancel`, { reason });
      setTrip(updated);
      setCancelOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't cancel.");
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
      <div className="relative h-[46vh] overflow-hidden rounded-[28px] shadow-[var(--shadow-card)] ring-1 ring-black/5 lg:h-[calc(100dvh-8rem)]">
        <CityMap markers={markers} route={[trip.pickup, trip.drop]} ariaLabel="Live trip map" />
        {trip.status === "requested" ? (
          <div className="absolute inset-0 grid place-items-center bg-white/35">
            <div className="grid place-items-center">
              <span className="absolute size-28 rounded-full bg-amber" style={{ animation: "rn-pulse 1.8s ease-in-out infinite" }} />
              <span className="relative grid size-16 place-items-center rounded-full bg-amber shadow-[var(--shadow-float)]">
                <Search className="size-7" aria-hidden="true" />
              </span>
            </div>
          </div>
        ) : null}
      </div>

      <div className="grid content-start gap-4">
        <Card className="p-5">
          <p className="text-sm font-semibold text-muted">{trip.code}</p>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight" aria-live="polite">{STATUS_LABEL[trip.status]}</h1>
          {trip.status === "requested" ? <p className="mt-1 text-sm text-muted">Offering your ride to the nearest drivers…</p> : null}
          {trip.status === "in_progress" ? <p className="mt-1 text-sm text-muted">Arriving around {timeLabel(new Date(new Date(trip.started_at!).getTime() + trip.duration_min * 60000))}</p> : null}
          {stepIndex >= 0 ? (
            <ol className="mt-4 grid grid-cols-5 gap-1" aria-label="Trip progress">
              {STEPS.map((step, index) => (
                <li key={step.status} className="grid gap-1.5">
                  <span className={cx("h-1.5 rounded-full", index <= stepIndex ? "bg-amber" : "bg-line")} />
                  <span className={cx("text-[10px] font-semibold leading-tight", index === stepIndex ? "text-ink" : "text-muted")}>{step.label}</span>
                </li>
              ))}
            </ol>
          ) : null}
        </Card>

        {trip.driver && live ? (
          <Card className="grid gap-4 p-5">
            <div className="flex items-center gap-3">
              <Avatar name={trip.driver.name} color={trip.driver.avatar_color} size={52} />
              <div className="min-w-0 flex-1">
                <p className="font-bold">{trip.driver.name}</p>
                <p className="flex items-center gap-1 text-sm text-muted">
                  <Star className="size-3.5 fill-amber text-amber" aria-hidden="true" />{trip.driver.rating?.toFixed(2)} · {trip.driver.vehicle}
                </p>
              </div>
              {trip.driver.phone ? (
                <a href={`tel:${trip.driver.phone}`} className="grid size-11 place-items-center rounded-full bg-teal-soft text-teal" aria-label={`Call ${trip.driver.name}`}>
                  <Phone className="size-5" aria-hidden="true" />
                </a>
              ) : null}
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-canvas px-4 py-3">
              <span className="rounded-lg border-2 border-ink bg-amber-soft px-3 py-1 font-mono text-lg font-extrabold tracking-wider">{trip.driver.plate}</span>
              {trip.pin && trip.status !== "in_progress" ? (
                <span className="text-right">
                  <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">Your PIN</span>
                  <span className="font-mono text-2xl font-extrabold tracking-[0.3em]">{trip.pin}</span>
                </span>
              ) : null}
            </div>
            {trip.status === "driver_arrived" ? <Alert tone="info">Your driver is at the pickup. Share your PIN to start the ride.</Alert> : null}
          </Card>
        ) : null}

        <Card className="grid gap-3 p-5 text-sm">
          <div className="flex gap-3">
            <span className="mt-1.5 size-2.5 shrink-0 rounded-full bg-success" aria-hidden="true" />
            <p><span className="block text-xs font-semibold text-muted">Pickup</span>{trip.pickup.name}</p>
          </div>
          <div className="flex gap-3">
            <span className="mt-1.5 size-2.5 shrink-0 bg-ink" aria-hidden="true" />
            <p><span className="block text-xs font-semibold text-muted">Drop</span>{trip.drop.name}</p>
          </div>
          {live ? (
            <p className="flex items-center justify-between border-t border-line pt-3">
              <span className="text-muted">{trip.vehicle_type_name} · {minutes(trip.duration_min)} · {trip.payment_method === "cash" ? "Cash" : "Wallet"}</span>
              <span className="text-base font-extrabold">{inr(trip.fare_estimate)}</span>
            </p>
          ) : null}
        </Card>

        {live ? (
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              onClick={async () => {
                const text = `I'm on a RideNow ride (${trip.code}) from ${trip.pickup.name} to ${trip.drop.name}${trip.driver ? ` with ${trip.driver.name}, ${trip.driver.plate}` : ""}.`;
                try {
                  await navigator.clipboard.writeText(text);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                } catch {
                  setCopied(false);
                }
              }}
            >
              <Copy className="size-4" aria-hidden="true" /> {copied ? "Copied" : "Share trip"}
            </Button>
            {trip.status !== "in_progress" ? (
              <Button variant="outline" className="text-danger" onClick={() => setCancelOpen(true)}>
                <XCircle className="size-4" aria-hidden="true" /> Cancel ride
              </Button>
            ) : (
              <ButtonLink href={`/help?trip=${trip.id}`} variant="outline"><ShieldCheck className="size-4" aria-hidden="true" /> Safety</ButtonLink>
            )}
          </div>
        ) : null}

        {trip.status === "completed" ? (
          <>
            <Card className="p-5">
              <p className="mb-3 flex items-center gap-2 font-bold text-success"><CheckCircle2 className="size-5" aria-hidden="true" /> You've arrived</p>
              <Receipt trip={trip} />
            </Card>
            {trip.driver && trip.my_rating === null ? (
              <Card className="p-5">
                <RateTrip tripId={trip.id} driverName={trip.driver.name} onRated={(stars) => setTrip({ ...trip, my_rating: stars })} />
              </Card>
            ) : null}
            <div className="grid grid-cols-2 gap-2">
              <ButtonLink href="/ride" variant="dark">Book another ride</ButtonLink>
              <ButtonLink href={`/help?trip=${trip.id}`} variant="outline">Get help</ButtonLink>
            </div>
          </>
        ) : null}

        {trip.status === "cancelled" || trip.status === "no_driver" ? (
          <Card className="grid gap-3 p-5">
            <p className="text-sm text-muted">{trip.cancel_reason}</p>
            {trip.fare_final ? <Receipt trip={trip} /> : <p className="text-sm font-semibold text-success">You were not charged.</p>}
            <ButtonLink href="/ride" variant="dark">{trip.status === "no_driver" ? "Try again" : "Book a new ride"}</ButtonLink>
          </Card>
        ) : null}
      </div>

      <Sheet open={cancelOpen} onClose={() => setCancelOpen(false)} title="Cancel this ride?">
        <div className="grid gap-2" role="radiogroup" aria-label="Reason">
          {CANCEL_REASONS.map((r) => (
            <button key={r} type="button" role="radio" aria-checked={reason === r} onClick={() => setReason(r)} className={cx("rounded-2xl border-2 px-4 py-3 text-left text-sm font-semibold", reason === r ? "border-ink" : "border-line")}>
              {r}
            </button>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">
          {cancelFee ? "Your driver has waited more than 3 minutes, so a ₹50 fee goes to them." : "Cancelling now is free."}
        </p>
        <div className="mt-5 grid grid-cols-2 gap-2">
          <Button variant="outline" onClick={() => setCancelOpen(false)}>Keep ride</Button>
          <Button variant="danger" busy={cancelling} onClick={cancel}>Cancel ride</Button>
        </div>
      </Sheet>
    </div>
  );
}
