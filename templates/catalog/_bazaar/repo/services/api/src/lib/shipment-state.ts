/** Finite State Machine for Multi-Vendor Shipment Lifecycle. */

import { BadRequestError } from "./errors.ts";

export type ShipmentStatus =
  | "placed"
  | "accepted"
  | "packed"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "returned";

export const ALLOWED_TRANSITIONS: Record<ShipmentStatus, ShipmentStatus[]> = {
  placed: ["accepted", "cancelled"],
  accepted: ["packed", "cancelled"],
  packed: ["shipped", "cancelled"],
  shipped: ["delivered", "cancelled"],
  delivered: ["returned"],
  cancelled: [],
  returned: [],
};

export function canTransition(from: ShipmentStatus, to: ShipmentStatus): boolean {
  const allowed = ALLOWED_TRANSITIONS[from];
  return Boolean(allowed && allowed.includes(to));
}

export function assertValidTransition(
  from: ShipmentStatus,
  to: ShipmentStatus
): void {
  if (!canTransition(from, to)) {
    throw new BadRequestError(
      `Invalid shipment status transition: cannot transition from '${from}' to '${to}'. Allowed: [${
        (ALLOWED_TRANSITIONS[from] || []).join(", ")
      }]`
    );
  }
}

export const STATUS_LABELS: Record<ShipmentStatus, string> = {
  placed: "Order Placed",
  accepted: "Accepted by Vendor",
  packed: "Packed & Ready",
  shipped: "In Transit",
  delivered: "Delivered",
  cancelled: "Cancelled",
  returned: "Returned & Refunded",
};
