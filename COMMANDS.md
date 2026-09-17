# OmniStackAI — Developer Command Reference

> A single-page, developer-friendly cheat sheet covering every command in the repository.
> Every command includes a single-line explanation of its exact purpose and when to use it.

---

## 1. Quick Start (Most Frequently Used)

```bash
# 0. Always navigate into the OmniStackAI project root first (all commands must be executed from here)
cd ~/Documents/Projects/Startup/Omnistackai

# 1. Check your machine setup, dependencies, and toolchains (Python, Docker, Node, Ollama)
task doctor

# 2. Start the local PostgreSQL database with pgvector
task db:up

# 3. Launch the OmniStackAI Web Studio with interactive live app preview (http://127.0.0.1:4173)
task agent-engine:studio:preview

# 4. Alternatively, launch Studio with live preview WITHOUT needing Docker/Colima running
OMNISTACKAI_STUDIO_LIVE_PREVIEW=1 task agent-engine:studio:serve

# 5. Run full automated verification (tests, lint, security checks) before committing code
task verify
```

---

## 2. OmniStackAI Web Studio (Chat-to-App)

The Web Studio runs locally on `http://127.0.0.1:4173` with zero external assets/CDNs.

```bash
# Start Studio with live interactive app preview (requires local PostgreSQL container running)
task agent-engine:studio:preview

# Start Studio in build-only mode (generates code to disk, doesn't run services)
task agent-engine:studio:serve

# Start Studio with live preview enabled without starting Docker
OMNISTACKAI_STUDIO_LIVE_PREVIEW=1 task agent-engine:studio:serve

# Start Studio saving generated apps to scratch/apps inside the project
export OMNISTACKAI_APP_OUT_DIR="$(pwd)/scratch/apps" && task agent-engine:studio:preview

# Start Studio saving generated apps to your personal Projects folder
export OMNISTACKAI_APP_OUT_DIR="$HOME/Documents/Projects/GeneratedApps" && task agent-engine:studio:preview
```

R-467: after a build, click any file in the result panel's file list to view it (read-only, backed by
`GET /api/build/{id}/files` / `.../file?path=...`, wired in every mode). Tick "Hybrid UI (experimental)" on
the build form before building to send `hybrid_ui: true` on `/api/build` — it threads R-465/R-466's engine
into the plain-prompt and Ecosystem Pack build paths and shows a per-file 🤖 badge for model-written pages
(Solution Pack builds don't support it yet and say so honestly rather than pretending).

R-468: use the "Continue editing this app" box under the file browser to send a follow-up instruction (e.g.
"add a favorites feature") — it lands as a real second commit on the *same* owned repo
(`POST /api/build/{id}/edit`; `GET /api/build/{id}/turns` for the chat log). Additive only (new
entities/apis/screens; renaming/removing existing structure is rejected); Solution Pack and multi-surface
Ecosystem builds aren't supported yet and say so honestly rather than pretending. See `docs/CHAT_EDIT.md`.

---

## 3. Database & Container Management (PostgreSQL + pgvector)

Local PostgreSQL runs in Docker via Colima or Docker Desktop on port `5432`.

```bash
# Start local PostgreSQL container and wait until pgvector is healthy
task db:up

# View container status, port bindings, and uptime
task db:status

# Verify database connection, pgvector extension, and migration schema version
task db:verify

# Validate Docker Compose configuration file syntax
task db:config

# Stop the database container (preserves all data in local volume)
task db:down
```

---

## 4. Local AI Model (Ollama)

OmniStackAI uses local Ollama by default for offline, zero-cost inference.

```bash
# Check Ollama connection, health, and server version
task ollama:status

# List all local models downloaded on this machine
task ollama:models

# Validate Ollama host configuration from .env
task ollama:config

# Download/pull the model configured in .env (e.g. qwen2.5-coder:14b)
task ollama:pull

# Run one real inference test to verify local model responses
task ollama:verify

# Start Ollama server in foreground if not running as a system service
task ollama:serve
```

---

## 5. App Generation & Running Generated Apps (CLI)

Generate and run full-stack apps directly from the terminal.

```bash
# Compile an app prompt into a complete Git repo using local Ollama
task agent-engine:app:build -- "Build a recipe box where users save recipes with ingredients and cooking steps"

# Compile an app prompt into a specific output directory
OMNISTACKAI_APP_OUT_DIR="$HOME/Documents/Projects/GeneratedApps" task agent-engine:app:build -- "Task tracker with projects and deadlines"

# HYBRID build (R-465/R-466): the UI is written by a model over the deterministic API/DB/auth layer, with a
# validation->feedback->retry loop and template fallback, then type-checked with tsc and repaired from the
# compiler's errors (still-failing files revert to templates; the repair is committed). Opt-in, paid per
# generation (Groq/Gemini keys in .env). 429s are paced automatically (Retry-After honoured, bounded) and a
# request a provider rejects as too large (413) is shrunk to a compact grounding and retried.
OMNISTACKAI_CLOUD_PROVIDER=groq task agent-engine:ui:synthesize -- "Create a food delivery app with restaurants and couriers"
# Optional: OMNISTACKAI_WEB_NODE_MODULES=/path/to/existing/node_modules  (skips `pnpm install` in Step 3)
#           OMNISTACKAI_MAX_RETRY_AFTER_SECONDS=180                      (free tiers ask for 1-3 minute waits)

# Compile a prompt into an Application IR (JSON architecture spec) without writing files
task agent-engine:intake:run -- "A bookstore with books, authors, and orders"

# Run a generated app locally in one command (DB migrations + FastAPI :8000 + Next.js :3000)
task agent-engine:app:run -- scratch/apps/recipe-box

# Run TypeScript typecheck on a generated app frontend
task agent-engine:web-typecheck -- minimal-blog scratch/apps/my-blog
```

### Managing & Cleaning Generated Projects (`scratch/apps` & Output Folders)

```bash
# 1. List all generated projects currently in scratch/apps
ls -la scratch/apps

# 2. Delete a single generated project by name (one by one)
rm -rf scratch/apps/<project-name>
# Example:
rm -rf scratch/apps/create-a-worker-attendance-management-sy

# 3. Delete ALL generated projects from scratch/apps at once (cleans all apps, preserves directory)
rm -rf scratch/apps/*

# 4. If using your personal projects folder (~/Documents/Projects/GeneratedApps):
# List all apps in personal projects folder
ls -la ~/Documents/Projects/GeneratedApps

# Delete a single app from personal projects folder by name
rm -rf ~/Documents/Projects/GeneratedApps/<project-name>

# Delete ALL apps from personal projects folder at once
rm -rf ~/Documents/Projects/GeneratedApps/*
```

---

## 6. Solution Packs & Multi-Surface Ecosystems

Pre-verified, deterministic architecture baselines with zero model calls.

```bash
# Build a verified customer app demo repository from a Solution Pack
task builder:demo -- minimal-blog

# Build demo repository to a specific custom folder
task builder:demo -- minimal-blog scratch/apps/my-demo-blog

# List available Solution Packs and matching capabilities
task agent-engine:solution-packs -- --domain rideshare --capability favourites

# Build a Solution Pack project directly into an owned Git repo
task agent-engine:solution-pack:build -- minimal-blog scratch/apps/blog-project

# Package and export a Solution Pack with checksum verification
task agent-engine:solution-pack:package -- export --pack minimal-blog

# Synthesize, inspect, or build a multi-surface ecosystem pack (Web + Admin + API + Worker + DB)
task agent-engine:solution-pack:ecosystem -- synthesize --pack minimal-blog

# Turn a business prompt into an ecosystem scope proposal (multi-app platform plan)
task agent-engine:scope:propose -- "Multi-tenant food delivery platform with customer app and restaurant portal"

# Generate multiple connected Git repositories from an ecosystem prompt
task agent-engine:ecosystem:build -- "Ride sharing service with rider and driver apps"
```

---

## 7. Platform Status, Cost & Architecture Inspection

```bash
# Show active tier (Tier 0 local vs Tier 2 cloud) and active model routing from .env
task platform:status

# View combined preview, verify, and deploy project plan for an architecture IR
task plan:show -- rideshare-favourites

# Print the verifiable-engineering quality gate ladder for Next.js web target
task agent-engine:verify-plan -- nextjs-web

# Refresh the Console's metadata-only model and token cost overview
task console:snapshot

# Launch the Developer Cost & Model Overview Console (http://127.0.0.1:4321)
task console:serve

# Check AI task execution status and durable task tracker state
task ai:status

# View the current developer handoff document
task ai:handoff
```

---

## 8. Testing, Linting & Verification (Quality Gates)

All tests in OmniStackAI execute 100% offline with zero external network or model calls.

```bash
# Run the complete project verification pipeline (lint + unit tests + security check)
task verify

# Run all 3,330+ automated contract tests across all packages
task test

# Run all static linting checks (Python + Go + TypeScript contracts)
task lint

# Fast test run for agent-engine Python contracts only
bash scripts/agent-engine.sh test

# Fast lint run for agent-engine Python contracts only
bash scripts/agent-engine.sh lint

# Run Go control-plane unit tests
task control-plane:test

# Run Go control-plane lint checks
task control-plane:lint

# Run secret policy and sensitive token scanner
task security:quick
```

---

## 9. Environment & Troubleshooting

```bash
# Validate that your local environment has all required tools (Docker, Node, Python, pnpm, etc.)
task doctor

# Install missing local dependencies deterministically
task bootstrap

# Check .env placeholders, exclusions, and secret boundary rules
task env:check

# Check Colima VM status (if using Colima for Docker on macOS)
colima status

# Start Colima VM if not running
colima start

# Check running Docker containers
docker ps
```

---

## 10. Control-Plane — Users, Auth, Plans, Credits (R-469)

The Go control-plane (`services/control-plane`) is the future home of the real, hosted, multi-user
OmniStackAI platform (see `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` for the full phased
plan). As of R-469 it has real accounts, sessions, and a plan/credit model — no frontend yet
(`apps/console-web` is still the old static page; the real Next.js console is Phase B).

```bash
# Run the Go control-plane's own unit tests (hermetic, no database needed)
task control-plane:test

# Format/vet check the control-plane
task control-plane:lint

# Build the control-plane binary locally
task control-plane:build

# Start Postgres + the control-plane for real via Docker Compose, and verify health/readiness
task control-plane:verify
```

Once `task control-plane:verify` (or `docker compose -f infra/environments/local/compose.yaml up -d
postgres control-plane`) is running, the control-plane listens on `http://127.0.0.1:8080`:

```bash
# Register a new account — every signup gets the free plan + a starting credit grant
# (OMNISTACKAI_SIGNUP_CREDIT_GRANT in .env, default 100)
curl -s -X POST http://127.0.0.1:8080/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"a-real-password"}'
# -> {"id":"...","email":"you@example.com","role":"user","plan":"free","credit_balance":100,"token":"..."}

# Log in (returns a new session token; the old one from register is still valid until it expires)
curl -s -X POST http://127.0.0.1:8080/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"a-real-password"}'

# Who am I — pass the token from register/login as a bearer token
curl -s http://127.0.0.1:8080/auth/me -H "Authorization: Bearer <token>"

# Sign out (idempotent — safe to call again on an already-invalid token)
curl -s -X POST http://127.0.0.1:8080/auth/logout -H "Authorization: Bearer <token>"
```

Two roles only: `super_admin` (full platform access, not a purchasable tier) and `user` (everyone who
signs up — all access is gated by `plan`, never a second role tier). Plans are
`free`/`developer`/`pro`/`agency`/`enterprise`, with `byok` as an add-on flag rather than a separate
tier. Local-model usage is intended to stay credit-exempt (that enforcement lands in Phase C, once the
control-plane's Job API bridges to the agent-engine — R-469 only builds the account/credit-ledger
foundation, it does not yet meter any actual generation call).

Config knobs (see `.env.example`): `OMNISTACKAI_SESSION_TTL` (default `720h`),
`OMNISTACKAI_SIGNUP_CREDIT_GRANT` (default `100`).

---

## 11. Console — Real Next.js App (R-470)

`apps/console-web` is now a real Next.js (App Router, TypeScript) app — register/login/logout wired
to the control-plane's auth API via a server-side cookie proxy, plus the carried-over model/cost
overview page.

```bash
# One-time (or after pulling changes that touch apps/console-web/package.json):
pnpm install

# Bring up the control-plane it talks to
task control-plane:verify

# Then, in another terminal — dev server with hot reload on http://127.0.0.1:4321
task console:dev

# Or a production-style run:
task console:build
task console:start

# Individual gates (all run automatically as part of `task verify`):
task console:typecheck
task console:lint
```

Open `http://127.0.0.1:4321/register` to create an account (grants the free plan + starting
credits), then `/` for the authenticated home page and `/fabric` for the model/cost overview.

Config: `OMNISTACKAI_CONTROL_PLANE_URL` in the repo root `.env` (default `http://127.0.0.1:8080`) —
`scripts/console.sh` exports it before running any Next.js command; the console does not read its
own `.env` files.
