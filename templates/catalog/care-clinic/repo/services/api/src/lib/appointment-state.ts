/** Appointment lifecycle state machine and transition guards. */

import { BadRequestError } from "./errors.ts";

export type AppointmentStatus =
  | "booked"
  | "checked_in"
  | "in_consult"
  | "completed"
  | "cancelled"
  | "no_show";

export const ALLOWED_TRANSITIONS: Record<AppointmentStatus, AppointmentStatus[]> = {
  booked: ["checked_in", "cancelled", "no_show"],
  checked_in: ["in_consult", "cancelled", "no_show"],
  in_consult: ["completed"],
  completed: [],
  cancelled: [],
  no_show: [],
};

export function isValidTransition(from: AppointmentStatus, to: AppointmentStatus): boolean {
  if (from === to) return true;
  const allowed = ALLOWED_TRANSITIONS[from];
  return Boolean(allowed && allowed.includes(to));
}

export function assertValidTransition(from: AppointmentStatus, to: AppointmentStatus): void {
  if (!isValidTransition(from, to)) {
    throw new BadRequestError(
      `Invalid appointment status transition from '${from}' to '${to}'. Allowed transitions: ${
        ALLOWED_TRANSITIONS[from]?.join(", ") || "none (terminal state)"
      }`
    );
  }
}
