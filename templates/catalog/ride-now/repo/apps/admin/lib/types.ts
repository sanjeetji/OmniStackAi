/** Shapes of the /admin/* endpoints (see services/api/src/routes/admin.ts). */
import type { LedgerEntry, Role, Ticket, Trip } from "@ridenow/shared";

export interface Dashboard {
  kpis: {
    trips_today: number;
    trips_yesterday: number;
    gmv_7d: number;
    gmv_prev_7d: number;
    revenue_7d: number;
    active_trips: number;
    active_riders_7d: number;
    completion_rate_7d: number;
    drivers_online: number;
    drivers_pending: number;
    avg_driver_rating: number | null;
    open_tickets: number;
    payouts_due: { count: number; amount: number };
  };
  series: { day: string; trips: number; gmv: number; revenue: number }[];
  vehicle_mix: { id: string; name: string; trips: number; gmv: number }[];
  top_drivers: { id: string; name: string; avatar_color: string; rating: number; vehicle_type: string; trips: number; earnings: number }[];
  recent_trips: Trip[];
}

export interface LiveDriver {
  id: string;
  name: string;
  vehicle_type: string;
  lat: number;
  lng: number;
  heading: number;
  simulated: boolean;
  trip_status: string | null;
}

export interface Zone {
  id: string;
  name: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  surge: number;
  active: boolean;
}

export interface Live {
  drivers: LiveDriver[];
  trips: Trip[];
  zones: Zone[];
}

export interface TripDetail extends Trip {
  offers: { status: string; pickup_km: number; offered_at: string; responded_at: string | null; driver_name: string }[];
  ledger: { kind: string; amount: number; note: string; created_at: string; account: string }[];
  ratings: { stars: number; tags: string[]; comment: string; from_role: Role }[];
}

export interface RiderRow {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  avatar_color: string;
  status: "active" | "suspended";
  created_at: string;
  last_login_at: string | null;
  balance: number;
  trips: number;
  spent: number;
  rating: number | null;
}

export interface RiderDetail extends Omit<RiderRow, "trips" | "spent" | "rating"> {
  trips: Trip[];
  ledger: LedgerEntry[];
  tickets: { id: string; code: string; subject: string; status: Ticket["status"]; created_at: string }[];
}

export type DriverStatus = "pending" | "approved" | "suspended";

export interface DriverRow {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  avatar_color: string;
  account_status: "active" | "suspended";
  status: DriverStatus;
  online: boolean;
  simulated: boolean;
  vehicle_type: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_color: string;
  plate: string;
  rating_avg: number;
  rating_count: number;
  joined_at: string;
  balance: number;
  trips: number;
  docs_pending: number;
  acceptance_rate: number;
}

export interface DriverDocument {
  id: string;
  kind: "license" | "registration" | "insurance" | "permit" | "photo";
  number: string;
  status: "pending" | "approved" | "rejected";
  expires_on: string | null;
  note: string;
  updated_at: string;
}

export interface DriverDetail {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  avatar_color: string;
  account_status: "active" | "suspended";
  created_at: string;
  status: DriverStatus;
  online: boolean;
  simulated: boolean;
  vehicle_type: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_color: string;
  plate: string;
  license_no: string;
  lat: number | null;
  lng: number | null;
  last_seen_at: string | null;
  rating_avg: number;
  rating_count: number;
  offers_received: number;
  offers_accepted: number;
  joined_at: string;
  balance: number;
  earnings_30d: number;
  trips_30d: number;
  acceptance_rate: number;
  documents: DriverDocument[];
  trips: Trip[];
  ratings: { stars: number; tags: string[]; comment: string; created_at: string }[];
}

export interface VehicleTypeRow {
  id: string;
  name: string;
  description: string;
  seats: number;
  base_fare: number;
  per_km: number;
  per_min: number;
  min_fare: number;
  booking_fee: number;
  commission_pct: number;
  active: boolean;
}

export interface PromoRow {
  code: string;
  description: string;
  kind: "percent" | "flat";
  value: number;
  max_discount: number | null;
  min_fare: number;
  valid_until: string | null;
  usage_limit: number | null;
  per_user_limit: number;
  used_count: number;
  active: boolean;
  created_at: string;
  total_discount: number;
}

export interface PayoutRow {
  id: string;
  driver_id: string;
  driver_name: string;
  avatar_color: string;
  plate: string;
  amount: number;
  status: "requested" | "paid" | "rejected";
  bank_last4: string;
  reference: string;
  requested_at: string;
  processed_at: string | null;
}

export interface Finance {
  platform_balance: number;
  last_30_days: Record<string, number>;
  owed_to_drivers: number;
  rider_wallet_float: number;
}

export type TicketStatus = "open" | "pending" | "resolved";
export type TicketPriority = "low" | "normal" | "high" | "urgent";

export interface TicketRow {
  id: string;
  code: string;
  category: string;
  subject: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_at: string;
  updated_at: string;
  user_name: string;
  user_role: Role;
  avatar_color: string;
  trip_code: string | null;
  messages: number;
}

export interface TicketDetail {
  id: string;
  code: string;
  category: string;
  subject: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_at: string;
  updated_at: string;
  user_id: string;
  user_name: string;
  user_role: Role;
  trip_id: string | null;
  trip_code: string | null;
  messages: { id: string; body: string; created_at: string; author_name: string; author_role: Role; avatar_color: string }[];
}

export interface AuditEntry {
  id: string;
  action: string;
  entity: string;
  entity_id: string;
  detail: Record<string, unknown>;
  at: string;
  actor_name: string | null;
}
