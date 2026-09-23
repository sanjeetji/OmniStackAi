# CareClinic

Clinic management and telemedicine for one multi-specialty clinic (Bengaluru, INR): three apps on
one API and one PostgreSQL database.

| Folder | What it is |
|---|---|
| `apps/patient` | The patient portal: find a doctor, book a 20-minute slot for yourself or a family member, pay, join a video visit, and read prescriptions, lab reports, vitals and invoices. |
| `apps/doctor` | The physician's clinical workstation: today's token queue, the consultation screen with SOAP notes, e-prescriptions, lab orders, the patient chart, the roster and reviews. |
| `apps/admin` | CareClinic Ops, the clinic operations console: front desk and check-in, walk-in booking, appointments, doctor rosters and rooms, the cashier, refunds, the diagnostics bench, reports, the chart-access audit and the waiting-room board. |
| `services/api` | One TypeScript API (Hono + `pg`) that every app calls. |
| `packages/shared` | API types, the typed client, the SSE hook, and money and time formatting. |

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Patient | `ananya@careclinic.test` | `Patient@2026` |
| Doctor | `dr.rajesh@careclinic.test` | `Doctor@2026` |
| Clinic operations | `admin@careclinic.test` | `Admin@2026` |
| Front desk | `suresh.gowda@careclinic.test` | `Admin@2026` |

Each app sends the role it is for when signing in, and the API answers 403 for an account of
another kind, so a patient cannot sign in to the clinic console.

## Run it

In the OmniStack preview everything below happens for you: a fresh database, migrations, demo data
and all three apps started together.

To run it yourself you need Node 22.18 or newer, pnpm and PostgreSQL:

```bash
pnpm install
cp .env.example .env                 # set DATABASE_URL and JWT_SECRET
set -a; source .env; set +a          # the apps read NEXT_PUBLIC_API_URL from the environment
for f in services/api/migrations/*.sql services/api/seed/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done

pnpm dev:api                         # http://127.0.0.1:4000/health
PORT=3000 pnpm dev:patient           # http://127.0.0.1:3000
PORT=3001 pnpm dev:doctor            # http://127.0.0.1:3001
PORT=3002 pnpm dev:admin             # http://127.0.0.1:3002
```

`pnpm test` runs the API's unit tests, `pnpm typecheck` type-checks every package, and
`pnpm --filter @careclinic/api seed:generate` rewrites `services/api/seed/001_demo.sql` from
`scripts/generate-seed.mjs` — the demo data is generated, never edited by hand.

## What the clinic knows

Twelve doctors across eight specialties, 150 patients with medical histories and family members,
about 770 appointments over the last 90 days and the next 14, and the clinical and financial trail
behind them: consultations with SOAP notes and ICD-10 diagnoses, signed prescriptions, vitals taken
at the desk, lab orders with results against reference ranges, invoices and their line items,
cancellation refunds, telehealth sessions, patient reviews, and a chart-access audit log.

## The rules the API enforces

- **No double booking.** Slots are generated from each doctor's weekly availability, and
  `UNIQUE(doctor_id, scheduled_date, start_time)` stops two patients taking the same one.
- **One way through a visit.** `booked → checked_in → in_consult → completed`, with `cancelled`
  and `no_show` as the exits. Any other transition is refused.
- **A signed prescription cannot be edited.** Once signed it is immutable; a correction is a new
  prescription.
- **Every chart access is recorded.** Reading a chart, a SOAP note, a prescription or a lab result
  writes a row to `chart_access_logs` in the same transaction as the read.
- **Cancellation refunds follow one policy.** Full refund more than 24 hours ahead, 70% between 4
  and 24 hours, nothing under 4 hours.

## What is simulated

The video room, the payment gateway and the SMS sender are mocks, so the template runs with no
credentials. Each one is a single module under `services/api/src/services/`; replace it with your
provider and add its keys to `.env`.
