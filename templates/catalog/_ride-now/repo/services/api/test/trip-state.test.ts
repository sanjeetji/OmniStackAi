import assert from "node:assert/strict";
import { test } from "node:test";
import { assertTransition, canTransition, cancellationFee, TransitionError } from "../src/lib/trip-state.ts";

test("the happy path is driver-driven", () => {
  assert.ok(canTransition("requested", "driver_assigned", "driver"));
  assert.ok(canTransition("driver_assigned", "driver_arrived", "driver"));
  assert.ok(canTransition("driver_arrived", "in_progress", "driver"));
  assert.ok(canTransition("in_progress", "completed", "driver"));
});

test("riders cannot move a trip forward, and cannot cancel once it has started", () => {
  assert.equal(canTransition("driver_arrived", "in_progress", "rider"), false);
  assert.equal(canTransition("in_progress", "cancelled", "rider"), false);
  assert.ok(canTransition("in_progress", "cancelled", "admin"));
});

test("final states are final", () => {
  for (const to of ["requested", "driver_assigned", "in_progress", "cancelled"] as const) {
    assert.equal(canTransition("completed", to, "admin"), false);
  }
  assert.throws(() => assertTransition("cancelled", "in_progress", "system"), TransitionError);
});

test("only a rider cancelling after the free wait pays a fee", () => {
  const arrived = new Date("2026-01-01T10:00:00Z");
  assert.equal(cancellationFee("driver_arrived", "rider", arrived, new Date("2026-01-01T10:02:00Z")), 0);
  assert.equal(cancellationFee("driver_arrived", "rider", arrived, new Date("2026-01-01T10:04:00Z")), 50);
  assert.equal(cancellationFee("driver_arrived", "driver", arrived, new Date("2026-01-01T10:10:00Z")), 0);
  assert.equal(cancellationFee("driver_assigned", "rider", null), 0);
});
