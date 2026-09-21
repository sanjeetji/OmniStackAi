import {
  Building2,
  Car,
  GraduationCap,
  HeartPulse,
  LayoutDashboard,
  Globe,
  Newspaper,
  Scissors,
  Server,
  ShoppingBag,
  Smartphone,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import type { TemplateAppKind } from "@/lib/control-plane";

/** The marketplace categories (the same list the agent-engine validator accepts). */
export const TEMPLATE_CATEGORIES: { id: string; label: string; icon: LucideIcon; blurb: string }[] = [
  { id: "mobility", label: "Mobility", icon: Car, blurb: "Ride-hailing, dispatch, fleets" },
  { id: "commerce", label: "Commerce", icon: ShoppingBag, blurb: "Marketplaces, stores, quick commerce" },
  { id: "healthcare", label: "Healthcare", icon: HeartPulse, blurb: "Clinics, appointments, telemedicine" },
  { id: "education", label: "Education", icon: GraduationCap, blurb: "Courses, learners, instructors" },
  { id: "real-estate", label: "Real estate", icon: Building2, blurb: "Listings, agents, viewings" },
  { id: "services", label: "Services", icon: Scissors, blurb: "Bookings, staff, home services" },
  { id: "fintech", label: "Fintech", icon: Wallet, blurb: "Wallets, merchants, payouts" },
  { id: "content", label: "Content", icon: Newspaper, blurb: "Publishing, writers, readers" },
];

export function categoryMeta(id: string) {
  return (
    TEMPLATE_CATEGORIES.find((category) => category.id === id) ?? {
      id,
      label: id,
      icon: Globe,
      blurb: "",
    }
  );
}

export const APP_KIND_META: Record<TemplateAppKind, { label: string; icon: LucideIcon; blurb: string }> = {
  web: { label: "Web app", icon: Globe, blurb: "The customer-facing website" },
  admin: { label: "Admin panel", icon: LayoutDashboard, blurb: "Operations and management" },
  pwa: { label: "Mobile app", icon: Smartphone, blurb: "Installable app for phones" },
  api: { label: "API", icon: Server, blurb: "One backend shared by every app" },
};

export function templateAssetUrl(slug: string, path: string): string {
  return `/template-assets/${encodeURIComponent(slug)}/${path.split("/").map(encodeURIComponent).join("/")}`;
}
