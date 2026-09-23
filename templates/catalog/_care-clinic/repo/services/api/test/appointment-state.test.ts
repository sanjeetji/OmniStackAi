import assert from "node:assert/strict";
import { test } from "node:test";
import {
  isValidTransition,
  assertValidTransition,
  type AppointmentStatus,
} from "../src/lib/appointment-state.ts";
import { BadRequestError } from "../src/lib/errors.ts";

test("valid appointment lifecycle flow: booked -> checked_in -> in_consult -> completed", () => {
  assert.equal(isValidTransition("booked", "checked_in"), true);
  assert.equal(isValidTransition("checked_in", "in_consult"), true);
  assert.equal(isValidTransition("in_consult", "completed"), true);
  assert.doesNotThrow(() => assertValidTransition("booked", "checked_in"));
  assert.doesNotThrow(() => assertValidTransition("checked_in", "in_consult"));
  assert.doesNotThrow(() => assertValidTransition("in_consult", "completed"));
});

test("appointment cancellation from booked or checked_in", () => {
  assert.equal(isValidTransition("booked", "cancelled"), true);
  assert.equal(isValidTransition("checked_in", "cancelled"), true);
  assert.equal(isValidTransition("booked", "no_show"), true);
  assert.equal(isValidTransition("checked_in", "no_show"), true);
});

test("illegal transitions are strictly rejected", () => {
  // Cannot jump from booked straight to completed without consultation
  assert.equal(isValidTransition("booked", "completed"), false);
  assert.throws(() => assertValidTransition("booked", "completed"), BadRequestError);

  // Terminal states cannot transition
  assert.equal(isValidTransition("completed", "booked"), false);
  assert.equal(isValidTransition("cancelled", "checked_in"), false);
  assert.throws(() => assertValidTransition("completed", "in_consult"), BadRequestError);
  assert.throws(() => assertValidTransition("cancelled", "booked"), BadRequestError);

  // In consult cannot directly jump to cancelled without completing
  assert.equal(isValidTransition("in_consult", "cancelled"), false);
});
