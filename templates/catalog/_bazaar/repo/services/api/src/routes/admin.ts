/** Operator administration routes for multi-vendor supervision, KYC, orders, and settlements. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { authenticate, requireRole } from "../auth/middleware.ts";
import { ledgerService } from "../services/ledger.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";

export const adminRoutes = new Hono();

adminRoutes.use("*", authenticate());
adminRoutes.use("*", requireRole("admin"));

// Platform Metrics
adminRoutes.get("/metrics", async (c) => {
  const ordStats = await query<{
    gmv_cents: string;
    order_count: string;
  }>(
    `SELECT COALESCE(SUM(total_cents), 0)::text AS gmv_cents,
            COUNT(*)::text AS order_count
     FROM orders`
  );

  const shopCountRes = await query<{ count: string }>(
    `SELECT COUNT(*)::text as count FROM shops`
  );

  const userCountRes = await query<{ count: string }>(
    `SELECT COUNT(*)::text as count FROM users WHERE role = 'shopper'`
  );

  const financials = await ledgerService.getPlatformFinancialSummary();

  return c.json({
    metrics: {
      totalGmvCents: parseInt(ordStats.rows[0]?.gmv_cents || "0", 10),
      totalOrdersCount: parseInt(ordStats.rows[0]?.order_count || "0", 10),
      totalShopsCount: parseInt(shopCountRes.rows[0]?.count || "0", 10),
      totalShoppersCount: parseInt(userCountRes.rows[0]?.count || "0", 10),
      financials,
    },
  });
});

// Shops Management
adminRoutes.get("/shops", async (c) => {
  const kycStatus = c.req.query("kycStatus");
  const conditions: string[] = [];
  const params: any[] = [];

  if (kycStatus) {
    conditions.push("s.kyc_status = $1");
    params.push(kycStatus);
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const res = await query(
    `SELECT s.*, u.name AS owner_name, u.email AS owner_email,
            (SELECT COUNT(*) FROM products p WHERE p.shop_id = s.id) AS product_count,
            (SELECT COUNT(*) FROM shipments sh WHERE sh.shop_id = s.id) AS shipment_count
     FROM shops s
     JOIN users u ON u.id = s.user_id
     ${whereClause}
     ORDER BY s.created_at DESC`,
    params
  );

  return c.json({ shops: res.rows });
});

// Update Shop KYC Status
adminRoutes.post("/shops/:id/kyc", async (c) => {
  const shopId = c.req.param("id");
  const { kycStatus } = await c.req.json();

  if (!["pending", "verified", "rejected", "suspended"].includes(kycStatus)) {
    throw new BadRequestError("Invalid KYC status");
  }

  const res = await query(
    `UPDATE shops SET kyc_status = $1, updated_at = NOW() WHERE id = $2 RETURNING *`,
    [kycStatus, shopId]
  );

  if (res.rows.length === 0) {
    throw new NotFoundError("Shop not found");
  }

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'update_shop_kyc', 'shop', $2, $3)`,
    [user.userId, shopId, JSON.stringify({ newStatus: kycStatus })]
  );

  return c.json({ shop: res.rows[0] });
});

// Global Orders List
adminRoutes.get("/orders", async (c) => {
  const status = c.req.query("status");
  const limit = c.req.query("limit") ? parseInt(c.req.query("limit")!, 10) : 50;
  const offset = c.req.query("offset") ? parseInt(c.req.query("offset")!, 10) : 0;

  const conditions: string[] = [];
  const params: any[] = [];
  let pIdx = 1;

  if (status) {
    conditions.push(`o.status = $${pIdx++}`);
    params.push(status);
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const res = await query(
    `SELECT o.*, u.name AS customer_name, u.email AS customer_email,
            (SELECT COUNT(*) FROM shipments s WHERE s.order_id = o.id) AS shipment_count
     FROM orders o
     JOIN users u ON u.id = o.user_id
     ${whereClause}
     ORDER BY o.created_at DESC
     LIMIT $${pIdx++} OFFSET $${pIdx++}`,
    [...params, limit, offset]
  );

  return c.json({ orders: res.rows });
});

// Settlement Batches
adminRoutes.get("/settlements", async (c) => {
  const res = await query(
    `SELECT sb.*, sh.name AS shop_name, sh.slug AS shop_slug
     FROM settlement_batches sb
     JOIN shops sh ON sh.id = sb.shop_id
     ORDER BY sb.created_at DESC
     LIMIT 50`
  );

  return c.json({ settlements: res.rows });
});

// Audit Logs
adminRoutes.get("/audit-logs", async (c) => {
  const res = await query(
    `SELECT al.*, u.name AS actor_name, u.email AS actor_email
     FROM audit_logs al
     LEFT JOIN users u ON u.id = al.actor_id
     ORDER BY al.created_at DESC
     LIMIT 100`
  );

  return c.json({ auditLogs: res.rows });
});
