/** Shapes returned by the RideNow API (see services/api). */
export type Role = "rider" | "driver" | "admin";
export type TripStatus = "requested" | "driver_assigned" | "driver_arrived" | "in_progress" | "completed" | "cancelled" | "no_driver";
export type PaymentMethod = "wallet" | "cash";

export interface LatLng {
  lat: number;
  lng: number;
}

export interface Stop extends LatLng {
  name: string;
}

export interface User {
  id: string;
  role: Role;
  full_name: string;
  email: string | null;
  phone: string | null;
  avatar_color: string;
  status: "active" | "suspended";
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface VehicleType {
  id: string;
  name: string;
  description: string;
  seats: number;
  base_fare: number;
  per_km: number;
  per_min: number;
  min_fare: number;
}

export interface Fare {
  base: number;
  distance: number;
  time: number;
  subtotal: number;
  surge: number;
  surgeAmount: number;
  bookingFee: number;
  discount: number;
  total: number;
}

export interface FareOption {
  vehicle_type: string;
  name: string;
  description: string;
  seats: number;
  fare: Fare;
  pickup_eta_min: number | null;
  drivers_nearby: number;
}

export interface Estimate {
  distance_km: number;
  duration_min: number;
  surge: number;
  surge_zone: string | null;
  promo: { code: string; valid: boolean; message: string } | null;
  options: FareOption[];
}

export interface TripDriver {
  id: string;
  name: string;
  phone: string | null;
  avatar_color: string;
  rating: number | null;
  vehicle: string;
  plate: string;
  location: (LatLng & { heading: number }) | null;
}

export interface TripEvent {
  kind: string;
  actor: string;
  detail: Record<string, unknown>;
  at: string;
}

export interface Trip {
  id: string;
  code: string;
  status: TripStatus;
  vehicle_type: string;
  vehicle_type_name: string;
  pickup: Stop;
  drop: Stop;
  distance_km: number;
  duration_min: number;
  surge: number;
  fare_estimate: number;
  discount: number;
  promo_code: string | null;
  fare_final: number | null;
  payment_method: PaymentMethod;
  payment_status: "pending" | "paid" | "refunded" | "waived";
  cancel_reason: string | null;
  cancelled_by: string | null;
  requested_at: string;
  assigned_at: string | null;
  arrived_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  rider: { id: string; name: string; phone: string | null; avatar_color: string } | null;
  driver: TripDriver | null;
  my_rating: number | null;
  pin?: string;
  commission?: number | null;
  driver_earning?: number | null;
  events?: TripEvent[];
}

export interface LedgerEntry {
  id: string;
  kind: string;
  amount: number;
  balance_after: number;
  reference: string;
  note: string;
  created_at: string;
}

export interface Place extends Stop {
  id: string;
  label?: string;
  address: string;
}

export interface Promo {
  code: string;
  description: string;
  kind: "percent" | "flat";
  value: number;
  max_discount: number | null;
  min_fare: number;
  valid_until: string | null;
  uses_left?: number;
}

export interface Notification {
  id: string;
  kind: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
}

export interface Ticket {
  id: string;
  code: string;
  category: string;
  subject: string;
  status: "open" | "pending" | "resolved";
  priority: string;
  created_at: string;
  updated_at: string;
  trip_code: string | null;
  last_message?: string | null;
  messages?: { id: string; body: string; created_at: string; author_name: string; author_role: Role; avatar_color: string }[];
}

export interface Offer {
  id: string;
  trip_id: string;
  status: string;
  code: string;
  vehicle_type: string;
  pickup: Stop;
  drop: Stop;
  pickup_km: number;
  trip_km: number;
  trip_min: number;
  fare: number;
  estimated_earning: number;
  surge: number;
  payment_method: PaymentMethod;
  rider_name: string;
  rider_rating: number | null;
  offered_at: string;
  expires_at: string;
}

export const ACTIVE_STATUSES: TripStatus[] = ["requested", "driver_assigned", "driver_arrived", "in_progress"];

export const STATUS_LABEL: Record<TripStatus, string> = {
  requested: "Finding your driver",
  driver_assigned: "Driver on the way",
  driver_arrived: "Driver has arrived",
  in_progress: "On the way",
  completed: "Completed",
  cancelled: "Cancelled",
  no_driver: "No driver found",
};
