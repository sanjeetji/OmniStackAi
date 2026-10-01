# Payments in a generated app

An app that takes payments gets a `money` capability in its plan: an order, a booking or a ticket
can be paid for, the platform can keep a commission, and the person who earns the sale (a vendor, a
driver) is paid out. The Python, Go and Node backends all generate the same model.

## How the money works

- **Amounts are whole numbers in the currency's smallest unit** (paise, cents), so ₹499.50 is
  stored as 49950. Floating-point is never used for money.
- **The price comes from the stored record.** Checkout reads `Order.total_amount`; anything the
  client sends as an amount is ignored.
- **Every movement is a ledger entry** that moves an amount from one account to another. A balance
  is the sum of an account's entries; no balance is stored. Across all accounts the books always
  sum to zero, and `GET /money/summary` reports `"balanced": true`.
- **Accounts:**

  | Account | What it holds |
  |---|---|
  | `external` | The outside world. Money comes in from it and goes back out to it. |
  | `escrow` | Collected money not yet split. |
  | `revenue` | The platform's commission. |
  | One per user | What that user is owed. |

- **A payment** moves the amount from `external` to `escrow`, then from `escrow` to `revenue` (the
  commission) and to the payee (the rest). If the plan names no payee, the platform keeps the whole
  sale. When the record has a `paid` field, it is set to true.
- **A refund** can be partial. It is taken back in proportion: the payee's share from the payee,
  the rest from revenue. A full refund sets `paid` back to false.
- **A payout** is requested by the person owed money, up to what is available (their balance minus
  pending requests). A manager or admin pays it, with a bank reference, or rejects it.

## Endpoints

| | |
|---|---|
| `POST /payments/checkout` `{entity, record_id}` | Start paying for a record. Only someone who may see the record can pay for it, and only once. |
| `POST /payments/{id}/confirm` | Mock provider only: the payer confirms. |
| `POST /payments/{id}/refund` `{amount?}` | Refund roles and admin only. |
| `GET /payments` | Your payments (as payer or payee). Refund roles see all. |
| `GET /money/balance`, `GET /money/ledger` | Your balance and your entries. |
| `GET /money/summary` | The platform's books. Refund roles only. |
| `POST /money/payouts` `{amount?}`, `GET /money/payouts` | Request a payout and see your payouts. |
| `POST /money/payouts/{id}/pay` or `/reject` `{reference?}` | Refund roles and admin. |
| `POST /payments/webhooks/stripe`, `/payments/webhooks/razorpay` | For the providers. These are signed, not signed in. |

## Providers: credentials come last

`PAYMENT_PROVIDER` chooses the provider at runtime. With no keys, it is **mock**: the whole flow
works offline (checkout, confirm, refund, payout), so an app is usable before anyone has a payment
account.

| Provider | Set | Webhook URL to give the provider |
|---|---|---|
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | `https://<api>/payments/webhooks/stripe`, event `checkout.session.completed` |
| Razorpay | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | `https://<api>/payments/webhooks/razorpay`, event `payment.captured` |

`PAYMENT_SUCCESS_URL` and `PAYMENT_CANCEL_URL` set where Stripe's hosted checkout returns.

With a real provider, a payment is marked paid **only by its signed webhook**:

- the signature is checked over the exact bytes received;
- a Stripe event more than 5 minutes old is refused, so an old event can't be replayed;
- each event is acted on once (`processed_event`);
- the amount and currency the provider charged must match the payment, or it is refused.

Refunds go through the provider's refund API.

## Proven so far

- **Live, without keys:** a marketplace (customers pay for orders, 10% commission, vendors paid
  out) ran on Python, Go, Express and Hono through the platform's runner and passed 33 checks on
  each. Those checks included Stripe and Razorpay webhooks signed locally with a test secret.
- **Live, real test-mode accounts (2026-10-01):** the console-built Bazaar Lite (INR, 10%
  commission), keys added only in **Manage -> Secrets**:
  - **Stripe:** a buyer paid ₹799 by card (4242 4242 4242 4242) in Stripe Checkout; the signed
    `checkout.session.completed` settled it; the seller got ₹719.10; an admin refunded ₹100; Stripe
    shows the PaymentIntent and the refund succeeded.
  - **Razorpay** (`PAYMENT_PROVIDER=razorpay`): the app created a Razorpay order; the buyer paid ₹799
    by test Netbanking; `payment.captured` and `order.paid` both arrived (the second was ignored as a
    duplicate); the seller got ₹719.10; an admin refunded ₹100; Razorpay shows the payment captured
    and the refund processed.
  - Both left balanced books: external -699.00, revenue 69.90, owed to users 629.10.
- **Still to do:** live-mode keys (real money), at PC-070 and PC-071. The founder deferred them on
  2026-10-01.

## Testing payments against a local preview

A preview's API listens on `127.0.0.1`, so a provider can't reach it on its own.

- **Stripe:** `stripe listen --events checkout.session.completed --forward-to <api>/payments/webhooks/stripe`.
  Without `--events`, nothing is forwarded. `stripe listen --print-secret` gives the
  `STRIPE_WEBHOOK_SECRET`. Instead of running `stripe login`, you can pass the project's
  `STRIPE_SECRET_KEY` in the `STRIPE_API_KEY` environment variable. Indian test cards ask for 3D
  Secure; 4242 4242 4242 4242 doesn't.
- **Razorpay:** open a public tunnel (`cloudflared tunnel --url <api>`). In the Razorpay Dashboard,
  under Webhooks, add `https://<tunnel>/payments/webhooks/razorpay` with `payment.captured`, and
  store the same secret as `RAZORPAY_WEBHOOK_SECRET`. On desktop, Razorpay Checkout's UPI tab shows
  only a QR code, so pay with test **Netbanking**: pick a bank, then press **Success** on the mock
  bank page. The checkout asks for a mobile number first and rejects placeholders such as
  9876543210.
- A preview nobody opens for 30 minutes stops (`OMNISTACKAI_PREVIEW_IDLE_MINUTES`); webhooks and
  direct API calls don't count as opening it. After a restart the API can be on a new port, so
  point the tunnel or `stripe listen` at the new port. Delete the test webhook when you're done.
