/** Server-Sent Events (SSE) stream for CareClinic real-time notifications. */

import { Hono } from "hono";
import type { AppEnv } from "../auth/middleware.ts";

export const streamRoutes = new Hono<AppEnv>();

interface SSEClient {
  id: string;
  controller: ReadableStreamDefaultController;
}

const clients = new Set<SSEClient>();

export function broadcastEvent(event: string, data: unknown) {
  const payload = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  const encoded = new TextEncoder().encode(payload);

  for (const client of clients) {
    try {
      client.controller.enqueue(encoded);
    } catch {
      clients.delete(client);
    }
  }
}

streamRoutes.get("/api/stream", (c) => {
  let clientRef: SSEClient | null = null;

  const stream = new ReadableStream({
    start(controller) {
      clientRef = {
        id: Math.random().toString(36).slice(2),
        controller,
      };
      clients.add(clientRef);

      // Initial connection ping
      const initial = new TextEncoder().encode(
        `: keepalive\nevent: connected\ndata: {"status":"connected","timestamp":"${new Date().toISOString()}"}\n\n`
      );
      controller.enqueue(initial);
    },
    cancel() {
      if (clientRef) {
        clients.delete(clientRef);
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
});
