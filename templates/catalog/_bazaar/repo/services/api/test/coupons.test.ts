import assert from "node:assert/strict";
import { test } from "node:test";

interface Coupon {
  code: string;
  discountType: "percentage" | "flat";
  discountValue: number;
  minOrderCents: number;
  maxDiscountCents?: number;
  isActive: boolean;
  expiresAt?: string;
}

function calculateDiscount(coupon: Coupon, subtotalCents: number) {
  if (!coupon.isActive) return { valid: false, discountCents: 0, reason: "Inactive" };
  if (coupon.expiresAt && new Date(coupon.expiresAt) < new Date()) {
    return { valid: false, discountCents: 0, reason: "Expired" };
  }
  if (subtotalCents < coupon.minOrderCents) {
    return { valid: false, discountCents: 0, reason: "Subtotal below minimum" };
  }

  let discount = 0;
  if (coupon.discountType === "percentage") {
    discount = Math.round((subtotalCents * coupon.discountValue) / 100);
  } else {
    discount = coupon.discountValue;
  }

  if (coupon.maxDiscountCents != null) {
    discount = Math.min(discount, coupon.maxDiscountCents);
  }

  return { valid: true, discountCents: discount };
}

test("percentage coupon applies correctly below max cap", () => {
  const coupon: Coupon = {
    code: "WELCOME10",
    discountType: "percentage",
    discountValue: 10,
    minOrderCents: 100000, // ₹1,000
    maxDiscountCents: 50000, // ₹500 cap
    isActive: true,
  };

  const res = calculateDiscount(coupon, 250000); // ₹2,500
  assert.equal(res.valid, true);
  assert.equal(res.discountCents, 25000); // 10% of 2,500 = 250
});

test("percentage coupon caps at max discount", () => {
  const coupon: Coupon = {
    code: "WELCOME10",
    discountType: "percentage",
    discountValue: 10,
    minOrderCents: 100000,
    maxDiscountCents: 50000, // ₹500 cap
    isActive: true,
  };

  const res = calculateDiscount(coupon, 800000); // ₹8,000 -> 10% would be ₹800
  assert.equal(res.valid, true);
  assert.equal(res.discountCents, 50000); // capped at ₹500
});

test("rejects order below minimum spend threshold", () => {
  const coupon: Coupon = {
    code: "FESTIVE20",
    discountType: "percentage",
    discountValue: 20,
    minOrderCents: 250000, // ₹2,500
    isActive: true,
  };

  const res = calculateDiscount(coupon, 200000); // ₹2,000
  assert.equal(res.valid, false);
  assert.equal(res.discountCents, 0);
});

test("flat discount coupon deduction", () => {
  const coupon: Coupon = {
    code: "FREESHIP",
    discountType: "flat",
    discountValue: 9900,
    minOrderCents: 99900,
    isActive: true,
  };

  const res = calculateDiscount(coupon, 150000);
  assert.equal(res.valid, true);
  assert.equal(res.discountCents, 9900);
});
