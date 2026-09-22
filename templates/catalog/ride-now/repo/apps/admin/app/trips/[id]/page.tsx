"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Ban, RotateCcw, Star } from "lucide-react";
import { ACTIVE_STATUSES, dateTimeLabel, inr, km, minutes, signedInr, timeLabel } from "@ridenow/shared";
import { CityMap, type MapMarker } from "@ridenow/shared/map";
import { Shell } from "@/components/shell";
import { LEDGER_KIND, PaymentBadge, TRIP_EVENT, TripStatusBadge } from "@/components/status";
import { Badge, Button, ErrorState, KeyValues, LoadingPage, Modal, Notice, PageHeader, Panel, Person, Table, TextArea, td, th } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin, useAdminEvent } from "@/lib/session";
import type { TripDetail } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

export default function TripPage() {
  return (
    <Shell>
      <TripView />
    </Shell>
  );
}

function TripView() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useAdmin();
  const { data: trip, error, reload } = useApi<TripDetail>(`/admin/trips/${id}`);
  const [dialog, setDialog] = useState<"cancel" | "refund" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  useAdminEvent(["trip.updated"], (_type, updated: { id: string }) => {
    if (updated.id === id) reload();
  });

  if (error && !trip) return <ErrorState message={error} onRetry={reload} />;
  if (!trip) return <LoadingPage label="Loading the trip" />;

  const active = ACTIVE_STATUSES.includes(trip.status);
  const refundable = trip.payment_status === "paid" && trip.fare_final !== null;
  const markers: MapMarker[] = [
    { id: "pickup", kind: "pickup", lat: trip.pickup.lat, lng: trip.pickup.lng, label: trip.pickup.name },
    { id: "drop", kind: "drop", lat: trip.drop.lat, lng: trip.drop.lng, label: trip.drop.name },
  ];
  if (active && trip.driver?.location) {
    markers.push({ id: "car", kind: "car", lat: trip.driver.location.lat, lng: trip.driver.location.lng, heading: trip.driver.location.heading, tone: "busy" });
  }

  async function act(kind: "cancel" | "refund") {
    setBusy(true);
    setActionError(null);
    try {
      await api.post(kind === "cancel" ? `/admin/trips/${id}/cancel` : `/admin/trips/${id}/refund`, { reason: reason.trim() });
      toast(kind === "cancel" ? `${trip!.code} cancelled` : `${inr(trip!.fare_final ?? 0)} refunded to ${trip!.rider?.name ?? "the rider"}`);
      setDialog(null);
      setReason("");
      reload();
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const fareRows: [string, string][] = [
    ["Upfront estimate", inr(trip.fare_estimate)],
    ...(trip.discount > 0 ? ([[`Promo ${trip.promo_code ?? ""}`.trim(), `−${inr(trip.discount)}`]] as [string, string][]) : []),
    ["Final fare", trip.fare_final === null ? "–" : inr(trip.fare_final)],
    ["Platform commission", trip.commission === null || trip.commission === undefined ? "–" : inr(trip.commission)],
    ["Driver earning", trip.driver_earning === null || trip.driver_earning === undefined ? "–" : inr(trip.driver_earning)],
  ];

  return (
    <>
      <PageHeader
        back={{ href: "/trips", label: "All trips" }}
        title={<span className="flex flex-wrap items-center gap-3">Trip <span className="font-mono">{trip.code}</span> <TripStatusBadge status={trip.status} /></span>}
        description={`${trip.pickup.name} → ${trip.drop.name} · requested ${dateTimeLabel(trip.requested_at)}`}
        actions={
          <>
            {active ? (
              <Button variant="danger" onClick={() => { setReason(""); setActionError(null); setDialog("cancel"); }}>
                <Ban className="size-4" aria-hidden="true" />
                Cancel trip
              </Button>
            ) : null}
            {refundable ? (
              <Button variant="secondary" onClick={() => { setReason(""); setActionError(null); setDialog("refund"); }}>
                <RotateCcw className="size-4" aria-hidden="true" />
                Refund {inr(trip.fare_final ?? 0)}
              </Button>
            ) : null}
          </>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="grid content-start gap-5">
          <Panel className="overflow-hidden">
            <div className="h-72">
              <CityMap markers={markers} route={[trip.pickup, trip.drop]} ariaLabel={`Route from ${trip.pickup.name} to ${trip.drop.name}`} />
            </div>
          </Panel>

          <Panel title="Timeline" description="Every state change, in order, with who made it">
            <ol className="grid gap-0 px-4 py-3">
              {(trip.events ?? []).map((event, index, all) => (
                <li key={index} className="relative flex gap-3 pb-4 last:pb-0">
                  {index < all.length - 1 ? <span className="absolute left-[5px] top-3 h-full w-px bg-line" aria-hidden="true" /> : null}
                  <span className={event.kind === "cancelled" ? "mt-1.5 size-[11px] shrink-0 rounded-full border-2 border-bad bg-panel" : "mt-1.5 size-[11px] shrink-0 rounded-full border-2 border-signal bg-panel"} aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium">{TRIP_EVENT[event.kind] ?? event.kind}</p>
                    <p className="text-xs text-muted">
                      {timeLabel(event.at)} · by {event.actor}
                      {eventNote(event.detail)}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </Panel>

          <Panel title="Dispatch" description="Drivers offered this ride, nearest first; each offer expires after 20 seconds">
            {trip.offers.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-muted">No offers were sent.</p>
            ) : (
              <Table label="Dispatch offers">
                <thead>
                  <tr>
                    <th className={th}>Driver</th>
                    <th className={`${th} text-right`}>Distance to pickup</th>
                    <th className={th}>Offered</th>
                    <th className={th}>Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {trip.offers.map((offer, index) => (
                    <tr key={index}>
                      <td className={td}>{offer.driver_name}</td>
                      <td className={`${td} num text-right`}>{km(offer.pickup_km)}</td>
                      <td className={`${td} text-ink-2`}>{timeLabel(offer.offered_at)}</td>
                      <td className={td}>
                        <Badge tone={offer.status === "accepted" ? "ok" : offer.status === "declined" ? "bad" : offer.status === "pending" ? "warn" : "neutral"} className="capitalize">{offer.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Panel>

          <Panel title="Money movements" description="Ledger lines booked for this trip; they always net to zero">
            {trip.ledger.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-muted">No money has moved for this trip.</p>
            ) : (
              <Table label="Ledger lines for this trip">
                <thead>
                  <tr>
                    <th className={th}>Account</th>
                    <th className={th}>Kind</th>
                    <th className={th}>Note</th>
                    <th className={th}>When</th>
                    <th className={`${th} text-right`}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {trip.ledger.map((line, index) => (
                    <tr key={index}>
                      <td className={td}>{line.account}</td>
                      <td className={td}>{LEDGER_KIND[line.kind] ?? line.kind}</td>
                      <td className={`${td} text-ink-2`}>{line.note || "–"}</td>
                      <td className={`${td} whitespace-nowrap text-ink-2`}>{timeLabel(line.created_at)}</td>
                      <td className={`${td} num text-right font-medium ${line.amount < 0 ? "text-bad" : "text-ok"}`}>{signedInr(line.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Panel>
        </div>

        <div className="grid content-start gap-5">
          <Panel title="Ride" bodyClassName="p-4">
            <KeyValues
              items={[
                ["Vehicle", trip.vehicle_type_name],
                ["Distance", km(trip.distance_km)],
                ["Duration", minutes(trip.duration_min)],
                ["Surge", trip.surge > 1 ? `${trip.surge.toFixed(2)}×` : "None"],
                ["Payment", <PaymentBadge key="p" method={trip.payment_method} status={trip.payment_status} />],
                ...(trip.cancel_reason ? ([["Cancelled", `${trip.cancelled_by ?? ""}: ${trip.cancel_reason}`]] as [string, string][]) : []),
              ]}
            />
          </Panel>
          <Panel title="Fare" bodyClassName="p-4">
            <KeyValues items={fareRows.map(([k, v]) => [k, <span key={k} className="num">{v}</span>])} />
          </Panel>
          <Panel title="People" bodyClassName="grid gap-4 p-4">
            {trip.rider ? (
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted">Rider</p>
                <Link href={`/riders/${trip.rider.id}`} className="block rounded-md hover:bg-sunken">
                  <Person name={trip.rider.name} color={trip.rider.avatar_color} sub={trip.rider.phone ?? undefined} />
                </Link>
              </div>
            ) : null}
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted">Driver</p>
              {trip.driver ? (
                <Link href={`/drivers/${trip.driver.id}`} className="block rounded-md hover:bg-sunken">
                  <Person name={trip.driver.name} color={trip.driver.avatar_color} sub={`${trip.driver.vehicle} · ${trip.driver.plate}`} />
                </Link>
              ) : (
                <p className="text-[13px] text-muted">No driver was assigned.</p>
              )}
            </div>
          </Panel>
          <Panel title="Ratings" bodyClassName="grid gap-3 p-4">
            {trip.ratings.length === 0 ? (
              <p className="text-[13px] text-muted">Not rated yet.</p>
            ) : (
              trip.ratings.map((rating, index) => (
                <div key={index}>
                  <p className="flex items-center gap-1.5 text-[13px] font-medium">
                    {rating.from_role === "rider" ? "Rider rated the driver" : "Driver rated the rider"}
                    <span className="num inline-flex items-center gap-0.5 text-warn"><Star className="size-3.5 fill-brand text-brand" aria-hidden="true" />{rating.stars}</span>
                  </p>
                  {rating.tags.length ? <p className="mt-1 flex flex-wrap gap-1">{rating.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}</p> : null}
                  {rating.comment ? <p className="mt-1 text-[13px] text-ink-2">“{rating.comment}”</p> : null}
                </div>
              ))
            )}
          </Panel>
        </div>
      </div>

      <Modal
        open={dialog !== null}
        onClose={() => setDialog(null)}
        title={dialog === "cancel" ? `Cancel ${trip.code}?` : `Refund ${trip.code}?`}
        description={
          dialog === "cancel"
            ? "The rider and driver are told immediately. Operator cancellations never charge the rider a fee."
            : `${inr(trip.fare_final ?? 0)} goes back to ${trip.rider?.name ?? "the rider"}'s RideNow wallet and is booked against the platform.`
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setDialog(null)}>Keep it</Button>
            <Button variant={dialog === "cancel" ? "danger" : "primary"} busy={busy} disabled={reason.trim().length < 3} onClick={() => dialog && void act(dialog)}>
              {dialog === "cancel" ? "Cancel trip" : "Refund"}
            </Button>
          </>
        }
      >
        <div className="grid gap-3">
          <TextArea label="Reason (shown to the rider and kept in the audit log)" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={200} placeholder={dialog === "cancel" ? "For example: safety report from the rider" : "For example: driver took a longer route"} />
          {actionError ? <Notice tone="bad">{actionError}</Notice> : null}
        </div>
      </Modal>
    </>
  );
}

/** The useful part of a trip event's detail: a reason, a fee or a refunded amount. */
function eventNote(detail: Record<string, unknown> | null | undefined): string {
  const d = detail ?? {};
  const parts: string[] = [];
  if (typeof d.reason === "string" && d.reason) parts.push(`“${d.reason}”`);
  if (typeof d.fee === "number" && d.fee > 0) parts.push(`fee ${inr(d.fee)}`);
  if (typeof d.amount === "number") parts.push(inr(d.amount));
  return parts.length ? ` · ${parts.join(" · ")}` : "";
}
