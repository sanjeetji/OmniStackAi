import type pg from "pg";
import { one, query, tx, type Queryable } from "../db.ts";
import { badRequest, conflict, notFound } from "../lib/errors.ts";
import { computeFare, splitFare, type VehiclePricing } from "../lib/fare.ts";
import { hub } from "../lib/events.ts";
import { money, num } from "../lib/money.ts";
import { evaluatePromo, type Promo } from "../lib/promo.ts";
import { assertTransition, cancellationFee, type Actor, type TripStatus } from "../lib/trip-state.ts";
import { haversineKm, type Point } from "../lib/geo.ts";
import { mockMaps } from "../providers/maps.ts";
import { notify } from "./notify.ts";
import { TRIP_SELECT, tripJson } from "./serialize.ts";
import { announceWallet, balanceOf, platformUser, postLedger } from "./wallet.ts";

export interface Stop extends Point {
  name: string;
}

export async function pricingFor(vehicleType: string, client?: Queryable): Promise<VehiclePricing & { name: string; active: boolean }> {
  const row = await one<Record<string, any>>("SELECT * FROM vehicle_types WHERE id = $1", [vehicleType], client);
  if (!row) throw badRequest("Choose a vehicle type.");
  return {
    id: row.id,
    name: row.name,
    active: row.active,
    base_fare: num(row.base_fare),
    per_km: num(row.per_km),
    per_min: num(row.per_min),
    min_fare: num(row.min_fare),
    booking_fee: num(row.booking_fee),
    commission_pct: num(row.commission_pct),
  };
}

/** The highest surge of the active zones that contain the pickup. */
export async function surgeAt(point: Point, client?: Queryable): Promise<{ surge: number; zone: string | null }> {
  const zones = await query<{ id: string; name: string; center_lat: number; center_lng: number; radius_km: string; surge: string }>(
    "SELECT id, name, center_lat, center_lng, radius_km, surge FROM zones WHERE active",
    [],
    client,
  );
  let best = { surge: 1, zone: null as string | null };
  for (const zone of zones) {
    if (haversineKm(point, { lat: zone.center_lat, lng: zone.center_lng }) <= num(zone.radius_km) && num(zone.surge) > best.surge) {
      best = { surge: num(zone.surge), zone: zone.name };
    }
  }
  return best;
}

export async function loadPromo(code: string, client?: Queryable): Promise<Promo | null> {
  const row = await one<Record<string, any>>("SELECT * FROM promo_codes WHERE upper(code) = upper($1)", [code], client);
  if (!row) return null;
  return {
    code: row.code,
    kind: row.kind,
    value: num(row.value),
    max_discount: row.max_discount === null ? null : num(row.max_discount),
    min_fare: num(row.min_fare),
    valid_until: row.valid_until,
    usage_limit: row.usage_limit,
    per_user_limit: row.per_user_limit,
    used_count: row.used_count,
    active: row.active,
  };
}

export async function promoUsesBy(riderId: string, code: string, client?: Queryable): Promise<number> {
  const row = await one<{ n: string }>(
    "SELECT count(*) AS n FROM trips WHERE rider_id = $1 AND upper(promo_code) = upper($2) AND status = 'completed'",
    [riderId, code],
    client,
  );
  return Number(row?.n ?? 0);
}

/** Estimates for every active vehicle type, with surge and an optional promo applied. */
export async function estimate(pickup: Point, drop: Point, riderId: string | null, promoCode = "") {
  const route = await mockMaps.route(pickup, drop);
  const { surge, zone } = await surgeAt(pickup);
  const types = await query<Record<string, any>>("SELECT * FROM vehicle_types WHERE active ORDER BY sort");
  const promo = promoCode ? await loadPromo(promoCode) : null;
  const uses = promo && riderId ? await promoUsesBy(riderId, promo.code) : 0;
  const nearest = await query<{ vehicle_type: string; lat: number; lng: number }>(
    "SELECT vehicle_type, lat, lng FROM drivers WHERE online AND status = 'approved' AND lat IS NOT NULL",
  );
  const options = types.map((row) => {
    const pricing = { ...row, base_fare: num(row.base_fare), per_km: num(row.per_km), per_min: num(row.per_min), min_fare: num(row.min_fare), booking_fee: num(row.booking_fee), commission_pct: num(row.commission_pct) } as VehiclePricing;
    const before = computeFare(pricing, route.distanceKm, route.durationMin, surge);
    let promoResult: { ok: boolean; discount?: number; reason?: string } | null = null;
    if (promo) promoResult = evaluatePromo(promo, before.total, uses);
    const fare = computeFare(pricing, route.distanceKm, route.durationMin, surge, promoResult?.ok ? promoResult.discount : 0);
    const distances = nearest.filter((d) => d.vehicle_type === row.id).map((d) => haversineKm(pickup, d));
    const closest = distances.length ? Math.min(...distances) : null;
    return {
      vehicle_type: row.id,
      name: row.name,
      description: row.description,
      seats: row.seats,
      fare,
      pickup_eta_min: closest === null ? null : Math.max(2, Math.round((closest * 1.3 / 22) * 60)),
      drivers_nearby: distances.filter((km) => km <= 5).length,
    };
  });
  return {
    distance_km: route.distanceKm,
    duration_min: route.durationMin,
    surge,
    surge_zone: zone,
    promo: promoSummary(promoCode, promo, uses, options.some((o) => o.fare.discount > 0)),
    options,
  };
}

function promoSummary(requested: string, promo: Promo | null, uses: number, appliedSomewhere: boolean) {
  if (!requested) return null;
  if (!promo) return { code: requested.toUpperCase(), valid: false, message: "That code does not exist." };
  if (appliedSomewhere) return { code: promo.code, valid: true, message: "" };
  // Not applied to any option: explain why (a huge fare isolates reasons other than the minimum).
  const check = evaluatePromo(promo, Number.MAX_SAFE_INTEGER, uses);
  const message = check.ok ? `This code needs a fare of at least ₹${promo.min_fare}.` : check.reason;
  return { code: promo.code, valid: false, message };
}

export async function recordEvent(client: Queryable, tripId: string, kind: string, actor: Actor, detail: Record<string, unknown> = {}) {
  await client.query("INSERT INTO trip_events (trip_id, kind, actor, detail) VALUES ($1, $2, $3, $4)", [tripId, kind, actor, JSON.stringify(detail)]);
}

export async function loadTrip(id: string, client?: Queryable): Promise<Record<string, any> | null> {
  return one(`${TRIP_SELECT} WHERE t.id = $1`, [id], client);
}

/** Tell the rider, the driver and the admin feed about the trip's new state. */
export async function broadcastTrip(tripId: string): Promise<void> {
  const row = await loadTrip(tripId);
  if (!row) return;
  hub.publish(`user:${row.rider_id}`, "trip.updated", tripJson(row, "rider"));
  if (row.driver_id) hub.publish(`user:${row.driver_id}`, "trip.updated", tripJson(row, "driver"));
  hub.publish("admin", "trip.updated", tripJson(row, "admin"));
}

export interface BookRequest {
  pickup: Stop;
  drop: Stop;
  vehicleType: string;
  paymentMethod: "wallet" | "cash";
  promoCode: string;
}

export async function bookTrip(riderId: string, req: BookRequest): Promise<Record<string, any>> {
  const route = await mockMaps.route(req.pickup, req.drop);
  if (route.distanceKm > 80) throw badRequest("RideNow covers trips up to 80 km inside the city.");
  const tripId = await tx(async (client) => {
    const pricing = await pricingFor(req.vehicleType, client);
    if (!pricing.active) throw badRequest(`${pricing.name} is not available right now.`);
    const { surge } = await surgeAt(req.pickup, client);
    let discount = 0;
    let promoCode: string | null = null;
    if (req.promoCode) {
      const promo = await loadPromo(req.promoCode, client);
      if (!promo) throw badRequest("That promo code does not exist.", "promo_invalid");
      const check = evaluatePromo(promo, computeFare(pricing, route.distanceKm, route.durationMin, surge).total, await promoUsesBy(riderId, promo.code, client));
      if (!check.ok) throw badRequest(check.reason, "promo_invalid");
      discount = check.discount;
      promoCode = promo.code;
    }
    const fare = computeFare(pricing, route.distanceKm, route.durationMin, surge, discount);
    if (req.paymentMethod === "wallet") {
      const balance = await balanceOf(riderId, client);
      if (balance < fare.total) {
        throw badRequest(`Your wallet has ₹${balance.toFixed(2)}; this ride costs ₹${fare.total.toFixed(2)}. Add money or pay in cash.`, "insufficient_balance");
      }
    }
    const pin = String(1000 + Math.floor(Math.random() * 9000));
    let row: { id: string };
    try {
      row = (await one<{ id: string }>(
        `INSERT INTO trips (rider_id, vehicle_type, status, pickup_name, pickup_lat, pickup_lng, drop_name, drop_lat, drop_lng,
                            distance_km, duration_min, surge, fare_estimate, promo_code, discount, payment_method, pin)
         VALUES ($1, $2, 'requested', $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16) RETURNING id`,
        [riderId, req.vehicleType, req.pickup.name, req.pickup.lat, req.pickup.lng, req.drop.name, req.drop.lat, req.drop.lng,
         route.distanceKm, route.durationMin, surge, fare.total, promoCode, fare.discount, req.paymentMethod, pin],
        client,
      ))!;
    } catch (error) {
      if ((error as { code?: string }).code === "23505") throw conflict("You already have a ride in progress.", "active_trip");
      throw error;
    }
    await recordEvent(client, row.id, "requested", "rider", { fare: fare.total, surge, vehicle_type: req.vehicleType });
    return row.id;
  });
  await broadcastTrip(tripId);
  return (await loadTrip(tripId))!;
}

/** Lock a trip row for a state change. */
async function lockTrip(client: pg.PoolClient, tripId: string): Promise<Record<string, any>> {
  const trip = await one<Record<string, any>>("SELECT * FROM trips WHERE id = $1 FOR UPDATE", [tripId], client);
  if (!trip) throw notFound("Trip");
  return trip;
}

/** Assign inside the caller's transaction (dispatch accepts an offer and assigns atomically). */
export async function assignDriverIn(client: pg.PoolClient, tripId: string, driverId: string, actor: Actor): Promise<void> {
  const trip = await lockTrip(client, tripId);
  assertTransition(trip.status as TripStatus, "driver_assigned", actor);
  await client.query("UPDATE trips SET status = 'driver_assigned', driver_id = $2, assigned_at = now() WHERE id = $1", [tripId, driverId]);
  const driver = await one<{ full_name: string; plate: string }>(
    "SELECT u.full_name, d.plate FROM users u JOIN drivers d ON d.user_id = u.id WHERE u.id = $1",
    [driverId],
    client,
  );
  await recordEvent(client, tripId, "driver_assigned", actor, { driver_id: driverId });
  await notify(client, trip.rider_id, "trip", "Your driver is on the way", `${driver?.full_name ?? "Your driver"} (${driver?.plate ?? ""}) accepted your ride.`);
}

export async function markArrived(tripId: string, driverId: string | null, actor: Actor): Promise<void> {
  await tx(async (client) => {
    const trip = await lockTrip(client, tripId);
    if (driverId && trip.driver_id !== driverId) throw notFound("Trip");
    assertTransition(trip.status, "driver_arrived", actor);
    await client.query("UPDATE trips SET status = 'driver_arrived', arrived_at = now() WHERE id = $1", [tripId]);
    await recordEvent(client, tripId, "driver_arrived", actor);
    await notify(client, trip.rider_id, "trip", "Your driver has arrived", `Share your PIN ${trip.pin} to start the ride.`);
  });
  await broadcastTrip(tripId);
}

export async function startTrip(tripId: string, driverId: string | null, pin: string | null, actor: Actor): Promise<void> {
  await tx(async (client) => {
    const trip = await lockTrip(client, tripId);
    if (driverId && trip.driver_id !== driverId) throw notFound("Trip");
    assertTransition(trip.status, "in_progress", actor);
    if (actor === "driver" && pin !== trip.pin) throw badRequest("That PIN is not right. Ask the rider for the 4-digit PIN.", "wrong_pin");
    await client.query("UPDATE trips SET status = 'in_progress', started_at = now() WHERE id = $1", [tripId]);
    await recordEvent(client, tripId, "started", actor);
  });
  await broadcastTrip(tripId);
}

/** Complete a trip and settle the money: rider pays, driver earns net of commission, platform books commission. */
export async function completeTrip(tripId: string, driverId: string | null, actor: Actor): Promise<void> {
  const touched: string[] = [];
  await tx(async (client) => {
    const trip = await lockTrip(client, tripId);
    if (driverId && trip.driver_id !== driverId) throw notFound("Trip");
    assertTransition(trip.status, "completed", actor);
    const pricing = await pricingFor(trip.vehicle_type, client);
    const fare = num(trip.fare_estimate);
    const discount = num(trip.discount);
    const { commission, driverEarning } = splitFare(fare, discount, pricing.commission_pct);
    const platform = await platformUser(client);
    const ref = trip.code as string;
    if (trip.payment_method === "wallet") {
      await postLedger(client, trip.rider_id, "trip_payment", -fare, { tripId, reference: ref, note: `${trip.pickup_name} → ${trip.drop_name}` });
      await postLedger(client, trip.driver_id, "trip_earning", driverEarning, { tripId, reference: ref });
      await postLedger(client, platform, "commission", money(commission - discount), { tripId, reference: ref, note: discount > 0 ? `after ₹${discount} promo` : "" });
    } else {
      // Cash: the driver collected the fare, owes the commission, and is reimbursed the promo.
      await postLedger(client, trip.driver_id, "cash_commission", money(discount - commission), { tripId, reference: ref, note: `cash fare ₹${fare}` });
      await postLedger(client, platform, "commission", money(commission - discount), { tripId, reference: ref, note: "cash trip" });
    }
    if (trip.promo_code) await client.query("UPDATE promo_codes SET used_count = used_count + 1 WHERE code = $1", [trip.promo_code]);
    await client.query(
      `UPDATE trips SET status = 'completed', completed_at = now(), fare_final = $2, commission = $3, driver_earning = $4, payment_status = 'paid'
        WHERE id = $1`,
      [tripId, fare, commission, driverEarning],
    );
    await recordEvent(client, tripId, "completed", actor, { fare, commission, driver_earning: driverEarning });
    await notify(client, trip.rider_id, "trip", "Thanks for riding with RideNow", `₹${fare.toFixed(2)} ${trip.payment_method === "cash" ? "paid in cash" : "paid from your wallet"}. Rate your driver.`);
    await notify(client, trip.driver_id, "earning", "Trip completed", `You earned ₹${driverEarning.toFixed(2)} on ${ref}.`);
    touched.push(trip.rider_id, trip.driver_id);
  });
  for (const userId of touched) announceWallet(userId, await balanceOf(userId));
  await broadcastTrip(tripId);
}

export async function cancelTrip(tripId: string, actor: Actor, actorId: string | null, reason: string): Promise<{ fee: number }> {
  let fee = 0;
  await tx(async (client) => {
    const trip = await lockTrip(client, tripId);
    if (actor === "rider" && trip.rider_id !== actorId) throw notFound("Trip");
    if (actor === "driver" && trip.driver_id !== actorId) throw notFound("Trip");
    assertTransition(trip.status, "cancelled", actor);
    fee = cancellationFee(trip.status, actor, trip.arrived_at);
    await client.query(
      `UPDATE trips SET status = 'cancelled', cancelled_at = now(), cancel_reason = $2, cancelled_by = $3,
                        payment_status = CASE WHEN $4::numeric > 0 THEN 'paid' ELSE 'waived' END,
                        fare_final = CASE WHEN $4::numeric > 0 THEN $4::numeric ELSE NULL END
        WHERE id = $1`,
      [tripId, reason, actor, fee],
    );
    await client.query("UPDATE ride_offers SET status = 'withdrawn', responded_at = now() WHERE trip_id = $1 AND status = 'pending'", [tripId]);
    if (fee > 0 && trip.driver_id) {
      await postLedger(client, trip.rider_id, "trip_payment", -fee, { tripId, reference: trip.code, note: "Cancellation fee" });
      await postLedger(client, trip.driver_id, "trip_earning", fee, { tripId, reference: trip.code, note: "Cancellation fee" });
    }
    await recordEvent(client, tripId, "cancelled", actor, { reason, fee });
    if (actor !== "rider") await notify(client, trip.rider_id, "trip", "Your ride was cancelled", reason);
    if (trip.driver_id && actor !== "driver") await notify(client, trip.driver_id, "trip", "Ride cancelled", reason);
  });
  await broadcastTrip(tripId);
  return { fee };
}

export async function rateTrip(tripId: string, fromUser: string, as: "rider" | "driver", stars: number, tags: string[], comment: string) {
  await tx(async (client) => {
    const trip = await lockTrip(client, tripId);
    const mine = as === "rider" ? trip.rider_id === fromUser : trip.driver_id === fromUser;
    if (!mine) throw notFound("Trip");
    if (trip.status !== "completed") throw badRequest("You can rate a trip once it is completed.");
    const toUser = as === "rider" ? trip.driver_id : trip.rider_id;
    try {
      await client.query(
        "INSERT INTO ratings (trip_id, from_user, to_user, stars, tags, comment) VALUES ($1, $2, $3, $4, $5, $6)",
        [tripId, fromUser, toUser, stars, tags.slice(0, 6), comment.slice(0, 500)],
      );
    } catch (error) {
      if ((error as { code?: string }).code === "23505") throw conflict("You have already rated this trip.");
      throw error;
    }
    if (as === "rider") {
      await client.query(
        `UPDATE drivers SET rating_count = rating_count + 1,
                rating_avg = round(((rating_avg * rating_count) + $2) / (rating_count + 1), 2)
          WHERE user_id = $1`,
        [toUser, stars],
      );
    }
  });
}

/** Admin refund of a paid wallet or cash trip: the platform returns the fare to the rider's wallet. */
export async function refundTrip(tripId: string, adminId: string, reason: string): Promise<number> {
  let amount = 0;
  let riderId = "";
  await tx(async (client) => {
    const trip = await lockTrip(client, tripId);
    if (trip.payment_status !== "paid" || trip.fare_final === null) throw badRequest("Only paid trips can be refunded.");
    amount = num(trip.fare_final);
    riderId = trip.rider_id;
    const platform = await platformUser(client);
    await postLedger(client, platform, "refund", -amount, { tripId, reference: trip.code, note: reason });
    await postLedger(client, trip.rider_id, "refund", amount, { tripId, reference: trip.code, note: reason });
    await client.query("UPDATE trips SET payment_status = 'refunded' WHERE id = $1", [tripId]);
    await recordEvent(client, tripId, "refunded", "admin", { amount, reason, by: adminId });
    await notify(client, trip.rider_id, "wallet", "Refund issued", `₹${amount.toFixed(2)} for ${trip.code} is back in your wallet.`);
  });
  announceWallet(riderId, await balanceOf(riderId));
  await broadcastTrip(tripId);
  return amount;
}
