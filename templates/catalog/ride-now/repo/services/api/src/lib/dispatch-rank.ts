import { haversineKm, type Point } from "./geo.ts";

export interface Candidate {
  user_id: string;
  lat: number;
  lng: number;
  rating_avg: number;
  simulated: boolean;
}

export const DISPATCH_RADIUS_KM = 5;
export const OFFER_SECONDS = 20;
export const MAX_DISPATCH_ATTEMPTS = 5;

/**
 * Order drivers for an offer: real (signed-in) drivers before simulated demo drivers, then by
 * pickup distance, then by rating. Drivers outside the radius or already offered are dropped.
 */
export function rankCandidates(pickup: Point, candidates: Candidate[], alreadyOffered: ReadonlySet<string>): (Candidate & { pickupKm: number })[] {
  return candidates
    .filter((c) => !alreadyOffered.has(c.user_id))
    .map((c) => ({ ...c, pickupKm: Math.round(haversineKm(pickup, c) * 100) / 100 }))
    .filter((c) => c.pickupKm <= DISPATCH_RADIUS_KM)
    .sort(
      (a, b) =>
        Number(a.simulated) - Number(b.simulated) ||
        a.pickupKm - b.pickupKm ||
        b.rating_avg - a.rating_avg ||
        a.user_id.localeCompare(b.user_id),
    );
}
