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

## Push to the phone app (PC-121)

A rule (or a reminder) can add the `push` channel; the prompt reader adds it for "push", "phone" or
"mobile". Then:

- **Registering a phone.** The generated React Native app asks for permission after sign-in, gets an
  Expo push token for the phone, and registers it with `POST /notifications/devices`.
  - A token belongs to whoever signed in on that phone last.
  - `DELETE /notifications/devices/{token}` forgets your own device, never someone else's.
- **Sending.** Each backend sends due pushes through Expo's push service (`EXPO_PUSH_URL`, default
  `https://exp.host/--/api/v2/push/send`). `EXPO_ACCESS_TOKEN` is needed only if the Expo project
  enforces push security.
  - A refusal from the service is retried like email.
  - A device Expo reports as `DeviceNotRegistered` (the app was uninstalled) is forgotten.
  - A person with no registered device gets `skipped`, not retries.
- **Muting.** Anyone can mute push per rule, or for everything, like the other channels. The
  preferences page shows a "Phone" column.

### Trying it on your own phone (your steps)

1. Install the Expo CLI tools: `npm install -g eas-cli`. Then sign in with `eas login`; create a free
   Expo account at expo.dev if you don't have one.
2. In the generated project's `apps/mobile`, run `eas init`. It creates the Expo project and prints
   its **project id**.
3. Add `EAS_PROJECT_ID=<that id>` to `apps/mobile/.env`. The app config reads it.
4. Push needs a development build, not Expo Go: `eas build --profile development --platform android`
   (or `ios`). Install the build on your phone from the link Expo gives you.
5. Start the preview, open the app on the phone, sign in, and allow notifications. Then make
   something happen that a rule announces, for example ship an order in the admin console. The
   phone shows it.

Store builds (later) also need the Apple and Google developer accounts covered in
`store-publishing.md`.

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

Push (PC-121) passed 14 checks on each of the four backends, against a stand-in for Expo's push
service:
- registration needs sign-in;
- a refused push was retried, then sent;
- staff with a phone got the new order, and staff without one were skipped;
- both of the customer's phones were pushed, and the uninstalled one was forgotten;
- a push mute held, and the notification still appeared in the app;
- a phone moved to whoever signed in on it;
- nobody could forget another person's device.

The generated mobile app type-checks with `expo-notifications`.

In a browser, the customer's bell went from nothing to 1 when staff shipped the order elsewhere,
with no reload. The notifications page listed it, marking it read cleared the bell live, and
turning off its email was saved (6 of 6).

## Not yet

- A push doesn't open the record it's about when tapped yet.
- SMS isn't a channel.
- A notification doesn't know who made the change, so a person who changes their own record is
  told too.
