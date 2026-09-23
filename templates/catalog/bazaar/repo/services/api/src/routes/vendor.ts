/** Vendor portal routes: inventory management, order fulfillment, and payout settlements. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { authenticate, requireRole } from "../auth/middleware.ts";
import { catalogService } from "../services/catalog.ts";
import { fulfillmentService } from "../services/fulfillment.ts";
import { ledgerService } from "../services/ledger.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";

export const vendorRoutes = new Hono();

vendorRoutes.use("*", authenticate());
vendorRoutes.use("*", requireRole("vendor"));

// Vendor Shop Profile
vendorRoutes.get("/shop", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Vendor shop profile not found");

  const res = await query(`SELECT * FROM shops WHERE id = $1`, [shopId]);
  if (res.rows.length === 0) throw new NotFoundError("Shop not found");
  return c.json({ shop: res.rows[0] });
});

vendorRoutes.put("/shop", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Vendor shop profile not found");

  const { name, tagline, description, logoUrl, bannerUrl, bankName, bankAccountLast4, bankIfscCode } =
    await c.req.json();

  const res = await query(
    `UPDATE shops
     SET name = COALESCE($1, name),
         tagline = COALESCE($2, tagline),
         description = COALESCE($3, description),
         logo_url = COALESCE($4, logo_url),
         banner_url = COALESCE($5, banner_url),
         bank_name = COALESCE($6, bank_name),
         bank_account_last4 = COALESCE($7, bank_account_last4),
         bank_ifsc_code = COALESCE($8, bank_ifsc_code),
         updated_at = NOW()
     WHERE id = $9
     RETURNING *`,
    [name, tagline, description, logoUrl, bannerUrl, bankName, bankAccountLast4, bankIfscCode, shopId]
  );

  return c.json({ shop: res.rows[0] });
});

// Dashboard Metrics
vendorRoutes.get("/dashboard", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Shop not found");

  const statsRes = await query<{
    total_sales_cents: string;
    pending_count: string;
    shipped_count: string;
    delivered_count: string;
  }>(
    `SELECT
       COALESCE(SUM(CASE WHEN status != 'cancelled' THEN vendor_payout_cents ELSE 0 END), 0)::text AS total_sales_cents,
       COUNT(CASE WHEN status IN ('placed', 'accepted', 'packed') THEN 1 END)::text AS pending_count,
       COUNT(CASE WHEN status = 'shipped' THEN 1 END)::text AS shipped_count,
       COUNT(CASE WHEN status = 'delivered' THEN 1 END)::text AS delivered_count
     FROM shipments
     WHERE shop_id = $1`,
    [shopId]
  );

  const prodCountRes = await query<{ count: string }>(
    `SELECT COUNT(*)::text as count FROM products WHERE shop_id = $1`,
    [shopId]
  );

  const shopRes = await query<{ rating_avg: string; rating_count: number }>(
    `SELECT rating_avg, rating_count FROM shops WHERE id = $1`,
    [shopId]
  );

  const account = await ledgerService.getOrCreateAccount("vendor", shopId, "INR");

  return c.json({
    metrics: {
      totalRevenueCents: parseInt(statsRes.rows[0]?.total_sales_cents || "0", 10),
      currentBalanceCents: account.balance_cents,
      pendingShipmentsCount: parseInt(statsRes.rows[0]?.pending_count || "0", 10),
      shippedShipmentsCount: parseInt(statsRes.rows[0]?.shipped_count || "0", 10),
      deliveredShipmentsCount: parseInt(statsRes.rows[0]?.delivered_count || "0", 10),
      totalProductsCount: parseInt(prodCountRes.rows[0]?.count || "0", 10),
      ratingAvg: parseFloat(shopRes.rows[0]?.rating_avg || "5.0"),
      ratingCount: shopRes.rows[0]?.rating_count || 0,
    },
  });
});

// Products
vendorRoutes.get("/products", async (c) => {
  const shopId = c.get("shopId");
  const limit = c.req.query("limit") ? parseInt(c.req.query("limit")!, 10) : 50;
  const offset = c.req.query("offset") ? parseInt(c.req.query("offset")!, 10) : 0;

  const result = await catalogService.listProducts({
    shopId,
    limit,
    offset,
  });

  return c.json(result);
});

vendorRoutes.post("/products", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Shop not found");

  const body = await c.req.json();
  const product = await catalogService.createProduct(shopId, body);
  return c.json({ product }, 201);
});

// Shipments
vendorRoutes.get("/shipments", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Shop not found");

  const status = c.req.query("status") as any;
  const limit = c.req.query("limit") ? parseInt(c.req.query("limit")!, 10) : 20;
  const offset = c.req.query("offset") ? parseInt(c.req.query("offset")!, 10) : 0;

  const result = await fulfillmentService.listVendorShipments(shopId, {
    status,
    limit,
    offset,
  });

  return c.json(result);
});

vendorRoutes.get("/shipments/:id", async (c) => {
  const shopId = c.get("shopId");
  const shipmentId = c.req.param("id");
  const shipment = await fulfillmentService.getShipmentDetail(shipmentId, shopId);
  return c.json({ shipment });
});

// Fulfillment transitions
vendorRoutes.post("/shipments/:id/accept", async (c) => {
  const shopId = c.get("shopId");
  const shipmentId = c.req.param("id");
  const result = await fulfillmentService.acceptShipment(shipmentId, shopId!);
  return c.json(result);
});

vendorRoutes.post("/shipments/:id/pack", async (c) => {
  const shopId = c.get("shopId");
  const shipmentId = c.req.param("id");
  const result = await fulfillmentService.packShipment(shipmentId, shopId!);
  return c.json(result);
});

vendorRoutes.post("/shipments/:id/ship", async (c) => {
  const shopId = c.get("shopId");
  const shipmentId = c.req.param("id");
  const { courierName, trackingNumber } = await c.req.json().catch(() => ({}));
  const result = await fulfillmentService.shipShipment(
    shipmentId,
    shopId!,
    courierName,
    trackingNumber
  );
  return c.json(result);
});

vendorRoutes.post("/shipments/:id/deliver", async (c) => {
  const shopId = c.get("shopId");
  const shipmentId = c.req.param("id");
  const result = await fulfillmentService.deliverShipment(shipmentId, shopId);
  return c.json(result);
});

// Ledger & Settlements
vendorRoutes.get("/ledger", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Shop not found");

  const ledger = await ledgerService.getVendorLedger(shopId);
  return c.json(ledger);
});

vendorRoutes.post("/settlements/request", async (c) => {
  const shopId = c.get("shopId");
  if (!shopId) throw new NotFoundError("Shop not found");

  const batch = await ledgerService.createSettlementBatch(shopId);
  return c.json({ settlement: batch }, 201);
});
