# RideNow

Ride-hailing for one city (Bengaluru, INR): three apps on one API and one PostgreSQL database.

| Folder | What it is |
|---|---|
| `apps/rider` | The rider website: book, track the ride live, pay, rate, wallet, offers, help. |
| `apps/driver` | The driver app (installable PWA, phone-first): go online, take offers, run the trip, earnings and payouts. |
| `apps/admin` | RideNow Ops, the operations console: live map, trips, riders, drivers, pricing, surge, promos, payouts, finance, support, audit. |
| `services/api` | One TypeScript API (Hono + `pg`) that every app calls. See its own [README](services/api/README.md). |
| `packages/shared` | API types, the typed client with token refresh, the SSE hook, money and time formatting, and the city map. |

## Run it

In the OmniStack preview everything below happens for you: a fresh database, migrations, demo
data, simulated drivers, and all three apps started together.

To run it yourself you need Node 22.18 or newer, pnpm and PostgreSQL:

```bash
pnpm install
cp .env.example .env                 # set DATABASE_URL and JWT_SECRET
set -a; source .env; set +a          # the apps read NEXT_PUBLIC_API_URL from the environment
for f in services/api/migrations/*.sql services/api/seed/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done

pnpm dev:api                         # http://127.0.0.1:4000/health
PORT=3000 pnpm dev:rider             # http://127.0.0.1:3000
PORT=3001 pnpm dev:driver            # http://127.0.0.1:3001
PORT=3002 pnpm dev:admin             # http://127.0.0.1:3002
```

Each command runs in its own terminal.

Set `DEMO_SIMULATION=1` so simulated drivers accept and complete rides by themselves; then one
person can see a whole trip without a second device.

## Demo logins

| Role | App | Email | Password |
|---|---|---|---|
| Rider | Rider app | `asha@ridenow.test` | `Rider@2026` |
| Driver | Driver app | `ravi@ridenow.test` | `Driver@2026` |
| Operations | Ops console | `admin@ridenow.test` | `Admin@2026` |

Each app only accepts its own role: a rider signing in to the ops console is refused, and the API
refuses the request as well. In the preview, phone sign-in accepts the code `123456`, and the card
`4000 0000 0000 0002` is always declined so failure paths can be tried.

## Try the whole flow

1. **Ops console** → *Live map*: the city with its online drivers.
2. **Driver app** → sign in and **Go online**.
3. **Rider app** → book a ride from MG Road. The request reaches the driver app within seconds.
4. **Driver app**: accept, "I've arrived", enter the PIN the rider sees, then complete.
5. **Rider app**: receipt and rating. **Ops console**: the trip, its dispatch trail and the money
   it moved; refund it from there if you like.

## Architecture

- **One API, one database.** Every app uses the same endpoints (`/rider`, `/driver`, `/admin`,
  `/support`) with a JWT access token (15 minutes) and a rotating refresh token. Roles are
  enforced on the server, not only in the apps.
- **Realtime** is server-sent events on `/stream`: trip updates, ride offers, driver positions,
  wallet changes, notifications, and an operations channel for tickets, payouts and zones.
- **Money** is a ledger: every movement is a row with the balance after it, and every completed
  trip books the rider, the driver and the platform so the books balance. Refunds and payouts are
  ledger entries too.
- **Each app has its own look** (design tokens and typeface) but shares the client, types and
  formatting in `packages/shared`.

## Where real providers plug in

Payments, SMS and maps are mocks behind interfaces in `services/api/src/providers/`. Implement the
same interface for your provider (Stripe or Razorpay, Twilio or MSG91, Google Maps or Mapbox), add
its keys to the API's `.env`, and nothing else in the product changes. The city map in
`packages/shared/src/city-map.tsx` is drawn from coordinates, so it needs no map tiles or key;
swap that component for a map SDK when you want live tiles.

## Make it yours

Ask in the OmniStack chat, for example: "add a women-only rides toggle to booking", "charge a
cancellation fee after 2 minutes", or "add a monthly ride pass". The code agent edits these files,
type-checks the result and commits it. You can also push the project to your own GitHub and work
on it with any editor.
