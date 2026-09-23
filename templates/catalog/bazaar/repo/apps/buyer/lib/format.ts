/** Operator-side formatting. Bazaar stores money in paise, and PostgreSQL returns counts as strings. */

export function num(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/** Paise to rupees. Every money column in Bazaar is an integer number of paise. */
export function inr(paise: string | number | null | undefined): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num(paise) / 100);
}

/** Paise to a short rupee label, for chart axes and dense tiles. */
export function inrShort(paise: string | number | null | undefined): string {
  const rupees = num(paise) / 100;
  if (rupees >= 10_000_000) return `₹${(rupees / 10_000_000).toFixed(1)}Cr`;
  if (rupees >= 100_000) return `₹${(rupees / 100_000).toFixed(1)}L`;
  if (rupees >= 1_000) return `₹${(rupees / 1_000).toFixed(1)}k`;
  return `₹${Math.round(rupees)}`;
}

export function count(value: string | number | null | undefined): string {
  return num(value).toLocaleString("en-IN");
}

export function day(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function dayShort(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value.length <= 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export function stamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function percent(part: number, whole: number): string {
  if (whole <= 0) return "0%";
  return `${Math.round((part / whole) * 100)}%`;
}

const SHIPMENT_TONES: Record<string, string> = {
  placed: "neutral",
  accepted: "signal",
  packed: "signal",
  shipped: "alert",
  delivered: "good",
  cancelled: "danger",
  returned: "danger",
};

// migrations/003_orders.sql
const ORDER_TONES: Record<string, string> = {
  pending_payment: "alert",
  processing: "signal",
  partially_shipped: "signal",
  completed: "good",
  cancelled: "danger",
};

// migrations/001_core.sql
const KYC_TONES: Record<string, string> = {
  pending: "alert",
  verified: "good",
  rejected: "danger",
  suspended: "danger",
};

// migrations/004_ledger.sql
const SETTLEMENT_TONES: Record<string, string> = {
  draft: "alert",
  approved: "signal",
  processed: "good",
};

export const tone = {
  shipment: (status: string) => SHIPMENT_TONES[status] ?? "neutral",
  order: (status: string) => ORDER_TONES[status] ?? "neutral",
  kyc: (status: string) => KYC_TONES[status] ?? "neutral",
  settlement: (status: string) => SETTLEMENT_TONES[status] ?? "neutral",
};
