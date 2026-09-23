/** Vendor shipment fulfillment lifecycle and customer returns management. */

import { query, withTransaction } from "../db.ts";
import { BadRequestError, NotFoundError, ForbiddenError } from "../lib/errors.ts";
import { assertValidTransition, type ShipmentStatus } from "../lib/shipment-state.ts";
import { logisticsProvider } from "../providers/logistics.ts";
import { notificationProvider } from "../providers/notifications.ts";
import { ledgerService } from "./ledger.ts";
import { eventBus } from "../lib/events.ts";

export class FulfillmentService {
  /** Lists shipments for a specific vendor shop. */
  async listVendorShipments(
    shopId: string,
    filters: { status?: ShipmentStatus; limit?: number; offset?: number } = {}
  ): Promise<{ shipments: any[]; total: number }> {
    const conditions = ["s.shop_id = $1"];
    const params: any[] = [shopId];
    let pIdx = 2;

    if (filters.status) {
      conditions.push(`s.status = $${pIdx++}`);
      params.push(filters.status);
    }

    const whereClause = `WHERE ${conditions.join(" AND ")}`;

    const countRes = await query<{ count: string }>(
      `SELECT COUNT(*)::text as count FROM shipments s ${whereClause}`,
      params
    );
    const total = parseInt(countRes.rows[0]?.count || "0", 10);

    const limit = Math.min(Math.max(filters.limit || 20, 1), 100);
    const offset = Math.max(filters.offset || 0, 0);

    const dataRes = await query(
      `SELECT s.*,
              o.order_number, o.created_at AS order_created_at,
              o.shipping_address_json,
              u.name AS customer_name, u.email AS customer_email,
              (SELECT COUNT(*) FROM shipment_items si WHERE si.shipment_id = s.id) AS item_count
       FROM shipments s
       JOIN orders o ON o.id = s.order_id
       JOIN users u ON u.id = o.user_id
       ${whereClause}
       ORDER BY s.created_at DESC
       LIMIT $${pIdx++} OFFSET $${pIdx++}`,
      [...params, limit, offset]
    );

    return { shipments: dataRes.rows, total };
  }

  /** Gets full shipment details including ordered items and tracking timeline. */
  async getShipmentDetail(shipmentId: string, shopId?: string): Promise<any> {
    const params: any[] = [shipmentId];
    let sql = `SELECT s.*, o.order_number, o.shipping_address_json,
                      u.name AS customer_name, u.email AS customer_email, u.phone AS customer_phone,
                      sh.name AS shop_name, sh.slug AS shop_slug
               FROM shipments s
               JOIN orders o ON o.id = s.order_id
               JOIN users u ON u.id = o.user_id
               JOIN shops sh ON sh.id = s.shop_id
               WHERE s.id = $1`;

    if (shopId) {
      sql += ` AND s.shop_id = $2`;
      params.push(shopId);
    }

    const shipRes = await query(sql, params);
    if (shipRes.rows.length === 0) {
      throw new NotFoundError(`Shipment '${shipmentId}' not found`);
    }

    const shipment = shipRes.rows[0];

    const itemsRes = await query(
      `SELECT * FROM shipment_items WHERE shipment_id = $1 ORDER BY total_price_cents DESC`,
      [shipment.id]
    );
    const trackingRes = await query(
      `SELECT * FROM shipment_tracking_events WHERE shipment_id = $1 ORDER BY occurred_at ASC`,
      [shipment.id]
    );

    shipment.items = itemsRes.rows;
    shipment.tracking = trackingRes.rows;

    return shipment;
  }

  /** Vendor confirms/accepts the order. */
  async acceptShipment(shipmentId: string, shopId: string): Promise<any> {
    return withTransaction(async (client) => {
      const shipRes = await client.query(
        `SELECT s.*, o.user_id FROM shipments s JOIN orders o ON o.id = s.order_id WHERE s.id = $1 AND s.shop_id = $2 FOR UPDATE`,
        [shipmentId, shopId]
      );
      if (shipRes.rows.length === 0) {
        throw new NotFoundError("Shipment not found or unauthorized");
      }

      const shipment = shipRes.rows[0];
      assertValidTransition(shipment.status, "accepted");

      await client.query(
        `UPDATE shipments SET status = 'accepted', accepted_at = NOW(), updated_at = NOW() WHERE id = $1`,
        [shipmentId]
      );

      await client.query(
        `INSERT INTO shipment_tracking_events (shipment_id, status, location, message)
         VALUES ($1, 'accepted', 'Seller Hub', 'Seller has confirmed the order and started processing')`,
        [shipmentId]
      );

      await notificationProvider.send({
        userId: shipment.user_id,
        title: `Order Accepted (${shipment.shipment_number})`,
        message: "The seller has accepted your items and started packing.",
        link: `/orders/${shipment.order_id}`,
      });

      return { success: true, status: "accepted" };
    });
  }

  /** Vendor packs the items and generates packing label. */
  async packShipment(shipmentId: string, shopId: string): Promise<any> {
    return withTransaction(async (client) => {
      const shipRes = await client.query(
        `SELECT s.*, o.user_id FROM shipments s JOIN orders o ON o.id = s.order_id WHERE s.id = $1 AND s.shop_id = $2 FOR UPDATE`,
        [shipmentId, shopId]
      );
      if (shipRes.rows.length === 0) {
        throw new NotFoundError("Shipment not found or unauthorized");
      }

      const shipment = shipRes.rows[0];
      assertValidTransition(shipment.status, "packed");

      await client.query(
        `UPDATE shipments SET status = 'packed', packed_at = NOW(), updated_at = NOW() WHERE id = $1`,
        [shipmentId]
      );

      await client.query(
        `INSERT INTO shipment_tracking_events (shipment_id, status, location, message)
         VALUES ($1, 'packed', 'Seller Warehouse', 'Package sealed in tamper-evident box and ready for courier pickup')`,
        [shipmentId]
      );

      return { success: true, status: "packed" };
    });
  }

  /** Vendor dispatches package with courier and tracking number. */
  async shipShipment(
    shipmentId: string,
    shopId: string,
    courierName?: string,
    trackingNumber?: string
  ): Promise<any> {
    const courierInfo = logisticsProvider.generateTrackingNumber("delhivery");
    const finalCourier = courierName || courierInfo.courierName;
    const finalTracking = trackingNumber || courierInfo.trackingNumber;

    return withTransaction(async (client) => {
      const shipRes = await client.query(
        `SELECT s.*, o.user_id, o.shipping_address_json FROM shipments s JOIN orders o ON o.id = s.order_id WHERE s.id = $1 AND s.shop_id = $2 FOR UPDATE`,
        [shipmentId, shopId]
      );
      if (shipRes.rows.length === 0) {
        throw new NotFoundError("Shipment not found or unauthorized");
      }

      const shipment = shipRes.rows[0];
      assertValidTransition(shipment.status, "shipped");

      // Deduct reserved stock and permanent stock on variants
      const itemsRes = await client.query<{ variant_id: string; quantity: number }>(
        `SELECT variant_id, quantity FROM shipment_items WHERE shipment_id = $1`,
        [shipmentId]
      );

      for (const it of itemsRes.rows) {
        await client.query(
          `UPDATE product_variants
           SET stock_quantity = stock_quantity - $1,
               reserved_quantity = reserved_quantity - $1,
               updated_at = NOW()
           WHERE id = $2`,
          [it.quantity, it.variant_id]
        );

        await client.query(
          `INSERT INTO inventory_logs (variant_id, delta_quantity, balance_after, reason, reference_id, notes)
           SELECT id, -$1, stock_quantity, 'order_fulfilled', $2, 'Dispatched to courier'
           FROM product_variants WHERE id = $3`,
          [it.quantity, shipment.id, it.variant_id]
        );
      }

      await client.query(
        `UPDATE shipments
         SET status = 'shipped', courier_name = $1, tracking_number = $2,
             shipped_at = NOW(), updated_at = NOW()
         WHERE id = $3`,
        [finalCourier, finalTracking, shipmentId]
      );

      const destCity = shipment.shipping_address_json?.city || "Destination";
      await client.query(
        `INSERT INTO shipment_tracking_events (shipment_id, status, location, message)
         VALUES ($1, 'shipped', 'Express Hub', $2)`,
        [shipmentId, `Picked up by ${finalCourier} (${finalTracking}) and in transit towards ${destCity}`]
      );

      // Check if parent order status should become partially_shipped
      await client.query(
        `UPDATE orders SET status = 'partially_shipped', updated_at = NOW() WHERE id = $1 AND status = 'processing'`,
        [shipment.order_id]
      );

      await notificationProvider.send({
        userId: shipment.user_id,
        title: `Package In Transit (${finalTracking})`,
        message: `Your package from the seller has been handed over to ${finalCourier}.`,
        link: `/orders/${shipment.order_id}`,
      });

      return {
        success: true,
        status: "shipped",
        courierName: finalCourier,
        trackingNumber: finalTracking,
      };
    });
  }

  /** Marks shipment as delivered, settles ledger entries, and finalizes order. */
  async deliverShipment(shipmentId: string, shopId?: string): Promise<any> {
    return withTransaction(async (client) => {
      const params: any[] = [shipmentId];
      let sql = `SELECT s.*, o.user_id, o.shipping_address_json FROM shipments s JOIN orders o ON o.id = s.order_id WHERE s.id = $1 FOR UPDATE`;
      if (shopId) {
        sql = `SELECT s.*, o.user_id, o.shipping_address_json FROM shipments s JOIN orders o ON o.id = s.order_id WHERE s.id = $1 AND s.shop_id = $2 FOR UPDATE`;
        params.push(shopId);
      }

      const shipRes = await client.query(sql, params);
      if (shipRes.rows.length === 0) {
        throw new NotFoundError("Shipment not found or unauthorized");
      }

      const shipment = shipRes.rows[0];
      assertValidTransition(shipment.status, "delivered");

      await client.query(
        `UPDATE shipments SET status = 'delivered', delivered_at = NOW(), updated_at = NOW() WHERE id = $1`,
        [shipmentId]
      );

      const destCity = shipment.shipping_address_json?.city || "Customer Address";
      await client.query(
        `INSERT INTO shipment_tracking_events (shipment_id, status, location, message)
         VALUES ($1, 'delivered', $2, 'Package delivered successfully. Recipient signature recorded')`,
        [shipmentId, destCity]
      );

      // Distribute funds in double-entry ledger
      await ledgerService.recordShipmentFulfillment(
        shipment.id,
        shipment.shop_id,
        parseInt(shipment.subtotal_cents, 10),
        parseInt(shipment.commission_cents, 10),
        parseInt(shipment.vendor_payout_cents, 10),
        client
      );

      // Check if all shipments in parent order are delivered
      const remainingRes = await client.query<{ count: string }>(
        `SELECT COUNT(*)::text as count FROM shipments WHERE order_id = $1 AND status != 'delivered' AND status != 'cancelled'`,
        [shipment.order_id]
      );
      const remaining = parseInt(remainingRes.rows[0]?.count || "0", 10);
      if (remaining === 0) {
        await client.query(
          `UPDATE orders SET status = 'completed', updated_at = NOW() WHERE id = $1`,
          [shipment.order_id]
        );
      }

      await notificationProvider.send({
        userId: shipment.user_id,
        title: `Package Delivered! (${shipment.shipment_number})`,
        message: "Your package has been delivered. Tap to view receipt and write a review.",
        link: `/orders/${shipment.order_id}`,
      });

      return { success: true, status: "delivered" };
    });
  }

  /** Customer submits return request for a delivered shipment. */
  async requestReturn(params: {
    shipmentId: string;
    userId: string;
    reason: string;
  }): Promise<any> {
    const shipRes = await query(
      `SELECT s.*, o.user_id FROM shipments s JOIN orders o ON o.id = s.order_id WHERE s.id = $1`,
      [params.shipmentId]
    );

    if (shipRes.rows.length === 0) {
      throw new NotFoundError("Shipment not found");
    }

    const shipment = shipRes.rows[0];
    if (shipment.user_id !== params.userId) {
      throw new ForbiddenError("You can only request returns for your own orders");
    }

    if (shipment.status !== "delivered") {
      throw new BadRequestError("Only delivered shipments can be requested for return");
    }

    const insRes = await query(
      `INSERT INTO order_returns (
         shipment_id, order_id, user_id, shop_id, reason, status, refund_amount_cents
       )
       VALUES ($1, $2, $3, $4, $5, 'requested', $6)
       RETURNING *`,
      [
        shipment.id,
        shipment.order_id,
        params.userId,
        shipment.shop_id,
        params.reason,
        shipment.subtotal_cents,
      ]
    );

    return insRes.rows[0];
  }
}

export const fulfillmentService = new FulfillmentService();
