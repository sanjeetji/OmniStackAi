import { Hono } from "hono";
import { one, query, tx } from "../db.ts";
import { type AppEnv, requireAuth } from "../auth/middleware.ts";
import { badRequest, conflict, notFound } from "../lib/errors.ts";
import { hub } from "../lib/events.ts";
import { money, num } from "../lib/money.ts";
import { ACTIVE_STATUSES } from "../lib/trip-state.ts";
import { numberIn, oneOf, pageParams, str } from "../lib/validate.ts";
import { audit, notify } from "../services/notify.ts";
import { TRIP_SELECT, tripJson } from "../services/serialize.ts";
import { cancelTrip, loadTrip, refundTrip } from "../services/trips.ts";
import { announceWallet, balanceOf, platformUser, postLedger } from "../services/wallet.ts";
import { txJson } from "./rider.ts";
import { body } from "./util.ts";

export const adminRoutes = new Hono<AppEnv>();
adminRoutes.use("*", requireAuth("admin"));

const actor = (c: { get(key: "user"): { sub: string } }) => c.get("user").sub;

// --- dashboard ----------------------------------------------------------------------------------

adminRoutes.get("/dashboard", async (c) => {
  const kpi = await one<Record<string, any>>(`
    SELECT
      count(*) FILTER (WHERE status = 'completed' AND completed_at >= date_trunc('day', now())) AS trips_today,
      count(*) FILTER (WHERE status = 'completed' AND completed_at >= date_trunc('day', now()) - interval '1 day' AND completed_at < date_trunc('day', now())) AS trips_yesterday,
      coalesce(sum(fare_final) FILTER (WHERE status = 'completed' AND completed_at >= now() - interval '7 days'), 0) AS gmv_7d,
      coalesce(sum(fare_final) FILTER (WHERE status = 'completed' AND completed_at >= now() - interval '14 days' AND completed_at < now() - interval '7 days'), 0) AS gmv_prev_7d,
      coalesce(sum(commission - discount) FILTER (WHERE status = 'completed' AND completed_at >= now() - interval '7 days'), 0) AS revenue_7d,
      count(*) FILTER (WHERE status = ANY($1)) AS active_trips,
      count(*) FILTER (WHERE requested_at >= now() - interval '7 days') AS requested_7d,
      count(*) FILTER (WHERE status IN ('cancelled', 'no_driver') AND requested_at >= now() - interval '7 days') AS lost_7d,
      count(DISTINCT rider_id) FILTER (WHERE requested_at >= now() - interval '7 days') AS active_riders_7d
    FROM trips`, [ACTIVE_STATUSES]);
  const fleet = await one<Record<string, any>>(`
    SELECT count(*) FILTER (WHERE online) AS online, count(*) FILTER (WHERE status = 'pending') AS pending_approval,
           round(avg(rating_avg) FILTER (WHERE rating_count > 0), 2) AS avg_rating
      FROM drivers`);
  const series = await query<Record<string, any>>(`
    SELECT to_char(d, 'YYYY-MM-DD') AS day, count(t.id) AS trips,
           coalesce(sum(t.fare_final), 0) AS gmv, coalesce(sum(t.commission - t.discount), 0) AS revenue
      FROM generate_series(date_trunc('day', now()) - interval '13 days', date_trunc('day', now()), interval '1 day') AS d
      LEFT JOIN trips t ON t.status = 'completed' AND date_trunc('day', t.completed_at) = d
     GROUP BY d ORDER BY d`);
  const mix = await query<Record<string, any>>(`
    SELECT vt.id, vt.name, count(t.id) AS trips, coalesce(sum(t.fare_final), 0) AS gmv
      FROM vehicle_types vt LEFT JOIN trips t ON t.vehicle_type = vt.id AND t.status = 'completed' AND t.completed_at >= now() - interval '30 days'
     GROUP BY vt.id, vt.name, vt.sort ORDER BY vt.sort`);
  const top = await query<Record<string, any>>(`
    SELECT u.id, u.full_name, u.avatar_color, d.rating_avg, d.vehicle_type, count(t.id) AS trips, coalesce(sum(t.driver_earning), 0) AS earnings
      FROM trips t JOIN users u ON u.id = t.driver_id JOIN drivers d ON d.user_id = t.driver_id
     WHERE t.status = 'completed' AND t.completed_at >= now() - interval '7 days'
     GROUP BY u.id, u.full_name, u.avatar_color, d.rating_avg, d.vehicle_type ORDER BY earnings DESC LIMIT 5`);
  const recent = await query(`${TRIP_SELECT} ORDER BY t.requested_at DESC LIMIT 8`);
  const openTickets = await one<{ n: string }>("SELECT count(*) AS n FROM support_tickets WHERE status <> 'resolved'");
  const payoutsDue = await one<{ n: string; total: string }>("SELECT count(*) AS n, coalesce(sum(amount), 0) AS total FROM payouts WHERE status = 'requested'");
  const requested = Number(kpi!.requested_7d);
  return c.json({
    kpis: {
      trips_today: Number(kpi!.trips_today),
      trips_yesterday: Number(kpi!.trips_yesterday),
      gmv_7d: num(kpi!.gmv_7d),
      gmv_prev_7d: num(kpi!.gmv_prev_7d),
      revenue_7d: num(kpi!.revenue_7d),
      active_trips: Number(kpi!.active_trips),
      active_riders_7d: Number(kpi!.active_riders_7d),
      completion_rate_7d: requested ? Math.round(((requested - Number(kpi!.lost_7d)) / requested) * 1000) / 10 : 100,
      drivers_online: Number(fleet!.online),
      drivers_pending: Number(fleet!.pending_approval),
      avg_driver_rating: fleet!.avg_rating === null ? null : num(fleet!.avg_rating),
      open_tickets: Number(openTickets?.n ?? 0),
      payouts_due: { count: Number(payoutsDue?.n ?? 0), amount: num(payoutsDue?.total ?? 0) },
    },
    series: series.map((s) => ({ day: s.day, trips: Number(s.trips), gmv: num(s.gmv), revenue: num(s.revenue) })),
    vehicle_mix: mix.map((m) => ({ id: m.id, name: m.name, trips: Number(m.trips), gmv: num(m.gmv) })),
    top_drivers: top.map((t) => ({ id: t.id, name: t.full_name, avatar_color: t.avatar_color, rating: num(t.rating_avg), vehicle_type: t.vehicle_type, trips: Number(t.trips), earnings: num(t.earnings) })),
    recent_trips: recent.map((r) => tripJson(r, "admin")),
  });
});

adminRoutes.get("/live", async (c) => {
  const drivers = await query(`
    SELECT d.user_id AS id, u.full_name AS name, d.vehicle_type, d.lat, d.lng, d.heading, d.simulated,
           (SELECT t.status FROM trips t WHERE t.driver_id = d.user_id AND t.status = ANY($1) LIMIT 1) AS trip_status
      FROM drivers d JOIN users u ON u.id = d.user_id WHERE d.online AND d.lat IS NOT NULL`, [ACTIVE_STATUSES]);
  const trips = await query(`${TRIP_SELECT} WHERE t.status = ANY($1) ORDER BY t.requested_at DESC`, [ACTIVE_STATUSES]);
  const zones = await query("SELECT id, name, center_lat, center_lng, radius_km, surge, active FROM zones ORDER BY name");
  return c.json({ drivers, trips: trips.map((t) => tripJson(t, "admin")), zones: zones.map((z: Record<string, any>) => ({ ...z, radius_km: num(z.radius_km), surge: num(z.surge) })) });
});

// --- trips --------------------------------------------------------------------------------------

adminRoutes.get("/trips", async (c) => {
  const url = new URL(c.req.url);
  const { limit, offset } = pageParams(url);
  const status = url.searchParams.get("status") || null;
  const q = (url.searchParams.get("q") ?? "").trim() || null;
  const vehicle = url.searchParams.get("vehicle_type") || null;
  const where = `WHERE ($1::text IS NULL OR t.status = $1) AND ($2::text IS NULL OR t.vehicle_type = $2)
                   AND ($3::text IS NULL OR t.code ILIKE '%' || $3 || '%' OR r.full_name ILIKE '%' || $3 || '%' OR du.full_name ILIKE '%' || $3 || '%'
                        OR t.pickup_name ILIKE '%' || $3 || '%' OR t.drop_name ILIKE '%' || $3 || '%')`;
  const rows = await query(`${TRIP_SELECT} ${where} ORDER BY t.requested_at DESC LIMIT $4 OFFSET $5`, [status, vehicle, q, limit, offset]);
  const total = await one<{ n: string }>(
    `SELECT count(*) AS n FROM trips t JOIN users r ON r.id = t.rider_id LEFT JOIN users du ON du.id = t.driver_id ${where}`,
    [status, vehicle, q],
  );
  return c.json({ trips: rows.map((r) => tripJson(r, "admin")), total: Number(total?.n ?? 0) });
});

adminRoutes.get("/trips/:id", async (c) => {
  const row = await loadTrip(c.req.param("id"));
  if (!row) throw notFound("Trip");
  const events = await query("SELECT kind, actor, detail, at FROM trip_events WHERE trip_id = $1 ORDER BY at", [row.id]);
  const offers = await query(
    `SELECT o.status, o.pickup_km, o.offered_at, o.responded_at, u.full_name AS driver_name
       FROM ride_offers o JOIN users u ON u.id = o.driver_id WHERE o.trip_id = $1 ORDER BY o.offered_at`,
    [row.id],
  );
  const ledger = await query("SELECT w.kind, w.amount, w.note, w.created_at, u.full_name AS account FROM wallet_transactions w JOIN users u ON u.id = w.user_id WHERE w.trip_id = $1 ORDER BY w.created_at", [row.id]);
  const ratings = await query("SELECT r.stars, r.tags, r.comment, u.role AS from_role FROM ratings r JOIN users u ON u.id = r.from_user WHERE r.trip_id = $1", [row.id]);
  return c.json({
    ...tripJson(row, "admin"),
    pin: undefined,
    events,
    offers: offers.map((o: Record<string, any>) => ({ ...o, pickup_km: num(o.pickup_km) })),
    ledger: ledger.map((l: Record<string, any>) => ({ ...l, amount: num(l.amount) })),
    ratings,
  });
});

adminRoutes.post("/trips/:id/cancel", async (c) => {
  const reason = str(await body(c), "reason", { max: 200 });
  await cancelTrip(c.req.param("id"), "admin", actor(c), reason);
  await tx((client) => audit(client, actor(c), "trip.cancel", "trip", c.req.param("id"), { reason }));
  return c.json(tripJson((await loadTrip(c.req.param("id")))!, "admin"));
});

adminRoutes.post("/trips/:id/refund", async (c) => {
  const reason = str(await body(c), "reason", { max: 200 });
  const amount = await refundTrip(c.req.param("id"), actor(c), reason);
  await tx((client) => audit(client, actor(c), "trip.refund", "trip", c.req.param("id"), { amount, reason }));
  return c.json(tripJson((await loadTrip(c.req.param("id")))!, "admin"));
});

// --- riders -------------------------------------------------------------------------------------

adminRoutes.get("/riders", async (c) => {
  const url = new URL(c.req.url);
  const { limit, offset } = pageParams(url);
  const q = (url.searchParams.get("q") ?? "").trim() || null;
  const rows = await query<Record<string, any>>(
    `SELECT u.id, u.full_name, u.email, u.phone, u.avatar_color, u.status, u.created_at, u.last_login_at,
            coalesce(w.balance, 0) AS balance,
            (SELECT count(*) FROM trips t WHERE t.rider_id = u.id AND t.status = 'completed') AS trips,
            (SELECT coalesce(sum(fare_final), 0) FROM trips t WHERE t.rider_id = u.id AND t.status = 'completed') AS spent,
            (SELECT round(avg(stars)::numeric, 2) FROM ratings r WHERE r.to_user = u.id) AS rating
       FROM users u LEFT JOIN wallets w ON w.user_id = u.id
      WHERE u.role = 'rider' AND ($1::text IS NULL OR u.full_name ILIKE '%' || $1 || '%' OR u.email ILIKE '%' || $1 || '%' OR u.phone ILIKE '%' || $1 || '%')
      ORDER BY u.created_at DESC LIMIT $2 OFFSET $3`,
    [q, limit, offset],
  );
  const total = await one<{ n: string }>(
    `SELECT count(*) AS n FROM users u WHERE u.role = 'rider' AND ($1::text IS NULL OR u.full_name ILIKE '%' || $1 || '%' OR u.email ILIKE '%' || $1 || '%' OR u.phone ILIKE '%' || $1 || '%')`,
    [q],
  );
  return c.json({
    riders: rows.map((r) => ({ ...r, balance: num(r.balance), trips: Number(r.trips), spent: num(r.spent), rating: r.rating === null ? null : num(r.rating) })),
    total: Number(total?.n ?? 0),
  });
});

adminRoutes.get("/riders/:id", async (c) => {
  const user = await one<Record<string, any>>("SELECT id, full_name, email, phone, avatar_color, status, created_at, last_login_at FROM users WHERE id = $1 AND role = 'rider'", [c.req.param("id")]);
  if (!user) throw notFound("Rider");
  const trips = await query(`${TRIP_SELECT} WHERE t.rider_id = $1 ORDER BY t.requested_at DESC LIMIT 20`, [user.id]);
  const ledger = await query("SELECT id, kind, amount, balance_after, reference, note, created_at FROM wallet_transactions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20", [user.id]);
  const tickets = await query("SELECT id, code, subject, status, created_at FROM support_tickets WHERE user_id = $1 ORDER BY created_at DESC", [user.id]);
  return c.json({ ...user, balance: await balanceOf(user.id), trips: trips.map((t) => tripJson(t, "admin")), ledger: ledger.map(txJson), tickets });
});

adminRoutes.post("/users/:id/status", async (c) => {
  const status = oneOf(await body(c), "status", ["active", "suspended"] as const);
  const user = await one<{ id: string; role: string }>("UPDATE users SET status = $2 WHERE id = $1 AND role <> 'admin' RETURNING id, role", [c.req.param("id"), status]);
  if (!user) throw notFound("Account");
  await tx(async (client) => {
    if (status === "suspended") {
      await client.query("UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = $1 AND revoked_at IS NULL", [user.id]);
      if (user.role === "driver") await client.query("UPDATE drivers SET online = FALSE WHERE user_id = $1", [user.id]);
    }
    await audit(client, actor(c), `user.${status}`, user.role, user.id);
    await notify(client, user.id, "account", status === "suspended" ? "Account suspended" : "Account reactivated",
      status === "suspended" ? "Contact support if you think this is a mistake." : "Welcome back.");
  });
  return c.json({ id: user.id, status });
});

// --- drivers ------------------------------------------------------------------------------------

adminRoutes.get("/drivers", async (c) => {
  const url = new URL(c.req.url);
  const { limit, offset } = pageParams(url);
  const status = url.searchParams.get("status") || null;
  const q = (url.searchParams.get("q") ?? "").trim() || null;
  const filter = `WHERE ($1::text IS NULL OR d.status = $1)
                    AND ($2::text IS NULL OR u.full_name ILIKE '%' || $2 || '%' OR d.plate ILIKE '%' || $2 || '%' OR u.phone ILIKE '%' || $2 || '%')`;
  const rows = await query<Record<string, any>>(
    `SELECT u.id, u.full_name, u.email, u.phone, u.avatar_color, u.status AS account_status, d.status, d.online, d.simulated,
            d.vehicle_type, d.vehicle_make, d.vehicle_model, d.vehicle_color, d.plate, d.rating_avg, d.rating_count,
            d.offers_received, d.offers_accepted, d.joined_at, coalesce(w.balance, 0) AS balance,
            (SELECT count(*) FROM trips t WHERE t.driver_id = u.id AND t.status = 'completed') AS trips,
            (SELECT count(*) FROM driver_documents dd WHERE dd.driver_id = u.id AND dd.status = 'pending') AS docs_pending
       FROM drivers d JOIN users u ON u.id = d.user_id LEFT JOIN wallets w ON w.user_id = u.id
      ${filter} ORDER BY d.status = 'pending' DESC, d.joined_at DESC LIMIT $3 OFFSET $4`,
    [status, q, limit, offset],
  );
  const total = await one<{ n: string }>(`SELECT count(*) AS n FROM drivers d JOIN users u ON u.id = d.user_id ${filter}`, [status, q]);
  return c.json({
    drivers: rows.map((d) => ({
      ...d,
      rating_avg: num(d.rating_avg),
      balance: num(d.balance),
      trips: Number(d.trips),
      docs_pending: Number(d.docs_pending),
      acceptance_rate: d.offers_received > 0 ? Math.round((d.offers_accepted / d.offers_received) * 100) : 100,
    })),
    total: Number(total?.n ?? 0),
  });
});

adminRoutes.get("/drivers/:id", async (c) => {
  const d = await one<Record<string, any>>(
    `SELECT u.id, u.full_name, u.email, u.phone, u.avatar_color, u.status AS account_status, u.created_at, d.*
       FROM drivers d JOIN users u ON u.id = d.user_id WHERE d.user_id = $1`,
    [c.req.param("id")],
  );
  if (!d) throw notFound("Driver");
  const documents = await query("SELECT id, kind, number, status, expires_on, note, updated_at FROM driver_documents WHERE driver_id = $1 ORDER BY kind", [d.id]);
  const trips = await query(`${TRIP_SELECT} WHERE t.driver_id = $1 ORDER BY t.requested_at DESC LIMIT 20`, [d.id]);
  const ratings = await query("SELECT r.stars, r.tags, r.comment, r.created_at FROM ratings r WHERE r.to_user = $1 ORDER BY r.created_at DESC LIMIT 10", [d.id]);
  const earnings = await one<Record<string, any>>(
    "SELECT coalesce(sum(driver_earning), 0) AS e30, count(*) AS n30 FROM trips WHERE driver_id = $1 AND status = 'completed' AND completed_at >= now() - interval '30 days'",
    [d.id],
  );
  return c.json({
    ...d,
    user_id: undefined,
    rating_avg: num(d.rating_avg),
    balance: await balanceOf(d.id),
    earnings_30d: num(earnings!.e30),
    trips_30d: Number(earnings!.n30),
    acceptance_rate: d.offers_received > 0 ? Math.round((d.offers_accepted / d.offers_received) * 100) : 100,
    documents,
    trips: trips.map((t) => tripJson(t, "admin")),
    ratings,
  });
});

adminRoutes.post("/drivers/:id/status", async (c) => {
  const status = oneOf(await body(c), "status", ["approved", "suspended", "pending"] as const);
  const id = c.req.param("id");
  await tx(async (client) => {
    const row = await one<{ status: string }>("SELECT status FROM drivers WHERE user_id = $1 FOR UPDATE", [id], client);
    if (!row) throw notFound("Driver");
    if (status === "approved") {
      const pending = await one<{ n: string }>("SELECT count(*) AS n FROM driver_documents WHERE driver_id = $1 AND status <> 'approved'", [id], client);
      if (Number(pending?.n ?? 0) > 0) throw conflict("Approve every document before approving the driver.", "documents_pending");
    }
    await client.query("UPDATE drivers SET status = $2, online = CASE WHEN $2 = 'approved' THEN online ELSE FALSE END WHERE user_id = $1", [id, status]);
    await audit(client, actor(c), `driver.${status}`, "driver", id, { from: row.status });
    await notify(client, id, "account",
      status === "approved" ? "You're approved to drive" : status === "suspended" ? "Driving paused" : "Account under review",
      status === "approved" ? "Go online to start receiving ride requests." : "Contact RideNow support for details.");
  });
  return c.json({ id, status });
});

adminRoutes.post("/documents/:id/review", async (c) => {
  const data = await body(c);
  const status = oneOf(data, "status", ["approved", "rejected"] as const);
  const note = typeof data.note === "string" ? data.note.slice(0, 200) : "";
  const doc = await one<{ driver_id: string; kind: string }>(
    "UPDATE driver_documents SET status = $2, note = $3, updated_at = now() WHERE id = $1 RETURNING driver_id, kind",
    [c.req.param("id"), status, note],
  );
  if (!doc) throw notFound("Document");
  await tx(async (client) => {
    await audit(client, actor(c), `document.${status}`, "driver_document", c.req.param("id"), { kind: doc.kind, note });
    if (status === "rejected") await notify(client, doc.driver_id, "account", `Your ${doc.kind} was not accepted`, note || "Please upload it again.");
  });
  return c.json({ id: c.req.param("id"), status });
});

// --- pricing, zones, promos --------------------------------------------------------------------

adminRoutes.get("/vehicle-types", async (c) => {
  const rows = await query<Record<string, any>>("SELECT * FROM vehicle_types ORDER BY sort");
  return c.json({
    vehicle_types: rows.map((v) => ({
      ...v,
      base_fare: num(v.base_fare), per_km: num(v.per_km), per_min: num(v.per_min),
      min_fare: num(v.min_fare), booking_fee: num(v.booking_fee), commission_pct: num(v.commission_pct),
    })),
  });
});

adminRoutes.put("/vehicle-types/:id", async (c) => {
  const data = await body(c);
  const values = [
    c.req.param("id"),
    money(numberIn(data, "base_fare", 0, 1000)),
    money(numberIn(data, "per_km", 0, 200)),
    money(numberIn(data, "per_min", 0, 50)),
    money(numberIn(data, "min_fare", 0, 2000)),
    money(numberIn(data, "booking_fee", 0, 200)),
    numberIn(data, "commission_pct", 0, 50),
    data.active !== false,
  ];
  const row = await one("UPDATE vehicle_types SET base_fare = $2, per_km = $3, per_min = $4, min_fare = $5, booking_fee = $6, commission_pct = $7, active = $8 WHERE id = $1 RETURNING id", values);
  if (!row) throw notFound("Vehicle type");
  await tx((client) => audit(client, actor(c), "pricing.update", "vehicle_type", c.req.param("id"), data));
  return c.json({ ok: true });
});

adminRoutes.get("/zones", async (c) => {
  const rows = await query<Record<string, any>>("SELECT * FROM zones ORDER BY name");
  return c.json({ zones: rows.map((z) => ({ ...z, radius_km: num(z.radius_km), surge: num(z.surge) })) });
});

adminRoutes.patch("/zones/:id", async (c) => {
  const data = await body(c);
  const surge = Math.round(numberIn(data, "surge", 1, 3) * 100) / 100;
  const active = data.active !== false;
  const row = await one("UPDATE zones SET surge = $2, active = $3 WHERE id = $1 RETURNING id", [c.req.param("id"), surge, active]);
  if (!row) throw notFound("Zone");
  await tx((client) => audit(client, actor(c), "zone.update", "zone", c.req.param("id"), { surge, active }));
  hub.publish("admin", "zone.updated", { id: c.req.param("id"), surge, active });
  return c.json({ id: c.req.param("id"), surge, active });
});

adminRoutes.get("/promos", async (c) => {
  const rows = await query<Record<string, any>>(`
    SELECT p.*, (SELECT coalesce(sum(discount), 0) FROM trips t WHERE t.promo_code = p.code AND t.status = 'completed') AS total_discount
      FROM promo_codes p ORDER BY created_at DESC`);
  return c.json({
    promos: rows.map((p) => ({ ...p, value: num(p.value), max_discount: p.max_discount === null ? null : num(p.max_discount), min_fare: num(p.min_fare), total_discount: num(p.total_discount) })),
  });
});

adminRoutes.post("/promos", async (c) => {
  const data = await body(c);
  const code = str(data, "code", { min: 3, max: 20 }).toUpperCase();
  if (!/^[A-Z0-9]+$/.test(code)) throw badRequest("Codes use letters and digits only.");
  const kind = oneOf(data, "kind", ["percent", "flat"] as const);
  const value = numberIn(data, "value", 1, kind === "percent" ? 100 : 1000);
  try {
    await query(
      `INSERT INTO promo_codes (code, description, kind, value, max_discount, min_fare, valid_until, usage_limit, per_user_limit)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        code, str(data, "description", { max: 120 }), kind, value,
        typeof data.max_discount === "number" ? data.max_discount : null,
        typeof data.min_fare === "number" ? data.min_fare : 0,
        typeof data.valid_until === "string" && data.valid_until ? data.valid_until : null,
        typeof data.usage_limit === "number" ? data.usage_limit : null,
        typeof data.per_user_limit === "number" ? data.per_user_limit : 1,
      ],
    );
  } catch (error) {
    if ((error as { code?: string }).code === "23505") throw conflict("That code already exists.");
    throw error;
  }
  await tx((client) => audit(client, actor(c), "promo.create", "promo", code, { kind, value }));
  return c.json({ code }, 201);
});

adminRoutes.patch("/promos/:code", async (c) => {
  const active = (await body(c)).active === true;
  const row = await one("UPDATE promo_codes SET active = $2 WHERE code = $1 RETURNING code", [c.req.param("code"), active]);
  if (!row) throw notFound("Promo code");
  await tx((client) => audit(client, actor(c), active ? "promo.resume" : "promo.pause", "promo", c.req.param("code")));
  return c.json({ code: c.req.param("code"), active });
});

// --- payouts ------------------------------------------------------------------------------------

adminRoutes.get("/payouts", async (c) => {
  const status = c.req.query("status") || null;
  const rows = await query<Record<string, any>>(
    `SELECT p.*, u.full_name AS driver_name, u.avatar_color, d.plate
       FROM payouts p JOIN users u ON u.id = p.driver_id JOIN drivers d ON d.user_id = p.driver_id
      WHERE ($1::text IS NULL OR p.status = $1) ORDER BY p.requested_at DESC LIMIT 100`,
    [status],
  );
  return c.json({ payouts: rows.map((p) => ({ ...p, amount: num(p.amount) })) });
});

adminRoutes.post("/payouts/:id/decision", async (c) => {
  const decision = oneOf(await body(c), "decision", ["paid", "rejected"] as const);
  const result = await tx(async (client) => {
    const payout = await one<Record<string, any>>("SELECT * FROM payouts WHERE id = $1 FOR UPDATE", [c.req.param("id")], client);
    if (!payout) throw notFound("Payout");
    if (payout.status !== "requested") throw conflict("This payout was already processed.");
    const reference = decision === "paid" ? `NEFT${Date.now().toString().slice(-8)}` : "";
    await client.query("UPDATE payouts SET status = $2, reference = $3, processed_at = now() WHERE id = $1", [payout.id, decision, reference]);
    let balance: number | null = null;
    if (decision === "rejected") {
      balance = await postLedger(client, payout.driver_id, "adjustment", num(payout.amount), { reference: payout.id, note: "Payout rejected, amount returned" });
    }
    await audit(client, actor(c), `payout.${decision}`, "payout", payout.id, { amount: num(payout.amount) });
    await notify(client, payout.driver_id, "payout", decision === "paid" ? "Payout sent" : "Payout rejected",
      decision === "paid" ? `₹${num(payout.amount).toFixed(2)} was sent (ref ${reference}).` : "The amount is back in your RideNow wallet.");
    return { driverId: payout.driver_id as string, balance };
  });
  if (result.balance !== null) announceWallet(result.driverId, result.balance);
  return c.json({ id: c.req.param("id"), status: decision });
});

/** Platform finance summary: commission earned, promos funded, refunds, balances owed to drivers. */
adminRoutes.get("/finance", async (c) => {
  const platform = await platformUser();
  const byKind = await query<{ kind: string; total: string }>(
    "SELECT kind, sum(amount) AS total FROM wallet_transactions WHERE user_id = $1 AND created_at >= now() - interval '30 days' GROUP BY kind",
    [platform],
  );
  const owed = await one<{ total: string }>("SELECT coalesce(sum(w.balance), 0) AS total FROM wallets w JOIN users u ON u.id = w.user_id WHERE u.role = 'driver' AND w.balance > 0");
  const riderFloat = await one<{ total: string }>("SELECT coalesce(sum(w.balance), 0) AS total FROM wallets w JOIN users u ON u.id = w.user_id WHERE u.role = 'rider'");
  return c.json({
    platform_balance: await balanceOf(platform),
    last_30_days: Object.fromEntries(byKind.map((k) => [k.kind, num(k.total)])),
    owed_to_drivers: num(owed?.total ?? 0),
    rider_wallet_float: num(riderFloat?.total ?? 0),
  });
});

// --- support and audit --------------------------------------------------------------------------

adminRoutes.get("/tickets", async (c) => {
  const status = c.req.query("status") || null;
  const rows = await query(
    `SELECT s.id, s.code, s.category, s.subject, s.status, s.priority, s.created_at, s.updated_at,
            u.full_name AS user_name, u.role AS user_role, u.avatar_color, t.code AS trip_code,
            (SELECT count(*) FROM ticket_messages m WHERE m.ticket_id = s.id) AS messages
       FROM support_tickets s JOIN users u ON u.id = s.user_id LEFT JOIN trips t ON t.id = s.trip_id
      WHERE ($1::text IS NULL OR s.status = $1)
      ORDER BY CASE s.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, s.updated_at DESC LIMIT 100`,
    [status],
  );
  return c.json({ tickets: rows.map((t: Record<string, any>) => ({ ...t, messages: Number(t.messages) })) });
});

adminRoutes.patch("/tickets/:id", async (c) => {
  const data = await body(c);
  const status = oneOf(data, "status", ["open", "pending", "resolved"] as const);
  const priority = oneOf(data, "priority", ["low", "normal", "high", "urgent"] as const, "normal");
  const row = await one<{ user_id: string; code: string }>(
    "UPDATE support_tickets SET status = $2, priority = $3, updated_at = now() WHERE id = $1 RETURNING user_id, code",
    [c.req.param("id"), status, priority],
  );
  if (!row) throw notFound("Ticket");
  await tx(async (client) => {
    await audit(client, actor(c), "ticket.update", "ticket", c.req.param("id"), { status, priority });
    if (status === "resolved") await notify(client, row.user_id, "support", `${row.code} resolved`, "Reply to the ticket if you need anything else.");
  });
  return c.json({ id: c.req.param("id"), status, priority });
});

adminRoutes.get("/audit", async (c) => {
  const { limit, offset } = pageParams(new URL(c.req.url));
  const rows = await query(
    `SELECT a.id, a.action, a.entity, a.entity_id, a.detail, a.at, u.full_name AS actor_name
       FROM audit_log a LEFT JOIN users u ON u.id = a.actor_id ORDER BY a.at DESC LIMIT $1 OFFSET $2`,
    [limit, offset],
  );
  return c.json({ entries: rows });
});

adminRoutes.get("/wallets/:userId", async (c) => {
  const { limit, offset } = pageParams(new URL(c.req.url));
  const rows = await query("SELECT id, kind, amount, balance_after, reference, note, created_at FROM wallet_transactions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3", [c.req.param("userId"), limit, offset]);
  return c.json({ balance: await balanceOf(c.req.param("userId")), transactions: rows.map(txJson) });
});

adminRoutes.post("/wallets/:userId/adjust", async (c) => {
  const data = await body(c);
  const amount = money(numberIn(data, "amount", -10000, 10000));
  if (amount === 0) throw badRequest("Enter a non-zero amount.");
  const note = str(data, "note", { max: 200 });
  const userId = c.req.param("userId");
  const balance = await tx(async (client) => {
    const next = await postLedger(client, userId, "adjustment", amount, { note });
    await audit(client, actor(c), "wallet.adjust", "wallet", userId, { amount, note });
    await notify(client, userId, "wallet", amount > 0 ? "Credit added" : "Wallet adjusted", `${amount > 0 ? "+" : "−"}₹${Math.abs(amount).toFixed(2)}: ${note}`);
    return next;
  });
  announceWallet(userId, balance);
  return c.json({ balance });
});
