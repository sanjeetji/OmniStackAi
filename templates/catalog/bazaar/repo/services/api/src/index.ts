/** Server entry point for Bazaar API service. */

import { serve } from "@hono/node-server";
import { app } from "./app.ts";
import { config } from "./config.ts";

console.log(`Starting Bazaar API server on port ${config.port}...`);

serve(
  {
    fetch: app.fetch,
    port: config.port,
  },
  (info) => {
    console.log(`✓ Bazaar API listening on http://localhost:${info.port}`);
  }
);
