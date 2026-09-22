import { Hono } from "hono";
import { config } from "../config.ts";
import { query } from "../db.ts";
import { verifyJwt } from "../auth/tokens.ts";
import { num } from "../lib/money.ts";
import { estimate } from "../services/trips.ts";
import { body, stop } from "./util.ts";

export const publicRoutes = new Hono();

publicRoutes.get("/config", async (c) => {
  const types = await query<Record<string, any>>("SELECT * FROM vehicle_types WHERE active ORDER BY sort");
  return c.json({
    city: config.city,
    currency: config.currency,
    preview: config.preview,
    vehicle_types: types.map((t) => ({
      id: t.id,
      name: t.name,
      description: t.description,
      seats: t.seats,
      base_fare: num(t.base_fare),
      per_km: num(t.per_km),
      per_min: num(t.per_min),
      min_fare: num(t.min_fare),
    })),
  });
});

/** Search the city's well-known places (a maps provider would add geocoding here). */
publicRoutes.get("/places/search", async (c) => {
  const q = (c.req.query("q") ?? "").trim();
  const rows = await query(
    `SELECT id, name, address, lat, lng FROM places WHERE user_id IS NULL
       AND ($1 = '' OR name ILIKE '%' || $1 || '%' OR address ILIKE '%' || $1 || '%')
     ORDER BY name LIMIT 12`,
    [q.slice(0, 60)],
  );
  return c.json({ places: rows });
});

publicRoutes.post("/fare/estimate", async (c) => {
  const data = await body(c);
  const token = (c.req.header("authorization") ?? "").replace(/^Bearer /, "");
  const claims = token ? verifyJwt(token, config.jwtSecret) : null;
  const promo = typeof data.promo_code === "string" ? data.promo_code.trim().slice(0, 30) : "";
  return c.json(await estimate(stop(data.pickup, "Pickup"), stop(data.drop, "Drop"), claims?.role === "rider" ? claims.sub : null, promo));
});
