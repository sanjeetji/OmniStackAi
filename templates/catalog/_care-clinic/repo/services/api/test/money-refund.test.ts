import assert from "node:assert/strict";
import { test } from "node:test";
import { calculateCancellationRefund, formatINR } from "../src/lib/money.ts";

test("formatINR formats Indian rupees correctly", () => {
  const formatted = formatINR(700);
  assert.ok(formatted.includes("700") || formatted.includes("₹"));
});

test("cancellation > 24 hours in advance gives 100% full refund", () => {
  const now = new Date("2026-10-01T10:00:00Z");
  const result = calculateCancellationRefund(
    800,
    "2026-10-03", // 48 hours later
    "10:00:00",
    now
  );

  assert.equal(result.canCancel, true);
  assert.equal(result.refundAmount, 800);
  assert.equal(result.cancellationFee, 0);
  assert.equal(result.refundPercentage, 100);
});

test("cancellation between 4 and 24 hours gives 70% refund with 30% clinic fee", () => {
  const now = new Date("2026-10-01T10:00:00Z");
  const result = calculateCancellationRefund(
    1000,
    "2026-10-01", // 6 hours later
    "16:00:00",
    now
  );

  assert.equal(result.canCancel, true);
  assert.equal(result.refundAmount, 700); // 70% of 1000
  assert.equal(result.cancellationFee, 300); // 30% of 1000
  assert.equal(result.refundPercentage, 70);
});

test("late cancellation < 4 hours gives 0% refund", () => {
  const now = new Date("2026-10-01T10:00:00Z");
  const result = calculateCancellationRefund(
    900,
    "2026-10-01", // 2 hours later
    "12:00:00",
    now
  );

  assert.equal(result.canCancel, true);
  assert.equal(result.refundAmount, 0);
  assert.equal(result.cancellationFee, 900);
  assert.equal(result.refundPercentage, 0);
});
