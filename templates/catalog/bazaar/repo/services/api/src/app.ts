/** Main Hono application definition for Bazaar API. */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { config } from "./config.ts";
import { HttpError } from "./lib/errors.ts";
import { publicRoutes } from "./routes/public.ts";
import { shopperRoutes } from "./routes/shopper.ts";
import { vendorRoutes } from "./routes/vendor.ts";
import { adminRoutes } from "./routes/admin.ts";
import { streamRoutes } from "./routes/stream.ts";

export function createApp(): Hono {
  const app = new Hono();

  // Middleware
  app.use(
    "*",
    cors({
      origin: config.corsOrigin === "*" ? (origin) => origin : config.corsOrigin,
      credentials: true,
      allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
      allowHeaders: ["Content-Type", "Authorization"],
    })
  );

  if (config.isDev) {
    app.use("*", logger());
  }

  // Health check
  app.get("/health", (c) => {
    return c.json({
      status: "ok",
      service: "bazaar-api",
      version: "1.0.0",
      timestamp: new Date().toISOString(),
    });
  });

  // Mount API modules
  app.route("/api/public", publicRoutes);
  app.route("/", publicRoutes);
  app.route("/api/shopper", shopperRoutes);
  app.route("/api/vendor", vendorRoutes);
  app.route("/api/admin", adminRoutes);
  app.route("/api", streamRoutes);

  // Global Error Handler
  app.onError((err, c) => {
    if (err instanceof HttpError) {
      return c.json({ error: err.message, status: err.status }, err.status as any);
    }

    console.error("[Bazaar API Unhandled Error]", err);
    return c.json(
      {
        error: config.isDev ? err.message : "Internal Server Error",
        status: 500,
      },
      500
    );
  });

  // Not Found Handler
  app.notFound((c) => {
    return c.json({ error: `Not found: ${c.req.method} ${c.req.url}`, status: 404 }, 404);
  });

  return app;
}

export const app = createApp();
