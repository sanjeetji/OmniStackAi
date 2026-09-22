import Link from "next/link";
import { ArrowRight, BadgeCheck, Clock3, Headset, KeyRound, MapPinned, Route, Share2, ShieldCheck, Sparkles, Wallet } from "lucide-react";
import type { VehicleType } from "@ridenow/shared";
import { inr } from "@ridenow/shared";
import { CityMap } from "@ridenow/shared/map";
import { Logo } from "@/components/logo";

export const dynamic = "force-dynamic";

const FALLBACK_TYPES: VehicleType[] = [
  { id: "bike", name: "Bike", description: "Beat the traffic, solo", seats: 1, base_fare: 20, per_km: 6, per_min: 1, min_fare: 35 },
  { id: "auto", name: "Auto", description: "Everyday rides, no haggling", seats: 3, base_fare: 30, per_km: 11, per_min: 1, min_fare: 45 },
  { id: "mini", name: "Mini", description: "Compact AC cars", seats: 4, base_fare: 40, per_km: 12, per_min: 1.5, min_fare: 80 },
  { id: "sedan", name: "Prime Sedan", description: "Roomy sedans, top-rated drivers", seats: 4, base_fare: 60, per_km: 15, per_min: 2, min_fare: 120 },
  { id: "xl", name: "XL", description: "SUVs for groups and luggage", seats: 6, base_fare: 90, per_km: 20, per_min: 2.5, min_fare: 180 },
];

async function vehicleTypes(): Promise<VehicleType[]> {
  try {
    const response = await fetch(`${process.env.API_URL ?? "http://127.0.0.1:4000"}/config`, { cache: "no-store" });
    if (!response.ok) return FALLBACK_TYPES;
    return ((await response.json()) as { vehicle_types: VehicleType[] }).vehicle_types;
  } catch {
    return FALLBACK_TYPES;
  }
}

const EMOJI: Record<string, string> = { bike: "🛵", auto: "🛺", mini: "🚗", sedan: "🚘", xl: "🚙" };

const HERO_CARS = [
  { id: "c1", kind: "car" as const, lat: 12.9762, lng: 77.6021, heading: 80 },
  { id: "c2", kind: "car" as const, lat: 12.9655, lng: 77.6318, heading: 210 },
  { id: "c3", kind: "car" as const, lat: 12.9468, lng: 77.6145, heading: 30, tone: "busy" as const },
  { id: "c4", kind: "car" as const, lat: 12.9815, lng: 77.6405, heading: 300 },
  { id: "p", kind: "pickup" as const, lat: 12.9719, lng: 77.6412, label: "Indiranagar" },
  { id: "d", kind: "drop" as const, lat: 12.9352, lng: 77.6245, label: "Koramangala" },
];

const FAQ = [
  ["How is my fare calculated?", "You see the full price before you book: a base fare plus distance and time, a small booking fee, and any surge in busy areas. What you see is what you pay."],
  ["How do I know it's the right car?", "Check the plate and driver photo in the app. Your ride starts only when you share your 4-digit PIN with the driver."],
  ["Can I pay in cash?", "Yes. Choose cash or your RideNow wallet when you book. The wallet also gets refunds and promo credits instantly."],
  ["What if I leave something in the car?", "Open the trip in your history and tap Get help. We'll connect you with the driver."],
  ["Is there a cancellation fee?", "Cancelling is free until your driver arrives. After they've waited more than 3 minutes, a ₹50 fee goes to the driver."],
];

export default async function Landing() {
  const types = await vehicleTypes();
  return (
    <div className="bg-canvas">
      <header className="mx-auto flex h-18 max-w-6xl items-center justify-between px-4">
        <Logo />
        <nav aria-label="Primary" className="flex items-center gap-2 text-sm font-semibold">
          <a href="#fares" className="hidden rounded-full px-4 py-2 text-ink-soft hover:bg-black/5 sm:inline">Fares</a>
          <a href="#safety" className="hidden rounded-full px-4 py-2 text-ink-soft hover:bg-black/5 sm:inline">Safety</a>
          <Link href="/login" className="rounded-full px-4 py-2 text-ink-soft hover:bg-black/5">Sign in</Link>
          <Link href="/signup" className="rounded-full bg-ink px-5 py-2.5 text-white hover:bg-ink-soft">Get started</Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-6 lg:grid-cols-[1.05fr_1fr] lg:pt-12">
        <div className="rn-rise">
          <span className="inline-flex items-center gap-2 rounded-full bg-amber-soft px-3 py-1 text-sm font-semibold text-amber-deep">
            <Sparkles className="size-4" aria-hidden="true" /> New here? First ride 50% off with WELCOME50
          </span>
          <h1 className="mt-5 text-balance text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl">
            Get there.<br />
            <span className="text-amber-deep">Right now.</span>
          </h1>
          <p className="mt-5 max-w-lg text-pretty text-lg text-ink-soft">
            Bikes, autos and cabs across Bengaluru, with upfront fares, live tracking and verified drivers. Book in seconds.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/ride" className="inline-flex h-14 items-center gap-2 rounded-full bg-amber px-8 text-base font-bold text-ink shadow-[0_10px_30px_-10px_rgb(229_148_0/0.9)] transition hover:bg-amber-deep">
              Book a ride <ArrowRight className="size-5" aria-hidden="true" />
            </Link>
            <a href="#how" className="inline-flex h-14 items-center rounded-full px-6 font-semibold text-ink-soft hover:bg-black/5">How it works</a>
          </div>
          <dl className="mt-10 grid max-w-md grid-cols-3 gap-4">
            {[["4.8★", "Average driver rating"], ["3 min", "Typical pickup time"], ["24×7", "Support"]].map(([value, label]) => (
              <div key={label}>
                <dt className="text-2xl font-extrabold">{value}</dt>
                <dd className="text-xs text-muted">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="relative">
          <div className="aspect-[4/3.4] overflow-hidden rounded-[32px] shadow-[var(--shadow-float)] ring-1 ring-black/5">
            <CityMap markers={HERO_CARS} route={[{ lat: 12.9719, lng: 77.6412 }, { lat: 12.9352, lng: 77.6245 }]} ariaLabel="RideNow cars near Indiranagar and Koramangala" />
          </div>
          <div className="rn-rise absolute -bottom-6 left-4 right-4 rounded-3xl bg-white p-4 shadow-[var(--shadow-float)] sm:left-8 sm:right-auto sm:w-80" style={{ animationDelay: "0.15s" }}>
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-2xl bg-ink text-xl">🚗</span>
              <div className="min-w-0 flex-1">
                <p className="font-bold">Mini · 4 min away</p>
                <p className="truncate text-sm text-muted">Indiranagar → Koramangala</p>
              </div>
              <p className="text-lg font-extrabold">₹142</p>
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="border-y border-line bg-white py-20">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">Three taps to your ride</h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              { icon: MapPinned, title: "Set your trip", body: "Search a place, tap the map, or pick a saved spot like Home or Work." },
              { icon: Route, title: "See the price first", body: "Compare bikes, autos and cabs with the full fare, the pickup time and any promo applied." },
              { icon: KeyRound, title: "Ride with your PIN", body: "Track your driver live. Share your PIN at pickup and you're off." },
            ].map(({ icon: Icon, title, body }, index) => (
              <div key={title} className="rounded-3xl bg-canvas p-6">
                <span className="grid size-12 place-items-center rounded-2xl bg-amber text-ink">
                  <Icon className="size-6" aria-hidden="true" />
                </span>
                <p className="mt-5 text-sm font-bold text-amber-deep">Step {index + 1}</p>
                <h3 className="mt-1 text-xl font-bold">{title}</h3>
                <p className="mt-2 text-pretty text-muted">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="fares" className="mx-auto max-w-6xl px-4 py-20">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">A ride for every trip</h2>
            <p className="mt-2 text-muted">Live fares. Surge applies only in busy zones, and you always see it before you book.</p>
          </div>
          <Link href="/ride" className="inline-flex items-center gap-1 font-semibold text-teal hover:underline">
            Check a fare <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {types.map((type) => (
            <li key={type.id} className="rounded-3xl bg-white p-5 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5">
              <span className="text-4xl" aria-hidden="true">{EMOJI[type.id] ?? "🚗"}</span>
              <p className="mt-3 text-lg font-bold">{type.name}</p>
              <p className="text-sm text-muted">{type.description}</p>
              <p className="mt-4 text-sm">
                From <span className="text-lg font-extrabold">{inr(type.min_fare)}</span>
              </p>
              <p className="text-xs text-muted">{inr(type.per_km)}/km · {type.seats} seat{type.seats > 1 ? "s" : ""}</p>
            </li>
          ))}
        </ul>
      </section>

      <section id="safety" className="bg-ink py-20 text-white">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 lg:grid-cols-2">
          <div>
            <h2 className="text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">Safety built into every ride</h2>
            <p className="mt-3 max-w-md text-white/70">Every driver is verified before their first trip, and every trip is tracked from pickup to drop.</p>
          </div>
          <ul className="grid gap-4 sm:grid-cols-2">
            {[
              { icon: BadgeCheck, title: "Verified drivers", body: "Licence, registration and insurance are checked, and ratings are reviewed weekly." },
              { icon: KeyRound, title: "Ride PIN", body: "The trip starts only when you give the driver your PIN." },
              { icon: Share2, title: "Share your trip", body: "Send a live link so family can follow your ride." },
              { icon: Headset, title: "24×7 safety line", body: "Safety tickets go to the front of the queue, around the clock." },
            ].map(({ icon: Icon, title, body }) => (
              <li key={title} className="rounded-3xl bg-white/5 p-5 ring-1 ring-white/10">
                <Icon className="size-6 text-amber" aria-hidden="true" />
                <p className="mt-3 font-bold">{title}</p>
                <p className="mt-1 text-sm text-white/65">{body}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-4 py-20 md:grid-cols-3">
        {[
          { icon: Wallet, title: "RideNow wallet", body: "Add money once, ride without thinking about change. Refunds land instantly." },
          { icon: Clock3, title: "Pickups in minutes", body: "Hundreds of drivers online across the city, from Hebbal to Electronic City." },
          { icon: ShieldCheck, title: "No haggling", body: "Autos at metered, upfront prices, even at night." },
        ].map(({ icon: Icon, title, body }) => (
          <div key={title} className="flex gap-4">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-teal-soft text-teal">
              <Icon className="size-5" aria-hidden="true" />
            </span>
            <div>
              <p className="font-bold">{title}</p>
              <p className="mt-1 text-sm text-muted">{body}</p>
            </div>
          </div>
        ))}
      </section>

      <section id="drive" className="mx-auto max-w-6xl px-4 pb-20">
        <div className="grid items-center gap-8 overflow-hidden rounded-[32px] bg-amber p-8 sm:p-12 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <h2 className="text-balance text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">Drive with RideNow</h2>
            <p className="mt-3 max-w-lg text-ink/75">Choose your hours, see your earnings after every trip, and withdraw to your bank any day. Bikes, autos and cars welcome.</p>
          </div>
          <ul className="grid gap-2 text-sm font-semibold text-ink">
            {["Weekly payouts, or any day on request", "Only 15–22% commission", "Promos are paid by us, never by you"].map((line) => (
              <li key={line} className="flex items-center gap-2 rounded-2xl bg-white/50 px-4 py-3">
                <BadgeCheck className="size-4" aria-hidden="true" /> {line}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="border-t border-line bg-white py-20">
        <div className="mx-auto max-w-3xl px-4">
          <h2 className="text-center text-3xl font-extrabold tracking-tight">Questions, answered</h2>
          <div className="mt-8 divide-y divide-line rounded-3xl border border-line">
            {FAQ.map(([question, answer]) => (
              <details key={question} className="group px-6 py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
                  {question}
                  <span className="text-2xl leading-none text-muted transition group-open:rotate-45" aria-hidden="true">+</span>
                </summary>
                <p className="mt-3 text-pretty text-muted">{answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <footer className="bg-canvas py-10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 text-sm text-muted">
          <Logo />
          <p>© {new Date().getFullYear()} RideNow Mobility Pvt. Ltd. · Bengaluru</p>
          <nav aria-label="Footer" className="flex gap-4">
            <Link href="/help" className="hover:text-ink">Help</Link>
            <a href="#safety" className="hover:text-ink">Safety</a>
            <a href="#fares" className="hover:text-ink">Fares</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
