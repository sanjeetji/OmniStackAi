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
