import type { TripStatus } from "@ridenow/shared";
import type { DriverStatus, PayoutRow, TicketPriority, TicketStatus } from "@/lib/types";
import { Badge, type Tone } from "./ui";

/** Operator wording for trip states (the rider app uses rider-facing wording). */
export const TRIP_STATUS: Record<TripStatus, { label: string; tone: Tone }> = {
  requested: { label: "Dispatching", tone: "warn" },
  driver_assigned: { label: "Driver en route", tone: "signal" },
  driver_arrived: { label: "At pickup", tone: "signal" },
  in_progress: { label: "On trip", tone: "info" },
  completed: { label: "Completed", tone: "ok" },
  cancelled: { label: "Cancelled", tone: "bad" },
  no_driver: { label: "No driver", tone: "neutral" },
};

export function TripStatusBadge({ status }: { status: TripStatus }) {
  const meta = TRIP_STATUS[status] ?? { label: status, tone: "neutral" as Tone };
  return <Badge tone={meta.tone} dot>{meta.label}</Badge>;
}

export function PaymentBadge({ method, status }: { method: string; status: string }) {
  const tone: Tone = status === "refunded" ? "warn" : status === "paid" ? "ok" : "neutral";
  return (
    <Badge tone={tone}>
      {method === "cash" ? "Cash" : "Wallet"} · {status}
    </Badge>
  );
}

export const DRIVER_STATUS: Record<DriverStatus, { label: string; tone: Tone }> = {
  pending: { label: "Pending review", tone: "warn" },
  approved: { label: "Approved", tone: "ok" },
  suspended: { label: "Suspended", tone: "bad" },
};

export function DriverStatusBadge({ status }: { status: DriverStatus }) {
  const meta = DRIVER_STATUS[status];
  return <Badge tone={meta.tone} dot>{meta.label}</Badge>;
}

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const meta = { open: { label: "Open", tone: "bad" }, pending: { label: "Waiting on user", tone: "warn" }, resolved: { label: "Resolved", tone: "ok" } }[status] as { label: string; tone: Tone };
  return <Badge tone={meta.tone} dot>{meta.label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const tone: Tone = priority === "urgent" ? "bad" : priority === "high" ? "warn" : priority === "low" ? "neutral" : "info";
  return <Badge tone={tone} className="capitalize">{priority}</Badge>;
}

export function PayoutStatusBadge({ status }: { status: PayoutRow["status"] }) {
  const meta = { requested: { label: "Requested", tone: "warn" }, paid: { label: "Paid", tone: "ok" }, rejected: { label: "Rejected", tone: "bad" } }[status] as { label: string; tone: Tone };
  return <Badge tone={meta.tone} dot>{meta.label}</Badge>;
}

export const LEDGER_KIND: Record<string, string> = {
  topup: "Top-up",
  trip_payment: "Trip payment",
  trip_earning: "Trip earning",
  commission: "Commission",
  cash_commission: "Cash commission",
  refund: "Refund",
  payout: "Payout",
  adjustment: "Adjustment",
};

export const TRIP_EVENT: Record<string, string> = {
  requested: "Ride requested",
  offer_sent: "Offer sent to a driver",
  driver_assigned: "Driver accepted",
  driver_arrived: "Driver arrived at pickup",
  started: "Ride started with PIN",
  completed: "Ride completed",
  cancelled: "Ride cancelled",
  no_driver: "No driver found",
  refunded: "Refund issued",
};

export const DOC_KIND: Record<string, string> = {
  license: "Driving licence",
  registration: "Vehicle registration (RC)",
  insurance: "Insurance",
  permit: "Commercial permit",
  photo: "Profile photo",
};

export const TICKET_CATEGORY: Record<string, string> = {
  payment: "Payment",
  safety: "Safety",
  lost_item: "Lost item",
  driver: "Driver",
  app: "App",
  other: "Other",
};
