# OmniStackAI — Platform Run & Operations Guide

This guide details all commands to run, inspect, develop, and verify OmniStackAI locally.

---

## 1. Quick Start: Single-Command Platform Runner

The easiest way to run the entire platform is with `scripts/omnistack.sh` or its `task` aliases.

```bash
# 1. Check your environment, tools, and ports
./scripts/omnistack.sh doctor
# or
task doctor

# 2. Start the entire platform (PostgreSQL + Control-Plane + Studio Preview + Console Web)
./scripts/omnistack.sh up
# or
task up

# 3. Check health and ports of all services
./scripts/omnistack.sh status
# or
task status

# 4. Open the Console Web in your browser
./scripts/omnistack.sh open
```

---

## 2. All `omnistack.sh` Commands & Options

### `up` — Start the Platform
Starts PostgreSQL, Control-Plane, Agent-Engine Studio, and Console Web in the correct dependency order.

```bash
./scripts/omnistack.sh up                 # Standard start (Preview mode ON by default)
./scripts/omnistack.sh up --dev           # Run Next.js Console in hot-reload dev mode
./scripts/omnistack.sh up --no-preview    # Safe build-only mode (does not run generated code)
./scripts/omnistack.sh up --no-console    # Run backend services only (no web frontend)
```

### `down` — Stop the Platform
Stops all background processes and containers. Named PostgreSQL data volumes are kept safe.

```bash
./scripts/omnistack.sh down               # Stop all services and Docker containers
./scripts/omnistack.sh down --keep-db     # Stop Studio & Console, leave PostgreSQL running
```

### `restart` — Restart Services
Performs a safe restart (`down --keep-db` followed by `up`).

```bash
./scripts/omnistack.sh restart            # Restart services keeping database intact
./scripts/omnistack.sh restart --dev      # Restart with Console in dev mode
```

### `status` — Service Health & Port Map
Probes health endpoints, active PIDs, and running modes across all 4 services.

```bash
./scripts/omnistack.sh status
# or
task status
```

| Service | Default Port | Health URL / Check |
| :--- | :--- | :--- |
| **Console Web** | `:4321` | `http://127.0.0.1:4321/login` |
| **Agent-Engine Studio** | `:4173` | `http://127.0.0.1:4173/healthz` |
| **Control-Plane** | `:8080` | `http://127.0.0.1:8080/healthz` |
| **PostgreSQL** | `:5432` | Docker container `postgres` |
| **Ollama (Local AI)** | `:11434` | `http://127.0.0.1:11434/api/version` |

### `logs` — Live Service Logs
Tail stdout/stderr for any platform component.

```bash
./scripts/omnistack.sh logs studio -f         # Follow Agent-Engine Studio logs
./scripts/omnistack.sh logs console -f        # Follow Console Web logs
./scripts/omnistack.sh logs control-plane -f  # Follow Go Control-Plane Docker logs
./scripts/omnistack.sh logs postgres -f       # Follow PostgreSQL Docker logs
```

### `build` — Build Console Web for Production
Runs dependency snapshot and Turbopack production build.

```bash
./scripts/omnistack.sh build
```

### `verify` — Run All System Gates
Runs contract checks, lints, and all 3,800+ tests offline.

```bash
./scripts/omnistack.sh verify
# or
task verify
```

---

## 3. Component-Specific Development Commands

### A. Console Web (`apps/console-web/`)

```bash
cd apps/console-web

pnpm dev          # Start local dev server with Turbopack on http://127.0.0.1:4321
pnpm build        # Optimized production build
pnpm start        # Start production server
pnpm typecheck    # TypeScript verification (tsc --noEmit)
pnpm lint         # ESLint check
```

### B. Control-Plane (`services/control-plane/`)

```bash
cd services/control-plane

# Run unit tests across all internal packages (auth, deploy, git, projects, secrets, seo, skills)
go test -v ./...

# Run tests for specific packages
go test -v ./internal/deploy/...
go test -v ./internal/projects/...
go test -v ./migrations/...

# Run database migrations
task db:up        # Start postgres container
task db:status    # Check migration status
task db:down      # Stop postgres container
```

### C. Agent-Engine (`services/agent-engine/`)

```bash
cd services/agent-engine

# Start Studio directly
PYTHONPATH=src python3 -m omnistackai_agent_engine.studio.main --preview --port 4173

# Lint agent-engine Python contracts
bash scripts/agent-engine.sh lint
# or
task agent-engine:lint

# Run agent-engine unit tests
PYTHONPATH=src python3 -m unittest discover -s tests
# or
task agent-engine:test
```

### D. Local Ollama AI Model

```bash
task ollama:config    # Inspect configured local model
task ollama:status    # Check if loopback Ollama is answering
task ollama:pull      # Pull default model (qwen2.5-coder:14b)
task ollama:serve     # Launch Ollama serve daemon
```

---

## 4. Verification & Quality Gates

Run these commands before committing any code:

```bash
task doctor           # Preflight toolchain check
task lint             # Static checks across Bash, Go, Python, TypeScript
bash scripts/test.sh  # Repository architectural contract tests
task verify           # Full suite verification (all unit & contract tests)
```
