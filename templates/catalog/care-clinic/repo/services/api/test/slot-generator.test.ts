import assert from "node:assert/strict";
import { test } from "node:test";
import { generateSlotsForShift } from "../src/lib/slot-generator.ts";

test("generates exact 20-minute consultation slots across a morning shift", () => {
  const shift = {
    startTime: "09:00:00",
    endTime: "11:00:00",
    slotDurationMins: 20,
  };
  const booked = new Set<string>();

  const slots = generateSlotsForShift(shift, booked);
  assert.equal(slots.length, 6); // 2 hours = 120 mins / 20 = 6 slots

  assert.deepEqual(slots[0], { startTime: "09:00:00", endTime: "09:20:00", isAvailable: true });
  assert.deepEqual(slots[1], { startTime: "09:20:00", endTime: "09:40:00", isAvailable: true });
  assert.deepEqual(slots[5], { startTime: "10:40:00", endTime: "11:00:00", isAvailable: true });
});

test("marks booked slots as unavailable", () => {
  const shift = {
    startTime: "09:00:00",
    endTime: "10:00:00",
    slotDurationMins: 20,
  };
  const booked = new Set<string>(["09:20:00"]);

  const slots = generateSlotsForShift(shift, booked);
  assert.equal(slots.length, 3);
  assert.equal(slots[0].isAvailable, true);
  assert.equal(slots[1].isAvailable, false); // Booked!
  assert.equal(slots[2].isAvailable, true);
});

test("handles custom slot duration (e.g. 30 minutes)", () => {
  const shift = {
    startTime: "14:00:00",
    endTime: "16:00:00",
    slotDurationMins: 30,
  };
  const booked = new Set<string>();

  const slots = generateSlotsForShift(shift, booked);
  assert.equal(slots.length, 4);
  assert.deepEqual(slots[0], { startTime: "14:00:00", endTime: "14:30:00", isAvailable: true });
  assert.deepEqual(slots[3], { startTime: "15:30:00", endTime: "16:00:00", isAvailable: true });
});
