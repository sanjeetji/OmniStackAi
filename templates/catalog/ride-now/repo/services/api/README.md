# RideNow API

One API for the rider app, the driver app and the operations console. TypeScript that Node
(22.18 or newer) runs directly: there is no build step. Built on [Hono](https://hono.dev) and
PostgreSQL (`pg`).

## Run it

```bash
pnpm install
cp ../../.env.example ../../.env   # then set DATABASE_URL and JWT_SECRET
for f in migrations/*.sql seed/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
pnpm dev                            # http://127.0.0.1:4000/health
```

In the OmniStack preview all of this happens for you: a fresh database, migrations, demo data and
simulated drivers.

## Demo logins

| Role | Email | Password |
|---|---|---|
| Rider | asha@ridenow.test | Rider@2026 |
| Driver | ravi@ridenow.test | Driver@2026 |
| Admin | admin@ridenow.test | Admin@2026 |

In the preview, phone sign-in accepts the code `123456`. The mock card `4000 0000 0000 0002` is
always declined, so failure paths can be tried; other card numbers succeed.

## How it works

- **Trips** move through `requested → driver_assigned → driver_arrived → in_progress → completed`
  (or `cancelled` / `no_driver`). Every transition is checked against who is allowed to make it
  (`src/lib/trip-state.ts`) and logged in `trip_events`. The ride starts only with the rider's
  4-digit PIN.
- **Dispatch** (`src/services/dispatch.ts`) offers a trip to one driver at a time: real drivers
  first, then the nearest. An offer lasts 20 seconds. After 5 attempts the trip becomes
  `no_driver`. With `DEMO_SIMULATION=1`, simulated drivers accept and drive by themselves.
- **Fares** are upfront: `max(minimum, base + per km + per minute) × surge + booking fee − promo`
  (`src/lib/fare.ts`). Surge comes from the zone around the pickup. The platform funds promo
  discounts, so drivers are never paid less because of one.
- **Money** is a ledger (`wallet_transactions`) with a running balance. A completed wallet trip
  debits the rider, credits the driver net of commission, and books the commission to the platform
  account. A cash trip debits the commission from the driver instead.
- **Realtime**: `GET /stream?token=<access token>` (Server-Sent Events) sends `trip.updated`,
  `offer.new`, `offer.closed`, `driver.location`, `wallet.updated`, `notification` and (to admins)
  the live operations feed.
- **Providers**: payments, maps and SMS are mocks behind small interfaces in `src/providers/`.
  Implement one for Stripe or Razorpay, Google Maps, or Twilio to go live.

The complete endpoint list is at `GET /openapi.json`.

## Tests

```bash
pnpm test                                    # unit tests, no database needed
API_BASE=http://127.0.0.1:4000 node --test test/workflow.test.ts   # end to end, demo data loaded
```

## Demo data

`seed/001_demo.sql` is generated. Change `scripts/generate-seed.mjs`, then run
`pnpm seed:generate`. The script reuses the API's fare code, so every seeded trip is priced exactly
as the API would price it.
