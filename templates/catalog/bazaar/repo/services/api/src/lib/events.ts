/** Real-time event broadcaster for Bazaar Server-Sent Events (SSE). */

import { EventEmitter } from "node:events";

export interface BazaarEvent {
  type:
    | "order.created"
    | "shipment.updated"
    | "inventory.low"
    | "return.requested"
    | "settlement.processed"
    | "order.cancelled";
  recipientUserId?: string;
  recipientShopId?: string;
  payload: Record<string, any>;
  timestamp: string;
}

class EventBus extends EventEmitter {
  broadcast(event: BazaarEvent) {
    this.emit("event", event);
    if (event.recipientUserId) {
      this.emit(`user:${event.recipientUserId}`, event);
    }
    if (event.recipientShopId) {
      this.emit(`shop:${event.recipientShopId}`, event);
    }
  }
}

export const eventBus = new EventBus();
