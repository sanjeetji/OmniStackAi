/** Currency, date, and status badge formatting helpers. */

export function formatPrice(cents: number | string | bigint, currency = "INR"): string {
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

export function formatDate(isoString?: string | null): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(d);
  } catch {
    return String(isoString);
  }
}

export function formatDateTime(isoString?: string | null): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }).format(d);
  } catch {
    return String(isoString);
  }
}

export function formatStatusLabel(status: string): string {
  switch (status) {
    case "placed":
      return "Order Placed";
    case "accepted":
      return "Confirmed by Seller";
    case "packed":
      return "Packed & Ready";
    case "shipped":
      return "In Transit";
    case "delivered":
      return "Delivered";
    case "cancelled":
      return "Cancelled";
    case "returned":
      return "Returned";
    case "processing":
      return "Processing";
    case "partially_shipped":
      return "Partially Shipped";
    case "completed":
      return "Completed";
    default:
      return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export function formatStatusBadge(status: string): {
  bg: string;
  text: string;
  border: string;
  dot: string;
} {
  switch (status) {
    case "placed":
    case "processing":
      return {
        bg: "bg-amber-50",
        text: "text-amber-800",
        border: "border-amber-200",
        dot: "bg-amber-500",
      };
    case "accepted":
    case "packed":
      return {
        bg: "bg-blue-50",
        text: "text-blue-800",
        border: "border-blue-200",
        dot: "bg-blue-500",
      };
    case "shipped":
    case "partially_shipped":
      return {
        bg: "bg-purple-50",
        text: "text-purple-800",
        border: "border-purple-200",
        dot: "bg-purple-500",
      };
    case "delivered":
    case "completed":
    case "verified":
    case "processed":
      return {
        bg: "bg-emerald-50",
        text: "text-emerald-800",
        border: "border-emerald-200",
        dot: "bg-emerald-500",
      };
    case "cancelled":
    case "rejected":
    case "suspended":
      return {
        bg: "bg-rose-50",
        text: "text-rose-800",
        border: "border-rose-200",
        dot: "bg-rose-500",
      };
    default:
      return {
        bg: "bg-stone-50",
        text: "text-stone-700",
        border: "border-stone-200",
        dot: "bg-stone-400",
      };
  }
}

export const formatCurrency = formatPrice;

export function getShipmentStatusBadge(status: string): { label: string; color: string } {
  const label = formatStatusLabel(status);
  const badge = formatStatusBadge(status);
  return {
    label,
    color: `${badge.bg} ${badge.text} ${badge.border} border`,
  };
}

