/** Operator administration routes for multi-vendor supervision, KYC, orders, and settlements. */

import { Hono } from "hono";
import { query, withTransaction } from "../db.ts";
import { authenticate, requireRole } from "../auth/middleware.ts";
import { ledgerService } from "../services/ledger.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";
import { eventBus } from "../lib/events.ts";

export const adminRoutes = new Hono();

adminRoutes.use("*", authenticate());
adminRoutes.use("*", requireRole("admin"));

// Platform Metrics & Overview
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

  const dailyVolumeRes = await query<{
    date: string;
    gmv_cents: string;
    order_count: string;
  }>(
    `SELECT TO_CHAR(created_at, 'YYYY-MM-DD') AS date,
            COALESCE(SUM(total_cents), 0)::text AS gmv_cents,
            COUNT(*)::text AS order_count
     FROM orders
     GROUP BY TO_CHAR(created_at, 'YYYY-MM-DD')
     ORDER BY date DESC
     LIMIT 14`
  );

  const pendingKycRes = await query<{ count: string }>(
    `SELECT COUNT(*)::text as count FROM shops WHERE kyc_status = 'pending'`
  );

  const pendingSettlementsRes = await query<{ count: string }>(
    `SELECT COUNT(*)::text as count FROM settlement_batches WHERE status = 'approved'`
  );

  const financials = await ledgerService.getPlatformFinancialSummary();

  return c.json({
    metrics: {
      totalGmvCents: parseInt(ordStats.rows[0]?.gmv_cents || "0", 10),
      totalOrdersCount: parseInt(ordStats.rows[0]?.order_count || "0", 10),
      totalShopsCount: parseInt(shopCountRes.rows[0]?.count || "0", 10),
      totalShoppersCount: parseInt(userCountRes.rows[0]?.count || "0", 10),
      pendingKycCount: parseInt(pendingKycRes.rows[0]?.count || "0", 10),
      pendingSettlementsCount: parseInt(pendingSettlementsRes.rows[0]?.count || "0", 10),
      dailyVolume: dailyVolumeRes.rows.reverse().map((r) => ({
        date: r.date,
        gmvCents: parseInt(r.gmv_cents, 10),
        orderCount: parseInt(r.order_count, 10),
      })),
      financials,
    },
  });
});

// Shops Directory
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
            (SELECT COUNT(*) FROM shipments sh WHERE sh.shop_id = s.id) AS shipment_count,
            (SELECT COALESCE(SUM(total_cents), 0) FROM orders o WHERE o.id IN (SELECT order_id FROM shipments sh WHERE sh.shop_id = s.id)) AS gmv_cents
     FROM shops s
     JOIN users u ON u.id = s.user_id
     ${whereClause}
     ORDER BY s.created_at DESC`,
    params
  );

  return c.json({ shops: res.rows });
});

// Single Shop Details
adminRoutes.get("/shops/:id", async (c) => {
  const shopId = c.req.param("id");
  const shopRes = await query(
    `SELECT s.*, u.name AS owner_name, u.email AS owner_email
     FROM shops s
     JOIN users u ON u.id = s.user_id
     WHERE s.id = $1`,
    [shopId]
  );

  if (shopRes.rows.length === 0) {
    throw new NotFoundError("Shop not found");
  }

  const shop = shopRes.rows[0];

  const productsRes = await query(
    `SELECT p.*, c.name AS category_name
     FROM products p
     JOIN categories c ON c.id = p.category_id
     WHERE p.shop_id = $1
     ORDER BY p.created_at DESC
     LIMIT 20`,
    [shopId]
  );

  const shipmentsRes = await query(
    `SELECT sh.*, o.order_number
     FROM shipments sh
     JOIN orders o ON o.id = sh.order_id
     WHERE sh.shop_id = $1
     ORDER BY sh.created_at DESC
     LIMIT 10`,
    [shopId]
  );

  return c.json({
    shop,
    products: productsRes.rows,
    shipments: shipmentsRes.rows,
  });
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

// Update Shop Commission Rate
adminRoutes.post("/shops/:id/commission", async (c) => {
  const shopId = c.req.param("id");
  const { commissionRateBasisPoints } = await c.req.json();

  const bps = parseInt(commissionRateBasisPoints, 10);
  if (isNaN(bps) || bps < 0 || bps > 10000) {
    throw new BadRequestError("Commission rate must be between 0 and 10000 basis points");
  }

  const res = await query(
    `UPDATE shops SET commission_rate_basis_points = $1, updated_at = NOW() WHERE id = $2 RETURNING *`,
    [bps, shopId]
  );

  if (res.rows.length === 0) {
    throw new NotFoundError("Shop not found");
  }

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'update_shop_commission', 'shop', $2, $3)`,
    [user.userId, shopId, JSON.stringify({ newCommissionBps: bps })]
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
            (SELECT COUNT(*) FROM shipments s WHERE s.order_id = o.id) AS shipment_count,
            (SELECT COUNT(*) FROM shipment_items si
              JOIN shipments s2 ON s2.id = si.shipment_id
             WHERE s2.order_id = o.id) AS item_count
     FROM orders o
     JOIN users u ON u.id = o.user_id
     ${whereClause}
     ORDER BY o.created_at DESC
     LIMIT $${pIdx++} OFFSET $${pIdx++}`,
    [...params, limit, offset]
  );

  return c.json({ orders: res.rows });
});

// Single Order Deep Investigation
adminRoutes.get("/orders/:id", async (c) => {
  const orderId = c.req.param("id");

  const ordRes = await query(
    `SELECT o.*, u.name AS customer_name, u.email AS customer_email, u.phone AS customer_phone
     FROM orders o
     JOIN users u ON u.id = o.user_id
     WHERE o.id = $1`,
    [orderId]
  );

  if (ordRes.rows.length === 0) {
    throw new NotFoundError("Order not found");
  }

  const order = ordRes.rows[0];

  const itemsRes = await query(
    `SELECT si.*, si.product_title, si.variant_title, si.unit_price_cents, si.quantity,
            s.name AS shop_name
     FROM shipment_items si
     JOIN shipments sh ON sh.id = si.shipment_id
     JOIN shops s ON s.id = sh.shop_id
     WHERE sh.order_id = $1
     ORDER BY s.name ASC`,
    [orderId]
  );

  const shipmentsRes = await query(
    `SELECT sh.*, s.name AS shop_name, s.slug AS shop_slug
     FROM shipments sh
     JOIN shops s ON s.id = sh.shop_id
     WHERE sh.order_id = $1
     ORDER BY sh.created_at ASC`,
    [orderId]
  );

  const shipmentIds = shipmentsRes.rows.map((s: any) => s.id);
  let trackingEvents: any[] = [];
  if (shipmentIds.length > 0) {
    const trackRes = await query(
      `SELECT * FROM shipment_tracking_events WHERE shipment_id = ANY($1) ORDER BY occurred_at ASC`,
      [shipmentIds]
    );
    trackingEvents = trackRes.rows;
  }

  const ledgerRes = await query(
    `SELECT le.*, da.holder_type AS debit_holder, ca.holder_type AS credit_holder
     FROM ledger_entries le
     JOIN accounts da ON da.id = le.debit_account_id
     JOIN accounts ca ON ca.id = le.credit_account_id
     WHERE le.reference_type = 'order' AND le.reference_id = $1
     ORDER BY le.created_at ASC`,
    [orderId]
  );

  return c.json({
    order,
    items: itemsRes.rows,
    shipments: shipmentsRes.rows.map((sh: any) => ({
      ...sh,
      trackingEvents: trackingEvents.filter((te) => te.shipment_id === sh.id),
    })),
    ledgerEntries: ledgerRes.rows,
  });
});

// Admin Cancel Order
adminRoutes.post("/orders/:id/cancel", async (c) => {
  const orderId = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));
  const reason = typeof body.reason === "string" && body.reason.trim()
    ? body.reason.trim()
    : "Administrative cancellation";

  const user = c.get("user");

  return withTransaction(async (client) => {
    const ordRes = await client.query(
      `SELECT * FROM orders WHERE id = $1 FOR UPDATE`,
      [orderId]
    );
    if (ordRes.rows.length === 0) throw new NotFoundError("Order not found");
    const order = ordRes.rows[0];
    if (order.status === "cancelled") {
      return c.json({ order, refundedCents: 0 });
    }

    // A cancelled order must not leave money posted against it: every entry raised for this
    // order is reversed, so the ledger still sums to zero and no vendor is credited for a
    // consignment that will never ship.
    const entriesRes = await client.query(
      `SELECT * FROM ledger_entries WHERE reference_type = 'order' AND reference_id = $1`,
      [orderId]
    );

    let refundedCents = 0;
    for (const entry of entriesRes.rows) {
      await ledgerService.postEntry(
        {
          entryType: "shopper_refund",
          // Reversing an entry means posting it the other way round.
          debitAccountId: entry.credit_account_id,
          creditAccountId: entry.debit_account_id,
          amountCents: parseInt(entry.amount_cents, 10),
          referenceType: "order",
          referenceId: orderId,
          description: `Reversal of ${entry.entry_type}: ${reason}`,
        },
        client
      );
      if (entry.entry_type === "order_payment") {
        refundedCents += parseInt(entry.amount_cents, 10);
      }
    }

    const updated = await client.query(
      `UPDATE orders SET status = 'cancelled' WHERE id = $1 RETURNING *`,
      [orderId]
    );
    await client.query(
      `UPDATE shipments SET status = 'cancelled' WHERE order_id = $1 AND status <> 'delivered'`,
      [orderId]
    );

    await client.query(
      `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
       VALUES ($1, 'cancel_order', 'order', $2, $3)`,
      [user.userId, orderId, JSON.stringify({ reason, reversedEntries: entriesRes.rows.length, refundedCents })]
    );

    eventBus.broadcast({
      type: "order.cancelled",
      recipientUserId: order.user_id,
      payload: { orderId, orderNumber: order.order_number, refundedCents },
      timestamp: new Date().toISOString(),
    });

    return c.json({ order: updated.rows[0], refundedCents });
  });
});

// Global Shipments Monitor
adminRoutes.get("/shipments", async (c) => {
  const status = c.req.query("status");
  const conditions: string[] = [];
  const params: any[] = [];

  if (status) {
    conditions.push("sh.status = $1");
    params.push(status);
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const res = await query(
    `SELECT sh.*, s.name AS shop_name, s.slug AS shop_slug, o.order_number, u.name AS customer_name
     FROM shipments sh
     JOIN shops s ON s.id = sh.shop_id
     JOIN orders o ON o.id = sh.order_id
     JOIN users u ON u.id = o.user_id
     ${whereClause}
     ORDER BY sh.created_at DESC
     LIMIT 50`,
    params
  );

  return c.json({ shipments: res.rows });
});

// Platform Financials
adminRoutes.get("/finance", async (c) => {
  const summary = await ledgerService.getPlatformFinancialSummary();
  const recentEntries = await query(
    `SELECT le.*, da.holder_type AS debit_holder, ca.holder_type AS credit_holder
     FROM ledger_entries le
     JOIN accounts da ON da.id = le.debit_account_id
     JOIN accounts ca ON ca.id = le.credit_account_id
     ORDER BY le.created_at DESC
     LIMIT 20`
  );

  return c.json({
    summary,
    recentEntries: recentEntries.rows,
  });
});

// Double-Entry Ledger Audit Trail
adminRoutes.get("/finance/ledger", async (c) => {
  const entryType = c.req.query("entryType");
  const conditions: string[] = [];
  const params: any[] = [];

  if (entryType) {
    conditions.push("le.entry_type = $1");
    params.push(entryType);
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const res = await query(
    `SELECT le.*,
            da.holder_type AS debit_holder, da.holder_id AS debit_holder_id,
            ca.holder_type AS credit_holder, ca.holder_id AS credit_holder_id
     FROM ledger_entries le
     JOIN accounts da ON da.id = le.debit_account_id
     JOIN accounts ca ON ca.id = le.credit_account_id
     ${whereClause}
     ORDER BY le.created_at DESC
     LIMIT 100`,
    params
  );

  return c.json({ entries: res.rows });
});

// Settlement Batches
adminRoutes.get("/settlements", async (c) => {
  const res = await query(
    `SELECT sb.*, sh.name AS shop_name, sh.slug AS shop_slug,
            sh.bank_name, sh.bank_account_last4, sh.bank_ifsc_code
     FROM settlement_batches sb
     JOIN shops sh ON sh.id = sb.shop_id
     ORDER BY sb.created_at DESC
     LIMIT 50`
  );

  return c.json({ settlements: res.rows });
});

// Single Settlement Batch
adminRoutes.get("/settlements/:id", async (c) => {
  const batchId = c.req.param("id");
  const res = await query(
    `SELECT sb.*, sh.name AS shop_name, sh.slug AS shop_slug,
            sh.bank_name, sh.bank_account_last4, sh.bank_ifsc_code,
            u.name AS owner_name, u.email AS owner_email
     FROM settlement_batches sb
     JOIN shops sh ON sh.id = sb.shop_id
     JOIN users u ON u.id = sh.user_id
     WHERE sb.id = $1`,
    [batchId]
  );

  if (res.rows.length === 0) {
    throw new NotFoundError("Settlement batch not found");
  }

  return c.json({ settlement: res.rows[0] });
});

// Approve Settlement Batch
adminRoutes.post("/settlements/:id/approve", async (c) => {
  const batchId = c.req.param("id");
  const res = await query(
    `UPDATE settlement_batches
     SET status = 'processed', processed_at = NOW()
     WHERE id = $1
     RETURNING *`,
    [batchId]
  );

  if (res.rows.length === 0) {
    throw new NotFoundError("Settlement batch not found");
  }

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'approve_settlement_batch', 'settlement_batch', $2, $3)`,
    [user.userId, batchId, JSON.stringify({ status: "processed" })]
  );

  return c.json({ settlement: res.rows[0] });
});

// Generate Settlement Batch for a shop
adminRoutes.post("/settlements/generate", async (c) => {
  const { shopId } = await c.req.json();
  if (!shopId) throw new BadRequestError("shopId is required");

  const batch = await ledgerService.createSettlementBatch(shopId);

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'generate_settlement_batch', 'settlement_batch', $2, $3)`,
    [user.userId, batch.id, JSON.stringify({ shopId, netPayoutCents: batch.net_payout_cents })]
  );

  return c.json({ settlement: batch });
});

// Promotional Coupons
adminRoutes.get("/coupons", async (c) => {
  const res = await query(`SELECT * FROM coupons ORDER BY created_at DESC`);
  return c.json({ coupons: res.rows });
});

// Create Coupon
adminRoutes.post("/coupons", async (c) => {
  const body = await c.req.json();
  const { code, description, discountType, discountValue, minOrderCents, maxDiscountCents, usageLimit, expiresAt } = body;

  if (!code || !discountType || discountValue === undefined) {
    throw new BadRequestError("code, discountType, and discountValue are required");
  }

  const res = await query(
    `INSERT INTO coupons (
       code, description, discount_type, discount_value, min_order_cents, max_discount_cents, usage_limit, expires_at
     )
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
     RETURNING *`,
    [
      code.toUpperCase().trim(),
      description || null,
      discountType,
      discountValue,
      minOrderCents || 0,
      maxDiscountCents || null,
      usageLimit || null,
      expiresAt || null,
    ]
  );

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'create_coupon', 'coupon', $2, $3)`,
    [user.userId, res.rows[0].id, JSON.stringify({ code })]
  );

  return c.json({ coupon: res.rows[0] });
});

// Toggle Coupon Active Status
adminRoutes.post("/coupons/:id/toggle", async (c) => {
  const couponId = c.req.param("id");
  const res = await query(
    `UPDATE coupons SET is_active = NOT is_active WHERE id = $1 RETURNING *`,
    [couponId]
  );

  if (res.rows.length === 0) throw new NotFoundError("Coupon not found");

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'toggle_coupon', 'coupon', $2, $3)`,
    [user.userId, couponId, JSON.stringify({ isActive: res.rows[0].is_active })]
  );

  return c.json({ coupon: res.rows[0] });
});

// Reviews Moderation
adminRoutes.get("/reviews", async (c) => {
  const res = await query(
    `SELECT r.*, p.title AS product_title, p.slug AS product_slug,
            s.name AS shop_name, s.slug AS shop_slug,
            u.name AS shopper_name, u.email AS shopper_email
     FROM reviews r
     JOIN products p ON p.id = r.product_id
     JOIN shops s ON s.id = r.shop_id
     JOIN users u ON u.id = r.user_id
     ORDER BY r.created_at DESC
     LIMIT 50`
  );

  return c.json({ reviews: res.rows });
});

// Delete Review (Moderation)
adminRoutes.post("/reviews/:id/delete", async (c) => {
  const reviewId = c.req.param("id");
  const res = await query(`DELETE FROM reviews WHERE id = $1 RETURNING *`, [reviewId]);
  if (res.rows.length === 0) throw new NotFoundError("Review not found");

  const user = c.get("user");
  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'delete_review', 'review', $2, $3)`,
    [user.userId, reviewId, JSON.stringify({ deleted: true })]
  );

  return c.json({ success: true });
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

// Platform Settings
adminRoutes.get("/settings", async (c) => {
  return c.json({
    settings: {
      defaultCommissionBasisPoints: 1000,
      escrowHoldDays: 7,
      gstin: "08AABCB1234F1Z5",
      taxRateBasisPoints: 1800,
      supportedCarriers: ["Blue Dart Express", "Delhivery", "India Post Speed Post", "Ekart"],
      mockLogistics: true,
      mockPayments: true,
    },
  });
});

adminRoutes.post("/settings", async (c) => {
  const body = await c.req.json();
  const user = c.get("user");

  await query(
    `INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, metadata_json)
     VALUES ($1, 'update_settings', 'platform', $1, $2)`,
    [user.userId, JSON.stringify(body)]
  );

  return c.json({
    success: true,
    settings: body,
  });
});
