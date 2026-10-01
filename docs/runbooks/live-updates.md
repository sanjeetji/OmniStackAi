# Live updates in a generated app

R-569. A generated app can show changes as they happen, without a reload:
- an order's status moving while the customer watches;
- a courier's assigned deliveries;
- a new record in the admin's table.

## What the plan says

```json
{"kind": "realtime", "name": "live_updates", "config": {"entities": ["Order", "Delivery"]}}
```

Each change to those entities reaches the signed-in people who may see the record: created,
changed or deleted, whether by a person, a scheduled job (R-568) or a script in the database.

### Where it comes from

- **The planning model.** It is told about the capability.
- **The prompt itself** (`intake/realtime_intent.py`). It reacts
  to phrases such as "live order status", "track ... in real time", "see new messages instantly" and
  "without refreshing", and makes live the entities the sentence names.
  - The people watching are not the thing that changes: in "customers see live order status", only
    Order becomes live.
  - With no entity named, the entities with a lifecycle or a position (latitude and longitude)
    become live.
  - "Live music" and "where they live" are not live updates.
- **Repair.** It resolves the names, merges duplicates and drops what the plan doesn't have.
- **Multi-app products.** Each app gets the live entities it has.

## How it works

- **The database publishes.** A trigger on each live table publishes
  `{table, op, id, creator, assignee}` with Postgres `LISTEN/NOTIFY` on channel `app_changes`.
  Every API replica listens, so a change made through one replica reaches people connected to
  another. There is no Supabase, Ably or Redis.
- **The API streams.** Each backend (Python, Go, Express, Hono) keeps one listening connection and
  sends each change to the open streams of the people who may see that row. The rule is the
  entity's ownership rule (R-570, PC-111):
  - the creator;
  - the assignee;
  - a role that sees all, or admin;
  - everyone signed in, for an entity without an ownership rule.

  Nobody learns even the id of a record they can't see.
- **An event names what changed; it never carries the data.** It is
  `{"entity": "Order", "op": "update", "id": "..."}`. The page fetches the record through the API,
  which applies every rule as always.
- **Opening a stream takes a ticket.** A browser's `EventSource` can't send an `Authorization`
  header. So the page first trades its token for a ticket at `POST /realtime/ticket`. The ticket is
  signed with `JWT_SECRET`, holds the user's id and roles, and lasts 60 seconds. The page then opens
  `GET /realtime/stream?ticket=...` (Server-Sent Events). `&entities=Order,Delivery` narrows the
  stream.
- **Keeping the stream healthy.** The stream sends a ping every 20 seconds. A stream that falls
  more than 256 events behind is closed, and the page reconnects with a fresh ticket and backoff.

## The pages

- **Generated web and admin apps.** These get `lib/realtime.ts`. The data hooks of live entities
  in `lib/hooks.ts` call `useLive`, so every page built on the hooks refetches quietly when its
  data changes. That covers generated pages and pages written by the model alike.
  - A list refreshes on any change to its entity.
  - A record's page refreshes on changes to that record.
  - A burst of changes is one refresh, a quarter-second later.
- **The admin console's tables** refresh the same way.

## Proven

On 2026-10-02, the same plan ran on each of Python, Go, Express and Hono through the platform's
runner, and each passed 19 checks:
- no ticket, a forged ticket, or a ticket without sign-in is refused;
- a customer hears of their own order, not another customer's;
- staff who see all hear of every order;
- a courier hears of an order once it is assigned to them;
- a change made in the database itself is heard;
- a public product reaches everyone signed in;
- a stream asked for products alone hears only products.

In the console: QuickShip, built from a prompt, planned Order live across its apps; a change reached a
stream opened through the Studio's preview proxy in 0.05 s.

In a browser: the customer's open order page showed "shipped" when staff shipped it; a new order
appeared in the admin's open table, and left it when deleted. No reload, 4 of 4.

## Not yet

- The React Native app doesn't listen yet. It refreshes when opened.
- A ticket is checked when the stream opens. A stream stays open after the user's token expires,
  until it reconnects.
