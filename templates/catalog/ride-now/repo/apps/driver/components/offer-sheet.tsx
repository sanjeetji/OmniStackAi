"use client";

import { useEffect, useState } from "react";
import { Banknote, MapPin, Navigation, Star, Wallet } from "lucide-react";
import { inr, km, minutes } from "@ridenow/shared";
import { useDriver } from "@/lib/driver";
import { Button, Sheet, Tag } from "./ui";

/** The incoming request, on whatever page the driver is. Expires when the API says so. */
export function OfferSheet() {
  const { offer, accept, decline, trip } = useDriver();
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!offer) return;
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [offer]);

  if (!offer || (trip && ["driver_assigned", "driver_arrived", "in_progress"].includes(trip.status))) return null;
  const total = new Date(offer.expires_at).getTime() - new Date(offer.offered_at).getTime();
  const left = Math.max(0, new Date(offer.expires_at).getTime() - now);
  const fraction = total > 0 ? left / total : 0;
  const seconds = Math.ceil(left / 1000);
  const circumference = 2 * Math.PI * 26;

  return (
    <Sheet open title="New ride request">
      <div className="grid gap-4">
        <div className="flex items-center gap-4">
          <div className="relative grid size-16 shrink-0 place-items-center">
            <svg viewBox="0 0 60 60" className="absolute inset-0 -rotate-90" aria-hidden="true">
              <circle cx="30" cy="30" r="26" fill="none" stroke="var(--color-line)" strokeWidth="5" />
              <circle cx="30" cy="30" r="26" fill="none" stroke={seconds <= 5 ? "var(--color-danger)" : "var(--color-go)"} strokeWidth="5" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - fraction)} style={{ transition: "stroke-dashoffset 0.25s linear" }} />
            </svg>
            <span className="text-xl font-extrabold tabular-nums" aria-live="polite">{seconds}</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-3xl font-extrabold text-go">{inr(offer.estimated_earning)}</p>
            <p className="text-sm text-fg-muted">
              You earn · fare {inr(offer.fare)}
              {offer.surge > 1 ? <span className="text-warn"> · {offer.surge.toFixed(2)}× surge</span> : null}
            </p>
          </div>
        </div>
        <div className="grid gap-3 rounded-2xl bg-raised p-4 text-sm">
          <p className="flex gap-3"><Navigation className="mt-0.5 size-4 shrink-0 text-go" aria-hidden="true" /><span><span className="block text-xs text-fg-muted">Pickup · {km(offer.pickup_km)} away</span>{offer.pickup.name}</span></p>
          <p className="flex gap-3"><MapPin className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden="true" /><span><span className="block text-xs text-fg-muted">Drop · {km(offer.trip_km)} · {minutes(offer.trip_min)}</span>{offer.drop.name}</span></p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Tag>{offer.rider_name}</Tag>
          {offer.rider_rating ? <Tag tone="warn"><Star className="size-3 fill-warn" aria-hidden="true" />{offer.rider_rating.toFixed(1)}</Tag> : <Tag>New rider</Tag>}
          <Tag tone={offer.payment_method === "cash" ? "info" : "go"}>
            {offer.payment_method === "cash" ? <Banknote className="size-3" aria-hidden="true" /> : <Wallet className="size-3" aria-hidden="true" />}
            {offer.payment_method === "cash" ? "Cash" : "Wallet"}
          </Tag>
        </div>
        <div className="grid grid-cols-[1fr_2fr] gap-2">
          <Button variant="outline" size="lg" onClick={() => void decline()}>Decline</Button>
          <Button size="lg" busy={busy} onClick={async () => { setBusy(true); await accept(); setBusy(false); }}>Accept</Button>
        </div>
      </div>
    </Sheet>
  );
}
