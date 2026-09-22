import { money } from "./money.ts";

export interface VehiclePricing {
  id: string;
  base_fare: number;
  per_km: number;
  per_min: number;
  min_fare: number;
  booking_fee: number;
  commission_pct: number;
}

export interface FareBreakdown {
  base: number;
  distance: number;
  time: number;
  subtotal: number; // max(minimum, base + distance + time)
  surge: number; // multiplier
  surgeAmount: number;
  bookingFee: number;
  discount: number;
  total: number;
}

/** The fare rider pays: max(min, base + per_km*km + per_min*min) * surge + booking fee - discount. */
export function computeFare(
  pricing: VehiclePricing,
  distanceKm: number,
  durationMin: number,
  surge = 1,
  discount = 0,
): FareBreakdown {
  const base = money(pricing.base_fare);
  const distance = money(pricing.per_km * distanceKm);
  const time = money(pricing.per_min * durationMin);
  const subtotal = money(Math.max(pricing.min_fare, base + distance + time));
  const surged = money(subtotal * surge);
  const bookingFee = money(pricing.booking_fee);
  const gross = money(surged + bookingFee);
  const appliedDiscount = money(Math.min(Math.max(0, discount), gross));
  return {
    base,
    distance,
    time,
    subtotal,
    surge,
    surgeAmount: money(surged - subtotal),
    bookingFee,
    discount: appliedDiscount,
    total: money(gross - appliedDiscount),
  };
}

/** Split a completed fare: the platform keeps commission on the pre-discount fare; promos are
 * funded by the platform, so the driver's earning does not shrink when a rider uses a code. */
export function splitFare(total: number, discount: number, commissionPct: number): { commission: number; driverEarning: number } {
  const gross = money(total + discount);
  const commission = money((gross * commissionPct) / 100);
  return { commission, driverEarning: money(gross - commission) };
}
