/** In-app and real-time notification dispatcher for Bazaar. */

import { query } from "../db.ts";
import { eventBus } from "../lib/events.ts";

export interface CreateNotificationParams {
  userId: string;
  title: string;
  message: string;
  link?: string;
  shopId?: string;
}

export class NotificationProvider {
  async send(params: CreateNotificationParams): Promise<void> {
    try {
      await query(
        `INSERT INTO notifications (user_id, title, message, link)
         VALUES ($1, $2, $3, $4)`,
        [params.userId, params.title, params.message, params.link || null]
      );

      // Broadcast real-time SSE event
      eventBus.broadcast({
        type: "shipment.updated",
        recipientUserId: params.userId,
        recipientShopId: params.shopId,
        payload: {
          title: params.title,
          message: params.message,
          link: params.link,
        },
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      console.error("[NotificationProvider] Failed to persist notification:", err);
    }
  }
}

export const notificationProvider = new NotificationProvider();
