import { Hono } from "hono";
import { one, query, tx } from "../db.ts";
import { type AppEnv, requireAuth } from "../auth/middleware.ts";
import { badRequest, notFound } from "../lib/errors.ts";
import { money, num } from "../lib/money.ts";
import { evaluatePromo } from "../lib/promo.ts";
import { numberIn, oneOf, pageParams, str } from "../lib/validate.ts";
import { ACTIVE_STATUSES } from "../lib/trip-state.ts";
import { mockPayments } from "../providers/payments.ts";
import { dispatchNext } from "../services/dispatch.ts";
import { notify } from "../services/notify.ts";
import { TRIP_SELECT, tripJson } from "../services/serialize.ts";
import { bookTrip, cancelTrip, loadPromo, loadTrip, promoUsesBy, rateTrip } from "../services/trips.ts";
import { announceWallet, balanceOf, postLedger } from "../services/wallet.ts";
import { body, stop } from "./util.ts";

export const riderRoutes = new Hono<AppEnv>();
riderRoutes.use("*", requireAuth("rider"));

const RIDER_TRIP_SELECT = `${TRIP_SELECT.replace("SELECT t.*,", "SELECT t.*, (SELECT stars FROM ratings WHERE trip_id = t.id AND from_user = t.rider_id) AS my_rating,")}`;

riderRoutes.post("/trips", async (c) => {
  const data = await body(c);
  const riderId = c.get("user").sub;
  const trip = await bookTrip(riderId, {
    pickup: stop(data.pickup, "Pickup"),
    drop: stop(data.drop, "Drop"),
    vehicleType: str(data, "vehicle_type", { max: 20 }),
    paymentMethod: oneOf(data, "payment_method", ["wallet", "cash"] as const, "wallet"),
    promoCode: typeof data.promo_code === "string" ? data.promo_code.trim().slice(0, 30) : "",
  });
  void dispatchNext(trip.id);
  return c.json(tripJson(trip, "rider"), 201);
});

riderRoutes.get("/trips/active", async (c) => {
  const row = await one(`${RIDER_TRIP_SELECT} WHERE t.rider_id = $1 AND t.status = ANY($2) ORDER BY t.requested_at DESC LIMIT 1`, [
    c.get("user").sub,
    ACTIVE_STATUSES,
  ]);
  return c.json({ trip: row ? tripJson(row, "rider") : null });
});

riderRoutes.get("/trips", async (c) => {
  const url = new URL(c.req.url);
  const { limit, offset } = pageParams(url, 50);
  const status = url.searchParams.get("status");
  const rows = await query(
    `${RIDER_TRIP_SELECT} WHERE t.rider_id = $1 AND ($2::text IS NULL OR t.status = $2) ORDER BY t.requested_at DESC LIMIT $3 OFFSET $4`,
    [c.get("user").sub, status, limit, offset],
  );
  const total = await one<{ n: string }>("SELECT count(*) AS n FROM trips WHERE rider_id = $1 AND ($2::text IS NULL OR status = $2)", [c.get("user").sub, status]);
  return c.json({ trips: rows.map((r) => tripJson(r, "rider")), total: Number(total?.n ?? 0) });
});

riderRoutes.get("/trips/:id", async (c) => {
  const row = await one(`${RIDER_TRIP_SELECT} WHERE t.id = $1 AND t.rider_id = $2`, [c.req.param("id"), c.get("user").sub]);
  if (!row) throw notFound("Trip");
  const events = await query("SELECT kind, actor, detail, at FROM trip_events WHERE trip_id = $1 ORDER BY at", [c.req.param("id")]);
  return c.json({ ...tripJson(row, "rider"), events });
});

riderRoutes.post("/trips/:id/cancel", async (c) => {
  const data = await body(c);
  const reason = typeof data.reason === "string" && data.reason.trim() ? data.reason.trim().slice(0, 200) : "Cancelled by rider";
  const result = await cancelTrip(c.req.param("id"), "rider", c.get("user").sub, reason);
  const row = await loadTrip(c.req.param("id"));
  return c.json({ ...tripJson(row!, "rider"), cancellation_fee: result.fee });
});

riderRoutes.post("/trips/:id/rate", async (c) => {
  const data = await body(c);
  const tags = Array.isArray(data.tags) ? data.tags.filter((t): t is string => typeof t === "string").map((t) => t.slice(0, 40)) : [];
  await rateTrip(c.req.param("id"), c.get("user").sub, "rider", numberIn(data, "stars", 1, 5), tags, typeof data.comment === "string" ? data.comment : "");
  return c.json({ ok: true });
});

// --- wallet -------------------------------------------------------------------------------------

riderRoutes.get("/wallet", async (c) => {
  const userId = c.get("user").sub;
  const recent = await query(
    "SELECT id, kind, amount, balance_after, reference, note, created_at FROM wallet_transactions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5",
    [userId],
  );
  return c.json({ balance: await balanceOf(userId), currency: "INR", recent: recent.map(txJson) });
});

riderRoutes.get("/wallet/transactions", async (c) => {
  const { limit, offset } = pageParams(new URL(c.req.url));
  const userId = c.get("user").sub;
  const rows = await query(
    "SELECT id, kind, amount, balance_after, reference, note, created_at FROM wallet_transactions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
    [userId, limit, offset],
  );
  const total = await one<{ n: string }>("SELECT count(*) AS n FROM wallet_transactions WHERE user_id = $1", [userId]);
  return c.json({ transactions: rows.map(txJson), total: Number(total?.n ?? 0) });
});

/** Add money with a card through the payments provider (mock: 4000 0000 0000 0002 is declined). */
riderRoutes.post("/wallet/topup", async (c) => {
  const data = await body(c);
  const userId = c.get("user").sub;
  const amount = money(numberIn(data, "amount", 50, 20000));
  const cardNumber = str(data, "card_number", { min: 12, max: 23 });
  const intent = await one<{ id: string }>("INSERT INTO payment_intents (user_id, amount, provider) VALUES ($1, $2, $3) RETURNING id", [userId, amount, mockPayments.name]);
  const result = await mockPayments.charge({ amount, currency: "INR", cardNumber, reference: intent!.id });
  if (!result.ok) {
    await query("UPDATE payment_intents SET status = 'failed', card_last4 = $2, failure_reason = $3, completed_at = now() WHERE id = $1", [intent!.id, result.last4, result.reason]);
    throw badRequest(result.reason, "payment_failed");
  }
  const balance = await tx(async (client) => {
    await client.query("UPDATE payment_intents SET status = 'succeeded', card_last4 = $2, completed_at = now() WHERE id = $1", [intent!.id, result.last4]);
    const next = await postLedger(client, userId, "topup", amount, { reference: result.providerRef, note: `Card •••• ${result.last4}` });
    await notify(client, userId, "wallet", "Money added", `₹${amount.toFixed(2)} was added to your wallet.`);
    return next;
  });
  announceWallet(userId, balance);
  return c.json({ balance, amount, card_last4: result.last4 }, 201);
});

// --- saved places -------------------------------------------------------------------------------

riderRoutes.get("/places", async (c) => {
  const rows = await query("SELECT id, label, name, address, lat, lng FROM places WHERE user_id = $1 ORDER BY created_at", [c.get("user").sub]);
  return c.json({ places: rows });
});

riderRoutes.post("/places", async (c) => {
  const data = await body(c);
  const where = stop(data, "Place");
  const count = await one<{ n: string }>("SELECT count(*) AS n FROM places WHERE user_id = $1", [c.get("user").sub]);
  if (Number(count?.n ?? 0) >= 20) throw badRequest("You can save up to 20 places.");
  const row = await one(
    "INSERT INTO places (user_id, label, name, address, lat, lng) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id, label, name, address, lat, lng",
    [c.get("user").sub, str(data, "label", { max: 30 }), where.name, str(data, "address", { optional: true, max: 200 }), where.lat, where.lng],
  );
  return c.json(row, 201);
});

riderRoutes.delete("/places/:id", async (c) => {
  const row = await one("DELETE FROM places WHERE id = $1 AND user_id = $2 RETURNING id", [c.req.param("id"), c.get("user").sub]);
  if (!row) throw notFound("Place");
  return c.body(null, 204);
});

// --- promotions ---------------------------------------------------------------------------------

riderRoutes.get("/promos", async (c) => {
  const riderId = c.get("user").sub;
  const rows = await query<Record<string, any>>(
    `SELECT code, description, kind, value, max_discount, min_fare, valid_until, per_user_limit,
            (SELECT count(*) FROM trips t WHERE t.rider_id = $1 AND t.promo_code = p.code AND t.status = 'completed') AS used_by_me
       FROM promo_codes p
      WHERE active AND (valid_until IS NULL OR valid_until > now()) AND (usage_limit IS NULL OR used_count < usage_limit)
      ORDER BY created_at DESC`,
    [riderId],
  );
  return c.json({
    promos: rows.map((p) => ({
      code: p.code,
      description: p.description,
      kind: p.kind,
      value: num(p.value),
      max_discount: p.max_discount === null ? null : num(p.max_discount),
      min_fare: num(p.min_fare),
      valid_until: p.valid_until,
      uses_left: Math.max(0, p.per_user_limit - Number(p.used_by_me)),
    })),
  });
});

riderRoutes.post("/promos/check", async (c) => {
  const data = await body(c);
  const promo = await loadPromo(str(data, "code", { max: 30 }));
  if (!promo) return c.json({ ok: false, reason: "That code does not exist." });
  const fare = typeof data.fare === "number" ? data.fare : Number.MAX_SAFE_INTEGER;
  return c.json({ code: promo.code, ...evaluatePromo(promo, fare, await promoUsesBy(c.get("user").sub, promo.code)) });
});

export function txJson(row: Record<string, any>) {
  return { ...row, amount: num(row.amount), balance_after: num(row.balance_after) };
}
