# OmniStackAI Console (`apps/console-web`)

The real product console — a Next.js (App Router, TypeScript) app, replacing the Stage-0
dependency-free static page (R-470). This is Phase B of
`R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`.

## Run it

```
# Bring up the control-plane it talks to (Postgres + control-plane via Docker Compose)
task control-plane:verify

# Then, in another terminal:
task console:dev      # http://localhost:3000, hot reload
```

Or for a production-style run: `task console:build` then `task console:start`.

## What's here

- `app/login`, `app/register` — account creation and sign-in, posting to this app's own
  `app/api/auth/*` Route Handlers.
- `app/api/auth/{register,login,logout}` — server-side proxies to the Go control-plane's
  `/auth/*` API (R-469). The browser never sees the raw session token: these routes set/clear an
  `httpOnly` cookie (`omnistackai_session`) instead, so there's no token in `localStorage` for an
  injected script to steal, and no CORS to configure (the browser only ever talks to this app's
  own origin).
- `app/page.tsx` — the signed-in home page: profile, plan, and credit balance, proving the cookie
  session round-trip against the real control-plane.
- `app/fabric` — the model fabric / cost overview, carried forward from the old static console on
  the exact same `data/overview.json` data contract (still refreshed by
  `task console:snapshot`, which is unchanged Python).
- `lib/control-plane.ts` — the one place that knows the control-plane's response shapes.
  `lib/session.ts` — the one place that knows the session cookie's name and how to read it.

## Config

`OMNISTACKAI_CONTROL_PLANE_URL` (server-side only, default `http://127.0.0.1:8080`) — where this
app calls the control-plane. Set in the repo root `.env`, exported into the environment by
`scripts/console.sh` before running any Next.js command (this app does not read `.env` files of
its own — the root `.env` stays the single source of truth for the whole repo).

## What's not here yet

The actual Studio/builder UX (chat, files, preview) is Phase D — built on this console once it
exists. No generation call spends a credit yet (Phase C bridges the control-plane's Job API to the
agent-engine). No payment processor, no password reset, no team/org — all named as deferred in
`.ai/tasks/R-469.md` and the kickoff doc, unchanged here.
