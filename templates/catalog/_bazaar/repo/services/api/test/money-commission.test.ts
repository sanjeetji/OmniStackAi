import assert from "node:assert/strict";
import { test } from "node:test";
import { formatMoney, calculateCommission } from "../src/lib/money.ts";

test("calculates marketplace commission at default 10.00% (1000 basis points)", () => {
  const { commissionCents, vendorPayoutCents } = calculateCommission(500000, 1000);
  assert.equal(commissionCents, 50000); // ₹500
  assert.equal(vendorPayoutCents, 450000); // ₹4,500
  assert.equal(commissionCents + vendorPayoutCents, 500000);
});

test("calculates commission at custom rates (e.g. 12% and 8%)", () => {
  // 1200 basis points = 12%
  const res12 = calculateCommission(100000, 1200);
  assert.equal(res12.commissionCents, 12000);
  assert.equal(res12.vendorPayoutCents, 88000);

  // 800 basis points = 8%
  const res8 = calculateCommission(250000, 800);
  assert.equal(res8.commissionCents, 20000);
  assert.equal(res8.vendorPayoutCents, 230000);
});

test("handles rounding and zero cleanly", () => {
  const zero = calculateCommission(0, 1000);
  assert.equal(zero.commissionCents, 0);
  assert.equal(zero.vendorPayoutCents, 0);

  // Fractional rounding
  const odd = calculateCommission(4999, 1000); // ₹49.99
  assert.equal(odd.commissionCents, 500); // 499.9 rounded to 500
  assert.equal(odd.vendorPayoutCents, 4499);
});

test("formats INR and USD currencies accurately", () => {
  assert.equal(formatMoney(299900, "INR"), "₹2,999.00");
  assert.equal(formatMoney(10000000, "INR"), "₹1,00,000.00");
  assert.equal(formatMoney(4999, "USD"), "$49.99");
});
