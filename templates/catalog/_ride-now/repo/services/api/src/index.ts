import { serve } from "@hono/node-server";
import { createApp } from "./app.ts";
import { config } from "./config.ts";
import { pool } from "./db.ts";
import { startDispatcher, stopDispatcher } from "./services/dispatch.ts";

const app = createApp();
const server = serve({ fetch: app.fetch, port: config.port, hostname: process.env.HOST ?? "127.0.0.1" }, (info) => {
  console.log(`RideNow API on http://127.0.0.1:${info.port} (simulation ${config.simulation ? "on" : "off"})`);
});
startDispatcher();

async function shutdown() {
  stopDispatcher();
  server.close();
  await pool.end();
  process.exit(0);
}
process.on("SIGINT", () => void shutdown());
process.on("SIGTERM", () => void shutdown());
