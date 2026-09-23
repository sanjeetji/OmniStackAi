/** Order placement, multi-vendor split shipment creation, cart management, and inventory reservation. */

import { randomUUID } from "node:crypto";
import { query, withTransaction } from "../db.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";
import { calculateCommission } from "../lib/money.ts";
import { ledgerService } from "./ledger.ts";
import { paymentProvider } from "../providers/payments.ts";
import { notificationProvider } from "../providers/notifications.ts";
import { eventBus } from "../lib/events.ts";

export interface CartItem {
  id: string;
  cart_id: string;
  variant_id: string;
  shop_id: string;
  quantity: number;
  price_cents: number;
  sku: string;
  product_title: string;
  variant_title: string;
  option_color?: string;
  option_size?: string;
  image_url?: string;
  shop_name: string;
  shop_slug: string;
}

export interface Cart {
  id: string;
  user_id: string | null;
  session_token: string | null;
  items: CartItem[];
  subtotal_cents: number;
}

export class OrderService {
  /** Gets an existing cart or creates a new one for user/session. */
  async getOrCreateCart(userId?: string, sessionToken?: string): Promise<Cart> {
    if (!userId && !sessionToken) {
      throw new BadRequestError("Either userId or sessionToken must be provided");
    }

    let cartRes = userId
      ? await query<{ id: string; user_id: string | null; session_token: string | null }>(
          `SELECT id, user_id, session_token FROM carts WHERE user_id = $1 LIMIT 1`,
          [userId]
        )
      : await query<{ id: string; user_id: string | null; session_token: string | null }>(
          `SELECT id, user_id, session_token FROM carts WHERE session_token = $1 LIMIT 1`,
          [sessionToken]
        );

    let cart = cartRes.rows[0];
    if (!cart) {
      const insRes = await query<{ id: string; user_id: string | null; session_token: string | null }>(
        `INSERT INTO carts (user_id, session_token)
         VALUES ($1, $2)
         RETURNING id, user_id, session_token`,
        [userId || null, sessionToken || null]
      );
      cart = insRes.rows[0];
    }

    // Fetch items with product/variant details
    const itemsRes = await query<CartItem>(
      `SELECT ci.id, ci.cart_id, ci.variant_id, ci.shop_id, ci.quantity, ci.price_cents,
              pv.sku, p.title AS product_title, pv.title AS variant_title,
              pv.option_color, pv.option_size, pv.image_url,
              s.name AS shop_name, s.slug AS shop_slug
       FROM cart_items ci
       JOIN product_variants pv ON pv.id = ci.variant_id
       JOIN products p ON p.id = pv.product_id
       JOIN shops s ON s.id = ci.shop_id
       WHERE ci.cart_id = $1
       ORDER BY ci.created_at ASC`,
      [cart.id]
    );

    let subtotal = 0;
    for (const it of itemsRes.rows) {
      subtotal += Number(it.price_cents) * it.quantity;
    }

    return {
      id: cart.id,
      user_id: cart.user_id,
      session_token: cart.session_token,
      items: itemsRes.rows,
      subtotal_cents: subtotal,
    };
  }

  /** Adds or increments an item in the cart. */
  async addToCart(params: {
    userId?: string;
    sessionToken?: string;
    variantId: string;
    quantity: number;
  }): Promise<Cart> {
    if (params.quantity <= 0) {
      throw new BadRequestError("Quantity must be greater than zero");
    }

    const varRes = await query<{
      id: string;
      product_id: string;
      price_cents: string;
      stock_quantity: number;
      reserved_quantity: number;
      shop_id: string;
    }>(
      `SELECT pv.id, pv.product_id, pv.price_cents, pv.stock_quantity, pv.reserved_quantity, p.shop_id
       FROM product_variants pv
       JOIN products p ON p.id = pv.product_id
       WHERE pv.id = $1 AND pv.is_active = TRUE`,
      [params.variantId]
    );

    if (varRes.rows.length === 0) {
      throw new NotFoundError("Product variant not found or inactive");
    }

    const variant = varRes.rows[0];
    const available = variant.stock_quantity - variant.reserved_quantity;
    if (available < params.quantity) {
      throw new BadRequestError(
        `Insufficient stock: only ${Math.max(0, available)} units available`
      );
    }

    const cart = await this.getOrCreateCart(params.userId, params.sessionToken);

    await query(
      `INSERT INTO cart_items (cart_id, variant_id, shop_id, quantity, price_cents)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (cart_id, variant_id)
       DO UPDATE SET quantity = cart_items.quantity + EXCLUDED.quantity`,
      [cart.id, variant.id, variant.shop_id, params.quantity, variant.price_cents]
    );

    return this.getOrCreateCart(params.userId, params.sessionToken);
  }

  /** Updates quantity of a cart item. */
  async updateCartItem(cartItemId: string, quantity: number): Promise<void> {
    if (quantity <= 0) {
      await query(`DELETE FROM cart_items WHERE id = $1`, [cartItemId]);
      return;
    }

    await query(`UPDATE cart_items SET quantity = $1 WHERE id = $2`, [quantity, cartItemId]);
  }

  /** Removes a cart item. */
  async removeCartItem(cartItemId: string): Promise<void> {
    await query(`DELETE FROM cart_items WHERE id = $1`, [cartItemId]);
  }

  /** Validates and applies a promo coupon. */
  async validateCoupon(code: string, subtotalCents: number): Promise<{
    valid: boolean;
    discountCents: number;
    description?: string;
  }> {
    const res = await query<{
      code: string;
      description: string;
      discount_type: "percentage" | "flat";
      discount_value: number;
      min_order_cents: string;
      max_discount_cents: string | null;
      is_active: boolean;
      expires_at: string | null;
    }>(
      `SELECT code, description, discount_type, discount_value, min_order_cents, max_discount_cents, is_active, expires_at
       FROM coupons
       WHERE UPPER(code) = UPPER($1) AND is_active = TRUE`,
      [code.trim()]
    );

    if (res.rows.length === 0) {
      return { valid: false, discountCents: 0 };
    }

    const coupon = res.rows[0];
    if (coupon.expires_at && new Date(coupon.expires_at) < new Date()) {
      return { valid: false, discountCents: 0 };
    }

    const minOrder = parseInt(coupon.min_order_cents, 10);
    if (subtotalCents < minOrder) {
      return { valid: false, discountCents: 0 };
    }

    let discount = 0;
    if (coupon.discount_type === "percentage") {
      discount = Math.round((subtotalCents * coupon.discount_value) / 100);
    } else {
      discount = coupon.discount_value;
    }

    if (coupon.max_discount_cents) {
      const maxDiscount = parseInt(coupon.max_discount_cents, 10);
      discount = Math.min(discount, maxDiscount);
    }

    return {
      valid: true,
      discountCents: discount,
      description: coupon.description,
    };
  }

  /**
   * Checkout: Converts cart into parent Order, splits into per-vendor Shipments,
   * reserves variant inventories, and posts to double-entry ledger.
   */
  async checkout(params: {
    userId: string;
    shippingAddress: Record<string, any>;
    billingAddress?: Record<string, any>;
    paymentMethod: "mock_card" | "mock_upi" | "cod";
    couponCode?: string;
    notes?: string;
  }): Promise<any> {
    const cart = await this.getOrCreateCart(params.userId);
    if (cart.items.length === 0) {
      throw new BadRequestError("Cart is empty. Add products before checking out");
    }

    let discountCents = 0;
    if (params.couponCode) {
      const couponResult = await this.validateCoupon(params.couponCode, cart.subtotal_cents);
      if (couponResult.valid) {
        discountCents = couponResult.discountCents;
      }
    }

    const shippingCents = cart.subtotal_cents > 100000 ? 0 : 9900; // Free shipping over ₹1,000
    const taxCents = Math.round((cart.subtotal_cents * 5) / 100); // 5% GST
    const totalCents = Math.max(0, cart.subtotal_cents - discountCents + shippingCents + taxCents);

    const orderNumber = `BZ-${Date.now().toString(36).toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`;

    // Process payment via mock payment provider
    const payment = await paymentProvider.initiatePayment({
      orderNumber,
      amountCents: totalCents,
      method: params.paymentMethod,
    });

    return withTransaction(async (client) => {
      // 1. Create parent order
      const ordRes = await client.query(
        `INSERT INTO orders (
           order_number, user_id, status, total_cents, subtotal_cents,
           discount_cents, shipping_cents, tax_cents, shipping_address_json,
           billing_address_json, payment_method, payment_status, payment_reference,
           coupon_code, notes
         )
         VALUES ($1, $2, 'processing', $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
         RETURNING *`,
        [
          orderNumber,
          params.userId,
          totalCents,
          cart.subtotal_cents,
          discountCents,
          shippingCents,
          taxCents,
          JSON.stringify(params.shippingAddress),
          JSON.stringify(params.billingAddress || params.shippingAddress),
          params.paymentMethod,
          payment.status,
          payment.reference,
          params.couponCode || null,
          params.notes || null,
        ]
      );
      const order = ordRes.rows[0];

      // 2. Group cart items by vendor shop
      const shopGroups = new Map<string, CartItem[]>();
      for (const item of cart.items) {
        if (!shopGroups.has(item.shop_id)) {
          shopGroups.set(item.shop_id, []);
        }
        shopGroups.get(item.shop_id)!.push(item);
      }

      // Fetch shop commission basis points
      const shopIds = Array.from(shopGroups.keys());
      const shopInfoRes = await client.query<{
        id: string;
        name: string;
        user_id: string;
        commission_rate_basis_points: number;
      }>(
        `SELECT id, name, user_id, commission_rate_basis_points FROM shops WHERE id = ANY($1::uuid[])`,
        [shopIds]
      );
      const shopInfoMap = new Map(shopInfoRes.rows.map((s) => [s.id, s]));

      const shipments: any[] = [];

      // 3. Create per-vendor shipment sub-orders
      let shopCounter = 1;
      for (const [shopId, items] of shopGroups.entries()) {
        const shopInfo = shopInfoMap.get(shopId);
        const commissionRate = shopInfo?.commission_rate_basis_points ?? 1000;

        let shopSubtotal = 0;
        for (const it of items) {
          shopSubtotal += Number(it.price_cents) * it.quantity;
        }

        const { commissionCents, vendorPayoutCents } = calculateCommission(
          shopSubtotal,
          commissionRate
        );
        const shipmentNumber = `${orderNumber}-S${shopCounter++}`;

        const shipRes = await client.query(
          `INSERT INTO shipments (
             order_id, shop_id, shipment_number, status, subtotal_cents,
             commission_cents, vendor_payout_cents, shipping_fee_cents
           )
           VALUES ($1, $2, $3, 'placed', $4, $5, $6, 0)
           RETURNING *`,
          [
            order.id,
            shopId,
            shipmentNumber,
            shopSubtotal,
            commissionCents,
            vendorPayoutCents,
          ]
        );
        const shipment = shipRes.rows[0];

        // Insert shipment items and reserve inventory
        const shipmentItems: any[] = [];
        for (const it of items) {
          const itemTotal = Number(it.price_cents) * it.quantity;
          const sItemRes = await client.query(
            `INSERT INTO shipment_items (
               shipment_id, variant_id, product_id, product_title,
               variant_title, sku, unit_price_cents, quantity, total_price_cents, image_url
             )
             SELECT $1, $2, pv.product_id, $3, $4, $5, $6, $7, $8, $9
             FROM product_variants pv WHERE pv.id = $2
             RETURNING *`,
            [
              shipment.id,
              it.variant_id,
              it.product_title,
              it.variant_title,
              it.sku,
              it.price_cents,
              it.quantity,
              itemTotal,
              it.image_url || null,
            ]
          );
          shipmentItems.push(sItemRes.rows[0]);

          // Reserve inventory
          await client.query(
            `UPDATE product_variants
             SET reserved_quantity = reserved_quantity + $1, updated_at = NOW()
             WHERE id = $2`,
            [it.quantity, it.variant_id]
          );

          await client.query(
            `INSERT INTO inventory_logs (
               variant_id, delta_quantity, balance_after, reason, reference_id, notes
             )
             SELECT id, -$1, stock_quantity - reserved_quantity, 'order_reserve', $2, 'Reserved for order'
             FROM product_variants WHERE id = $3`,
            [it.quantity, order.id, it.variant_id]
          );
        }

        // Add initial tracking event
        await client.query(
          `INSERT INTO shipment_tracking_events (shipment_id, status, location, message)
           VALUES ($1, 'placed', 'Platform Order Center', 'Order placed and dispatched to vendor for packing')`,
          [shipment.id]
        );

        shipment.items = shipmentItems;
        shipments.push(shipment);

        // Notify vendor
        if (shopInfo?.user_id) {
          await notificationProvider.send({
            userId: shopInfo.user_id,
            shopId: shopId,
            title: `New Order Received (${shipmentNumber})`,
            message: `You received an order with ${items.length} items totaling ₹${(shopSubtotal / 100).toFixed(2)}.`,
            link: `/vendor/shipments/${shipment.id}`,
          });
        }
      }

      // 4. Record double-entry ledger transaction for order payment
      await ledgerService.recordOrderPayment(order.id, totalCents, client);

      // 5. Clear cart
      await client.query(`DELETE FROM cart_items WHERE cart_id = $1`, [cart.id]);

      // 6. Notify shopper
      await notificationProvider.send({
        userId: params.userId,
        title: `Order Confirmed: ${orderNumber}`,
        message: `Your order of ₹${(totalCents / 100).toFixed(2)} across ${shipments.length} seller(s) has been placed successfully.`,
        link: `/orders/${order.id}`,
      });

      // 7. Emit real-time event
      eventBus.broadcast({
        type: "order.created",
        recipientUserId: params.userId,
        payload: { orderNumber, totalCents, shipmentCount: shipments.length },
        timestamp: new Date().toISOString(),
      });

      order.shipments = shipments;
      return order;
    });
  }

  /** Gets complete order details with all sub-vendor shipments and items. */
  async getOrderById(orderId: string, userId?: string): Promise<any> {
    const params: any[] = [orderId];
    let sql = `SELECT * FROM orders WHERE id = $1`;
    if (userId) {
      sql += ` AND user_id = $2`;
      params.push(userId);
    }

    const ordRes = await query(sql, params);
    if (ordRes.rows.length === 0) {
      throw new NotFoundError(`Order '${orderId}' not found`);
    }

    const order = ordRes.rows[0];

    // Fetch shipments
    const shipRes = await query(
      `SELECT s.*, sh.name AS shop_name, sh.slug AS shop_slug, sh.logo_url AS shop_logo
       FROM shipments s
       JOIN shops sh ON sh.id = s.shop_id
       WHERE s.order_id = $1
       ORDER BY s.created_at ASC`,
      [order.id]
    );

    const shipmentIds = shipRes.rows.map((s) => s.id);
    if (shipmentIds.length > 0) {
      const itemsRes = await query(
        `SELECT * FROM shipment_items WHERE shipment_id = ANY($1::uuid[])`,
        [shipmentIds]
      );
      const trackingRes = await query(
        `SELECT * FROM shipment_tracking_events WHERE shipment_id = ANY($1::uuid[]) ORDER BY occurred_at ASC`,
        [shipmentIds]
      );

      const itemMap = new Map<string, any[]>();
      for (const it of itemsRes.rows) {
        if (!itemMap.has(it.shipment_id)) itemMap.set(it.shipment_id, []);
        itemMap.get(it.shipment_id)!.push(it);
      }

      const trackMap = new Map<string, any[]>();
      for (const tr of trackingRes.rows) {
        if (!trackMap.has(tr.shipment_id)) trackMap.set(tr.shipment_id, []);
        trackMap.get(tr.shipment_id)!.push(tr);
      }

      for (const ship of shipRes.rows) {
        ship.items = itemMap.get(ship.id) || [];
        ship.tracking = trackMap.get(ship.id) || [];
      }
    }

    order.shipments = shipRes.rows;
    return order;
  }

  /** Lists customer orders. */
  async listUserOrders(userId: string, limit = 20, offset = 0): Promise<any[]> {
    const res = await query(
      `SELECT o.*,
              (SELECT COUNT(*) FROM shipments s WHERE s.order_id = o.id) AS shipment_count
       FROM orders o
       WHERE o.user_id = $1
       ORDER BY o.created_at DESC
       LIMIT $2 OFFSET $3`,
      [userId, limit, offset]
    );

    return res.rows;
  }
}

export const orderService = new OrderService();
