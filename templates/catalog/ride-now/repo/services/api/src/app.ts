import { Hono } from "hono";
import { cors } from "hono/cors";
import { config } from "./config.ts";
import { pool } from "./db.ts";
import { HttpError } from "./lib/errors.ts";
import { TransitionError } from "./lib/trip-state.ts";
import { openapi } from "./openapi.ts";
import { adminRoutes } from "./routes/admin.ts";
import { authRoutes } from "./routes/auth.ts";
import { driverRoutes } from "./routes/driver.ts";
import { publicRoutes } from "./routes/public.ts";
import { riderRoutes } from "./routes/rider.ts";
import { streamRoutes } from "./routes/stream.ts";
import { supportRoutes } from "./routes/support.ts";

export function createApp() {
  const app = new Hono();
  app.use("*", cors({ origin: config.corsOrigin, allowHeaders: ["Authorization", "Content-Type"], allowMethods: ["GET", "POST", "PUT", "PATCH", "DELETE"] }));

  app.get("/health", async (c) => {
    await pool.query("SELECT 1");
    return c.json({ status: "ok", service: "ridenow-api" });
  });
  app.get("/openapi.json", (c) => c.json(openapi));
  app.route("/", publicRoutes);
  app.route("/auth", authRoutes);
  app.route("/rider", riderRoutes);
  app.route("/driver", driverRoutes);
  app.route("/admin", adminRoutes);
  app.route("/support", supportRoutes);
  app.route("/stream", streamRoutes);

  app.notFound((c) => c.json({ error: "Not found.", code: "not_found" }, 404));
  app.onError((error, c) => {
    if (error instanceof HttpError) return c.json({ error: error.message, code: error.code }, error.status as 400);
    if (error instanceof TransitionError) return c.json({ error: error.message, code: "invalid_transition" }, 409);
    if ((error as { code?: string }).code === "23505") return c.json({ error: "That already exists.", code: "conflict" }, 409);
    if ((error as { code?: string }).code === "22P02") return c.json({ error: "That id is not valid.", code: "bad_request" }, 400);
    console.error("[api] unexpected error:", error);
    return c.json({ error: "Something went wrong. Please try again.", code: "internal" }, 500);
  });
  return app;
}
