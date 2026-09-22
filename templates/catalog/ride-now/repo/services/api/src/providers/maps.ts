import { haversineKm, type Point } from "../lib/geo.ts";

/**
 * Maps provider. The mock estimates road distance from the straight line (a 1.3 road factor) and
 * time from an average city speed. A real provider (Google Routes, Mapbox, OSRM) implements the
 * same interface; set MAPS_PROVIDER and its key in .env.
 */
export interface RouteEstimate {
  distanceKm: number;
  durationMin: number;
}

export interface MapsProvider {
  readonly name: string;
  route(from: Point, to: Point): Promise<RouteEstimate>;
}

export const ROAD_FACTOR = 1.3;
export const CITY_SPEED_KMH = 22;

export function estimateRoute(from: Point, to: Point): RouteEstimate {
  const distanceKm = Math.max(0.5, haversineKm(from, to) * ROAD_FACTOR);
  const durationMin = Math.max(3, (distanceKm / CITY_SPEED_KMH) * 60);
  return { distanceKm: Math.round(distanceKm * 100) / 100, durationMin: Math.round(durationMin * 10) / 10 };
}

export const mockMaps: MapsProvider = {
  name: "mock",
  async route(from, to) {
    return estimateRoute(from, to);
  },
};
