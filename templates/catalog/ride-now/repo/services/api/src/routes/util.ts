import type { Context } from "hono";
import { badRequest } from "../lib/errors.ts";
import { isValidPoint } from "../lib/geo.ts";
import type { Stop } from "../services/trips.ts";

export async function body(c: Context): Promise<Record<string, unknown>> {
  const data = await c.req.json().catch(() => null);
  if (data === null || typeof data !== "object" || Array.isArray(data)) return {};
  return data as Record<string, unknown>;
}

export function stop(value: unknown, label: string): Stop {
  if (!isValidPoint(value)) throw badRequest(`${label} needs a location.`);
  const name = (value as { name?: unknown }).name;
  if (typeof name !== "string" || !name.trim()) throw badRequest(`${label} needs a name.`);
  return { name: name.trim().slice(0, 200), lat: (value as { lat: number }).lat, lng: (value as { lng: number }).lng };
}
