"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Banknote, CheckCircle2, MapPin, Navigation, Phone, Wallet } from "lucide-react";
import { ApiError, inr, km, minutes, type Trip } from "@ridenow/shared";
import { CityMap, type MapMarker } from "@ridenow/shared/map";
import { Shell } from "@/components/shell";
import { Avatar, Button, LinkButton, Notice, Panel, Sheet, Stars, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useDriver } from "@/lib/driver";

const CANCEL_REASONS = ["Rider not at pickup", "Rider asked to cancel", "Vehicle problem", "Unsafe pickup", "Other"] as const;
const RIDER_TAGS = ["Polite", "On time", "Clean", "Great conversation", "Late", "Rude"];

export default function TripPage() {
  return (
    <Shell title="Current trip">
      <ActiveTrip />
    </Shell>
  );
}

function ActiveTrip() {
  const { trip, setTrip, position, refresh } = useDriver();
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState<(typeof CANCEL_REASONS)[number]>("Rider not at pickup");
  const [stars, setStars] = useState(5);
  const [tags, setTags] = useState<string[]>([]);
  const [rated, setRated] = useState(false);

  const markers = useMemo<MapMarker[]>(() => {
    if (!trip) return [];
    const list: MapMarker[] = [];
    if (["driver_assigned", "driver_arrived"].includes(trip.status)) list.push({ id: "pickup", kind: "pickup", ...trip.pickup, label: "Pickup" });
    list.push({ id: "drop", kind: "drop", ...trip.drop, label: "Drop" });
    if (position) list.push({ id: "me", kind: "car", ...position, heading: position.heading });
    return list;
  }, [trip, position]);

  if (!trip) {
    return (
      <Panel className="grid justify-items-center gap-3 p-8 text-center">
        <Navigation className="size-8 text-fg-muted" aria-hidden="true" />
        <p className="font-bold">No active trip</p>
        <p className="text-sm text-fg-muted">Go online from Home to receive ride requests.</p>
        <LinkButton href="/" variant="go">Go to Home</LinkButton>
      </Panel>
    );
  }

  async function act(action: string, path: string, body?: unknown) {
    setBusy(action);
    setError(null);
    try {
      setTrip(await api.post<Trip>(path, body));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That didn't work. Try again.");
    } finally {
      setBusy(null);
    }
  }

  const target = trip.status === "in_progress" ? trip.drop : trip.pickup;
  const distanceLeft = position ? Math.hypot((target.lat - position.lat) * 110.57, (target.lng - position.lng) * 108.5) : null;

  if (trip.status === "completed") {
    const cash = trip.payment_method === "cash";
    return (
      <div className="grid gap-4">
        <Panel className="grid justify-items-center gap-2 p-6 text-center">
          <CheckCircle2 className="size-12 text-go" aria-hidden="true" />
          <p className="text-xl font-extrabold">Trip completed</p>
          <p className="text-4xl font-extrabold text-go">{inr(trip.driver_earning ?? 0)}</p>
          <p className="text-sm text-fg-muted">Your earning · fare {inr(trip.fare_final)} · commission {inr(trip.commission ?? 0)}</p>
        </Panel>
        <Notice tone={cash ? "warn" : "go"}>
          <span className="flex items-center gap-2">
            {cash ? <Banknote className="size-5" aria-hidden="true" /> : <Wallet className="size-5" aria-hidden="true" />}
            {cash ? `Collect ${inr(trip.fare_final)} in cash from the rider.` : "Paid from the rider's wallet. Nothing to collect."}
          </span>
        </Notice>
        {trip.rider && !rated ? (
          <Panel className="grid gap-4 p-5">
            <p className="font-bold">Rate {trip.rider.name.split(" ")[0]}</p>
            <Stars value={stars} onChange={setStars} size={34} />
            <div className="flex flex-wrap gap-2">
              {RIDER_TAGS.map((tag) => (
                <button key={tag} type="button" aria-pressed={tags.includes(tag)} onClick={() => setTags(tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag])} className={cx("rounded-full border px-3 py-1.5 text-sm font-semibold", tags.includes(tag) ? "border-go bg-go-soft text-go" : "border-line text-fg-muted")}>{tag}</button>
              ))}
            </div>
            <Button busy={busy === "rate"} onClick={async () => {
              setBusy("rate");
              try {
                await api.post(`/driver/trips/${trip.id}/rate`, { stars, tags });
                setRated(true);
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Couldn't save the rating.");
              } finally {
                setBusy(null);
              }
            }}>Submit rating</Button>
          </Panel>
        ) : null}
        {error ? <Notice>{error}</Notice> : null}
        <Button size="lg" variant="light" onClick={() => { setTrip(null); void refresh(); }}>Back to Home</Button>
      </div>
    );
  }

  if (trip.status === "cancelled" || trip.status === "no_driver") {
    return (
      <div className="grid gap-4">
        <Notice tone="warn">This trip was cancelled{trip.cancelled_by ? ` by the ${trip.cancelled_by}` : ""}. {trip.cancel_reason}</Notice>
        {trip.fare_final ? <Notice tone="go">You receive the {inr(trip.fare_final)} cancellation fee.</Notice> : null}
        <Button size="lg" variant="light" onClick={() => { setTrip(null); void refresh(); }}>Back to Home</Button>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div className="h-64 overflow-hidden rounded-[var(--radius-card)] border border-line/60">
        <CityMap markers={markers} route={[position ?? trip.pickup, target]} ariaLabel="Route to your next stop" />
      </div>

      <Panel className="grid gap-3 p-5">
        <p className="text-xs font-bold uppercase tracking-wider text-go">
          {trip.status === "driver_assigned" ? "Head to pickup" : trip.status === "driver_arrived" ? "Waiting at pickup" : "On trip"}
        </p>
        <p className="flex gap-3 text-lg font-bold">
          {trip.status === "in_progress" ? <MapPin className="mt-1 size-5 shrink-0 text-warn" aria-hidden="true" /> : <Navigation className="mt-1 size-5 shrink-0 text-go" aria-hidden="true" />}
          {target.name}
        </p>
        <p className="text-sm text-fg-muted">
          {distanceLeft !== null ? `${km(Math.max(0, distanceLeft * 1.3))} to go · ` : ""}
          {trip.status === "in_progress" ? `trip about ${minutes(trip.duration_min)}` : `then ${km(trip.distance_km)} to ${trip.drop.name}`}
        </p>
      </Panel>

      {trip.rider ? (
        <Panel className="flex items-center gap-3 p-4">
          <Avatar name={trip.rider.name} color={trip.rider.avatar_color} />
          <div className="min-w-0 flex-1">
            <p className="font-bold">{trip.rider.name}</p>
            <p className="text-sm text-fg-muted">{trip.code} · {trip.payment_method === "cash" ? `Cash ${inr(trip.fare_estimate)}` : "Wallet"}</p>
          </div>
          {trip.rider.phone ? (
            <a href={`tel:${trip.rider.phone}`} className="grid size-12 place-items-center rounded-2xl bg-go-soft text-go" aria-label={`Call ${trip.rider.name}`}>
              <Phone className="size-5" aria-hidden="true" />
            </a>
          ) : null}
        </Panel>
      ) : null}

      {error ? <Notice>{error}</Notice> : null}

      {trip.status === "driver_assigned" ? (
        <Button size="xl" busy={busy === "arrive"} onClick={() => act("arrive", `/driver/trips/${trip.id}/arrive`)}>I've arrived</Button>
      ) : null}

      {trip.status === "driver_arrived" ? (
        <form
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void act("start", `/driver/trips/${trip.id}/start`, { pin });
          }}
        >
          <label htmlFor="pin" className="text-sm font-semibold text-fg-muted">Ask the rider for their 4-digit PIN</label>
          <input
            id="pin"
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="• • • •"
            className="h-16 rounded-2xl border border-line bg-raised text-center font-mono text-3xl font-extrabold tracking-[0.6em] outline-none focus:border-go focus:ring-4 focus:ring-go/20"
          />
          <Button size="xl" type="submit" busy={busy === "start"} disabled={pin.length !== 4}>Start ride</Button>
        </form>
      ) : null}

      {trip.status === "in_progress" ? (
        <Button size="xl" busy={busy === "complete"} onClick={() => act("complete", `/driver/trips/${trip.id}/complete`)}>Complete trip</Button>
      ) : null}

      {trip.status !== "in_progress" ? (
        <Button variant="ghost" onClick={() => setCancelOpen(true)}>Cancel trip</Button>
      ) : null}

      <Sheet open={cancelOpen} onClose={() => setCancelOpen(false)} title="Cancel this trip?">
        <div className="grid gap-2" role="radiogroup" aria-label="Reason">
          {CANCEL_REASONS.map((r) => (
            <button key={r} type="button" role="radio" aria-checked={reason === r} onClick={() => setReason(r)} className={cx("rounded-2xl border px-4 py-3 text-left text-sm font-semibold", reason === r ? "border-go bg-go-soft" : "border-line")}>{r}</button>
          ))}
        </div>
        <p className="mt-3 text-xs text-fg-muted">Frequent cancellations lower your acceptance score.</p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Button variant="outline" onClick={() => setCancelOpen(false)}>Keep trip</Button>
          <Button variant="danger" busy={busy === "cancel"} onClick={async () => { await act("cancel", `/driver/trips/${trip.id}/cancel`, { reason }); setCancelOpen(false); }}>Cancel trip</Button>
        </div>
      </Sheet>
      <p className="text-center text-xs text-fg-muted">
        Need help? <Link href="/help" className="font-semibold text-fg underline-offset-4 hover:underline">Contact support</Link>
      </p>
    </div>
  );
}
