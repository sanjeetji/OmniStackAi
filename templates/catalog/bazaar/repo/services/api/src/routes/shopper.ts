/** Shopper authenticated endpoints: cart, checkout, addresses, orders, and returns. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { authenticate, requireRole } from "../auth/middleware.ts";
import { orderService } from "../services/orders.ts";
import { fulfillmentService } from "../services/fulfillment.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";

export const shopperRoutes = new Hono();

// Apply auth middleware to all shopper routes
shopperRoutes.use("*", authenticate());

// Profile
shopperRoutes.get("/me", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT id, email, role, name, phone, avatar_url, created_at FROM users WHERE id = $1`,
    [user.userId]
  );
  if (res.rows.length === 0) throw new NotFoundError("User not found");
  return c.json({ user: res.rows[0] });
});

// Addresses
shopperRoutes.get("/addresses", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT * FROM user_addresses WHERE user_id = $1 ORDER BY is_default DESC, created_at DESC`,
    [user.userId]
  );
  return c.json({ addresses: res.rows });
});

shopperRoutes.post("/addresses", async (c) => {
  const user = c.get("user");
  const body = await c.req.json();
  const {
    label = "home",
    recipientName,
    phone,
    street,
    city,
    state,
    postalCode,
    country = "India",
    isDefault = false,
  } = body;

  if (!recipientName || !phone || !street || !city || !state || !postalCode) {
    throw new BadRequestError("All address fields are required");
  }

  if (isDefault) {
    await query(`UPDATE user_addresses SET is_default = FALSE WHERE user_id = $1`, [user.userId]);
  }

  const res = await query(
    `INSERT INTO user_addresses (
       user_id, label, recipient_name, phone, street, city, state, postal_code, country, is_default
     )
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
     RETURNING *`,
    [user.userId, label, recipientName, phone, street, city, state, postalCode, country, isDefault]
  );

  return c.json({ address: res.rows[0] }, 201);
});

// Cart
shopperRoutes.get("/cart", async (c) => {
  const user = c.get("user");
  const cart = await orderService.getOrCreateCart(user.userId);
  return c.json({ cart });
});

shopperRoutes.post("/cart/items", async (c) => {
  const user = c.get("user");
  const body = await c.req.json();
  const { variantId, quantity = 1 } = body;
  if (!variantId) throw new BadRequestError("variantId is required");

  const cart = await orderService.addToCart({
    userId: user.userId,
    variantId,
    quantity,
  });

  return c.json({ cart });
});

shopperRoutes.put("/cart/items/:id", async (c) => {
  const itemId = c.req.param("id");
  const { quantity } = await c.req.json();
  await orderService.updateCartItem(itemId, quantity);
  const user = c.get("user");
  const cart = await orderService.getOrCreateCart(user.userId);
  return c.json({ cart });
});

shopperRoutes.delete("/cart/items/:id", async (c) => {
  const itemId = c.req.param("id");
  await orderService.removeCartItem(itemId);
  const user = c.get("user");
  const cart = await orderService.getOrCreateCart(user.userId);
  return c.json({ cart });
});

// Checkout
shopperRoutes.post("/checkout", async (c) => {
  const user = c.get("user");
  const body = await c.req.json();
  const { shippingAddress, billingAddress, paymentMethod = "mock_card", couponCode, notes } = body;

  if (!shippingAddress) {
    throw new BadRequestError("shippingAddress is required");
  }

  const order = await orderService.checkout({
    userId: user.userId,
    shippingAddress,
    billingAddress,
    paymentMethod,
    couponCode,
    notes,
  });

  return c.json({ order }, 201);
});

// Orders
shopperRoutes.get("/orders", async (c) => {
  const user = c.get("user");
  const limit = c.req.query("limit") ? parseInt(c.req.query("limit")!, 10) : 20;
  const offset = c.req.query("offset") ? parseInt(c.req.query("offset")!, 10) : 0;
  const orders = await orderService.listUserOrders(user.userId, limit, offset);
  return c.json({ orders });
});

shopperRoutes.get("/orders/:id", async (c) => {
  const user = c.get("user");
  const orderId = c.req.param("id");
  const order = await orderService.getOrderById(orderId, user.userId);
  return c.json({ order });
});

// Return Request
shopperRoutes.post("/shipments/:id/return", async (c) => {
  const user = c.get("user");
  const shipmentId = c.req.param("id");
  const { reason } = await c.req.json();

  if (!reason) {
    throw new BadRequestError("Return reason is required");
  }

  const result = await fulfillmentService.requestReturn({
    shipmentId,
    userId: user.userId,
    reason,
  });

  return c.json({ return: result }, 201);
});

// Submit Product Review
shopperRoutes.post("/reviews", async (c) => {
  const user = c.get("user");
  const { productId, rating, title, comment } = await c.req.json();

  if (!productId || !rating || !comment) {
    throw new BadRequestError("productId, rating (1-5), and comment are required");
  }

  const prodRes = await query<{ shop_id: string }>(
    `SELECT shop_id FROM products WHERE id = $1`,
    [productId]
  );
  if (prodRes.rows.length === 0) {
    throw new NotFoundError("Product not found");
  }
  const shopId = prodRes.rows[0].shop_id;

  const revRes = await query(
    `INSERT INTO reviews (product_id, shop_id, user_id, rating, title, comment, verified_purchase)
     VALUES ($1, $2, $3, $4, $5, $6, TRUE)
     ON CONFLICT (product_id, user_id)
     DO UPDATE SET rating = EXCLUDED.rating, title = EXCLUDED.title, comment = EXCLUDED.comment, updated_at = NOW()
     RETURNING *`,
    [productId, shopId, user.userId, rating, title || null, comment]
  );

  // Update product average rating
  await query(
    `UPDATE products
     SET rating_avg = (SELECT ROUND(AVG(rating), 2) FROM reviews WHERE product_id = $1),
         rating_count = (SELECT COUNT(*) FROM reviews WHERE product_id = $1)
     WHERE id = $1`,
    [productId]
  );

  return c.json({ review: revRes.rows[0] });
});

// Notifications
shopperRoutes.get("/notifications", async (c) => {
  const user = c.get("user");
  const res = await query(
    `SELECT * FROM notifications WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50`,
    [user.userId]
  );
  return c.json({ notifications: res.rows });
});

// The reviews this shopper has written, and the delivered items they could still review.
shopperRoutes.get("/reviews", async (c) => {
  const user = c.get("user");

  const mine = await query(
    `SELECT r.*, p.title AS product_title, p.slug AS product_slug, s.name AS shop_name, s.slug AS shop_slug
       FROM reviews r
       JOIN products p ON p.id = r.product_id
       JOIN shops s ON s.id = r.shop_id
      WHERE r.user_id = $1
      ORDER BY r.created_at DESC`,
    [user.userId]
  );

  // Anything delivered to them that they have not reviewed yet.
  const awaiting = await query(
    `SELECT DISTINCT p.id AS product_id, p.title AS product_title, p.slug AS product_slug,
            s.name AS shop_name, sh.delivered_at
       FROM shipments sh
       JOIN orders o ON o.id = sh.order_id
       JOIN shipment_items si ON si.shipment_id = sh.id
       JOIN products p ON p.id = si.product_id
       JOIN shops s ON s.id = p.shop_id
      WHERE o.user_id = $1
        AND sh.status = 'delivered'
        AND NOT EXISTS (
          SELECT 1 FROM reviews r WHERE r.product_id = p.id AND r.user_id = $1
        )
      ORDER BY sh.delivered_at DESC NULLS LAST
      LIMIT 20`,
    [user.userId]
  );

  return c.json({ reviews: mine.rows, awaitingReview: awaiting.rows });
});
