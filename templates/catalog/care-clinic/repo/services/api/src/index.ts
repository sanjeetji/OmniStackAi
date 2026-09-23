/** Server entry point for CareClinic API service. */

import { serve } from "@hono/node-server";
import { app } from "./app.ts";
import { config } from "./config.ts";

console.log(`Starting CareClinic API server on port ${config.port}...`);

serve(
  {
    fetch: app.fetch,
    port: config.port,
  },
  (info) => {
    console.log(`✓ CareClinic API listening on http://localhost:${info.port}`);
  }
);
