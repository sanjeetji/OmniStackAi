import { config } from "../config.ts";
import { one, query, tx } from "../db.ts";
import { conflict, notFound } from "../lib/errors.ts";
import { hub } from "../lib/events.ts";
import { bearing, haversineKm, interpolate } from "../lib/geo.ts";
import { DISPATCH_RADIUS_KM, MAX_DISPATCH_ATTEMPTS, OFFER_SECONDS, rankCandidates, type Candidate } from "../lib/dispatch-rank.ts";
import { num } from "../lib/money.ts";
import { notify } from "./notify.ts";
import { assignDriverIn, broadcastTrip, completeTrip, markArrived, recordEvent, startTrip } from "./trips.ts";

/** A trip with nobody to offer it to gives up after this long. */
export const SEARCH_TIMEOUT_SECONDS = 150;

/** Offer a requested trip to the best next driver, or give up once the attempts or time run out. */
export async function dispatchNext(tripId: string): Promise<void> {
  let offered: { driverId: string; offerId: string } | null = null;
  let changed = false;
  await tx(async (client) => {
    const trip = await one<Record<string, any>>("SELECT * FROM trips WHERE id = $1 FOR UPDATE", [tripId], client);
    if (!trip || trip.status !== "requested") return;
    const pending = await one("SELECT 1 FROM ride_offers WHERE trip_id = $1 AND status = 'pending'", [tripId], client);
    if (pending) return;
    const ageSeconds = (Date.now() - new Date(trip.requested_at).getTime()) / 1000;
    const giveUp = async (why: string) => {
      await client.query("UPDATE trips SET status = 'no_driver', cancelled_at = now(), cancelled_by = 'system', cancel_reason = $2, payment_status = 'waived' WHERE id = $1", [tripId, why]);
      await recordEvent(client, tripId, "no_driver", "system", { attempts: trip.dispatch_attempts });
      await notify(client, trip.rider_id, "trip", "No drivers available", "We couldn't find a driver nearby. Please try again in a few minutes.");
      changed = true;
    };
    if (trip.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS) return giveUp("No driver accepted the ride.");

    const alreadyOffered = new Set(
      (await query<{ driver_id: string }>("SELECT driver_id FROM ride_offers WHERE trip_id = $1", [tripId], client)).map((r) => r.driver_id),
    );
    const candidates = await query<Candidate & { rating_avg: string }>(
      `SELECT d.user_id, d.lat, d.lng, d.rating_avg, d.simulated
         FROM drivers d JOIN users u ON u.id = d.user_id
        WHERE d.online AND d.status = 'approved' AND u.status = 'active' AND d.vehicle_type = $1 AND d.lat IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM trips t WHERE t.driver_id = d.user_id AND t.status IN ('driver_assigned', 'driver_arrived', 'in_progress'))
          AND NOT EXISTS (SELECT 1 FROM ride_offers o WHERE o.driver_id = d.user_id AND o.status = 'pending')`,
      [trip.vehicle_type],
      client,
    );
    const ranked = rankCandidates(
      { lat: trip.pickup_lat, lng: trip.pickup_lng },
      candidates.map((c) => ({ ...c, rating_avg: num(c.rating_avg) })),
      alreadyOffered,
    );
    if (ranked.length === 0) {
      if (ageSeconds > SEARCH_TIMEOUT_SECONDS) await giveUp(`No ${trip.vehicle_type} drivers within ${DISPATCH_RADIUS_KM} km.`);
      return;
    }
    const best = ranked[0];
    const offer = await one<{ id: string }>(
      `INSERT INTO ride_offers (trip_id, driver_id, pickup_km, expires_at) VALUES ($1, $2, $3, now() + ($4 || ' seconds')::interval) RETURNING id`,
      [tripId, best.user_id, best.pickupKm, String(OFFER_SECONDS)],
      client,
    );
    await client.query("UPDATE trips SET dispatch_attempts = dispatch_attempts + 1 WHERE id = $1", [tripId]);
    await client.query("UPDATE drivers SET offers_received = offers_received + 1 WHERE user_id = $1", [best.user_id]);
    await recordEvent(client, tripId, "offer_sent", "system", { driver_id: best.user_id, pickup_km: best.pickupKm });
    offered = { driverId: best.user_id, offerId: offer!.id };
  });
  if (offered) {
    const { driverId, offerId } = offered as { driverId: string; offerId: string };
    hub.publish(`user:${driverId}`, "offer.new", await offerJson(offerId));
  }
  if (changed) await broadcastTrip(tripId);
}

export async function offerJson(offerId: string) {
  const row = await one<Record<string, any>>(
    `SELECT o.id, o.trip_id, o.status, o.pickup_km, o.offered_at, o.expires_at,
            t.code, t.vehicle_type, t.pickup_name, t.pickup_lat, t.pickup_lng, t.drop_name, t.drop_lat, t.drop_lng,
            t.distance_km, t.duration_min, t.fare_estimate, t.discount, t.surge, t.payment_method,
            vt.commission_pct, u.full_name AS rider_name,
            (SELECT round(avg(stars)::numeric, 2) FROM ratings WHERE to_user = t.rider_id) AS rider_rating
       FROM ride_offers o JOIN trips t ON t.id = o.trip_id JOIN vehicle_types vt ON vt.id = t.vehicle_type
       JOIN users u ON u.id = t.rider_id
      WHERE o.id = $1`,
    [offerId],
  );
  if (!row) return null;
  const fare = num(row.fare_estimate);
  const gross = fare + num(row.discount);
  return {
    id: row.id,
    trip_id: row.trip_id,
    status: row.status,
    code: row.code,
    vehicle_type: row.vehicle_type,
    pickup: { name: row.pickup_name, lat: row.pickup_lat, lng: row.pickup_lng },
    drop: { name: row.drop_name, lat: row.drop_lat, lng: row.drop_lng },
    pickup_km: num(row.pickup_km),
    trip_km: num(row.distance_km),
    trip_min: num(row.duration_min),
    fare,
    estimated_earning: Math.round(gross * (1 - num(row.commission_pct) / 100) * 100) / 100,
    surge: num(row.surge),
    payment_method: row.payment_method,
    rider_name: row.rider_name,
    rider_rating: row.rider_rating === null ? null : num(row.rider_rating),
    offered_at: row.offered_at,
    expires_at: row.expires_at,
  };
}

export async function acceptOffer(offerId: string, driverId: string): Promise<string> {
  const tripId = await tx(async (client) => {
    const offer = await one<Record<string, any>>(
      "SELECT *, expires_at < now() AS expired FROM ride_offers WHERE id = $1 FOR UPDATE",
      [offerId],
      client,
    );
    if (!offer || offer.driver_id !== driverId) throw notFound("Ride request");
    if (offer.status !== "pending" || offer.expired) throw conflict("This request is no longer available.", "offer_closed");
    await client.query("UPDATE ride_offers SET status = 'accepted', responded_at = now() WHERE id = $1", [offerId]);
    await client.query("UPDATE drivers SET offers_accepted = offers_accepted + 1 WHERE user_id = $1", [driverId]);
    await assignDriverIn(client, offer.trip_id, driverId, "driver");
    return offer.trip_id as string;
  });
  hub.publish(`user:${driverId}`, "offer.closed", { id: offerId, status: "accepted" });
  await broadcastTrip(tripId);
  return tripId;
}

export async function declineOffer(offerId: string, driverId: string): Promise<void> {
  const offer = await one<{ trip_id: string }>(
    "UPDATE ride_offers SET status = 'declined', responded_at = now() WHERE id = $1 AND driver_id = $2 AND status = 'pending' RETURNING trip_id",
    [offerId, driverId],
  );
  if (!offer) throw notFound("Ride request");
  hub.publish(`user:${driverId}`, "offer.closed", { id: offerId, status: "declined" });
  await dispatchNext(offer.trip_id);
}

// --- the sweeper: expiries, re-dispatch and (in the preview) simulated drivers -------------------

const ARRIVE_KM = 0.08;
const SIM_ACCEPT_AFTER_MS = 2500;
const SIM_START_AFTER_MS = 4000;

async function moveSimulatedDriver(trip: Record<string, any>, target: { lat: number; lng: number }): Promise<boolean> {
  const here = { lat: trip.driver_lat, lng: trip.driver_lng };
  const remaining = haversineKm(here, target);
  if (remaining <= ARRIVE_KM) return true;
  const step = Math.max(0.3, remaining / 6);
  const next = step >= remaining ? target : interpolate(here, target, step / remaining);
  const heading = bearing(here, next);
  await query("UPDATE drivers SET lat = $2, lng = $3, heading = $4, last_seen_at = now() WHERE user_id = $1", [trip.driver_id, next.lat, next.lng, heading]);
  const payload = { trip_id: trip.id, driver_id: trip.driver_id, lat: next.lat, lng: next.lng, heading };
  hub.publish(`user:${trip.rider_id}`, "driver.location", payload);
  hub.publish("admin", "driver.location", payload);
  return haversineKm(next, target) <= ARRIVE_KM;
}

let running = false;

export async function sweep(): Promise<void> {
  if (running) return;
  running = true;
  try {
    const expired = await query<{ id: string; trip_id: string; driver_id: string }>(
      "UPDATE ride_offers SET status = 'expired', responded_at = now() WHERE status = 'pending' AND expires_at < now() RETURNING id, trip_id, driver_id",
    );
    for (const offer of expired) hub.publish(`user:${offer.driver_id}`, "offer.closed", { id: offer.id, status: "expired" });

    const waiting = await query<{ id: string }>(
      `SELECT t.id FROM trips t WHERE t.status = 'requested'
         AND NOT EXISTS (SELECT 1 FROM ride_offers o WHERE o.trip_id = t.id AND o.status = 'pending')`,
    );
    for (const trip of waiting) await dispatchNext(trip.id);

    // Real drivers who stopped sending locations go offline.
    await query("UPDATE drivers SET online = FALSE WHERE online AND NOT simulated AND last_seen_at < now() - interval '3 minutes'");

    if (config.simulation) await simulate();
  } catch (error) {
    console.error("[dispatch] sweep failed:", error);
  } finally {
    running = false;
  }
}

async function simulate(): Promise<void> {
  const offers = await query<{ id: string; driver_id: string }>(
    `SELECT o.id, o.driver_id FROM ride_offers o JOIN drivers d ON d.user_id = o.driver_id
      WHERE o.status = 'pending' AND d.simulated AND o.offered_at < now() - ($1 || ' milliseconds')::interval`,
    [String(SIM_ACCEPT_AFTER_MS)],
  );
  for (const offer of offers) {
    try {
      await acceptOffer(offer.id, offer.driver_id);
    } catch {
      // Raced with an expiry or cancellation; the next sweep moves on.
    }
  }
  const active = await query<Record<string, any>>(
    `SELECT t.*, d.lat AS driver_lat, d.lng AS driver_lng FROM trips t JOIN drivers d ON d.user_id = t.driver_id
      WHERE d.simulated AND t.status IN ('driver_assigned', 'driver_arrived', 'in_progress')`,
  );
  for (const trip of active) {
    try {
      if (trip.status === "driver_assigned") {
        if (await moveSimulatedDriver(trip, { lat: trip.pickup_lat, lng: trip.pickup_lng })) await markArrived(trip.id, null, "system");
      } else if (trip.status === "driver_arrived") {
        if (Date.now() - new Date(trip.arrived_at).getTime() > SIM_START_AFTER_MS) await startTrip(trip.id, null, null, "system");
      } else if (await moveSimulatedDriver(trip, { lat: trip.drop_lat, lng: trip.drop_lng })) {
        await completeTrip(trip.id, null, "system");
      }
    } catch (error) {
      console.error(`[simulation] trip ${trip.code}:`, error);
    }
  }
}

let timer: NodeJS.Timeout | null = null;

export function startDispatcher(intervalMs = 1500): void {
  if (timer) return;
  timer = setInterval(() => void sweep(), intervalMs);
  timer.unref();
}

export function stopDispatcher(): void {
  if (timer) clearInterval(timer);
  timer = null;
}
