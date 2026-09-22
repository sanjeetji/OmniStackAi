import { Hono } from "hono";
import { one, query, tx } from "../db.ts";
import { type AppEnv, requireAuth } from "../auth/middleware.ts";
import { notFound } from "../lib/errors.ts";
import { hub } from "../lib/events.ts";
import { oneOf, pageParams, str } from "../lib/validate.ts";
import { notify } from "../services/notify.ts";
import { body } from "./util.ts";

/** Tickets and notifications for every signed-in role. Admins see any ticket; others only their own. */
export const supportRoutes = new Hono<AppEnv>();
supportRoutes.use("*", requireAuth());

supportRoutes.get("/tickets", async (c) => {
  const rows = await query(
    `SELECT s.id, s.code, s.category, s.subject, s.status, s.priority, s.created_at, s.updated_at, t.code AS trip_code,
            (SELECT body FROM ticket_messages m WHERE m.ticket_id = s.id ORDER BY created_at DESC LIMIT 1) AS last_message
       FROM support_tickets s LEFT JOIN trips t ON t.id = s.trip_id WHERE s.user_id = $1 ORDER BY s.updated_at DESC`,
    [c.get("user").sub],
  );
  return c.json({ tickets: rows });
});

supportRoutes.post("/tickets", async (c) => {
  const data = await body(c);
  const user = c.get("user");
  const category = oneOf(data, "category", ["payment", "safety", "lost_item", "driver", "app", "other"] as const);
  const subject = str(data, "subject", { min: 4, max: 120 });
  const message = str(data, "message", { min: 5, max: 2000 });
  let tripId: string | null = null;
  if (typeof data.trip_id === "string" && data.trip_id) {
    const trip = await one<{ id: string }>("SELECT id FROM trips WHERE id = $1 AND (rider_id = $2 OR driver_id = $2)", [data.trip_id, user.sub]);
    if (!trip) throw notFound("Trip");
    tripId = trip.id;
  }
  const ticket = await tx(async (client) => {
    const row = (await client.query<{ id: string; code: string }>(
      "INSERT INTO support_tickets (user_id, trip_id, category, subject, priority) VALUES ($1, $2, $3, $4, $5) RETURNING id, code",
      [user.sub, tripId, category, subject, category === "safety" ? "urgent" : "normal"],
    )).rows[0];
    await client.query("INSERT INTO ticket_messages (ticket_id, author_id, body) VALUES ($1, $2, $3)", [row.id, user.sub, message]);
    await notify(client, user.sub, "support", `We got your request ${row.code}`, "Our team usually replies within a few hours.");
    return row;
  });
  hub.publish("admin", "ticket.created", { id: ticket.id, code: ticket.code, category });
  return c.json(ticket, 201);
});

async function ticketFor(id: string, user: { sub: string; role: string }) {
  const ticket = await one<Record<string, any>>(
    `SELECT s.*, t.code AS trip_code, u.full_name AS user_name, u.role AS user_role
       FROM support_tickets s JOIN users u ON u.id = s.user_id LEFT JOIN trips t ON t.id = s.trip_id WHERE s.id = $1`,
    [id],
  );
  if (!ticket || (user.role !== "admin" && ticket.user_id !== user.sub)) throw notFound("Ticket");
  return ticket;
}

supportRoutes.get("/tickets/:id", async (c) => {
  const ticket = await ticketFor(c.req.param("id"), c.get("user"));
  const messages = await query(
    `SELECT m.id, m.body, m.created_at, u.full_name AS author_name, u.role AS author_role, u.avatar_color
       FROM ticket_messages m JOIN users u ON u.id = m.author_id WHERE m.ticket_id = $1 ORDER BY m.created_at`,
    [ticket.id],
  );
  return c.json({ ...ticket, messages });
});

supportRoutes.post("/tickets/:id/messages", async (c) => {
  const user = c.get("user");
  const ticket = await ticketFor(c.req.param("id"), user);
  const text = str(await body(c), "body", { min: 1, max: 2000 });
  await tx(async (client) => {
    await client.query("INSERT INTO ticket_messages (ticket_id, author_id, body) VALUES ($1, $2, $3)", [ticket.id, user.sub, text]);
    const status = user.role === "admin" ? "pending" : "open";
    await client.query("UPDATE support_tickets SET status = $2, updated_at = now() WHERE id = $1", [ticket.id, status]);
    if (user.role === "admin") await notify(client, ticket.user_id, "support", `New reply on ${ticket.code}`, text.slice(0, 140));
  });
  if (user.role !== "admin") hub.publish("admin", "ticket.updated", { id: ticket.id, code: ticket.code });
  return c.json({ ok: true }, 201);
});

supportRoutes.get("/notifications", async (c) => {
  const { limit, offset } = pageParams(new URL(c.req.url), 50);
  const userId = c.get("user").sub;
  const rows = await query("SELECT id, kind, title, body, read_at, created_at FROM notifications WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3", [userId, limit, offset]);
  const unread = await one<{ n: string }>("SELECT count(*) AS n FROM notifications WHERE user_id = $1 AND read_at IS NULL", [userId]);
  return c.json({ notifications: rows, unread: Number(unread?.n ?? 0) });
});

supportRoutes.post("/notifications/read", async (c) => {
  await query("UPDATE notifications SET read_at = now() WHERE user_id = $1 AND read_at IS NULL", [c.get("user").sub]);
  return c.body(null, 204);
});
