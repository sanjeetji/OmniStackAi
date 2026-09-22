import assert from "node:assert/strict";
import { test } from "node:test";
import { initials, inr, km, minutes, relativeTime, signedInr } from "../src/format.ts";

test("INR formatting (Indian grouping, no .00)", () => {
  assert.equal(inr(1234), "₹1,234");
  assert.equal(inr(123456.5), "₹1,23,456.50");
  assert.equal(inr(null), "—");
  assert.equal(signedInr(-80), "−₹80");
  assert.equal(signedInr(120.25), "+₹120.25");
});

test("distance and duration", () => {
  assert.equal(km(0.42), "420 m");
  assert.equal(km(6.34), "6.3 km");
  assert.equal(km(24.6), "25 km");
  assert.equal(minutes(0.2), "1 min");
  assert.equal(minutes(75), "1 h 15 min");
  assert.equal(minutes(120), "2 h");
});

test("relative time and initials", () => {
  const now = Date.UTC(2026, 8, 22, 12);
  assert.equal(relativeTime(new Date(now - 20_000), now), "just now");
  assert.equal(relativeTime(new Date(now - 5 * 60_000), now), "5 minutes ago");
  assert.equal(relativeTime(new Date(now - 3 * 3_600_000), now), "3 hours ago");
  assert.equal(initials("Asha  Rao"), "AR");
  assert.equal(initials("Ravi Kumar Singh"), "RK");
});
