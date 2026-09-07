# OmniStackAI Console (`apps/console-web`)

The dependency-free Stage 0 visual console. It now shows both halves of the platform:

- a real builder proof — the combined preview/verify project plan for a bundled Application IR and a
  hunk-level unified edit patch produced from an actual old/new IR assembly; and
- the model fabric — providers (local + all supported cloud, with active/key state), Balanced routing,
  price book, resilience, and usage/cost accounting.

## Run it

```
task console:snapshot   # refresh data/overview.json from the Python model gateway
task console:serve      # snapshot + serve on http://127.0.0.1:4321
```

Then open <http://127.0.0.1:4321>.

## How it works

- `data/overview.json` is a **metadata-only** snapshot composed by
  `omnistackai_agent_engine.console_snapshot`. It calls the existing model overview, project planner,
  IR assembler, and edit-diff contracts; it never installs/runs/verifies/deploys generated code or
  connects to a database. It never contains an API key or secret — provider key state is a boolean.
- `index.html` + `styles.css` + `app.js` render that snapshot with safe DOM APIs (`textContent`
  only, never `innerHTML`). The page makes **no external network requests** (same-origin fetch of the
  snapshot only) and sets a strict `Content-Security-Policy` meta tag.

## Why static (for now)

This slice is intentionally dependency-free so it builds and runs in the offline Stage 0 environment
and keeps `task bootstrap`/`task verify` green. The forward path is a Next.js (App Router, TypeScript)
app once the build environment can install the front-end toolchain; the data contract
(`overview.json`) and the design carry over unchanged.
