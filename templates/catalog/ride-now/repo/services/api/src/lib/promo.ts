import { money } from "./money.ts";

export interface Promo {
  code: string;
  kind: "percent" | "flat";
  value: number;
  max_discount: number | null;
  min_fare: number;
  valid_until: Date | null;
  usage_limit: number | null;
  per_user_limit: number;
  used_count: number;
  active: boolean;
}

export type PromoCheck = { ok: true; discount: number } | { ok: false; reason: string };

/** Whether a promo applies to a fare for a rider who has used it `usedByRider` times already. */
export function evaluatePromo(promo: Promo, fare: number, usedByRider: number, now = new Date()): PromoCheck {
  if (!promo.active) return { ok: false, reason: "This code is no longer active." };
  if (promo.valid_until && promo.valid_until.getTime() < now.getTime()) return { ok: false, reason: "This code has expired." };
  if (promo.usage_limit !== null && promo.used_count >= promo.usage_limit) return { ok: false, reason: "This code has been fully used." };
  if (usedByRider >= promo.per_user_limit) return { ok: false, reason: "You have already used this code." };
  if (fare < promo.min_fare) return { ok: false, reason: `This code needs a fare of at least ₹${promo.min_fare}.` };
  let discount = promo.kind === "percent" ? (fare * promo.value) / 100 : promo.value;
  if (promo.max_discount !== null) discount = Math.min(discount, promo.max_discount);
  return { ok: true, discount: money(Math.min(discount, fare)) };
}
