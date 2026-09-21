import { Hono } from "hono";
import { one, query, tx } from "../db.ts";
import { type AppEnv, requireAuth } from "../auth/middleware.ts";
import { badRequest, conflict, forbidden, notFound } from "../lib/errors.ts";
import { hub } from "../lib/events.ts";
import { isValidPoint } from "../lib/geo.ts";
import { money, num } from "../lib/money.ts";
import { ACTIVE_STATUSES } from "../lib/trip-state.ts";
import { numberIn, oneOf, pageParams, str } from "../lib/validate.ts";
import { acceptOffer, declineOffer, offerJson } from "../services/dispatch.ts";
import { notify } from "../services/notify.ts";
import { TRIP_SELECT, tripJson } from "../services/serialize.ts";
import { cancelTrip, completeTrip, loadTrip, markArrived, rateTrip, startTrip } from "../services/trips.ts";
import { announceWallet, balanceOf, postLedger } from "../services/wallet.ts";
import { txJson } from "./rider.ts";
import { body } from "./util.ts";

export const driverRoutes = new Hono<AppEnv>();
driverRoutes.use("*", requireAuth("driver"));

const MIN_PAYOUT = 100;

async function driverRow(userId: string) {
  const row = await one<Record<string, any>>(
    `SELECT d.*, u.full_name, u.email, u.phone, u.avatar_color, vt.name AS vehicle_type_name, vt.commission_pct
       FROM drivers d JOIN users u ON u.id = d.user_id JOIN vehicle_types vt ON vt.id = d.vehicle_type
      WHERE d.user_id = $1`,
    [userId],
  );
  if (!row) throw notFound("Driver profile");
  return row;
}

driverRoutes.get("/me", async (c) => {
  const d = await driverRow(c.get("user").sub);
  const documents = await query("SELECT id, kind, number, status, expires_on, note, updated_at FROM driver_documents WHERE driver_id = $1 ORDER BY kind", [d.user_id]);
  return c.json({
    id: d.user_id,
    full_name: d.full_name,
    email: d.email,
    phone: d.phone,
    avatar_color: d.avatar_color,
    status: d.status,
    online: d.online,
    location: d.lat === null ? null : { lat: d.lat, lng: d.lng, heading: d.heading },
    vehicle: { type: d.vehicle_type, type_name: d.vehicle_type_name, make: d.vehicle_make, model: d.vehicle_model, color: d.vehicle_color, plate: d.plate },
    license_no: d.license_no,
    rating: num(d.rating_avg),
    rating_count: d.rating_count,
    acceptance_rate: d.offers_received > 0 ? Math.round((d.offers_accepted / d.offers_received) * 100) : 100,
    commission_pct: num(d.commission_pct),
    joined_at: d.joined_at,
    documents,
  });
});

driverRoutes.post("/online", async (c) => {
  const data = await body(c);
  const userId = c.get("user").sub;
  const online = data.online === true;
  const d = await driverRow(userId);
  if (online && d.status !== "approved") throw forbidden(d.status === "pending" ? "Your account is waiting for approval." : "Your account is suspended.");
  if (online && !isValidPoint(data.location)) throw badRequest("Share your location to go online.");
  if (!online) {
    const active = await one("SELECT 1 FROM trips WHERE driver_id = $1 AND status = ANY($2)", [userId, ACTIVE_STATUSES]);
    if (active) throw conflict("Finish your current trip before going offline.");
  }
  const loc = online ? (data.location as { lat: number; lng: number }) : null;
  await query(
    `UPDATE drivers SET online = $2, lat = COALESCE($3, lat), lng = COALESCE($4, lng), last_seen_at = now() WHERE user_id = $1`,
    [userId, online, loc?.lat ?? null, loc?.lng ?? null],
  );
  if (!online) {
    await query("UPDATE ride_offers SET status = 'withdrawn', responded_at = now() WHERE driver_id = $1 AND status = 'pending'", [userId]);
  }
  hub.publish("admin", "driver.status", { driver_id: userId, online, lat: loc?.lat ?? d.lat, lng: loc?.lng ?? d.lng });
  return c.json({ online });
});

driverRoutes.post("/location", async (c) => {
  const data = await body(c);
  if (!isValidPoint(data)) throw badRequest("lat and lng are required.");
  const userId = c.get("user").sub;
  const heading = typeof data.heading === "number" ? data.heading : 0;
  await query("UPDATE drivers SET lat = $2, lng = $3, heading = $4, last_seen_at = now() WHERE user_id = $1", [userId, data.lat, data.lng, heading]);
  const trip = await one<{ id: string; rider_id: string }>("SELECT id, rider_id FROM trips WHERE driver_id = $1 AND status = ANY($2)", [userId, ACTIVE_STATUSES]);
  const payload = { trip_id: trip?.id ?? null, driver_id: userId, lat: data.lat, lng: data.lng, heading };
  if (trip) hub.publish(`user:${trip.rider_id}`, "driver.location", payload);
  hub.publish("admin", "driver.location", payload);
  return c.json({ ok: true });
});

driverRoutes.get("/offers/current", async (c) => {
  const row = await one<{ id: string }>(
    "SELECT id FROM ride_offers WHERE driver_id = $1 AND status = 'pending' AND expires_at > now() ORDER BY offered_at DESC LIMIT 1",
    [c.get("user").sub],
  );
  return c.json({ offer: row ? await offerJson(row.id) : null });
});

driverRoutes.post("/offers/:id/accept", async (c) => {
  const tripId = await acceptOffer(c.req.param("id"), c.get("user").sub);
  return c.json(tripJson((await loadTrip(tripId))!, "driver"));
});

driverRoutes.post("/offers/:id/decline", async (c) => {
  await declineOffer(c.req.param("id"), c.get("user").sub);
  return c.json({ ok: true });
});

driverRoutes.get("/trips/active", async (c) => {
  const row = await one(`${TRIP_SELECT} WHERE t.driver_id = $1 AND t.status = ANY($2) LIMIT 1`, [c.get("user").sub, ACTIVE_STATUSES]);
  return c.json({ trip: row ? tripJson(row, "driver") : null });
});

driverRoutes.post("/trips/:id/arrive", async (c) => {
  await markArrived(c.req.param("id"), c.get("user").sub, "driver");
  return c.json(tripJson((await loadTrip(c.req.param("id")))!, "driver"));
});

driverRoutes.post("/trips/:id/start", async (c) => {
  const pin = str(await body(c), "pin", { min: 4, max: 4 });
  await startTrip(c.req.param("id"), c.get("user").sub, pin, "driver");
  return c.json(tripJson((await loadTrip(c.req.param("id")))!, "driver"));
});

driverRoutes.post("/trips/:id/complete", async (c) => {
  await completeTrip(c.req.param("id"), c.get("user").sub, "driver");
  return c.json(tripJson((await loadTrip(c.req.param("id")))!, "driver"));
});

driverRoutes.post("/trips/:id/cancel", async (c) => {
  const data = await body(c);
  const reason = oneOf(data, "reason", ["Rider not at pickup", "Rider asked to cancel", "Vehicle problem", "Unsafe pickup", "Other"] as const);
  await cancelTrip(c.req.param("id"), "driver", c.get("user").sub, reason);
  return c.json(tripJson((await loadTrip(c.req.param("id")))!, "driver"));
});

driverRoutes.post("/trips/:id/rate", async (c) => {
  const data = await body(c);
  const tags = Array.isArray(data.tags) ? data.tags.filter((t): t is string => typeof t === "string") : [];
  await rateTrip(c.req.param("id"), c.get("user").sub, "driver", numberIn(data, "stars", 1, 5), tags, typeof data.comment === "string" ? data.comment : "");
  return c.json({ ok: true });
});

driverRoutes.get("/trips", async (c) => {
  const url = new URL(c.req.url);
  const { limit, offset } = pageParams(url, 50);
  const userId = c.get("user").sub;
  const rows = await query(`${TRIP_SELECT} WHERE t.driver_id = $1 ORDER BY t.requested_at DESC LIMIT $2 OFFSET $3`, [userId, limit, offset]);
  const total = await one<{ n: string }>("SELECT count(*) AS n FROM trips WHERE driver_id = $1", [userId]);
  return c.json({ trips: rows.map((r) => tripJson(r, "driver")), total: Number(total?.n ?? 0) });
});

driverRoutes.get("/trips/:id", async (c) => {
  const row = await one(`${TRIP_SELECT} WHERE t.id = $1 AND t.driver_id = $2`, [c.req.param("id"), c.get("user").sub]);
  if (!row) throw notFound("Trip");
  const events = await query("SELECT kind, actor, detail, at FROM trip_events WHERE trip_id = $1 ORDER BY at", [c.req.param("id")]);
  const rating = await one("SELECT stars, tags, comment FROM ratings WHERE trip_id = $1 AND to_user = $2", [c.req.param("id"), c.get("user").sub]);
  return c.json({ ...tripJson(row, "driver"), events, rating_received: rating });
});

/** Earnings for a range: totals, a per-day series and the latest completed trips. */
driverRoutes.get("/earnings", async (c) => {
  const range = oneOf({ range: c.req.query("range") ?? "week" }, "range", ["today", "week", "month"] as const);
  const days = range === "today" ? 1 : range === "week" ? 7 : 30;
  const userId = c.get("user").sub;
  const totals = await one<Record<string, any>>(
    `SELECT count(*) FILTER (WHERE status = 'completed') AS trips,
            coalesce(sum(driver_earning) FILTER (WHERE status = 'completed'), 0) AS earnings,
            coalesce(sum(fare_final) FILTER (WHERE status = 'completed' AND payment_method = 'cash'), 0) AS cash_collected,
            coalesce(sum(distance_km) FILTER (WHERE status = 'completed'), 0) AS km,
            coalesce(sum(extract(epoch FROM (completed_at - started_at)) / 60) FILTER (WHERE status = 'completed'), 0) AS minutes_driving,
            count(*) FILTER (WHERE status = 'cancelled' AND cancelled_by = 'driver') AS cancelled_by_me
       FROM trips WHERE driver_id = $1 AND requested_at >= date_trunc('day', now()) - (($2 - 1) || ' days')::interval`,
    [userId, String(days)],
  );
  const series = await query<Record<string, any>>(
    `SELECT to_char(d, 'YYYY-MM-DD') AS day,
            coalesce(sum(t.driver_earning), 0) AS earnings, count(t.id) AS trips
       FROM generate_series(date_trunc('day', now()) - (($2 - 1) || ' days')::interval, date_trunc('day', now()), interval '1 day') AS d
       LEFT JOIN trips t ON t.driver_id = $1 AND t.status = 'completed' AND date_trunc('day', t.completed_at) = d
      GROUP BY d ORDER BY d`,
    [userId, String(days)],
  );
  const tips = await one<{ n: string }>("SELECT count(*) AS n FROM ratings WHERE to_user = $1 AND stars = 5 AND created_at >= now() - ($2 || ' days')::interval", [userId, String(days)]);
  return c.json({
    range,
    trips: Number(totals!.trips),
    earnings: num(totals!.earnings),
    cash_collected: num(totals!.cash_collected),
    distance_km: Math.round(num(totals!.km) * 10) / 10,
    minutes_driving: Math.round(num(totals!.minutes_driving)),
    cancelled_by_me: Number(totals!.cancelled_by_me),
    five_star_ratings: Number(tips?.n ?? 0),
    series: series.map((s) => ({ day: s.day, earnings: num(s.earnings), trips: Number(s.trips) })),
  });
});

driverRoutes.get("/wallet", async (c) => {
  const userId = c.get("user").sub;
  const { limit, offset } = pageParams(new URL(c.req.url));
  const rows = await query(
    "SELECT id, kind, amount, balance_after, reference, note, created_at FROM wallet_transactions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
    [userId, limit, offset],
  );
  const payouts = await query("SELECT id, amount, status, bank_last4, reference, requested_at, processed_at FROM payouts WHERE driver_id = $1 ORDER BY requested_at DESC LIMIT 20", [userId]);
  return c.json({
    balance: await balanceOf(userId),
    min_payout: MIN_PAYOUT,
    transactions: rows.map(txJson),
    payouts: payouts.map((p: Record<string, any>) => ({ ...p, amount: num(p.amount) })),
  });
});

driverRoutes.post("/payouts", async (c) => {
  const data = await body(c);
  const userId = c.get("user").sub;
  const amount = money(numberIn(data, "amount", MIN_PAYOUT, 500000));
  const result = await tx(async (client) => {
    const pending = await one("SELECT 1 FROM payouts WHERE driver_id = $1 AND status = 'requested'", [userId], client);
    if (pending) throw conflict("You already have a payout being processed.");
    const balance = await balanceOf(userId, client);
    if (amount > balance) throw badRequest(`You can withdraw up to ₹${balance.toFixed(2)}.`, "insufficient_balance");
    const payout = await one<{ id: string }>(
      "INSERT INTO payouts (driver_id, amount, bank_last4) VALUES ($1, $2, $3) RETURNING id",
      [userId, amount, "4417"],
      client,
    );
    const next = await postLedger(client, userId, "payout", -amount, { reference: payout!.id, note: "Payout requested" });
    await notify(client, userId, "payout", "Payout requested", `₹${amount.toFixed(2)} will reach your bank account ending 4417.`);
    return { id: payout!.id, balance: next };
  });
  announceWallet(userId, result.balance);
  hub.publish("admin", "payout.requested", { id: result.id, driver_id: userId, amount });
  return c.json(result, 201);
});

driverRoutes.get("/ratings", async (c) => {
  const userId = c.get("user").sub;
  const rows = await query(
    `SELECT r.stars, r.tags, r.comment, r.created_at, t.code FROM ratings r JOIN trips t ON t.id = r.trip_id
      WHERE r.to_user = $1 ORDER BY r.created_at DESC LIMIT 50`,
    [userId],
  );
  const breakdown = await query<{ stars: number; n: string }>("SELECT stars, count(*) AS n FROM ratings WHERE to_user = $1 GROUP BY stars", [userId]);
  const tags = await query<{ tag: string; n: string }>(
    "SELECT tag, count(*) AS n FROM ratings, unnest(tags) AS tag WHERE to_user = $1 GROUP BY tag ORDER BY n DESC LIMIT 8",
    [userId],
  );
  const d = await driverRow(userId);
  return c.json({
    average: num(d.rating_avg),
    count: d.rating_count,
    breakdown: [5, 4, 3, 2, 1].map((stars) => ({ stars, count: Number(breakdown.find((b) => b.stars === stars)?.n ?? 0) })),
    top_tags: tags.map((t) => ({ tag: t.tag, count: Number(t.n) })),
    recent: rows,
  });
});
