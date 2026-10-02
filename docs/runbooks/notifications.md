# Notifications in a generated app

PC-053. A generated app tells people what concerns them:
- **in the app**, behind a bell that updates live (R-569);
- **by email**, through an outbox with retries.

Each person decides what they hear about.

## What the plan says

```json
{"kind": "notifications", "name": "app_notifications", "config": {"rules": [
  {"name": "order_shipped", "entity": "Order", "when": {"field": "status", "becomes": "shipped"},
   "to": ["creator"], "title": "Your order is on its way", "body": "Total: {total_amount}",
   "channels": ["in_app", "email"]},
  {"name": "order_assigned", "entity": "Order", "when": "assigned", "to": ["assignee"],
   "title": "Order {status} is assigned to you"},
  {"name": "new_order", "entity": "Order", "when": "created", "to": ["role:staff"],
   "title": "New order: {total_amount}", "channels": ["in_app", "email"]}]}}
```

| Key | Meaning |
|---|---|
| `when` | `created`, `changed`, `deleted`, `assigned`, or a field becoming a value. `assigned` fires when the ownership assignee (PC-111) changes to someone new, not on every change. |
| `to` | `creator` (who made the record), `assignee`, a uuid field holding a user's id, or `role:<role>`. |
| `title`, `body` | Text with `{field}` placeholders from the record. |
| `channels` | `in_app` and/or `email`. |

### Reminders

A reminder is a scheduled job (R-568) whose action is to notify. `due_within` picks the records
whose date falls within the next interval:

```json
{"name": "visit_reminder", "entity": "Visit", "every": "15m",
 "due_within": {"field": "starts_at", "age": "1d"},
 "do": {"notify": {"to": ["creator"], "title": "Reminder: your visit at {starts_at}", "channels": ["in_app", "email"]}}}
```

Each record is reminded once. A unique index backs this up when two replicas run at the same time.

### From the prompt

`intake/notifications_intent.py` reads sentences such as:
- "notify the customer when their order is shipped";
- "email staff when a new order is placed";
- "tell the courier when an order is assigned to them";
- "remind patients a day before their appointment".

It works out who should hear:
- a coordinating role (staff, dispatcher, admin) hears as that role;
- the role an entity is assigned to hears as its assignee;
- anyone else hears as the record's creator.

The word "email" adds the email channel. When an entity has a plain `status` and no lifecycle, "when
their order is delivered" means status becoming "delivered". The reader adds nothing the plan can't
carry out. Repair resolves names and drops rules that name what the plan lacks.

## How it works

- **The database writes the notifications.** A trigger on each entity with rules calls
  `notification_send` once per recipient. Each reminder's job calls it once per due record.
  - The function leaves out the channels the recipient muted, and writes nothing when no channel
    is left.
  - So a change made through any backend, by a scheduled job or by a script notifies the same
    people, and Python, Go, Express and Hono only serve and send what the database wrote.
- **In the app.** `GET /notifications` (`?unread=1`), `GET /notifications/unread`,
  `POST /notifications/{id}/read` and `POST /notifications/read-all` answer only for the signed-in
  person. Someone else's notification gets a 404.
  - Notifications are live: only their recipient's stream hears of them, never an admin's.
  - The web app's navbar shows a bell with the unread count; the admin console lists Notifications
    in its sidebar.
- **Email.** Notifications with the email channel wait in the outbox (`email_status`). Each backend
  sends them every `NOTIFICATIONS_EMAIL_SECONDS` (10) through Resend, using `RESEND_API_KEY` and
  `EMAIL_FROM`.
  - Failures are retried after 1, 2, 4 and 8 minutes, then marked `failed`.
  - Without keys, each email is marked `skipped`, with the reason, rather than retried forever.
  - `EMAIL_API_URL` points the sender at a test double. `NOTIFICATIONS_EMAIL_DISABLED=1` turns
    sending off on one replica.
- **Preferences.** `GET` and `PUT /notifications/preferences` mute a rule, or everything (`*`), per
  channel. A rule addressed only to roles (new orders, for staff) is offered only to people with
  one of those roles.

## Proven

On 2026-10-02, the same plan ran on each of Python, Go, Express and Hono through the platform's
runner, with a stand-in email provider, and each passed 27 checks:
- both staff heard of a new order, and nobody else did;
- the courier heard once when assigned, and not on the next change;
- the customer heard the order shipped, with its total;
- the notification reached the customer's live stream and not another customer's;
- only the recipient could mark it read;
- emails went out with the right subject, text, sender and key, and the email the provider
  refused was retried and sent;
- per-rule and per-channel mutes held;
- each person was offered only the rules that can reach them;
- a reminder fired once, and a visit three days away was not reminded.

In a browser, the customer's bell went from nothing to 1 when staff shipped the order elsewhere,
with no reload. The notifications page listed it, marking it read cleared the bell live, and
turning off its email was saved (6 of 6).

## Not yet

- Push notifications (Expo and native) wait for the go-ahead on mobile work.
- SMS isn't a channel.
- A notification doesn't know who made the change, so a person who changes their own record is
  told too.
