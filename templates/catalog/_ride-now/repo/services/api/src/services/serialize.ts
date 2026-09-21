import { num } from "../lib/money.ts";

/** Shape a trips row (joined with rider/driver/vehicle columns) for the API. */
export function tripJson(row: Record<string, any>, viewer: "rider" | "driver" | "admin") {
  const trip = {
    id: row.id,
    code: row.code,
    status: row.status,
    vehicle_type: row.vehicle_type,
    vehicle_type_name: row.vehicle_type_name ?? row.vehicle_type,
    pickup: { name: row.pickup_name, lat: row.pickup_lat, lng: row.pickup_lng },
    drop: { name: row.drop_name, lat: row.drop_lat, lng: row.drop_lng },
    distance_km: num(row.distance_km),
    duration_min: num(row.duration_min),
    surge: num(row.surge),
    fare_estimate: num(row.fare_estimate),
    discount: num(row.discount),
    promo_code: row.promo_code,
    fare_final: row.fare_final === null ? null : num(row.fare_final),
    payment_method: row.payment_method,
    payment_status: row.payment_status,
    cancel_reason: row.cancel_reason,
    cancelled_by: row.cancelled_by,
    requested_at: row.requested_at,
    assigned_at: row.assigned_at,
    arrived_at: row.arrived_at,
    started_at: row.started_at,
    completed_at: row.completed_at,
    cancelled_at: row.cancelled_at,
    rider: row.rider_name ? { id: row.rider_id, name: row.rider_name, phone: row.rider_phone, avatar_color: row.rider_color } : null,
    driver: row.driver_id
      ? {
          id: row.driver_id,
          name: row.driver_name,
          phone: row.driver_phone,
          avatar_color: row.driver_color,
          rating: row.driver_rating === null || row.driver_rating === undefined ? null : num(row.driver_rating),
          vehicle: `${row.vehicle_color ?? ""} ${row.vehicle_make ?? ""} ${row.vehicle_model ?? ""}`.trim(),
          plate: row.plate,
          location: row.driver_lat === null || row.driver_lat === undefined ? null : { lat: row.driver_lat, lng: row.driver_lng, heading: row.driver_heading },
        }
      : null,
    my_rating: row.my_rating ?? null,
  } as Record<string, unknown>;
  // The start PIN is shown to the rider only; the driver must ask for it.
  if (viewer === "rider") trip.pin = row.pin;
  if (viewer !== "rider") {
    trip.commission = row.commission === null ? null : num(row.commission);
    trip.driver_earning = row.driver_earning === null ? null : num(row.driver_earning);
  }
  return trip;
}

export const TRIP_SELECT = `
  SELECT t.*, vt.name AS vehicle_type_name,
         r.full_name AS rider_name, r.phone AS rider_phone, r.avatar_color AS rider_color,
         du.full_name AS driver_name, du.phone AS driver_phone, du.avatar_color AS driver_color,
         d.rating_avg AS driver_rating, d.vehicle_make, d.vehicle_model, d.vehicle_color, d.plate,
         d.lat AS driver_lat, d.lng AS driver_lng, d.heading AS driver_heading
    FROM trips t
    JOIN vehicle_types vt ON vt.id = t.vehicle_type
    JOIN users r ON r.id = t.rider_id
    LEFT JOIN drivers d ON d.user_id = t.driver_id
    LEFT JOIN users du ON du.id = t.driver_id`;
