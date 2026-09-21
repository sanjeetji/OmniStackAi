import { Banknote, Wallet } from "lucide-react";
import { inr, km, minutes, type Trip } from "@ridenow/shared";

/** Fare breakdown for a completed (or charged-cancelled) trip. */
export function Receipt({ trip }: { trip: Trip }) {
  const total = trip.fare_final ?? trip.fare_estimate;
  const gross = trip.fare_estimate + trip.discount;
  return (
    <div className="grid gap-3 text-sm">
      <div className="flex items-center justify-between text-muted">
        <span>{trip.vehicle_type_name} · {km(trip.distance_km)} · {minutes(trip.duration_min)}</span>
        <span>{trip.code}</span>
      </div>
      <dl className="grid gap-2">
        <Row label="Ride fare" value={inr(gross)} />
        {trip.surge > 1 ? <Row label={`Includes surge ${trip.surge.toFixed(2)}×`} value="" muted /> : null}
        {trip.discount > 0 ? <Row label={`Promo ${trip.promo_code ?? ""}`} value={`−${inr(trip.discount)}`} accent /> : null}
        {trip.status === "cancelled" && trip.fare_final ? <Row label="Cancellation fee" value={inr(trip.fare_final)} /> : null}
      </dl>
      <div className="flex items-center justify-between border-t border-dashed border-line pt-3 text-base font-extrabold">
        <span>{trip.payment_status === "refunded" ? "Refunded" : "Total paid"}</span>
        <span>{inr(total)}</span>
      </div>
      <p className="flex items-center gap-2 text-xs text-muted">
        {trip.payment_method === "cash" ? <Banknote className="size-4" aria-hidden="true" /> : <Wallet className="size-4" aria-hidden="true" />}
        {trip.payment_method === "cash" ? "Paid in cash to the driver" : "Paid from your RideNow wallet"}
        {trip.payment_status === "refunded" ? " · refunded to your wallet" : ""}
      </p>
    </div>
  );
}

function Row({ label, value, muted, accent }: { label: string; value: string; muted?: boolean; accent?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${muted ? "text-xs text-muted" : ""}`}>
      <dt>{label}</dt>
      <dd className={accent ? "font-semibold text-success" : "font-semibold"}>{value}</dd>
    </div>
  );
}
