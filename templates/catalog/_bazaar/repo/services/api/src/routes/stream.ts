/** Real-time Server-Sent Events (SSE) stream for shopper and vendor live updates. */

import { Hono } from "hono";
import { streamSSE } from "hono/streaming";
import { eventBus, type BazaarEvent } from "../lib/events.ts";
import { authenticate } from "../auth/middleware.ts";

export const streamRoutes = new Hono();

// Stream endpoint with optional auth
streamRoutes.get("/stream", authenticate({ optional: true }), async (c) => {
  const user = c.get("user");
  const shopId = c.get("shopId");

  return streamSSE(c, async (stream) => {
    // Send initial connected heartbeat
    await stream.writeSSE({
      event: "connected",
      data: JSON.stringify({
        status: "online",
        userId: user?.userId || null,
        shopId: shopId || null,
        serverTime: new Date().toISOString(),
      }),
    });

    const onEvent = async (event: BazaarEvent) => {
      // Filter if user or shop specific
      if (
        event.recipientUserId &&
        user?.userId &&
        event.recipientUserId !== user.userId
      ) {
        return;
      }
      if (
        event.recipientShopId &&
        shopId &&
        event.recipientShopId !== shopId
      ) {
        return;
      }

      await stream.writeSSE({
        event: event.type,
        data: JSON.stringify(event),
      });
    };

    eventBus.on("event", onEvent);

    // Keepalive ping interval
    const pingInterval = setInterval(async () => {
      try {
        await stream.writeSSE({
          event: "ping",
          data: JSON.stringify({ time: new Date().toISOString() }),
        });
      } catch {
        clearInterval(pingInterval);
      }
    }, 25000);

    stream.onAbort(() => {
      clearInterval(pingInterval);
      eventBus.off("event", onEvent);
    });
  });
});
