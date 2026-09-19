# F-02 · Preview that actually works (proposed Tracker ID: R-500)

**Status:** specified, unblocked (better after F-01). **Depends on:** F-01 for per-project keying.

## The two real defects

Measured on 2026-09-19 with the platform running in preview mode:

```
POST /api/jobs/build/stream        → 200, build finished in 30s
POST /api/jobs/build/1/preview     → 200 in 5s
   {"status":"ready","web_url":"http://127.0.0.1:59570","api_url":"http://127.0.0.1:59569"}
GET  http://127.0.0.1:59570        → 200, 41,338 bytes, <title>Simple Note Taking</title>
```

**The preview engine is fine.** The founder saw "Live preview isn't running" for two reasons:

1. **Wrong mode.** The Studio was started with `agent-engine:studio:serve` (build-only), where the
   preview manager is not wired at all, so `/api/preview` 404s and the tab shows its disabled
   state. Already fixed at the operator level by `scripts/omnistack.sh up` (preview by default);
   this task removes the remaining footguns.
2. **Loopback-only URL.** `localrun/run.py` allocates ports on `127.0.0.1` and the returned
   `web_url` is `http://127.0.0.1:<port>`. On the same machine the iframe loads; from a phone or a
   second laptop pointed at `http://<lan-ip>:4321` it can never load, because `127.0.0.1` there
   means *that* device.

## Outcome

Opening a project shows the running app without the user knowing what a mode is, from any device
that can reach the console, with an honest status when it genuinely cannot run.

## Design

### 1. One reachable preview URL (the core change)

Add a **preview proxy** to the console: `/preview/{projectId}/**` → the project's local
`web_url`, and `/preview/{projectId}/api/**` → its `api_url`. The iframe then points at a
same-origin path that works from every device that can already reach the console.

- Implemented as a Next route handler that streams the upstream response (the same technique the
  R-485 SSE route already uses), forwarding method, path, query, body and the relevant headers.
- Only proxies to a `127.0.0.1:<port>` the preview manager reported for **that project**, looked
  up server-side — never a caller-supplied URL (that would be an SSRF hole).
- Requires the session cookie and project ownership, so a preview is not public.
- WebSocket/HMR: dev-server sockets are not proxied in v1; the preview is served from the app's
  production-ish dev server and refreshed explicitly after an edit (today's behaviour). Stated in
  the spec so nobody assumes live HMR.
- `OMNISTACKAI_PREVIEW_PROXY=0` disables it and falls back to the direct loopback URL.

### 2. Auto-start, with real feedback

- Opening a project whose preview is not running starts it automatically (today the user gets a
  disabled panel until something triggers it).
- The start call streams progress instead of blocking silently: `install → migrate → start →
  ready`, with the real elapsed seconds the UI already shows. First run installs dependencies and
  can take minutes; each phase is named so the wait is explainable.
- After an edit, the existing re-preview call stays (R-479's decision — `_edit()` never restarts
  the preview itself).

### 3. Mode is a platform fact, not operator trivia

- `GET /api/preview` on the agent-engine already distinguishes the modes (200 vs 404) — the
  console reads it once and, in build-only mode, shows: *"This server runs in build-only mode.
  Restart it with `./scripts/omnistack.sh up` to run your app."*
- `scripts/omnistack.sh status` prints the live mode (already implemented).

### 4. Ports and lifetime

- Keep the existing free-port allocation; record `web_port`/`api_port` per project in the preview
  manager (in memory is fine — a preview is a running process, not persistent state).
- Idle previews are stopped after `OMNISTACKAI_PREVIEW_IDLE_MINUTES` (default 30) to bound
  resource use, with the tab showing "stopped — start again" rather than a dead iframe.

## Database

None. Preview state belongs to the running process.

## API

| Layer | Route | Change |
| --- | --- | --- |
| console | `ALL /preview/{projectId}/**` | **New.** Authenticated same-origin proxy to the project's local preview. |
| console | `GET /api/projects/{id}/preview` | Status, including `phase` and `elapsed_ms`. |
| control-plane | `POST /projects/{id}/preview` | Existing proxy, project-scoped (F-01). |
| control-plane | `POST /projects/{id}/preview/stop` | **New**, project-scoped stop. |
| agent-engine | `POST /api/workspaces/{id}/preview` | Returns `web_url`, `api_url`, `phase`, `web_port`, `api_port`. |

## UI

Reference: Lovable's preview frame (`Lova-02`).

- Preview tab: the R-494 toolbar (status pill, URL, open-in-new-tab, Desktop/Tablet/Phone,
  Restart, Stop) now points at the proxied URL, and **Open in new tab** opens the proxy path, so
  it works from any device too.
- Starting state: phase label + elapsed seconds + skeleton frame (already built; wire the phases).
- Disabled state: the build-only message above, with the exact command.
- Failure state: the real error text from the runner, plus a "Show log" link (F-08).

## Acceptance criteria

- [ ] From a second device on the same network, opening the console, opening a project and
      clicking Preview renders the generated app inside the iframe.
- [ ] A cold preview reports install → migrate → start → ready with real elapsed time.
- [ ] Requesting `/preview/{other-users-project}/` returns 404; a caller-supplied host is never
      proxied (test).
- [ ] Build-only mode shows the honest message, not a broken frame.
- [ ] Gates as usual, plus a live smoke from a non-loopback address.

## Out of scope

- Public preview links for people without an account (that is Publish, G-01).
- Running previews in the R-486…R-490 sandbox providers. That is the multi-tenant answer and is
  scoped separately — once this proxy exists, swapping the target URL is a small change.
