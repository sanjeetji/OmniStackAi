export type TripStatus =
  | "requested"
  | "driver_assigned"
  | "driver_arrived"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "no_driver";

export type Actor = "rider" | "driver" | "admin" | "system";

export const ACTIVE_STATUSES: readonly TripStatus[] = ["requested", "driver_assigned", "driver_arrived", "in_progress"];
export const FINAL_STATUSES: readonly TripStatus[] = ["completed", "cancelled", "no_driver"];

/** Every allowed transition and who may make it. Anything else is refused. */
const TRANSITIONS: Record<TripStatus, Partial<Record<TripStatus, readonly Actor[]>>> = {
  requested: { driver_assigned: ["driver", "system"], cancelled: ["rider", "admin", "system"], no_driver: ["system"] },
  driver_assigned: { driver_arrived: ["driver", "system"], cancelled: ["rider", "driver", "admin"] },
  driver_arrived: { in_progress: ["driver", "system"], cancelled: ["rider", "driver", "admin"] },
  in_progress: { completed: ["driver", "system"], cancelled: ["admin"] },
  completed: {},
  cancelled: {},
  no_driver: {},
};

export function canTransition(from: TripStatus, to: TripStatus, actor: Actor): boolean {
  return (TRANSITIONS[from][to] ?? []).includes(actor);
}

export function assertTransition(from: TripStatus, to: TripStatus, actor: Actor): void {
  if (!canTransition(from, to, actor)) {
    throw new TransitionError(`A ${actor} cannot move a trip from ${from} to ${to}.`);
  }
}

export class TransitionError extends Error {}

/** Riders pay a cancellation fee only after the driver has arrived and waited. */
export const CANCELLATION_FEE = 50;
export const FREE_WAIT_MINUTES = 3;

export function cancellationFee(status: TripStatus, actor: Actor, arrivedAt: Date | null, now = new Date()): number {
  if (actor !== "rider" || status !== "driver_arrived" || !arrivedAt) return 0;
  return now.getTime() - arrivedAt.getTime() > FREE_WAIT_MINUTES * 60_000 ? CANCELLATION_FEE : 0;
}
