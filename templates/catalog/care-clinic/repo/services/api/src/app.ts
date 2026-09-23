/** Main Hono application definition for CareClinic API. */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { config } from "./config.ts";
import { AppError } from "./lib/errors.ts";
import { publicRoutes } from "./routes/public.ts";
import { patientRoutes } from "./routes/patient.ts";
import { doctorRoutes } from "./routes/doctor.ts";
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
      service: "careclinic-api",
      version: "1.0.0",
      timestamp: new Date().toISOString(),
    });
  });

  // Mount API modules
  app.route("/api/public", publicRoutes);
  app.route("/", publicRoutes);
  app.route("/", patientRoutes);
  app.route("/", doctorRoutes);
  app.route("/", adminRoutes);
  app.route("/", streamRoutes);

  // Global Error Handler
  app.onError((err, c) => {
    if (err instanceof AppError) {
      return c.json(
        { error: err.message, code: err.code, details: err.details },
        err.statusCode as any
      );
    }

    console.error("[CareClinic API Unhandled Error]", err);
    return c.json(
      {
        error: config.isDev ? err.message : "Internal Server Error",
        code: "INTERNAL_ERROR",
      },
      500
    );
  });

  // Not Found Handler
  app.notFound((c) => {
    return c.json(
      { error: `Not found: ${c.req.method} ${c.req.url}`, code: "NOT_FOUND" },
      404
    );
  });

  return app;
}

export const app = createApp();
