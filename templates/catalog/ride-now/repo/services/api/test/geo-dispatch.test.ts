import assert from "node:assert/strict";
import { test } from "node:test";
import { rankCandidates } from "../src/lib/dispatch-rank.ts";
import { bearing, haversineKm, interpolate } from "../src/lib/geo.ts";
import { estimateRoute } from "../src/providers/maps.ts";

const mgRoad = { lat: 12.9756, lng: 77.6066 };
const koramangala = { lat: 12.9352, lng: 77.6245 };

test("haversine distance in Bengaluru", () => {
  const km = haversineKm(mgRoad, koramangala);
  assert.ok(km > 4.8 && km < 5.0, `got ${km}`);
});

test("route estimate adds a road factor and city speed", () => {
  const route = estimateRoute(mgRoad, koramangala);
  assert.ok(route.distanceKm > 6.2 && route.distanceKm < 6.5);
  assert.ok(route.durationMin > 16 && route.durationMin < 18);
});

test("bearing and interpolation", () => {
  assert.ok(Math.abs(bearing({ lat: 0, lng: 0 }, { lat: 1, lng: 0 })) < 1e-6);
  assert.deepEqual(interpolate({ lat: 0, lng: 0 }, { lat: 2, lng: 4 }, 0.5), { lat: 1, lng: 2 });
});

test("dispatch prefers real drivers, then the nearest, and skips far or already-offered ones", () => {
  const near = { lat: 12.9760, lng: 77.6070 };
  const ranked = rankCandidates(
    mgRoad,
    [
      { user_id: "sim-near", ...near, rating_avg: 4.9, simulated: true },
      { user_id: "real-far", lat: 12.99, lng: 77.62, rating_avg: 4.5, simulated: false },
      { user_id: "real-offered", ...near, rating_avg: 5, simulated: false },
      { user_id: "too-far", lat: 13.2, lng: 77.7, rating_avg: 5, simulated: false },
    ],
    new Set(["real-offered"]),
  );
  assert.deepEqual(ranked.map((c) => c.user_id), ["real-far", "sim-near"]);
});
