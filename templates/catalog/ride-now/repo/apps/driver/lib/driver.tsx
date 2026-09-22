"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ACTIVE_STATUSES, ApiError, useStream, type LatLng, type Offer, type Session, type Trip, type User } from "@ridenow/shared";
import { api } from "./api";

export interface DriverProfile {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  avatar_color: string;
  status: "pending" | "approved" | "suspended";
  online: boolean;
  location: (LatLng & { heading: number }) | null;
  vehicle: { type: string; type_name: string; make: string; model: string; color: string; plate: string };
  license_no: string;
  rating: number;
  rating_count: number;
  acceptance_rate: number;
  commission_pct: number;
  joined_at: string;
  documents: { id: string; kind: string; number: string; status: string; expires_on: string | null; note: string }[];
}

export type LocationMode = "simulated" | "gps";

interface DriverState {
  user: User | null;
  ready: boolean;
  profile: DriverProfile | null;
  online: boolean;
  position: (LatLng & { heading: number }) | null;
  mode: LocationMode;
  offer: Offer | null;
  trip: Trip | null;
  error: string | null;
  setMode: (mode: LocationMode) => void;
  goOnline: (online: boolean) => Promise<void>;
  accept: () => Promise<void>;
  decline: () => Promise<void>;
  refresh: () => Promise<void>;
  setTrip: (trip: Trip | null) => void;
  signIn: (session: Session) => void;
  signOut: () => Promise<void>;
  clearError: () => void;
}

const Ctx = createContext<DriverState | null>(null);
const CITY = { lat: 12.9716, lng: 77.5946, heading: 0 };
const REPORT_MS = 3000;

function stepToward(from: LatLng, to: LatLng): LatLng & { heading: number; remainingKm: number } {
  const dLat = to.lat - from.lat;
  const dLng = to.lng - from.lng;
  const kmLat = dLat * 110.574;
  const kmLng = dLng * 111.32 * Math.cos((from.lat * Math.PI) / 180);
  const remaining = Math.hypot(kmLat, kmLng);
  const heading = ((Math.atan2(kmLng, kmLat) * 180) / Math.PI + 360) % 360;
  if (remaining < 0.05) return { ...to, heading, remainingKm: 0 };
  const step = Math.min(remaining, Math.max(0.12, remaining / 8));
  const f = step / remaining;
  return { lat: from.lat + dLat * f, lng: from.lng + dLng * f, heading, remainingKm: remaining - step };
}

export function DriverProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [online, setOnline] = useState(false);
  const [position, setPosition] = useState<(LatLng & { heading: number }) | null>(null);
  const [mode, setModeState] = useState<LocationMode>("simulated");
  const [offer, setOffer] = useState<Offer | null>(null);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [error, setError] = useState<string | null>(null);
  const positionRef = useRef(position);
  positionRef.current = position;
  const tripRef = useRef(trip);
  tripRef.current = trip;

  useEffect(() => {
    setUser(api.session()?.user ?? null);
    try {
      const saved = window.localStorage.getItem("ridenow.driver.location-mode");
      if (saved === "gps" || saved === "simulated") setModeState(saved);
    } catch {
      // Storage blocked: keep the default.
    }
    setReady(true);
    const onChange = (event: Event) => setUser((event as CustomEvent<Session | null>).detail?.user ?? null);
    window.addEventListener("ridenow:session", onChange);
    return () => window.removeEventListener("ridenow:session", onChange);
  }, []);

  const refresh = useCallback(async () => {
    if (!api.session()) return;
    try {
      const me = await api.get<DriverProfile>("/driver/me");
      setProfile(me);
      setOnline(me.online);
      setPosition((current) => current ?? me.location ?? CITY);
      const active = await api.get<{ trip: Trip | null }>("/driver/trips/active");
      setTrip(active.trip);
      const pending = await api.get<{ offer: Offer | null }>("/driver/offers/current");
      setOffer(pending.offer);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) setError("This account is not a driver account.");
    }
  }, []);

  useEffect(() => {
    if (user) void refresh();
    else {
      setProfile(null);
      setOffer(null);
      setTrip(null);
    }
  }, [user, refresh]);

  useStream(api, {
    "offer.new": (next: Offer) => setOffer(next),
    "offer.closed": (closed: { id: string }) => setOffer((current) => (current?.id === closed.id ? null : current)),
    "trip.updated": (updated: Trip) => {
      setTrip((current) => {
        if (ACTIVE_STATUSES.includes(updated.status)) return updated;
        if (current?.id === updated.id) return updated; // keep the finished trip for the summary
        return current;
      });
    },
  }, Boolean(user));

  // Poll as a fallback while online: offers expire in 20 s, so do not rely on the stream alone.
  useEffect(() => {
    if (!user || !online || trip && ACTIVE_STATUSES.includes(trip.status)) return;
    const timer = setInterval(() => {
      api.get<{ offer: Offer | null }>("/driver/offers/current").then((r) => setOffer(r.offer)).catch(() => undefined);
    }, 4000);
    return () => clearInterval(timer);
  }, [user, online, trip]);

  // Device GPS.
  useEffect(() => {
    if (!online || mode !== "gps" || typeof navigator === "undefined" || !navigator.geolocation) return;
    const watch = navigator.geolocation.watchPosition(
      (p) => setPosition({ lat: p.coords.latitude, lng: p.coords.longitude, heading: p.coords.heading ?? 0 }),
      () => setError("Location permission was denied. Switch to simulated location in Account."),
      { enableHighAccuracy: true, maximumAge: 5000 },
    );
    return () => navigator.geolocation.clearWatch(watch);
  }, [online, mode]);

  // Report the position; in simulated mode, also drive toward the current target.
  useEffect(() => {
    if (!user || !online) return;
    const timer = setInterval(() => {
      let here = positionRef.current;
      if (!here) return;
      const current = tripRef.current;
      if (mode === "simulated" && current && ["driver_assigned", "in_progress"].includes(current.status)) {
        const target = current.status === "driver_assigned" ? current.pickup : current.drop;
        const next = stepToward(here, target);
        here = { lat: next.lat, lng: next.lng, heading: next.heading };
        setPosition(here);
      }
      api.post("/driver/location", { lat: here.lat, lng: here.lng, heading: here.heading }).catch(() => undefined);
    }, REPORT_MS);
    return () => clearInterval(timer);
  }, [user, online, mode]);

  const value: DriverState = {
    user,
    ready,
    profile,
    online,
    position,
    mode,
    offer,
    trip,
    error,
    clearError: () => setError(null),
    setMode: (next) => {
      setModeState(next);
      try {
        window.localStorage.setItem("ridenow.driver.location-mode", next);
      } catch {
        // ignore
      }
    },
    setTrip,
    refresh,
    async goOnline(next) {
      setError(null);
      try {
        const location = positionRef.current ?? CITY;
        await api.post("/driver/online", { online: next, location: { lat: location.lat, lng: location.lng } });
        setOnline(next);
        if (!next) setOffer(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Couldn't change your status.");
      }
    },
    async accept() {
      if (!offer) return;
      try {
        const accepted = await api.post<Trip>(`/driver/offers/${offer.id}/accept`);
        setTrip(accepted);
        setOffer(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Couldn't accept the ride.");
        setOffer(null);
      }
    },
    async decline() {
      if (!offer) return;
      const id = offer.id;
      setOffer(null);
      await api.post(`/driver/offers/${id}/decline`).catch(() => undefined);
    },
    signIn: (session) => api.signIn(session),
    async signOut() {
      if (online) await api.post("/driver/online", { online: false }).catch(() => undefined);
      await api.signOut();
      setOnline(false);
    },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDriver(): DriverState {
  const value = useContext(Ctx);
  if (!value) throw new Error("useDriver must be used inside DriverProvider");
  return value;
}

export function useRequireDriver(): DriverState {
  const state = useDriver();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (state.ready && !state.user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [state.ready, state.user, router, pathname]);
  return state;
}
