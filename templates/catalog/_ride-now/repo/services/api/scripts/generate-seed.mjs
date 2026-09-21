// Generates seed/001_demo.sql: deterministic, realistic RideNow demo data for one city.
//
//   node scripts/generate-seed.mjs > seed/001_demo.sql
//
// It imports the API's own fare and route code, so every seeded trip is priced exactly as the live
// API would price it. Timestamps are written relative to now() so the data always looks recent,
// and every wallet ledger row carries the correct running balance.
import { scryptSync } from "node:crypto";
import { computeFare, splitFare } from "../src/lib/fare.ts";
import { money } from "../src/lib/money.ts";
import { estimateRoute } from "../src/providers/maps.ts";

// --- deterministic randomness -----------------------------------------------------------------
let state = 20260921;
function rand() {
  state |= 0;
  state = (state + 0x6d2b79f5) | 0;
  let t = Math.imul(state ^ (state >>> 15), 1 | state);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const pick = (items) => items[Math.floor(rand() * items.length)];
const between = (lo, hi) => lo + rand() * (hi - lo);
const intBetween = (lo, hi) => Math.floor(between(lo, hi + 1));
let uuidCounter = 0;
function uuid() {
  uuidCounter += 1;
  const hex = [...Array(32)].map(() => Math.floor(rand() * 16).toString(16)).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-a${hex.slice(17, 20)}-${hex.slice(20, 32)}`;
}

// --- SQL helpers ------------------------------------------------------------------------------
const q = (v) => (v === null || v === undefined ? "NULL" : typeof v === "number" ? String(v) : typeof v === "boolean" ? (v ? "TRUE" : "FALSE") : `'${String(v).replace(/'/g, "''")}'`);
const ago = (minutes) => (minutes === null ? "NULL" : `now() - interval '${Math.round(minutes * 60)} seconds'`);
const arr = (items) => `ARRAY[${items.map(q).join(", ")}]::text[]`;
const out = [];
function insert(table, columns, rows) {
  for (let i = 0; i < rows.length; i += 200) {
    const chunk = rows.slice(i, i + 200);
    out.push(`INSERT INTO ${table} (${columns.join(", ")}) VALUES\n${chunk.map((r) => `  (${r.join(", ")})`).join(",\n")};`);
  }
}
const password = (plain, email) => {
  const salt = Buffer.from(scryptSync(email, "ridenow-demo-salt", 16));
  return `scrypt$16384$${salt.toString("hex")}$${scryptSync(plain, salt, 32, { N: 16384 }).toString("hex")}`;
};

// --- reference data ---------------------------------------------------------------------------
const VEHICLES = [
  { id: "bike", name: "Bike", description: "Beat the traffic, solo", seats: 1, base_fare: 20, per_km: 6, per_min: 1, min_fare: 35, booking_fee: 5, commission_pct: 15, sort: 1 },
  { id: "auto", name: "Auto", description: "Everyday rides, no haggling", seats: 3, base_fare: 30, per_km: 11, per_min: 1, min_fare: 45, booking_fee: 5, commission_pct: 15, sort: 2 },
  { id: "mini", name: "Mini", description: "Compact AC cars", seats: 4, base_fare: 40, per_km: 12, per_min: 1.5, min_fare: 80, booking_fee: 10, commission_pct: 20, sort: 3 },
  { id: "sedan", name: "Prime Sedan", description: "Roomy sedans, top-rated drivers", seats: 4, base_fare: 60, per_km: 15, per_min: 2, min_fare: 120, booking_fee: 15, commission_pct: 20, sort: 4 },
  { id: "xl", name: "XL", description: "SUVs for groups and luggage", seats: 6, base_fare: 90, per_km: 20, per_min: 2.5, min_fare: 180, booking_fee: 20, commission_pct: 22, sort: 5 },
];
const PLACES = [
  ["MG Road Metro", "MG Road, Bengaluru 560001", 12.9756, 77.6066],
  ["Koramangala 5th Block", "Koramangala, Bengaluru 560095", 12.9352, 77.6245],
  ["Indiranagar 100 Feet Road", "Indiranagar, Bengaluru 560038", 12.9719, 77.6412],
  ["Kempegowda International Airport", "Devanahalli, Bengaluru 560300", 13.1986, 77.7066],
  ["Whitefield ITPL", "Whitefield, Bengaluru 560066", 12.9855, 77.7310],
  ["Electronic City Phase 1", "Electronic City, Bengaluru 560100", 12.8452, 77.6602],
  ["HSR Layout Sector 1", "HSR Layout, Bengaluru 560102", 12.9121, 77.6446],
  ["Jayanagar 4th Block", "Jayanagar, Bengaluru 560011", 12.9250, 77.5838],
  ["Hebbal Flyover", "Hebbal, Bengaluru 560024", 13.0358, 77.5970],
  ["Marathahalli Bridge", "Marathahalli, Bengaluru 560037", 12.9569, 77.7011],
  ["Bengaluru City Railway Station", "Majestic, Bengaluru 560023", 12.9784, 77.5690],
  ["Cubbon Park", "Kasturba Road, Bengaluru 560001", 12.9763, 77.5929],
  ["Lalbagh Botanical Garden", "Mavalli, Bengaluru 560004", 12.9507, 77.5848],
  ["UB City", "Vittal Mallya Road, Bengaluru 560001", 12.9716, 77.5963],
  ["Phoenix Marketcity", "Whitefield Road, Bengaluru 560048", 12.9975, 77.6960],
  ["Manyata Tech Park", "Nagawara, Bengaluru 560045", 13.0474, 77.6214],
  ["Bellandur Lake Road", "Bellandur, Bengaluru 560103", 12.9260, 77.6762],
  ["BTM Layout 2nd Stage", "BTM Layout, Bengaluru 560076", 12.9166, 77.6101],
  ["Malleshwaram 8th Cross", "Malleshwaram, Bengaluru 560003", 13.0035, 77.5693],
  ["Yeshwanthpur Junction", "Yeshwanthpur, Bengaluru 560022", 13.0232, 77.5500],
  ["Banashankari Temple", "Banashankari, Bengaluru 560070", 12.9153, 77.5736],
  ["JP Nagar 6th Phase", "JP Nagar, Bengaluru 560078", 12.9063, 77.5857],
  ["Sarjapur Road Wipro", "Sarjapur Road, Bengaluru 560035", 12.9101, 77.6879],
  ["Bannerghatta Road IIM", "Bannerghatta Road, Bengaluru 560076", 12.8950, 77.6010],
  ["Commercial Street", "Tasker Town, Bengaluru 560001", 12.9822, 77.6083],
  ["Brigade Road", "Ashok Nagar, Bengaluru 560025", 12.9719, 77.6070],
  ["Rajajinagar ISKCON", "Rajajinagar, Bengaluru 560010", 13.0098, 77.5511],
  ["Frazer Town Mosque Road", "Frazer Town, Bengaluru 560005", 12.9980, 77.6134],
  ["Domlur Flyover", "Domlur, Bengaluru 560071", 12.9610, 77.6387],
  ["KR Puram Railway Station", "KR Puram, Bengaluru 560036", 13.0003, 77.6780],
].map(([name, address, lat, lng]) => ({ name, address, lat, lng }));
const ZONES = [
  ["airport", "Airport", 13.1986, 77.7066, 3.0, 1.3],
  ["koramangala", "Koramangala", 12.9352, 77.6245, 2.0, 1.2],
  ["whitefield", "Whitefield", 12.9855, 77.7310, 3.0, 1.15],
  ["cbd", "Central (MG Road)", 12.9756, 77.6066, 2.5, 1.0],
  ["ecity", "Electronic City", 12.8452, 77.6602, 3.0, 1.0],
  ["indiranagar", "Indiranagar", 12.9719, 77.6412, 1.5, 1.1],
];
const FIRST = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Ananya", "Vikram", "Isha", "Arjun", "Saanvi", "Nikhil", "Pooja", "Karthik", "Lakshmi", "Siddharth", "Nandini", "Rahul", "Priya", "Aditya", "Kavya", "Farhan", "Zoya", "Tenzin", "Grace", "Joseph", "Fatima", "Harpreet", "Manoj", "Divya", "Suresh", "Ayesha", "Varun"];
const LAST = ["Sharma", "Iyer", "Reddy", "Nair", "Rao", "Gupta", "Menon", "Khan", "Das", "Pillai", "Joshi", "Hegde", "Shetty", "Kulkarni", "Singh", "Fernandes", "Bhat", "Chowdhury", "Patel", "Gowda"];
const COLORS = ["#5B5BD6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6"];
const CARS = {
  bike: [["Honda", "Activa 6G"], ["TVS", "Jupiter"], ["Bajaj", "Pulsar 150"], ["Hero", "Splendor+"]],
  auto: [["Bajaj", "RE Compact"], ["Piaggio", "Ape City"], ["TVS", "King Duramax"]],
  mini: [["Maruti", "WagonR"], ["Hyundai", "i10 Nios"], ["Tata", "Tiago"], ["Maruti", "Celerio"]],
  sedan: [["Maruti", "Dzire"], ["Honda", "Amaze"], ["Hyundai", "Aura"], ["Toyota", "Etios"]],
  xl: [["Toyota", "Innova Crysta"], ["Maruti", "Ertiga"], ["Kia", "Carens"]],
};
const PAINT = ["White", "Silver", "Grey", "Blue", "Red", "Black"];
const RIDER_TAGS_GOOD = ["Clean vehicle", "Safe driving", "Polite", "On time", "Knew the route", "Great music"];
const RIDER_TAGS_BAD = ["Late pickup", "Rash driving", "Took a longer route", "AC not working"];
const RIDER_COMMENTS = ["", "", "", "Smooth ride, thanks!", "Very professional.", "Reached on time for my meeting.", "Car was spotless.", "Helped with my luggage.", "Driver was a bit late but polite."];

const plate = () => `KA-${pick(["01", "02", "03", "04", "05", "41", "51", "53"])}-${String.fromCharCode(65 + intBetween(0, 25))}${String.fromCharCode(65 + intBetween(0, 25))}-${intBetween(1000, 9999)}`;
const name = () => `${pick(FIRST)} ${pick(LAST)}`;

// --- people -----------------------------------------------------------------------------------
const users = [];
const drivers = [];
const platform = { id: uuid(), role: "admin", full_name: "RideNow Platform", email: "platform@ridenow.local", phone: null, password: null, color: "#111827", created: 400 * 24 * 60 };
const admins = [
  { id: uuid(), role: "admin", full_name: "Neha Kapoor", email: "admin@ridenow.test", phone: "+919900000003", password: "Admin@2026", color: "#111827", created: 380 * 24 * 60 },
  { id: uuid(), role: "admin", full_name: "Imran Siddiqui", email: "ops@ridenow.test", phone: "+919900000004", password: "Admin@2026", color: "#0EA5E9", created: 200 * 24 * 60 },
];
const demoRider = { id: uuid(), role: "rider", full_name: "Asha Rao", email: "asha@ridenow.test", phone: "+919900000001", password: "Rider@2026", color: "#EC4899", created: 120 * 24 * 60 };
const demoDriverUser = { id: uuid(), role: "driver", full_name: "Ravi Kumar", email: "ravi@ridenow.test", phone: "+919900000002", password: "Driver@2026", color: "#10B981", created: 300 * 24 * 60 };
users.push(platform, ...admins, demoRider, demoDriverUser);

const riders = [demoRider];
for (let i = 0; i < 47; i += 1) {
  const full = name();
  const handle = full.toLowerCase().replace(/[^a-z]+/g, ".") + (i + 1);
  riders.push({ id: uuid(), role: "rider", full_name: full, email: `${handle}@example.com`, phone: `+9198${String(45000000 + i * 7919).padStart(8, "0")}`, password: null, color: pick(COLORS), created: between(5, 360) * 24 * 60 });
}
users.push(...riders.slice(1));

const driverPlan = [
  ["mini", 9], ["sedan", 7], ["auto", 7], ["bike", 5], ["xl", 3],
];
const demoDriver = { user: demoDriverUser, vehicle_type: "mini", make: "Maruti", model: "WagonR", color: "White", plate: "KA-01-RN-2026", status: "approved", online: false, simulated: false, lat: 12.9745, lng: 77.6080 };
drivers.push(demoDriver);
let simulatedLeft = { mini: 3, sedan: 2, auto: 2, bike: 1, xl: 1 };
for (const [type, count] of driverPlan) {
  for (let i = 0; i < count; i += 1) {
    const full = name();
    const user = { id: uuid(), role: "driver", full_name: full, email: `${full.toLowerCase().replace(/[^a-z]+/g, ".")}.${type}${i}@drivers.example.com`, phone: `+9197${String(31000000 + drivers.length * 6173).padStart(8, "0")}`, password: null, color: pick(COLORS), created: between(20, 600) * 24 * 60 };
    users.push(user);
    const [make, model] = pick(CARS[type]);
    const simulated = simulatedLeft[type] > 0;
    if (simulated) simulatedLeft[type] -= 1;
    const status = simulated ? "approved" : i === count - 1 && type !== "xl" ? "pending" : i === count - 2 && type === "mini" ? "suspended" : "approved";
    const spot = pick(PLACES.filter((p) => p.name !== "Kempegowda International Airport"));
    drivers.push({ user, vehicle_type: type, make, model, color: pick(PAINT), plate: plate(), status, online: simulated, simulated, lat: spot.lat + between(-0.012, 0.012), lng: spot.lng + between(-0.012, 0.012) });
  }
}

// --- trips, events, ratings and money ----------------------------------------------------------
const ledger = []; // { user, minutesAgo, kind, amount, trip, reference, note }
const trips = [];
const events = [];
const offers = [];
const ratings = [];
const promoUses = {};
const PROMOS = [
  { code: "WELCOME50", description: "50% off your first ride, up to ₹75", kind: "percent", value: 50, max_discount: 75, min_fare: 100, valid_until: null, usage_limit: null, per_user_limit: 1, active: true },
  { code: "RIDE20", description: "₹20 off rides above ₹120", kind: "flat", value: 20, max_discount: null, min_fare: 120, valid_until: -60 * 24 * 60, usage_limit: 5000, per_user_limit: 5, active: true },
  { code: "AIRPORT100", description: "₹100 off airport rides above ₹600", kind: "flat", value: 100, max_discount: null, min_fare: 600, valid_until: -90 * 24 * 60, usage_limit: 1000, per_user_limit: 2, active: true },
  { code: "WEEKEND15", description: "15% off weekend rides, up to ₹60", kind: "percent", value: 15, max_discount: 60, min_fare: 0, valid_until: -30 * 24 * 60, usage_limit: null, per_user_limit: 4, active: true },
  { code: "MONSOON25", description: "25% off during the monsoon sale", kind: "percent", value: 25, max_discount: 50, min_fare: 0, valid_until: 20 * 24 * 60, usage_limit: null, per_user_limit: 3, active: true },
  { code: "DIWALI30", description: "30% off festive rides (paused)", kind: "percent", value: 30, max_discount: 90, min_fare: 150, valid_until: -45 * 24 * 60, usage_limit: 2000, per_user_limit: 2, active: false },
];
const surgeAt = (p) => Math.max(1, ...ZONES.filter(([, , lat, lng, r]) => Math.hypot((lat - p.lat) * 111, (lng - p.lng) * 108.5) <= r).map((z) => z[5]));
const riderBalance = new Map();
const approvedDrivers = drivers.filter((d) => d.status === "approved" || d.status === "suspended");
let tripNo = 10001;

function riderPays(rider, minutes, amount) {
  const bal = riderBalance.get(rider.id) ?? 0;
  if (bal < amount) {
    const topup = amount > 600 ? 1000 : pick([300, 500, 500, 1000]);
    ledger.push({ user: rider.id, minutesAgo: minutes + between(30, 600), kind: "topup", amount: topup, trip: null, reference: `mock_${uuid().slice(0, 8)}`, note: `Card •••• ${intBetween(1000, 9999)}` });
    riderBalance.set(rider.id, bal + topup);
  }
  riderBalance.set(rider.id, (riderBalance.get(rider.id) ?? 0) - amount);
}

for (const rider of riders) {
  ledger.push({ user: rider.id, minutesAgo: rider.created, kind: "topup", amount: 100, trip: null, reference: "WELCOME", note: "Welcome credit" });
  riderBalance.set(rider.id, 100);
}

const TOTAL_TRIPS = 430;
for (let i = 0; i < TOTAL_TRIPS; i += 1) {
  const rider = i % 9 === 0 ? demoRider : pick(riders);
  // More trips recently, and at morning and evening peaks.
  const dayAgo = Math.floor(Math.pow(rand(), 1.3) * 30);
  const hour = pick([8, 8, 9, 9, 10, 12, 13, 17, 18, 18, 19, 19, 20, 21, 22, 23, 7, 15]);
  const minutesAgo = dayAgo * 24 * 60 + ((24 - hour) % 24) * 60 + between(0, 59) + 30;
  const pickup = pick(PLACES);
  let drop = pick(PLACES);
  while (drop === pickup) drop = pick(PLACES);
  const type = pick(["mini", "mini", "mini", "auto", "auto", "bike", "sedan", "sedan", "xl"]);
  const route = estimateRoute(pickup, drop);
  const pricing = VEHICLES.find((v) => v.id === type);
  const surge = surgeAt(pickup);
  let promo = null;
  let discount = 0;
  if (rand() < 0.18) {
    const candidate = pick(PROMOS.filter((p) => p.active));
    const gross = computeFare(pricing, route.distanceKm, route.durationMin, surge).total;
    const used = promoUses[`${rider.id}:${candidate.code}`] ?? 0;
    if (gross >= candidate.min_fare && used < candidate.per_user_limit) {
      discount = candidate.kind === "percent" ? Math.min((gross * candidate.value) / 100, candidate.max_discount ?? Infinity) : candidate.value;
      discount = money(Math.min(discount, gross));
      promo = candidate.code;
    }
  }
  const fare = computeFare(pricing, route.distanceKm, route.durationMin, surge, discount);
  const roll = rand();
  const status = roll < 0.84 ? "completed" : roll < 0.95 ? "cancelled" : "no_driver";
  const payment = rand() < 0.68 ? "wallet" : "cash";
  const pool = approvedDrivers.filter((d) => d.vehicle_type === type);
  const driver = status === "no_driver" ? null : i % 7 === 3 && type === "mini" ? demoDriver : pick(pool);
  const id = uuid();
  const code = `RN-${tripNo++}`;
  const t0 = minutesAgo;
  const assignedAgo = driver ? t0 - between(0.3, 1.5) : null;
  const arrivedAgo = driver ? assignedAgo - between(2, 9) : null;
  const cancelledBy = status === "cancelled" ? pick(["rider", "rider", "rider", "driver"]) : status === "no_driver" ? "system" : null;
  const startedAgo = status === "completed" ? arrivedAgo - between(0.5, 3) : null;
  const completedAgo = status === "completed" ? startedAgo - route.durationMin * between(0.85, 1.25) : null;
  const cancelledAgo = status === "cancelled" ? (cancelledBy === "driver" ? arrivedAgo - between(1, 5) : assignedAgo - between(0.5, 4)) : status === "no_driver" ? t0 - 2.5 : null;
  const { commission, driverEarning } = splitFare(fare.total, fare.discount, pricing.commission_pct);
  const trip = {
    id, code, rider: rider.id, driver: driver?.user.id ?? null, type, status, pickup, drop, route, surge, fare, promo, payment,
    t0, assignedAgo: status === "no_driver" ? null : assignedAgo, arrivedAgo: status === "completed" || (status === "cancelled" && cancelledBy === "driver") ? arrivedAgo : null,
    startedAgo, completedAgo, cancelledAgo, cancelledBy,
    commission: status === "completed" ? commission : null, driverEarning: status === "completed" ? driverEarning : null,
    reason: status === "cancelled" ? (cancelledBy === "driver" ? pick(["Rider not at pickup", "Vehicle problem"]) : pick(["Changed my plans", "Driver was too far", "Booked by mistake", "Found another ride"])) : status === "no_driver" ? "No driver accepted the ride." : null,
    pin: String(intBetween(1000, 9999)),
  };
  trips.push(trip);
  if (promo && status === "completed") promoUses[`${rider.id}:${promo}`] = (promoUses[`${rider.id}:${promo}`] ?? 0) + 1;

  events.push([id, "requested", "rider", { fare: fare.total, surge, vehicle_type: type }, t0]);
  if (driver) {
    offers.push([uuid(), id, driver.user.id, "accepted", money(between(0.4, 3.5)), t0 - 0.05, assignedAgo]);
    events.push([id, "offer_sent", "system", { driver_id: driver.user.id }, t0 - 0.05]);
    events.push([id, "driver_assigned", "driver", { driver_id: driver.user.id }, assignedAgo]);
  }
  if (trip.arrivedAgo !== null) events.push([id, "driver_arrived", "driver", {}, arrivedAgo]);
  if (status === "completed") {
    events.push([id, "started", "driver", {}, startedAgo]);
    events.push([id, "completed", "driver", { fare: fare.total, commission, driver_earning: driverEarning }, completedAgo]);
    if (payment === "wallet") {
      riderPays(rider, completedAgo, fare.total);
      ledger.push({ user: rider.id, minutesAgo: completedAgo, kind: "trip_payment", amount: -fare.total, trip: id, reference: code, note: `${pickup.name} → ${drop.name}` });
      ledger.push({ user: driver.user.id, minutesAgo: completedAgo, kind: "trip_earning", amount: driverEarning, trip: id, reference: code, note: "" });
    } else {
      ledger.push({ user: driver.user.id, minutesAgo: completedAgo, kind: "cash_commission", amount: money(fare.discount - commission), trip: id, reference: code, note: `cash fare ₹${fare.total}` });
    }
    ledger.push({ user: platform.id, minutesAgo: completedAgo, kind: "commission", amount: money(commission - fare.discount), trip: id, reference: code, note: payment === "cash" ? "cash trip" : fare.discount > 0 ? `after ₹${fare.discount} promo` : "" });
    if (rand() < 0.78) {
      const stars = rand() < 0.72 ? 5 : rand() < 0.75 ? 4 : intBetween(2, 3);
      const tags = stars >= 4 ? [pick(RIDER_TAGS_GOOD), ...(rand() < 0.4 ? [pick(RIDER_TAGS_GOOD)] : [])] : [pick(RIDER_TAGS_BAD)];
      ratings.push([uuid(), id, rider.id, driver.user.id, stars, [...new Set(tags)], pick(RIDER_COMMENTS), completedAgo - between(1, 30)]);
    }
    if (rand() < 0.85) ratings.push([uuid(), id, driver.user.id, rider.id, rand() < 0.85 ? 5 : 4, [], "", completedAgo - between(0.5, 5)]);
  } else if (status === "cancelled") {
    events.push([id, "cancelled", cancelledBy, { reason: trip.reason, fee: 0 }, cancelledAgo]);
  } else {
    events.push([id, "no_driver", "system", { attempts: 5 }, cancelledAgo]);
  }
}

// Driver ratings and acceptance follow from the generated history.
for (const d of drivers) {
  const received = ratings.filter((r) => r[3] === d.user.id);
  d.rating_count = received.length;
  d.rating_avg = received.length ? Math.round((received.reduce((s, r) => s + r[4], 0) / received.length) * 100) / 100 : 5;
  const accepted = offers.filter((o) => o[2] === d.user.id).length;
  d.offers_accepted = accepted;
  d.offers_received = accepted + Math.round(accepted * between(0.04, 0.2));
}

// Payouts: weekly paid payouts for busy drivers; the demo driver has one waiting for approval.
const payouts = [];
for (const d of drivers.filter((x) => x.status === "approved")) {
  const earned = ledger.filter((l) => l.user === d.user.id).reduce((s, l) => s + l.amount, 0);
  if (earned > 1500) {
    const amount = money(Math.floor(earned * 0.55 / 100) * 100);
    const paidAgo = between(3, 12) * 24 * 60;
    const pid = uuid();
    payouts.push([pid, d.user.id, amount, "paid", "4417", `NEFT${intBetween(10000000, 99999999)}`, paidAgo + 60 * 26, paidAgo]);
    ledger.push({ user: d.user.id, minutesAgo: paidAgo + 60 * 26, kind: "payout", amount: -amount, trip: null, reference: pid, note: "Payout requested" });
  }
}
{
  const earned = ledger.filter((l) => l.user === demoDriver.user.id).reduce((s, l) => s + l.amount, 0);
  const amount = money(Math.max(100, Math.floor(earned * 0.5 / 50) * 50));
  const pid = uuid();
  payouts.push([pid, demoDriver.user.id, amount, "requested", "4417", "", 60 * 5, null]);
  ledger.push({ user: demoDriver.user.id, minutesAgo: 60 * 5, kind: "payout", amount: -amount, trip: null, reference: pid, note: "Payout requested" });
}

// --- write SQL ---------------------------------------------------------------------------------
out.push("-- RideNow demo data. Generated by scripts/generate-seed.mjs; regenerate instead of editing.");
out.push("-- Demo logins: rider asha@ridenow.test / Rider@2026, driver ravi@ridenow.test / Driver@2026, admin admin@ridenow.test / Admin@2026");
insert("vehicle_types", ["id", "name", "description", "seats", "base_fare", "per_km", "per_min", "min_fare", "booking_fee", "commission_pct", "sort"],
  VEHICLES.map((v) => [q(v.id), q(v.name), q(v.description), v.seats, v.base_fare, v.per_km, v.per_min, v.min_fare, v.booking_fee, v.commission_pct, v.sort]));
insert("zones", ["id", "name", "center_lat", "center_lng", "radius_km", "surge"], ZONES.map((z) => z.map(q)));
insert("users", ["id", "role", "full_name", "email", "phone", "password_hash", "avatar_color", "status", "created_at", "last_login_at"],
  users.map((u) => [q(u.id), q(u.role), q(u.full_name), q(u.email), q(u.phone), q(u.password ? password(u.password, u.email) : null), q(u.color),
    q(drivers.find((d) => d.user === u)?.status === "suspended" ? "suspended" : "active"), ago(u.created), u.password ? ago(between(60, 60 * 30)) : "NULL"]));
insert("drivers", ["user_id", "vehicle_type", "vehicle_make", "vehicle_model", "vehicle_color", "plate", "license_no", "status", "online", "simulated", "lat", "lng", "heading", "last_seen_at", "rating_avg", "rating_count", "offers_received", "offers_accepted", "joined_at"],
  drivers.map((d) => [q(d.user.id), q(d.vehicle_type), q(d.make), q(d.model), q(d.color), q(d.plate), q(`KA${intBetween(10, 99)}${intBetween(2008, 2022)}000${intBetween(1000, 9999)}`),
    q(d.status), q(d.online), q(d.simulated), d.lat.toFixed(6), d.lng.toFixed(6), intBetween(0, 359), d.online || d.simulated ? "now()" : ago(between(60, 5000)),
    d.rating_avg, d.rating_count, d.offers_received, d.offers_accepted, ago(d.user.created)]));
const DOC_KINDS = ["license", "registration", "insurance", "photo"];
insert("driver_documents", ["driver_id", "kind", "number", "status", "expires_on", "note"],
  drivers.flatMap((d, index) => DOC_KINDS.map((kind) => {
    const status = d.status === "pending" ? (kind === "photo" ? "approved" : "pending") : d.status === "suspended" && kind === "insurance" ? "rejected" : "approved";
    const expires = kind === "photo" ? "NULL" : kind === "insurance" && index % 6 === 1 ? "(current_date + 12)" : `(current_date + ${intBetween(120, 1400)})`;
    return [q(d.user.id), q(kind), q(kind === "photo" ? "" : `${kind.slice(0, 3).toUpperCase()}-${intBetween(100000, 999999)}`), q(status), expires, q(status === "rejected" ? "Policy has lapsed; upload the renewed policy." : "")];
  })));
insert("places", ["user_id", "label", "name", "address", "lat", "lng"], PLACES.map((p) => ["NULL", q("Landmark"), q(p.name), q(p.address), p.lat, p.lng]));
insert("places", ["user_id", "label", "name", "address", "lat", "lng"], [
  [q(demoRider.id), q("Home"), q("Koramangala 5th Block"), q("Flat 302, Maple Residency, Koramangala"), 12.9348, 77.6239],
  [q(demoRider.id), q("Work"), q("UB City"), q("Level 9, UB City Tower, Vittal Mallya Road"), 12.9716, 77.5963],
  [q(demoRider.id), q("Gym"), q("Indiranagar 100 Feet Road"), q("Cult.fit, 100 Feet Road"), 12.9719, 77.6412],
]);
insert("promo_codes", ["code", "description", "kind", "value", "max_discount", "min_fare", "valid_until", "usage_limit", "per_user_limit", "used_count", "active"],
  PROMOS.map((p) => [q(p.code), q(p.description), q(p.kind), p.value, q(p.max_discount), p.min_fare, p.valid_until === null ? "NULL" : ago(p.valid_until),
    q(p.usage_limit), p.per_user_limit, trips.filter((t) => t.promo === p.code && t.status === "completed").length, q(p.active)]));
insert("trips", ["id", "code", "rider_id", "driver_id", "vehicle_type", "status", "pickup_name", "pickup_lat", "pickup_lng", "drop_name", "drop_lat", "drop_lng", "distance_km", "duration_min", "surge", "fare_estimate", "promo_code", "discount", "fare_final", "commission", "driver_earning", "payment_method", "payment_status", "pin", "cancel_reason", "cancelled_by", "dispatch_attempts", "requested_at", "assigned_at", "arrived_at", "started_at", "completed_at", "cancelled_at"],
  trips.map((t) => [q(t.id), q(t.code), q(t.rider), q(t.driver), q(t.type), q(t.status), q(t.pickup.name), t.pickup.lat, t.pickup.lng, q(t.drop.name), t.drop.lat, t.drop.lng,
    t.route.distanceKm, t.route.durationMin, t.surge, t.fare.total, q(t.promo), t.fare.discount, t.status === "completed" ? t.fare.total : "NULL", q(t.commission), q(t.driverEarning),
    q(t.payment), q(t.status === "completed" ? "paid" : "waived"), q(t.pin), q(t.reason), q(t.cancelledBy), t.status === "no_driver" ? 5 : 1,
    ago(t.t0), ago(t.assignedAgo), ago(t.arrivedAgo), ago(t.startedAgo), ago(t.completedAgo), ago(t.cancelledAgo)]));
out.push(`SELECT setval('trip_code_seq', ${tripNo});`);
insert("trip_events", ["trip_id", "kind", "actor", "detail", "at"], events.map(([trip, kind, actor, detail, at]) => [q(trip), q(kind), q(actor), `${q(JSON.stringify(detail))}::jsonb`, ago(at)]));
insert("ride_offers", ["id", "trip_id", "driver_id", "status", "pickup_km", "offered_at", "expires_at", "responded_at"],
  offers.map(([id, trip, driver, status, km, at, responded]) => [q(id), q(trip), q(driver), q(status), km, ago(at), ago(at - 20 / 60), ago(responded)]));
insert("ratings", ["id", "trip_id", "from_user", "to_user", "stars", "tags", "comment", "created_at"],
  ratings.map(([id, trip, from, to, stars, tags, comment, at]) => [q(id), q(trip), q(from), q(to), stars, arr(tags), q(comment), ago(at)]));
insert("payouts", ["id", "driver_id", "amount", "status", "bank_last4", "reference", "requested_at", "processed_at"],
  payouts.map(([id, driver, amount, status, last4, ref, requested, processed]) => [q(id), q(driver), amount, q(status), q(last4), q(ref), ago(requested), ago(processed)]));

// The ledger, in time order per account, with exact running balances.
ledger.sort((a, b) => b.minutesAgo - a.minutesAgo);
const balances = new Map();
const ledgerRows = ledger.map((l) => {
  const next = money((balances.get(l.user) ?? 0) + l.amount);
  balances.set(l.user, next);
  return [q(l.user), q(l.trip), q(l.kind), money(l.amount), next, q(l.reference), q(l.note), ago(l.minutesAgo)];
});
insert("wallet_transactions", ["user_id", "trip_id", "kind", "amount", "balance_after", "reference", "note", "created_at"], ledgerRows);
insert("wallets", ["user_id", "balance"], users.map((u) => [q(u.id), balances.get(u.id) ?? 0]));

// Support tickets with realistic threads.
const TICKETS = [
  [demoRider, "payment", "Charged twice for RN ride to UB City", "open", "high", ["I see two debits in my wallet for the same ride this morning.", "Sorry about that, Asha. We're checking with our payments team and will update you shortly."]],
  [demoRider, "lost_item", "Left my umbrella in the car", "resolved", "normal", ["I left a black umbrella in the back seat.", "Your driver has it and will drop it at the Koramangala hub. You can collect it any time."]],
  [pick(riders), "safety", "Driver was driving very fast on ORR", "open", "urgent", ["The driver was over-speeding on the Outer Ring Road and did not slow down when asked."]],
  [pick(riders), "driver", "Driver asked me to cancel and pay cash", "pending", "high", ["The driver called and asked me to cancel the booking and pay him directly.", "Thank you for reporting this. We've warned the driver and are reviewing his account."]],
  [pick(riders), "app", "App stuck on 'Finding your driver'", "resolved", "normal", ["It kept searching for 5 minutes.", "We had a brief outage in the Whitefield area. It's fixed now; sorry for the trouble."]],
  [pick(riders), "payment", "Promo WELCOME50 not applied", "resolved", "low", ["My first ride didn't get the 50% discount.", "The ride was below the ₹100 minimum for WELCOME50. We've added ₹40 credit as a goodwill gesture."]],
  [demoDriverUser, "payment", "Payout not received yet", "open", "normal", ["I requested a payout this morning. When will it reach my account?"]],
  [pick(drivers.filter((d) => !d.simulated)).user, "app", "Navigation shows the wrong pickup pin", "pending", "normal", ["The pickup pin at Manyata Tech Park is on the wrong gate.", "Thanks! We've moved it to Gate 5 and will confirm once the change is live."]],
  [pick(riders), "other", "Can I book a ride for my parents?", "resolved", "low", ["Can I book a ride for someone else and track it?", "Yes. Book with their pickup and drop; you'll see the live trip and can share the PIN with them."]],
  [pick(riders), "driver", "Driver was very helpful with luggage", "resolved", "low", ["Just wanted to say the driver was excellent at the airport.", "Thank you! We've passed on your kind words."]],
];
TICKETS.forEach(([user, category, subject, status, priority, messages], index) => {
  const id = uuid();
  const created = between(60, 20 * 24 * 60);
  const trip = trips.find((t) => t.rider === user.id || t.driver === user.id);
  insert("support_tickets", ["id", "code", "user_id", "trip_id", "category", "subject", "status", "priority", "created_at", "updated_at"],
    [[q(id), q(`T-${5001 + index}`), q(user.id), q(trip?.id ?? null), q(category), q(subject), q(status), q(priority), ago(created), ago(created - 30 * messages.length)]]);
  insert("ticket_messages", ["ticket_id", "author_id", "body", "created_at"],
    messages.map((body, i) => [q(id), q(i % 2 === 0 ? user.id : admins[i % admins.length].id), q(body), ago(created - i * 30)]));
});
out.push(`SELECT setval('ticket_code_seq', ${5001 + TICKETS.length});`);

insert("notifications", ["user_id", "kind", "title", "body", "read_at", "created_at"], [
  [q(demoRider.id), q("promo"), q("MONSOON25 is live"), q("25% off rides this week, up to ₹50."), "NULL", ago(90)],
  [q(demoRider.id), q("trip"), q("Thanks for riding with RideNow"), q("Rate your last trip to help drivers improve."), ago(300), ago(600)],
  [q(demoRider.id), q("support"), q("New reply on T-5001"), q("We're checking with our payments team."), "NULL", ago(45)],
  [q(demoDriverUser.id), q("payout"), q("Payout requested"), q("Your payout will reach the account ending 4417 within a day."), "NULL", ago(300)],
  [q(demoDriverUser.id), q("earning"), q("Weekly summary"), q("You completed more trips than last week. Keep it up!"), ago(1500), ago(2000)],
]);
insert("audit_log", ["actor_id", "action", "entity", "entity_id", "detail", "at"], [
  [q(admins[0].id), q("pricing.update"), q("vehicle_type"), q("sedan"), `'{"per_km": 15}'::jsonb`, ago(9 * 24 * 60)],
  [q(admins[1].id), q("zone.update"), q("zone"), q("airport"), `'{"surge": 1.3, "active": true}'::jsonb`, ago(2 * 24 * 60)],
  [q(admins[0].id), q("promo.pause"), q("promo"), q("DIWALI30"), `'{}'::jsonb`, ago(24 * 60)],
  [q(admins[0].id), q("driver.suspended"), q("driver"), q(drivers.find((d) => d.status === "suspended")?.user.id ?? ""), `'{"from": "approved"}'::jsonb`, ago(3 * 24 * 60)],
]);

process.stdout.write(`${out.join("\n\n")}\n`);
process.stderr.write(`riders ${riders.length}, drivers ${drivers.length} (${drivers.filter((d) => d.simulated).length} simulated), trips ${trips.length}, ratings ${ratings.length}, ledger ${ledgerRows.length}\n`);
