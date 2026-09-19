# G-04 · Payments in generated apps — Stripe & Razorpay (proposed Tracker ID: R-512)

**Status:** specified, **GATED — needs test accounts for both gateways.**
**Depends on:** F-05 (secrets), F-02 (to verify a real checkout), G-01 (for a live callback URL).

## Important distinction

This task is about **payments inside the apps our users build** — "my store takes money".
It is **not** about charging our own users for OmniStackAI; that is platform billing, a separate
paid-service decision recorded in the kickoff doc's Phase E. Keeping them separate matters: this
one costs us nothing and can ship early.

## Why both gateways

- **Stripe** — the default for most of the world, best APIs and test mode.
- **Razorpay** — the practical choice for India (UPI, netbanking, INR settlement), which is the
  founder's home market and likely the first real customers.

Two is the right number to start: each gateway is real integration work (checkout, webhook,
verification, refund), and breadth here is worthless if the flows are not correct.

## What enabling a gateway generates

A `payments` capability in codegen, emitted only when the user enables it:

- `lib/payments/<gateway>.ts` — a typed server-side client reading keys from environment
  (Secrets, F-05), never from source.
- A **checkout route** (`POST /api/checkout`) creating a session/order from a product or amount
  in the app's own database.
- A **webhook route** (`POST /api/webhooks/<gateway>`) that **verifies the signature** before
  trusting anything, is idempotent on the event id, and records the payment in a generated
  `payments` table with its own migration.
- A success and a cancel page.
- Generated tests for signature verification and idempotency — the two things that are wrong in
  most hand-written integrations.
- `.env.example` entries (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `RAZORPAY_KEY_ID`,
  `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`) — names only, values live in Secrets.

Security rules baked into the generated code: the amount is always computed server-side from the
database, never taken from the client; the webhook is the only thing that marks an order paid;
keys never reach the browser (only the publishable key does).

## Database (ours)

```sql
-- migrations/000013_project_payments.up.sql
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS payment_gateway TEXT NOT NULL DEFAULT ''
        CHECK (payment_gateway IN ('', 'stripe', 'razorpay'));
```

Everything else lives in the **generated app's** database, where it belongs. We do not store our
users' customers' payment data — a deliberate decision that keeps us out of PCI scope.

## API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/projects/{id}/payments` | Which gateway is enabled, which keys are set (names only), webhook URL to register. |
| `PUT` | `/projects/{id}/payments` | `{gateway}` → generates the integration as an edit commit. |
| `DELETE` | `/projects/{id}/payments` | Removes it in an edit commit. |

## UI

Reference: Lovable's Payments page (`Lova-21`).

- **Manage → Payments**: two cards (Stripe, Razorpay) with "what this adds to your app" listed
  file by file; on enable, a checklist — set the secret keys (deep-links to Secrets), copy the
  webhook URL into the gateway dashboard, run a test payment.
- A **Test mode** banner while test keys are in use, and an explicit warning before switching to
  live keys.
- Never render a key; show "set" / "not set" with the last-updated time.

## Acceptance criteria

- [ ] Enabling Stripe produces a project where a test-mode checkout completes and the webhook
      marks the order paid, verified against Stripe's test dashboard.
- [ ] The same for Razorpay in test mode, including a UPI test flow.
- [ ] A forged webhook (bad signature) is rejected; a duplicate event does not double-credit
      (generated tests cover both).
- [ ] No secret key appears in client bundles (grep of the built output in the task evidence).
- [ ] Disabling removes the integration cleanly.
- [ ] Gates as usual.

## Open question for the founder

Test accounts: do you have Stripe test keys and a Razorpay test account we can use for the live
verification, or should this task ship with generated tests only and the live check deferred?
(Recommendation: get both test accounts — payments verified only by unit tests is not honest
evidence for a money feature.)
