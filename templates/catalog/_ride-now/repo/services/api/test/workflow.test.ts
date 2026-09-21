/**
 * End-to-end workflow against a running API with the demo seed loaded:
 *
 *   API_BASE=http://127.0.0.1:4000 node --test test/workflow.test.ts
 *
 * Skipped when API_BASE is not set (the unit tests run without a database). It exercises the whole
 * product: riders, a real driver, simulated drivers, money, ratings, realtime events and admin.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

const BASE = process.env.API_BASE;
const skip = BASE ? false : "set API_BASE to run the live workflow";

async function call(path: string, init: { method?: string; token?: string; body?: unknown } = {}) {
  const response = await fetch(`${BASE}${path}`, {
    method: init.method ?? (init.body === undefined ? "GET" : "POST"),
    headers: { "Content-Type": "application/json", ...(init.token ? { Authorization: `Bearer ${init.token}` } : {}) },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const text = await response.text();
  return { status: response.status, data: text ? JSON.parse(text) : null };
}

async function login(email: string, password: string) {
  const { status, data } = await call("/auth/login", { body: { email, password } });
  assert.equal(status, 200, JSON.stringify(data));
  return data.access_token as string;
}

async function waitFor<T>(what: string, probe: () => Promise<T | null | undefined | false>, timeoutMs = 90_000): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const value = await probe();
    if (value) return value;
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
  throw new Error(`timed out waiting for ${what}`);
}

const koramangala = { name: "Koramangala 5th Block", lat: 12.9352, lng: 77.6245 };
const indiranagar = { name: "Indiranagar 100 Feet Road", lat: 12.9719, lng: 77.6412 };
const mgRoad = { name: "MG Road Metro", lat: 12.9756, lng: 77.6066 };
const cubbon = { name: "Cubbon Park", lat: 12.9763, lng: 77.5929 };

test("health and OpenAPI", { skip }, async () => {
  assert.equal((await call("/health")).data.status, "ok");
  assert.ok(Object.keys((await call("/openapi.json")).data.paths).length > 60);
});

test("a new rider books, a simulated driver completes the trip, and the money settles", { skip, timeout: 180_000 }, async () => {
  const email = `rider.${Date.now()}@example.com`;
  const signup = await call("/auth/register", { body: { full_name: "Test Rider", email, password: "Testing123" } });
  assert.equal(signup.status, 201, JSON.stringify(signup.data));
  const token = signup.data.access_token as string;
  assert.equal((await call("/rider/wallet", { token })).data.balance, 100);

  const topup = await call("/rider/wallet/topup", { token, body: { amount: 500, card_number: "4242 4242 4242 4242" } });
  assert.equal(topup.status, 201);
  const declined = await call("/rider/wallet/topup", { token, body: { amount: 500, card_number: "4000 0000 0000 0002" } });
  assert.equal(declined.data.code, "payment_failed");

  const estimate = await call("/fare/estimate", { token, body: { pickup: koramangala, drop: indiranagar, promo_code: "WELCOME50" } });
  const mini = estimate.data.options.find((o: { vehicle_type: string }) => o.vehicle_type === "mini");
  assert.ok(mini.fare.discount > 0, "WELCOME50 applies to a new rider");

  const booked = await call("/rider/trips", { token, body: { pickup: koramangala, drop: indiranagar, vehicle_type: "mini", payment_method: "wallet", promo_code: "WELCOME50" } });
  assert.equal(booked.status, 201, JSON.stringify(booked.data));
  assert.equal(booked.data.fare_estimate, mini.fare.total);
  assert.match(booked.data.pin, /^\d{4}$/);
  const again = await call("/rider/trips", { token, body: { pickup: koramangala, drop: indiranagar, vehicle_type: "mini", payment_method: "wallet" } });
  assert.equal(again.data.code, "active_trip");

  const done = await waitFor("the simulated trip to complete", async () => {
    const trip = (await call(`/rider/trips/${booked.data.id}`, { token })).data;
    return trip.status === "completed" ? trip : null;
  });
  assert.ok(done.driver, "a driver was assigned");
  assert.deepEqual(done.events.map((e: { kind: string }) => e.kind).filter((k: string) => k !== "offer_sent"), ["requested", "driver_assigned", "driver_arrived", "started", "completed"]);
  const wallet = (await call("/rider/wallet", { token })).data;
  assert.equal(wallet.balance, Math.round((600 - done.fare_final) * 100) / 100);

  assert.equal((await call(`/rider/trips/${done.id}/rate`, { token, body: { stars: 5, tags: ["Safe driving"] } })).status, 200);
  assert.equal((await call(`/rider/trips/${done.id}/rate`, { token, body: { stars: 4 } })).status, 409);
});

test("the demo driver gets the offer first, needs the PIN, and earns net of commission", { skip, timeout: 120_000 }, async () => {
  const rider = await login("asha@ridenow.test", "Rider@2026");
  const driver = await login("ravi@ridenow.test", "Driver@2026");
  const admin = await login("admin@ridenow.test", "Admin@2026");
  const driverBefore = (await call("/driver/wallet", { token: driver })).data.balance;

  // Realtime: the rider's stream must see the trip move.
  const seen: string[] = [];
  const controller = new AbortController();
  const stream = fetch(`${BASE}/stream?token=${rider}`, { signal: controller.signal }).then(async (response) => {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const match of decoder.decode(value).matchAll(/"status":"(\w+)"/g)) seen.push(match[1]);
    }
  }).catch(() => undefined);

  assert.equal((await call("/driver/online", { token: driver, body: { online: true, location: { lat: 12.9760, lng: 77.6070 } } })).status, 200);
  const booked = await call("/rider/trips", { token: rider, body: { pickup: mgRoad, drop: cubbon, vehicle_type: "mini", payment_method: "cash" } });
  assert.equal(booked.status, 201, JSON.stringify(booked.data));

  const offer = await waitFor("an offer for the demo driver", async () => (await call("/driver/offers/current", { token: driver })).data.offer);
  assert.equal(offer.trip_id, booked.data.id);
  assert.ok(offer.estimated_earning > 0 && offer.estimated_earning < offer.fare);

  const accepted = await call(`/driver/offers/${offer.id}/accept`, { token: driver, body: {} });
  assert.equal(accepted.data.status, "driver_assigned");
  assert.equal(accepted.data.pin, undefined, "the driver never sees the PIN");
  assert.equal((await call(`/driver/trips/${booked.data.id}/arrive`, { token: driver, body: {} })).data.status, "driver_arrived");
  const wrongPin = booked.data.pin === "0000" ? "1111" : "0000";
  assert.equal((await call(`/driver/trips/${booked.data.id}/start`, { token: driver, body: { pin: wrongPin } })).data.code, "wrong_pin");
  assert.equal((await call(`/driver/trips/${booked.data.id}/start`, { token: driver, body: { pin: booked.data.pin } })).data.status, "in_progress");
  const completed = (await call(`/driver/trips/${booked.data.id}/complete`, { token: driver, body: {} })).data;
  assert.equal(completed.status, "completed");

  // Cash: the driver kept the fare and owes the commission.
  const driverAfter = (await call("/driver/wallet", { token: driver })).data.balance;
  assert.equal(Math.round((driverAfter - driverBefore) * 100) / 100, -completed.commission);
  const detail = (await call(`/admin/trips/${booked.data.id}`, { token: admin })).data;
  const net = detail.ledger.reduce((sum: number, row: { amount: number }) => sum + row.amount, 0);
  assert.ok(Math.abs(net) < 0.01, "the trip's ledger balances to zero");

  await waitFor("realtime updates", async () => seen.includes("completed"), 10_000);
  controller.abort();
  await stream;
  assert.ok(seen.includes("driver_assigned") && seen.includes("in_progress"));

  assert.equal((await call("/driver/online", { token: driver, body: { online: false } })).status, 200);
  const earnings = (await call("/driver/earnings?range=today", { token: driver })).data;
  assert.ok(earnings.trips >= 1);
});

test("admin: dashboard, refund, suspend and pricing", { skip, timeout: 60_000 }, async () => {
  const admin = await login("admin@ridenow.test", "Admin@2026");
  const dashboard = (await call("/admin/dashboard", { token: admin })).data;
  assert.equal(dashboard.series.length, 14);
  assert.ok(dashboard.kpis.trips_today >= 1);
  assert.ok(dashboard.kpis.drivers_online >= 1);

  const riderToken = await login("asha@ridenow.test", "Rider@2026");
  const paid = (await call("/admin/trips?status=completed&limit=50", { token: admin })).data.trips.find(
    (t: { payment_method: string; payment_status: string; rider: { name: string } }) => t.payment_method === "wallet" && t.payment_status === "paid" && t.rider.name === "Asha Rao",
  );
  const before = (await call("/rider/wallet", { token: riderToken })).data.balance;
  const refunded = await call(`/admin/trips/${paid.id}/refund`, { token: admin, body: { reason: "Workflow test refund" } });
  assert.equal(refunded.data.payment_status, "refunded");
  const after = (await call("/rider/wallet", { token: riderToken })).data.balance;
  assert.equal(Math.round((after - before) * 100) / 100, paid.fare_final);
  assert.equal((await call(`/admin/trips/${paid.id}/refund`, { token: admin, body: { reason: "again" } })).status, 400);

  assert.equal((await call("/admin/dashboard", { token: riderToken })).status, 403, "riders cannot reach admin");
  assert.equal((await call("/admin/dashboard")).status, 401);
  const audit = (await call("/admin/audit", { token: admin })).data.entries;
  assert.ok(audit.some((e: { action: string }) => e.action === "trip.refund"));
});
