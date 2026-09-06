# OmniStackAI Console (`apps/console-web`)

The first slice of the visual platform console: a read-only overview of the model fabric —
providers (local + all supported cloud, with active/key state), the Balanced routing ladder, the
price book, and the usage/cost dashboard from the accounting ledger.

## Run it

```
task console:snapshot   # refresh data/overview.json from the Python model gateway
task console:serve      # snapshot + serve on http://127.0.0.1:4321
```

Then open <http://127.0.0.1:4321>.

## How it works

- `data/overview.json` is a **metadata-only** snapshot exported by the Python gateway
  (`omnistackai_agent_engine.model_gateway.overview`). It never contains an API key or secret — a
  provider's key state is a boolean only.
- `index.html` + `styles.css` + `app.js` render that snapshot with safe DOM APIs (`textContent`
  only, never `innerHTML`). The page makes **no external network requests** (same-origin fetch of the
  snapshot only) and sets a strict `Content-Security-Policy` meta tag.

## Why static (for now)

This slice is intentionally dependency-free so it builds and runs in the offline Stage 0 environment
and keeps `task bootstrap`/`task verify` green. The forward path is a Next.js (App Router, TypeScript)
app once the build environment can install the front-end toolchain; the data contract
(`overview.json`) and the design carry over unchanged.
