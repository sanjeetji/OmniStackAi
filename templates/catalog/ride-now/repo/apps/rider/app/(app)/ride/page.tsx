"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowDownUp, Banknote, BadgePercent, CarFront, Flame, Users, Wallet } from "lucide-react";
import { ApiError, inr, km, minutes, type Estimate, type Place, type Stop, type Trip } from "@ridenow/shared";
import { CityMap, type MapMarker } from "@ridenow/shared/map";
import { AppShell } from "@/components/app-shell";
import { PlaceSearch } from "@/components/place-search";
import { Alert, Badge, Button, Card, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

const EMOJI: Record<string, string> = { bike: "🛵", auto: "🛺", mini: "🚗", sedan: "🚘", xl: "🚙" };

export default function RidePage() {
  return (
    <AppShell wide>
      <Booking />
    </AppShell>
  );
}

function Booking() {
  const router = useRouter();
  const { user } = useSession();
  const [pickup, setPickup] = useState<Stop | null>(null);
  const [drop, setDrop] = useState<Stop | null>(null);
  const [picking, setPicking] = useState<"pickup" | "drop" | null>(null);
  const [saved, setSaved] = useState<Place[]>([]);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [loadingEstimate, setLoadingEstimate] = useState(false);
  const [vehicle, setVehicle] = useState("mini");
  const [payment, setPayment] = useState<"wallet" | "cash">("wallet");
  const [promoInput, setPromoInput] = useState("");
  const [promo, setPromo] = useState("");
  const [balance, setBalance] = useState<number | null>(null);
  const [active, setActive] = useState<Trip | null>(null);
  const [error, setError] = useState<{ message: string; code: string } | null>(null);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    api.get<{ places: Place[] }>("/rider/places").then((r) => {
      setSaved(r.places);
      const home = r.places.find((p) => p.label === "Home");
      if (home) setPickup((current) => current ?? { name: home.name, lat: home.lat, lng: home.lng });
    }).catch(() => undefined);
    api.get<{ balance: number }>("/rider/wallet").then((r) => setBalance(r.balance)).catch(() => undefined);
    api.get<{ trip: Trip | null }>("/rider/trips/active").then((r) => setActive(r.trip)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!pickup || !drop) {
      setEstimate(null);
      return;
    }
    let cancelled = false;
    setLoadingEstimate(true);
    api.post<Estimate>("/fare/estimate", { pickup, drop, promo_code: promo || undefined })
      .then((result) => {
        if (cancelled) return;
        setEstimate(result);
        if (!result.options.some((o) => o.vehicle_type === vehicle) && result.options[0]) setVehicle(result.options[0].vehicle_type);
      })
      .catch((err) => !cancelled && setError({ message: err instanceof ApiError ? err.message : "Couldn't get fares.", code: "estimate" }))
      .finally(() => !cancelled && setLoadingEstimate(false));
    return () => {
      cancelled = true;
    };
  }, [pickup, drop, promo]); // eslint-disable-line react-hooks/exhaustive-deps

  const chosen = estimate?.options.find((o) => o.vehicle_type === vehicle) ?? null;
  const markers = useMemo<MapMarker[]>(() => [
    ...(pickup ? [{ id: "pickup", kind: "pickup" as const, ...pickup, label: "Pickup" }] : []),
    ...(drop ? [{ id: "drop", kind: "drop" as const, ...drop, label: "Drop" }] : []),
  ], [pickup, drop]);

  function pickOnMap(point: { lat: number; lng: number }) {
    if (!picking) return;
    const stop = { name: `Pinned location (${point.lat.toFixed(4)}, ${point.lng.toFixed(4)})`, ...point };
    if (picking === "pickup") setPickup(stop);
    else setDrop(stop);
    setPicking(null);
  }

  async function book() {
    if (!pickup || !drop || !chosen) return;
    setBooking(true);
    setError(null);
    try {
      const trip = await api.post<Trip>("/rider/trips", { pickup, drop, vehicle_type: vehicle, payment_method: payment, promo_code: promo || undefined });
      router.push(`/trip/${trip.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? { message: err.message, code: err.code } : { message: "Couldn't book the ride. Please try again.", code: "error" });
      setBooking(false);
    }
  }

  const shortOfMoney = payment === "wallet" && chosen && balance !== null && balance < chosen.fare.total;

  return (
    <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
      <div className="order-2 grid content-start gap-4 lg:order-1">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Where to, {user?.full_name.split(" ")[0]}?</h1>
          <p className="mt-1 text-sm text-muted">Upfront fares. No surprises.</p>
        </div>

        {active ? (
          <Link href={`/trip/${active.id}`} className="flex items-center gap-3 rounded-2xl bg-ink px-4 py-3 text-white">
            <CarFront className="size-5 text-amber" aria-hidden="true" />
            <span className="flex-1 text-sm font-semibold">You have a ride in progress · {active.code}</span>
            <span className="text-sm text-amber">Open</span>
          </Link>
        ) : null}

        <Card className="relative grid gap-2 p-3">
          <PlaceSearch label="Pickup" tone="pickup" value={pickup} onChange={setPickup} saved={saved} picking={picking === "pickup"} onPickOnMap={() => setPicking(picking === "pickup" ? null : "pickup")} />
          <button
            type="button"
            onClick={() => { setPickup(drop); setDrop(pickup); }}
            className="absolute right-16 top-[calc(50%-18px)] z-10 grid size-9 place-items-center rounded-full border border-line bg-white shadow-sm hover:bg-canvas"
            aria-label="Swap pickup and drop"
          >
            <ArrowDownUp className="size-4" aria-hidden="true" />
          </button>
          <PlaceSearch label="Drop" tone="drop" value={drop} onChange={setDrop} saved={saved} picking={picking === "drop"} onPickOnMap={() => setPicking(picking === "drop" ? null : "drop")} autoFocus={Boolean(pickup) && !drop} />
          {saved.length > 0 && !drop ? (
            <div className="flex flex-wrap gap-2 px-1 pt-1">
              {saved.filter((p) => p.name !== pickup?.name).slice(0, 4).map((p) => (
                <button key={p.id} type="button" onClick={() => setDrop({ name: p.name, lat: p.lat, lng: p.lng })} className="rounded-full bg-canvas px-3 py-1.5 text-xs font-semibold hover:bg-black/5">
                  {p.label}
                </button>
              ))}
            </div>
          ) : null}
        </Card>

        {picking ? <Alert tone="info">Tap the map to set your {picking}.</Alert> : null}

        {pickup && drop ? (
          <Card className="p-3">
            {loadingEstimate && !estimate ? (
              <div className="grid gap-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-18" />)}</div>
            ) : estimate ? (
              <>
                <div className="flex flex-wrap items-center gap-2 px-2 pb-3 pt-1 text-sm text-muted">
                  <span>{km(estimate.distance_km)}</span>·<span>about {minutes(estimate.duration_min)}</span>
                  {estimate.surge > 1 ? (
                    <Badge tone="amber"><Flame className="size-3.5" aria-hidden="true" /> {estimate.surge.toFixed(2)}× in {estimate.surge_zone}</Badge>
                  ) : null}
                </div>
                <div role="radiogroup" aria-label="Vehicle" className="grid gap-1.5">
                  {estimate.options.map((option) => {
                    const selected = option.vehicle_type === vehicle;
                    return (
                      <button
                        key={option.vehicle_type}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        onClick={() => setVehicle(option.vehicle_type)}
                        className={cx("flex items-center gap-3 rounded-2xl border-2 px-3 py-3 text-left transition", selected ? "border-ink bg-canvas" : "border-transparent hover:bg-canvas")}
                      >
                        <span className="text-3xl" aria-hidden="true">{EMOJI[option.vehicle_type] ?? "🚗"}</span>
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center gap-2 font-bold">
                            {option.name}
                            <span className="inline-flex items-center gap-0.5 text-xs font-medium text-muted"><Users className="size-3" aria-hidden="true" />{option.seats}</span>
                          </span>
                          <span className="block text-xs text-muted">
                            {option.pickup_eta_min === null ? "No drivers nearby right now" : `${option.pickup_eta_min} min away · ${option.drivers_nearby} nearby`}
                          </span>
                        </span>
                        <span className="text-right">
                          <span className="block text-lg font-extrabold">{inr(option.fare.total)}</span>
                          {option.fare.discount > 0 ? <span className="block text-xs text-muted line-through">{inr(option.fare.total + option.fare.discount)}</span> : null}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </>
            ) : null}
          </Card>
        ) : (
          <Card className="grid gap-1 p-5 text-sm text-muted">
            <p className="font-semibold text-ink">Tip</p>
            <p>Pick a saved place, search the city, or tap the pin icon and choose a spot on the map.</p>
          </Card>
        )}

        {estimate ? (
          <Card className="grid gap-3 p-4">
            <form
              className="flex items-center gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                setPromo(promoInput.trim().toUpperCase());
              }}
            >
              <BadgePercent className="size-5 shrink-0 text-muted" aria-hidden="true" />
              <input value={promoInput} onChange={(e) => setPromoInput(e.target.value)} placeholder="Promo code" aria-label="Promo code" className="h-10 min-w-0 flex-1 rounded-xl bg-canvas px-3 text-sm font-semibold uppercase outline-none focus:ring-2 focus:ring-amber/40" />
              {promo ? (
                <Button type="button" variant="ghost" size="sm" onClick={() => { setPromo(""); setPromoInput(""); }}>Remove</Button>
              ) : (
                <Button type="submit" variant="outline" size="sm" disabled={!promoInput.trim()}>Apply</Button>
              )}
            </form>
            {estimate.promo ? (
              <p className={cx("text-xs font-semibold", estimate.promo.valid ? "text-success" : "text-danger")}>
                {estimate.promo.valid ? `${estimate.promo.code} applied. You save ${inr(chosen?.fare.discount ?? 0)}.` : estimate.promo.message}
              </p>
            ) : null}
            <div role="radiogroup" aria-label="Payment" className="grid grid-cols-2 gap-2">
              {([["wallet", Wallet, balance === null ? "Wallet" : `Wallet · ${inr(balance)}`], ["cash", Banknote, "Cash"]] as const).map(([value, Icon, text]) => (
                <button key={value} type="button" role="radio" aria-checked={payment === value} onClick={() => setPayment(value)} className={cx("flex h-12 items-center justify-center gap-2 rounded-2xl border-2 text-sm font-semibold", payment === value ? "border-ink" : "border-line text-muted")}>
                  <Icon className="size-4" aria-hidden="true" /> {text}
                </button>
              ))}
            </div>
          </Card>
        ) : null}

        {error ? (
          <Alert>
            {error.message}{" "}
            {error.code === "insufficient_balance" ? <Link href="/wallet" className="underline">Add money</Link> : null}
            {error.code === "active_trip" && active ? <Link href={`/trip/${active.id}`} className="underline">Open your ride</Link> : null}
          </Alert>
        ) : null}
        {shortOfMoney ? <Alert tone="info">Your wallet is {inr(balance ?? 0)}. <Link href="/wallet" className="underline">Add money</Link> or pay in cash.</Alert> : null}

        <Button size="lg" disabled={!chosen || Boolean(shortOfMoney) || Boolean(active)} busy={booking} onClick={book} className="w-full">
          {chosen ? `Book ${chosen.name} · ${inr(chosen.fare.total)}` : "Choose pickup and drop"}
        </Button>
      </div>

      <div className="order-1 h-[42vh] overflow-hidden rounded-[28px] shadow-[var(--shadow-card)] ring-1 ring-black/5 lg:sticky lg:top-24 lg:order-2 lg:h-[calc(100dvh-8rem)]">
        <CityMap markers={markers} route={pickup && drop ? [pickup, drop] : null} onPick={picking ? pickOnMap : undefined} ariaLabel="Trip map" />
      </div>
    </div>
  );
}
