/**
 * Formatting and domain calculation helpers for CareClinic.
 */

import type { AppointmentStatus, PaymentStatus } from "./types";

/** Formats an integer rupee amount as INR (e.g. ₹800 or ₹1,250) */
export function formatINR(amount: number): string {
  if (isNaN(amount)) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Formats time string (HH:MM or HH:MM:SS) to 12-hour format e.g. "9:00 AM", "2:30 PM" */
export function formatSlotTime(timeStr: string): string {
  if (!timeStr) return "";
  const parts = timeStr.split(":");
  let hours = parseInt(parts[0], 10);
  const minutes = parts[1] || "00";
  if (isNaN(hours)) return timeStr;

  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  hours = hours ? hours : 12;
  return `${hours}:${minutes} ${ampm}`;
}

/** Formats a date string (YYYY-MM-DD) into readable format e.g. "Wed, Sep 23, 2026" */
export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr + "T00:00:00");
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Formats short date e.g. "23 Sep 2026" */
export function formatShortDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Appointment status styling metadata */
export function getAppointmentStatusBadge(status: AppointmentStatus): {
  label: string;
  bg: string;
  text: string;
  border: string;
} {
  switch (status) {
    case "booked":
      return {
        label: "Confirmed",
        bg: "bg-teal-50",
        text: "text-teal-700",
        border: "border-teal-200",
      };
    case "checked_in":
      return {
        label: "Checked In",
        bg: "bg-blue-50",
        text: "text-blue-700",
        border: "border-blue-200",
      };
    case "in_consult":
      return {
        label: "In Consultation",
        bg: "bg-purple-50",
        text: "text-purple-700",
        border: "border-purple-200",
      };
    case "completed":
      return {
        label: "Completed",
        bg: "bg-emerald-50",
        text: "text-emerald-700",
        border: "border-emerald-200",
      };
    case "cancelled":
      return {
        label: "Cancelled",
        bg: "bg-rose-50",
        text: "text-rose-700",
        border: "border-rose-200",
      };
    case "no_show":
      return {
        label: "No Show",
        bg: "bg-amber-50",
        text: "text-amber-700",
        border: "border-amber-200",
      };
    default:
      return {
        label: status,
        bg: "bg-slate-50",
        text: "text-slate-700",
        border: "border-slate-200",
      };
  }
}

/** Payment status styling metadata */
export function getPaymentStatusBadge(status: PaymentStatus): {
  label: string;
  bg: string;
  text: string;
} {
  switch (status) {
    case "paid":
      return { label: "Paid", bg: "bg-emerald-50", text: "text-emerald-700" };
    case "pending":
      return { label: "Pending", bg: "bg-amber-50", text: "text-amber-700" };
    case "partially_paid":
      return { label: "Partial", bg: "bg-blue-50", text: "text-blue-700" };
    case "refunded":
      return { label: "Refunded", bg: "bg-slate-100", text: "text-slate-700" };
    default:
      return { label: status, bg: "bg-slate-50", text: "text-slate-700" };
  }
}

/** Deterministic cancellation refund calculator (>24h 100%, 4-24h 70%, <4h 0%) */
export function calculateCancellationRefund(
  scheduledDate: string,
  startTime: string,
  feeInr: number,
  nowUtcMs?: number
): {
  refundPercent: number;
  refundAmountInr: number;
  deductionInr: number;
  hoursUntil: number;
  policyNote: string;
} {
  const [year, month, day] = scheduledDate.split("-").map(Number);
  const [hour, minute] = startTime.split(":").map(Number);

  const aptTime = Date.UTC(year, month - 1, day, hour, minute, 0);
  const currentTime = nowUtcMs !== undefined ? nowUtcMs : Date.now();
  const diffHours = (aptTime - currentTime) / (1000 * 60 * 60);

  if (diffHours >= 24) {
    return {
      refundPercent: 100,
      refundAmountInr: feeInr,
      deductionInr: 0,
      hoursUntil: Math.round(diffHours * 10) / 10,
      policyNote: "Full 100% refund applied (>24 hours prior)",
    };
  } else if (diffHours >= 4) {
    const refund = Math.round(feeInr * 0.7);
    return {
      refundPercent: 70,
      refundAmountInr: refund,
      deductionInr: feeInr - refund,
      hoursUntil: Math.round(diffHours * 10) / 10,
      policyNote: "70% refund applied (4-24 hours prior; 30% retention fee)",
    };
  } else {
    return {
      refundPercent: 0,
      refundAmountInr: 0,
      deductionInr: feeInr,
      hoursUntil: Math.max(0, Math.round(diffHours * 10) / 10),
      policyNote: "Non-refundable (<4 hours prior to appointment)",
    };
  }
}

/** Blood pressure category evaluator */
export function evaluateBloodPressure(
  systolic?: number | null,
  diastolic?: number | null
): { category: string; color: string } {
  if (!systolic || !diastolic) return { category: "Unrecorded", color: "text-slate-500" };
  if (systolic < 120 && diastolic < 80) {
    return { category: "Optimal", color: "text-emerald-600" };
  }
  if (systolic <= 129 && diastolic < 80) {
    return { category: "Elevated", color: "text-amber-600" };
  }
  if ((systolic >= 130 && systolic <= 139) || (diastolic >= 80 && diastolic <= 89)) {
    return { category: "Stage 1 HTN", color: "text-orange-600" };
  }
  return { category: "Stage 2 HTN", color: "text-rose-600" };
}
