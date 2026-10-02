# Scheduled jobs in a generated app

R-568. A generated app can do things on its own, on a clock. For example:

- cancel unpaid orders after 30 minutes;
- mark invoices overdue once the due date passes;
- delete drafts older than 30 days.

Each rule is a **schedule** in the plan's `jobs` capability. Every backend runs the schedules:
Python, Go, Express and Hono.

## What a schedule says

```json
{"kind": "jobs", "name": "app_jobs", "config": {"schedules": [
  {"name": "cancel_unpaid_orders", "entity": "Order", "every": "5m",
   "where": {"paid": [false]}, "older_than": {"field": "created_at", "age": "30m"},
   "do": {"transition": "cancel"}}]}}
```

| Key | Meaning |
|---|---|
| `every` | How often to look: `1m` to `7d`. |
| `where` | A field and the values it must hold. |
| `older_than` | A datetime field and an age. `0m` means "the time has passed", for a due date. |
| `do` | One of: `{"transition": ...}` (a transition of the entity's workflow), `{"set": {...}}` (fields, never the workflow's own), or `{"delete": true}`. |

A schedule needs at least one of `where` and `older_than`. A rule over every row is refused.

### At a time of day (PC-117)

```json
{"kind": "jobs", "name": "app_jobs", "config": {"timezone": "Asia/Kolkata", "schedules": [
  {"name": "purge_old_products", "entity": "Product", "every": "1d", "at": "02:00",
   "older_than": {"field": "created_at", "age": "365d"}, "do": {"delete": true}},
  {"name": "weekly_close", "entity": "Ticket", "every": "7d", "at": "09:00", "on": "monday",
   "where": {"status": ["resolved"]}, "do": {"transition": "close"}}]}}
```

- `at` is a 24-hour local time, and `every` is then a whole number of days.
- `on` is a weekday, with `every` set to `7d`.
- `timezone` is IANA; the default is UTC.
- A schedule at a time of day does **not** run at startup. Its first run is the next time that
  local time comes round, and each run after that is a day (or a week) later at the same local
  time.
- The next run is computed in Postgres (`scheduler_next_at`), so daylight saving is handled by the
  database, and every backend runs the same statements.
- Changing a schedule's time, day or zone moves its next run. Leaving them alone keeps it.
- The prompt reader picks up "every night at 2am", "daily at 23:15", "every Monday at 9:30 am" and
  "at midnight". It sets the time zone from the prompt, for example rupees or India gives
  Asia/Kolkata.

### Where schedules come from

- **The planning model.** It is told about the `jobs` capability.
- **The prompt itself** (`intake/jobs_intent.py`). It reads sentences such as:
  - "cancel unpaid orders after 30 minutes";
  - "orders not paid within 2 hours are cancelled";
  - "mark invoices as overdue when the due date passes".

  It adds a schedule only when the plan can carry it out: through the entity's own workflow
  transition, its flag field, or a delete. "Customers can cancel an order within 2 hours" is a
  button, not a job, so it is left alone.
- **Repair** (`ir_repair._repair_jobs`). It drops a schedule that names something the plan
  doesn't have, and says so in the build notes.

## How it runs

- **One statement per schedule.** The platform compiles each schedule into one SQL statement
  (`codegen/jobs_sql.py`) that every backend runs unchanged.
  - The statement picks at most 500 rows (`FOR UPDATE SKIP LOCKED`), so it never blocks a request
    that is editing a row.
  - It repeats while it fills a batch, up to 20 batches. Whatever is left waits for the next run.
- **A transition only moves rows the workflow allows.** Cancelling affects only orders in the
  transition's source states.
- **`set` leaves alone rows that already hold the value.** So a run's count is what it actually
  changed.
- **The scheduler lives in the app's own Postgres.** There is no Redis and no queue service.
  - Its tables are `scheduler_schedule`, where each schedule's next run is a row, and
    `scheduler_run`, where each run is a row.
  - A loop in the API turns due schedules into runs and claims them with `SKIP LOCKED`. Several
    API replicas therefore share the work without running it twice.
  - A failed run is retried after 20s, 40s, 80s and 160s. After its fifth attempt it is **dead**
    and waits for an admin.
  - A run whose worker died is taken again after 5 minutes.
  - Done runs are kept for 14 days.
- **The loop syncs schedules at startup.** It adds new schedules (due at once), keeps each existing
  schedule's next run, and drops the ones the app no longer has.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `SCHEDULER_TICK_SECONDS` | `10` | How often a replica looks for due work. |
| `SCHEDULER_DISABLED` | empty | `1` turns the loop off on this replica (another replica runs the jobs). |

## The admin's view

The admin console has a **Scheduled jobs** page. It shows:

- each schedule in a sentence, its last run and how many rows it changed;
- **Run now**, **Pause** and **Resume** for each schedule;
- **Needs attention**: failed and dead runs, each with its error and **Retry**;
- the recent runs.

The API admits only the admin. Its endpoints:

- `GET /scheduler/schedules`
- `POST /scheduler/schedules/{name}/run|pause|resume`
- `GET /scheduler/runs?status=`
- `POST /scheduler/runs/{id}/retry`

An app's own entities and routes can't use the `scheduler_*` tables or `/scheduler`.

## Proven

On 2026-10-01, the same plan ran on each of Python, Go, Express and Hono through the platform's
runner, and each passed 28 checks:

- only the unpaid orders past their time were cancelled;
- the clock ran a schedule on its own;
- two runs at once changed each row once;
- a failing schedule was retried with backoff and ended dead;
- an admin retried it once the cause was fixed;
- a paused schedule did not run.

In a browser, the admin page ran a job, showed the failed run and retried it, and paused a
schedule (8 of 8 checks).

Times of day (PC-117) passed 7 checks on each of the four backends. A daily and a weekly schedule
two minutes ahead in Asia/Kolkata waited, ran by themselves at that minute, and were next due a day
and a week later at the same local time.

## Not yet

- Reminders and emails. Notifications are PC-053, which builds on this.
