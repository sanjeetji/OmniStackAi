// RideNow screenshot plan for scripts/capture-template-screens.mjs (R-530). Not part of the
// template repository users receive: it lives beside template.json, like media/.
//
// Run it against a freshly seeded database with DEMO_SIMULATION=1. It signs in as the demo users,
// captures every page of the rider, driver and ops apps, and stages live scenes through the API:
// a new rider books near MG Road, the demo driver (online) receives the offer, accepts and arrives.

export const users = {
  rider: { email: "asha@ridenow.test", password: "Rider@2026", role: "rider" },
  driver: { email: "ravi@ridenow.test", password: "Driver@2026", role: "driver" },
  admin: { email: "admin@ridenow.test", password: "Admin@2026", role: "admin" },
  // Registered by this plan, so the staged booking never clashes with Asha's history.
  guest: { email: "kavya.demo@ridenow.test", password: "Kavya@2026", role: "rider" },
};

export const storageKeys = {
  rider: "ridenow.rider.session",
  driver: "ridenow.driver.session",
  admin: "ridenow.admin.session",
};

const MG_ROAD = { name: "MG Road Metro", lat: 12.9756, lng: 77.6066 };
const KORAMANGALA = { name: "Forum Mall, Koramangala", lat: 12.9345, lng: 77.6111 };

async function firstTicket(api, as) {
  const { tickets } = await api(as, "GET", "/support/tickets");
  if (tickets.length) return tickets[0].id;
  const created = await api(as, "POST", "/support/tickets", { category: "payment", subject: "Charged twice for one ride", message: "I see two payments for my ride yesterday evening. Can you check?" });
  return created.id;
}

export default async function capture({ api, session, open, shot, render, image, sleep }) {
  // --- ids for detail pages -----------------------------------------------------------------------
  const riderTrips = (await api("rider", "GET", "/rider/trips?status=completed&limit=5")).trips;
  const driverTrips = (await api("driver", "GET", "/driver/trips?limit=10")).trips.filter((t) => t.status === "completed");
  const adminTrips = (await api("admin", "GET", "/admin/trips?status=completed&limit=20")).trips;
  const adminTrip = adminTrips.find((t) => t.promo_code) ?? adminTrips[0];
  const pendingDriver = (await api("admin", "GET", "/admin/drivers?status=pending&limit=1")).drivers[0];
  const openTicket = (await api("admin", "GET", "/admin/tickets?status=open")).tickets[0];
  const riderTicket = await firstTicket(api, "rider");
  const driverTicket = await firstTicket(api, "driver");
  const asha = (await session("rider")).user;

  // --- rider web app (signed out, then as Asha) ---------------------------------------------------
  await shot({ app: "rider", name: "landing", route: "/", title: "Landing page", description: "Hero with an instant fare check, how it works, vehicle types, safety, cities and FAQ.", highlight: true });
  await shot({ app: "rider", name: "login", route: "/login", title: "Sign in", description: "Password or phone OTP sign-in (the OTP is sent by a mock SMS provider in the demo)." });
  await shot({ app: "rider", name: "signup", route: "/signup", title: "Create an account", description: "New riders get a ₹100 welcome credit in their wallet." });
  await shot({
    app: "rider", name: "book", route: "/ride", as: "rider", highlight: true,
    title: "Book a ride",
    description: "Pickup and drop from search, saved places or the map; upfront fares for every vehicle type with surge, promo codes, and wallet or cash.",
    prepare: async (page) => {
      await page.locator("button.rounded-full.bg-canvas").first().click({ timeout: 8000 }).catch(() => undefined);
      await sleep(2500);
    },
  });
  await shot({ app: "rider", name: "trips", route: "/trips", as: "rider", title: "Trip history", description: "Every ride with its status, fare and rating." });
  await shot({ app: "rider", name: "trip-receipt", route: `/trips/${riderTrips[0].id}`, displayRoute: "/trips/[id]", as: "rider", title: "Trip receipt", description: "Route, driver, fare breakdown, payment, the rating given, and help with this ride." });
  await shot({ app: "rider", name: "wallet", route: "/wallet", as: "rider", title: "Wallet", description: "Balance, add money by card (mock payment provider) and every transaction." });
  await shot({ app: "rider", name: "places", route: "/places", as: "rider", title: "Saved places", description: "Home, work and favourites, picked on the map." });
  await shot({ app: "rider", name: "promos", route: "/promos", as: "rider", title: "Offers", description: "Promo codes the rider can use, with limits and expiry." });
  await shot({ app: "rider", name: "account", route: "/account", as: "rider", title: "Account", description: "Profile, phone and sign-out." });
  await shot({ app: "rider", name: "help", route: "/help", as: "rider", title: "Help centre", description: "Answers to common questions and the rider's support tickets." });
  await shot({ app: "rider", name: "ticket", route: `/help/${riderTicket}`, displayRoute: "/help/[id]", as: "rider", title: "Support conversation", description: "A ticket thread with RideNow support." });
  await shot({ app: "rider", name: "notifications", route: "/notifications", as: "rider", title: "Notifications", description: "Trip, wallet and support updates." });

  // --- driver PWA (phone), offline first ----------------------------------------------------------
  await shot({ app: "driver", device: "phone", name: "login", route: "/login", title: "Driver sign-in", description: "Sign in to go online; new drivers apply from here." });
  await shot({ app: "driver", device: "phone", name: "apply", route: "/apply", title: "Apply to drive", description: "Personal and vehicle details; operations review the documents before approval." });
  await shot({ app: "driver", device: "phone", name: "home-offline", route: "/", as: "driver", title: "Home, offline", description: "Today's earnings, trips, acceptance and rating, surge zones on the map, and the go-online switch." });
  await shot({ app: "driver", device: "phone", name: "earnings", route: "/earnings", as: "driver", title: "Earnings", description: "Day, week or month totals with a per-day chart, trips, online time and cash collected." });
  await shot({ app: "driver", device: "phone", name: "wallet", route: "/wallet", as: "driver", title: "Wallet and payouts", description: "Balance, withdraw to the bank (one request at a time) and the ledger." });
  await shot({ app: "driver", device: "phone", name: "trips", route: "/trips", as: "driver", title: "Trip history", description: "Past rides grouped by day with earnings." });
  await shot({ app: "driver", device: "phone", name: "trip-detail", route: `/trips/${driverTrips[0].id}`, displayRoute: "/trips/[id]", as: "driver", title: "Trip details", description: "Earning breakdown, commission and the rating received." });
  await shot({ app: "driver", device: "phone", name: "ratings", route: "/ratings", as: "driver", title: "Ratings", description: "Average rating, star breakdown, top compliments and recent comments." });
  await shot({ app: "driver", device: "phone", name: "account", route: "/account", as: "driver", title: "Account", description: "Profile, vehicle, document status with expiry warnings, and location mode." });
  await shot({ app: "driver", device: "phone", name: "help", route: "/help", as: "driver", title: "Help", description: "Driver support topics and tickets." });
  await shot({ app: "driver", device: "phone", name: "ticket", route: `/help/${driverTicket}`, displayRoute: "/help/[id]", as: "driver", title: "Support conversation", description: "A driver's ticket thread with operations." });
  await shot({ app: "driver", device: "phone", name: "notifications", route: "/notifications", as: "driver", title: "Notifications", description: "Payouts, account and trip updates." });

  // --- ops console (desktop) ----------------------------------------------------------------------
  await shot({ app: "admin", name: "login", route: "/login", title: "Ops sign-in", description: "Operations accounts only; rider and driver accounts are refused." });
  await shot({ app: "admin", name: "dashboard", route: "/", as: "admin", title: "Dashboard", description: "Trips, gross bookings, revenue and completion rate with trends, a 14-day chart, vehicle mix, top drivers and work queues.", highlight: true });
  await shot({ app: "admin", name: "trips", route: "/trips", as: "admin", title: "Trips", description: "Every ride request with status, vehicle and search filters, paging and CSV export." });
  await shot({ app: "admin", name: "trip-detail", route: `/trips/${adminTrip.id}`, displayRoute: "/trips/[id]", as: "admin", title: "Trip investigation", description: "Route map, status timeline, dispatch offers, fare breakdown, ledger lines and ratings, with cancel and refund." });
  await shot({ app: "admin", name: "riders", route: "/riders", as: "admin", title: "Riders", description: "Search riders with trips, spend, rating and wallet balance." });
  await shot({ app: "admin", name: "rider-detail", route: `/riders/${asha.id}`, displayRoute: "/riders/[id]", as: "admin", title: "Rider profile", description: "Wallet, recent trips, ledger and tickets; suspend or adjust the wallet." });
  await shot({ app: "admin", name: "drivers", route: "/drivers", as: "admin", title: "Drivers", description: "Status filters, vehicles, documents waiting, rating, acceptance and wallet." });
  if (pendingDriver) {
    await shot({ app: "admin", name: "driver-review", route: `/drivers/${pendingDriver.id}`, displayRoute: "/drivers/[id]", as: "admin", title: "Driver review", description: "Approve or reject each document, then approve the driver to go online." });
  }
  await shot({ app: "admin", name: "pricing", route: "/pricing", as: "admin", title: "Pricing", description: "Base, per km, per minute, minimum, booking fee and commission per vehicle type, with a live sample fare." });
  await shot({ app: "admin", name: "zones", route: "/zones", as: "admin", title: "Surge zones", description: "Zones on the city map with a surge multiplier and on/off switch each." });
  await shot({ app: "admin", name: "promos", route: "/promos", as: "admin", title: "Promo codes", description: "Usage and discount given per code; create, pause and resume." });
  await shot({ app: "admin", name: "payouts", route: "/payouts", as: "admin", title: "Payouts", description: "Driver withdrawal requests to pay or reject." });
  await shot({ app: "admin", name: "finance", route: "/finance", as: "admin", title: "Finance", description: "Platform balance, 30-day movements, money owed to drivers and rider wallet float." });
  await shot({ app: "admin", name: "support", route: "/tickets", as: "admin", title: "Support queue", description: "Rider and driver tickets by status and priority." });
  if (openTicket) {
    await shot({ app: "admin", name: "ticket", route: `/tickets/${openTicket.id}`, displayRoute: "/tickets/[id]", as: "admin", title: "Ticket thread", description: "Reply with canned answers, set priority and resolve." });
  }
  await shot({ app: "admin", name: "audit", route: "/audit", as: "admin", title: "Audit log", description: "Every refund, approval, pricing change and payout, with who did it." });
  await shot({ app: "admin", name: "settings", route: "/settings", as: "admin", title: "Settings", description: "Operator account, device preferences, and which providers are mocks and where real ones plug in." });

  // --- live scenes ---------------------------------------------------------------------------------
  await api(null, "POST", "/auth/register", { full_name: "Kavya Iyer", email: users.guest.email, password: users.guest.password }).catch(() => undefined);
  await api("driver", "POST", "/driver/online", { online: true, location: { lat: 12.9745, lng: 77.608 } });
  await shot({ app: "driver", device: "phone", name: "home-online", route: "/", as: "driver", title: "Home, online", description: "Online with the position shown to dispatch; requests arrive here." });

  const me = await api("driver", "GET", "/driver/me");
  const driverHome = await open({ app: "driver", device: "phone", route: "/", as: "driver" });
  const booked = await api("guest", "POST", "/rider/trips", { pickup: MG_ROAD, drop: KORAMANGALA, vehicle_type: me.vehicle.type, payment_method: "cash" });
  await driverHome.waitForSelector("[role='dialog']", { timeout: 20_000 }).catch(() => undefined);
  await sleep(1200);
  await shot({ app: "driver", device: "phone", name: "offer", route: "/", page: driverHome, title: "Incoming ride request", description: "Fare, your earning, pickup distance, trip length, rider rating and payment, with a countdown to accept or decline.", highlight: true });
  await driverHome.close();

  const { offer } = await api("driver", "GET", "/driver/offers/current");
  if (offer) await api("driver", "POST", `/driver/offers/${offer.id}/accept`);
  await sleep(1500);
  await shot({ app: "driver", device: "phone", name: "to-pickup", route: "/trip", as: "driver", title: "Heading to pickup", description: "The rider, pickup on the map, call, and “I've arrived”.", highlight: true });
  await shot({ app: "rider", name: "live-trip", route: `/trip/${booked.id}`, displayRoute: "/trip/[id]", as: "guest", title: "Live trip", description: "Driver and car details, the start PIN, the car moving on the map and the status timeline, with cancel and share.", highlight: true });
  await shot({ app: "admin", name: "live-map", route: "/live", as: "admin", title: "Live map", description: "Online drivers (free or on a trip), riders waiting for pickup and surge zones, updating as cars move.", highlight: true });
  await api("driver", "POST", `/driver/trips/${booked.id}/arrive`).catch(() => undefined);
  await sleep(1000);
  await shot({ app: "driver", device: "phone", name: "verify-pin", route: "/trip", as: "driver", title: "Verify the rider's PIN", description: "The ride starts only with the 4-digit PIN the rider sees in their app." });

  // --- cover ---------------------------------------------------------------------------------------
  const [ops, book, offerShot] = await Promise.all([image("media/admin/dashboard.jpg"), image("media/rider/book.jpg"), image("media/driver/offer.jpg")]);
  await render(coverHtml(ops, book, offerShot), { file: "cover.jpg", width: 1600, height: 1000 });
}

export function coverHtml(ops, book, offer) {
  return `<!doctype html><html><head><style>
    * { box-sizing: border-box; margin: 0; }
    body { width: 1600px; height: 1000px; overflow: hidden; font-family: -apple-system, "Segoe UI", sans-serif;
           background: radial-gradient(1200px 700px at 85% -10%, #ffcf6b 0%, rgba(255,176,32,0.35) 35%, transparent 60%), #0b1b2b; color: #fff; }
    .title { position: absolute; left: 80px; top: 72px; }
    .title h1 { font-size: 64px; font-weight: 800; letter-spacing: -0.02em; }
    .title h1 span { color: #ffb020; }
    .title p { margin-top: 10px; font-size: 24px; color: #c9d4e2; }
    .chips { position: absolute; left: 80px; top: 222px; display: flex; gap: 10px; }
    .chips b { font-size: 16px; font-weight: 600; padding: 8px 14px; border-radius: 999px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.18); }
    .win { position: absolute; border-radius: 14px; overflow: hidden; background: #fff; box-shadow: 0 40px 90px -20px rgba(0,0,0,0.6); }
    .win .bar { height: 30px; background: #eef1f5; display: flex; align-items: center; gap: 7px; padding-left: 14px; }
    .win .bar i { width: 11px; height: 11px; border-radius: 50%; background: #d3d8e0; }
    .win img { display: block; width: 100%; height: calc(100% - 30px); object-fit: cover; object-position: top; }
    .ops { left: 520px; top: 300px; width: 1000px; height: 640px; }
    .rider { left: 80px; top: 420px; width: 620px; height: 470px; }
    .phone { position: absolute; left: 1230px; top: 170px; width: 300px; height: 620px; border-radius: 44px; background: #111; padding: 12px; box-shadow: 0 40px 90px -20px rgba(0,0,0,0.7); }
    .phone img { width: 100%; height: 100%; object-fit: cover; object-position: top; border-radius: 34px; display: block; }
    .label { position: absolute; font-size: 15px; font-weight: 700; color: #0b1b2b; background: #ffb020; padding: 6px 12px; border-radius: 8px; }
  </style></head><body>
    <div class="title"><h1>Ride<span>Now</span></h1><p>Ride-hailing for one city: rider app, driver app and ops console on one API.</p></div>
    <div class="chips"><b>Live dispatch</b><b>Upfront fares + surge</b><b>Wallet &amp; payouts</b><b>Support desk</b></div>
    <div class="win ops"><div class="bar"><i></i><i></i><i></i></div><img src="${ops}"></div>
    <div class="win rider"><div class="bar"><i></i><i></i><i></i></div><img src="${book}"></div>
    <div class="phone"><img src="${offer}"></div>
    <div class="label" style="left:96px;top:392px">Rider web app</div>
    <div class="label" style="left:1246px;top:142px">Driver app</div>
    <div class="label" style="left:536px;top:268px">Ops console</div>
  </body></html>`;
}
