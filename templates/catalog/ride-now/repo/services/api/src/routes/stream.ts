import { Hono } from "hono";
import { streamSSE } from "hono/streaming";
import { config } from "../config.ts";
import { verifyJwt } from "../auth/tokens.ts";
import { unauthorized } from "../lib/errors.ts";
import { hub, type RealtimeEvent } from "../lib/events.ts";

/**
 * GET /stream?token=<access token>: Server-Sent Events for the signed-in user. The token goes in
 * the query string because the browser EventSource API cannot set headers; it is checked once, when
 * the stream opens, and access tokens are short-lived.
 */
export const streamRoutes = new Hono();

streamRoutes.get("/", (c) => {
  const claims = verifyJwt(c.req.query("token") ?? "", config.jwtSecret);
  if (!claims) throw unauthorized();
  const channels = [`user:${claims.sub}`];
  if (claims.role === "admin") channels.push("admin");
  return streamSSE(c, async (stream) => {
    const queue: RealtimeEvent[] = [];
    let wake: (() => void) | null = null;
    const unsubscribe = hub.subscribe(channels, (event) => {
      queue.push(event);
      wake?.();
    });
    stream.onAbort(() => {
      unsubscribe();
      wake?.();
    });
    await stream.writeSSE({ event: "ready", data: JSON.stringify({ role: claims.role }) });
    let lastPing = Date.now();
    while (!stream.aborted) {
      while (queue.length > 0) {
        const event = queue.shift()!;
        await stream.writeSSE({ event: event.type, data: JSON.stringify(event.data) });
      }
      if (Date.now() - lastPing > 15_000) {
        await stream.writeSSE({ event: "ping", data: "{}" });
        lastPing = Date.now();
      }
      await new Promise<void>((resolve) => {
        wake = resolve;
        setTimeout(resolve, 5_000);
      });
      wake = null;
    }
    unsubscribe();
  });
});
