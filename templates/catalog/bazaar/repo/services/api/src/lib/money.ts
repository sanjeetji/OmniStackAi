/** Money, currency formatting, and marketplace commission calculation. */

export function formatMoney(cents: number | string | bigint, currency = "INR"): string {
  const num = typeof cents === "bigint" ? Number(cents) : Number(cents || 0);
  const units = num / 100;

  if (currency === "INR") {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(units);
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(units);
}

/** Calculates commission based on basis points (e.g. 1000 = 10.00%). */
export function calculateCommission(
  subtotalCents: number | bigint,
  basisPoints: number = 1000
): { commissionCents: number; vendorPayoutCents: number } {
  const sub = typeof subtotalCents === "bigint" ? Number(subtotalCents) : subtotalCents;
  const commissionCents = Math.round((sub * basisPoints) / 10000);
  const vendorPayoutCents = Math.max(0, sub - commissionCents);

  return {
    commissionCents,
    vendorPayoutCents,
  };
}
