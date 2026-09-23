/** Workstation-side formatting for values the API returns as strings or SQL types. */

import { formatINR } from "@careclinic/shared";

/** PostgreSQL sends COUNT() and SUM() as strings; treat anything unparseable as zero. */
export function num(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function money(value: string | number | null | undefined): string {
  return formatINR(num(value));
}

export function count(value: string | number | null | undefined): string {
  return num(value).toLocaleString("en-IN");
}

/** "2026-09-23T18:30:00.000Z" or "2026-09-23" both print as "23 Sep 2026". */
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

/** "14:20:00" → "2:20 pm". */
export function clock(value: string | null | undefined): string {
  if (!value) return "—";
  const [hours, minutes] = value.split(":").map(Number);
  if (!Number.isFinite(hours)) return value;
  const suffix = hours >= 12 ? "pm" : "am";
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  return `${hour12}:${String(minutes ?? 0).padStart(2, "0")} ${suffix}`;
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function percent(part: number, whole: number): string {
  if (whole <= 0) return "0%";
  return `${Math.round((part / whole) * 100)}%`;
}

const APPOINTMENT_TONES: Record<string, string> = {
  booked: "neutral",
  checked_in: "signal",
  in_consult: "alert",
  completed: "good",
  cancelled: "danger",
  no_show: "danger",
};

const PAYMENT_TONES: Record<string, string> = {
  paid: "good",
  pending: "alert",
  refunded: "danger",
  partially_refunded: "danger",
};

const LAB_TONES: Record<string, string> = {
  ordered: "neutral",
  sample_collected: "signal",
  processing: "alert",
  completed: "good",
  cancelled: "danger",
};

const FLAG_TONES: Record<string, string> = {
  normal: "good",
  high: "alert",
  low: "alert",
  critical: "danger",
};

export const tone = {
  appointment: (status: string) => APPOINTMENT_TONES[status] ?? "neutral",
  payment: (status: string | null | undefined) => (status ? PAYMENT_TONES[status] ?? "neutral" : "neutral"),
  lab: (status: string) => LAB_TONES[status] ?? "neutral",
  flag: (flag: string) => FLAG_TONES[flag] ?? "neutral",
};

/** "1992-06-14" -> 34. The API sends patient_age where it can; this covers the rest. */
export function ageFrom(dob: string | null | undefined): number | null {
  if (!dob) return null;
  const born = new Date(dob);
  if (Number.isNaN(born.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - born.getFullYear();
  const month = now.getMonth() - born.getMonth();
  if (month < 0 || (month === 0 && now.getDate() < born.getDate())) age -= 1;
  return age;
}

/** "1-0-1" -> "morning and night". The frequency notation every Indian prescription uses. */
export function readFrequency(frequency: string): string {
  const slots = ["morning", "afternoon", "night"];
  const taken = frequency
    .split("-")
    .map((part, index) => (Number(part) > 0 ? slots[index] : null))
    .filter(Boolean) as string[];
  if (taken.length === 0) return "as directed";
  if (taken.length === 1) return taken[0];
  return `${taken.slice(0, -1).join(", ")} and ${taken[taken.length - 1]}`;
}

/** Minutes between two timestamps, for "in the chair for 14 minutes". */
export function minutesSince(value: string | null | undefined): number | null {
  if (!value) return null;
  const started = new Date(value);
  if (Number.isNaN(started.getTime())) return null;
  return Math.max(0, Math.round((Date.now() - started.getTime()) / 60000));
}
