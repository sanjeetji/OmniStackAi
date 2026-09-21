import assert from "node:assert/strict";
import { test } from "node:test";
import { computeFare, splitFare, type VehiclePricing } from "../src/lib/fare.ts";
import { money } from "../src/lib/money.ts";

const mini: VehiclePricing = { id: "mini", base_fare: 40, per_km: 12, per_min: 1.5, min_fare: 80, booking_fee: 10, commission_pct: 20 };

test("fare adds base, distance, time and booking fee", () => {
  const fare = computeFare(mini, 10, 30);
  assert.equal(fare.subtotal, 40 + 120 + 45);
  assert.equal(fare.total, 215);
});

test("the minimum fare applies to short trips", () => {
  const fare = computeFare(mini, 1, 3);
  assert.equal(fare.subtotal, 80);
  assert.equal(fare.total, 90);
});

test("surge multiplies the ride but not the booking fee", () => {
  const fare = computeFare(mini, 10, 30, 1.5);
  assert.equal(fare.surgeAmount, 102.5);
  assert.equal(fare.total, money(205 * 1.5 + 10));
});

test("a discount never makes the fare negative", () => {
  const fare = computeFare(mini, 1, 3, 1, 500);
  assert.equal(fare.discount, 90);
  assert.equal(fare.total, 0);
});

test("the platform funds promos: driver earning uses the pre-discount fare", () => {
  const { commission, driverEarning } = splitFare(180, 20, 20);
  assert.equal(commission, 40);
  assert.equal(driverEarning, 160);
});

test("money rounds to two decimals, half away from zero", () => {
  assert.equal(money(1.005), 1.01);
  assert.equal(money(-1.005), -1.01);
  assert.equal(money(0.1 + 0.2), 0.3);
});
