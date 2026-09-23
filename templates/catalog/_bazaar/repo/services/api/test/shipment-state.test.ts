import assert from "node:assert/strict";
import { test } from "node:test";
import {
  canTransition,
  assertValidTransition,
  STATUS_LABELS,
  type ShipmentStatus,
} from "../src/lib/shipment-state.ts";
import { BadRequestError } from "../src/lib/errors.ts";

test("happy path fulfillment lifecycle transitions", () => {
  assert.ok(canTransition("placed", "accepted"));
  assert.ok(canTransition("accepted", "packed"));
  assert.ok(canTransition("packed", "shipped"));
  assert.ok(canTransition("shipped", "delivered"));
});

test("cancellations are allowed prior to delivery", () => {
  assert.ok(canTransition("placed", "cancelled"));
  assert.ok(canTransition("accepted", "cancelled"));
  assert.ok(canTransition("packed", "cancelled"));
  assert.ok(canTransition("shipped", "cancelled"));
});

test("customer return is only valid from delivered status", () => {
  assert.ok(canTransition("delivered", "returned"));
  assert.equal(canTransition("placed", "returned"), false);
  assert.equal(canTransition("accepted", "returned"), false);
  assert.equal(canTransition("packed", "returned"), false);
  assert.equal(canTransition("shipped", "returned"), false);
});

test("terminal states cannot transition anywhere", () => {
  const terminalStatuses: ShipmentStatus[] = ["cancelled", "returned"];
  const allTargets: ShipmentStatus[] = [
    "placed",
    "accepted",
    "packed",
    "shipped",
    "delivered",
    "cancelled",
    "returned",
  ];

  for (const term of terminalStatuses) {
    for (const target of allTargets) {
      assert.equal(canTransition(term, target), false);
      assert.throws(
        () => assertValidTransition(term, target),
        BadRequestError
      );
    }
  }
});

test("status labels exist for all valid statuses", () => {
  const statuses: ShipmentStatus[] = [
    "placed",
    "accepted",
    "packed",
    "shipped",
    "delivered",
    "cancelled",
    "returned",
  ];

  for (const s of statuses) {
    assert.ok(STATUS_LABELS[s]);
    assert.ok(STATUS_LABELS[s].length > 3);
  }
});
