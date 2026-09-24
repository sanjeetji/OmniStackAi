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

### `fresh` — Factory reset, then become the owner

`fresh` **destroys every byte of local platform data** and hands you a clean platform that you own.

It removes the PostgreSQL volume (accounts, projects, sessions, billing, analytics) and every
generated project under the Studio workspace, starts the platform again, and creates the first
account as a `super_admin` on the `enterprise` plan. Templates in `templates/catalog` are part of
the repository and are never touched.

```bash
./scripts/omnistack.sh fresh
#   Type 'wipe' to confirm:  wipe
#   Owner email: you@example.com
#   Owner name (optional): Your Name

# Non-interactive, for a scripted rebuild:
./scripts/omnistack.sh fresh --yes --email you@example.com --name "Your Name"

# With your own password instead of a generated one (at least 12 characters):
./scripts/omnistack.sh fresh --yes --email you@example.com --password 'choose-something-long'
```

If you do not pass `--password`, one is generated and printed **once**. Write it down: only its
hash is stored. Then sign in at http://127.0.0.1:4321 with that email and password.

### `admin` — Administer platform accounts

The console has no admin screen yet, so accounts are managed from the shell. These talk to the same
database the control-plane uses and reuse its password hashing, so an account created here is
identical to one created by signing up.

```bash
./scripts/omnistack.sh admin list-users
./scripts/omnistack.sh admin list-users --limit 200

# Create the owner, or promote and re-password an existing account. Safe to re-run.
./scripts/omnistack.sh admin create-owner --email you@example.com --name "Your Name"

# Promote or demote
./scripts/omnistack.sh admin set-role --email teammate@example.com --role super_admin
./scripts/omnistack.sh admin set-role --email teammate@example.com --role user

# Move an account between plans: free, developer, pro, agency, enterprise
./scripts/omnistack.sh admin set-plan --email customer@example.com --plan pro

# Add model credits; every grant is written to the append-only credit_ledger
./scripts/omnistack.sh admin grant-credits --email customer@example.com --credits 500000 \
  --reason "annual plan top-up"

./scripts/omnistack.sh admin help
```

**Ordinary users sign themselves up** at the console; nothing below `super_admin` needs a command.

---

## 2b. Starting and stopping (R-551)

`start` and `stop` are the names most people reach for; `up` and `down` are the same commands.
Both names dispatch to one implementation, so they cannot drift apart.

```bash
./scripts/omnistack.sh start          # PostgreSQL, control-plane, Studio, console
./scripts/omnistack.sh status         # every component, its port and its health
./scripts/omnistack.sh stop           # stops everything; the database volume is kept
./scripts/omnistack.sh restart        # stop --keep-db, then start
```

### `doctor` checks that the toolchain *works*

A version number says nothing about whether an interpreter functions. On a machine where
Homebrew's `python@3.13` shipped a broken `pyexpat`, `doctor` reported the toolchain was fine
while `python3 -m venv` failed completely — so every generated Python backend refused to start and
the error looked like a platform bug. `doctor` now checks the two things that actually have to
hold:

```bash
./scripts/omnistack.sh doctor
  ok    python3 is 3.13 (3.13.15)
  ok    python3 can create a virtualenv with pip (generated backends will install)
```

If either fails it names the cause and a remedy that works:

```bash
brew install uv && uv python install 3.13
ln -sf "$(uv python find 3.13)" ~/.local/bin/python3
export PATH="$HOME/.local/bin:$PATH"
```

### `start` and `status` print every address you need

Both print the same table, from one function, so they cannot drift apart:

```
  Open this
    Console            http://127.0.0.1:4321
    On this network    http://192.168.1.57:4321

  APIs
    Studio             http://127.0.0.1:4173            health http://127.0.0.1:4173/healthz
    Control-plane      http://127.0.0.1:8080            health http://127.0.0.1:8080/healthz

  Data and models
    PostgreSQL         127.0.0.1:5432  db omnistackai  user omnistackai
    Ollama (local)     http://127.0.0.1:11434  model qwen2.5-coder:7b

  A generated project's apps
    Preview            http://127.0.0.1:4321/preview/<project-id>/<app>
    where <app> is one of: web, admin, api  (a mobile app is opened by QR, not in a frame)
```

`status` additionally reports each component's health, its pid and the Studio's mode
(`preview` means generated apps can run; `build-only` means they cannot).

### `verify` runs the whole gate set

```bash
./scripts/omnistack.sh verify   # contract tests, task verify, lint, security, env contract
```

---

## 3. Accounts, roles and plans

### What exists today

| Column | Values | Enforced? |
|---|---|---|
| `users.role` | `user`, `super_admin` | Stored and returned at sign-in. **No endpoint requires it yet** — there is no admin area. |
| `users.plan` | `free`, `developer`, `pro`, `agency`, `enterprise` | Stored and returned. **No quota is attached to it yet.** |
| `users.credit_balance` + `credit_ledger` | integer, append-only ledger | **Yes.** Every model call is metered and debited; a call with no balance is refused. |
| `users.byok_enabled` | boolean | Yes — decides whether the user's own provider key is used instead of the platform's. |
| `organizations`, `workspaces`, `workspace_members` | roles `owner`, `admin`, `member`, `viewer` | Tables exist. **Nothing in the console uses them yet.** |

So: metering is real, identity is real, and **plan limits and the admin surface are not built**.
Until they are, a `free` account can create as many projects and previews as it likes; only model
spend is capped.

### Looking at it directly

```bash
# A psql shell on the platform's own database
docker exec -it -e PGPASSWORD="$(grep '^OMNISTACKAI_POSTGRES_PASSWORD=' .env | cut -d= -f2-)" \
  omnistackai-local-postgres-1 psql -U omnistackai -d omnistackai

SELECT email, role, plan, credit_balance FROM users ORDER BY created_at;
SELECT * FROM credit_ledger ORDER BY created_at DESC LIMIT 20;
```

The control-plane applies its own migrations (`services/control-plane/migrations/`) on start-up;
there is no separate migrate command, so restarting it is enough.

---

## 4. Working on a template

A template lives in `templates/catalog/<slug>/`: a `template.json` manifest, a `repo/` golden
repository, `media/` screenshots, and a `capture.mjs` screenshot plan. Published today:
`ride-now` (mobility), `bazaar` (commerce), `care-clinic` (healthcare).

```bash
cd templates/catalog/care-clinic/repo
pnpm install
pnpm -r typecheck                          # every package
pnpm --filter @careclinic/api test         # API unit tests; no database needed

# Regenerate the demo data (it is generated, never hand-edited)
cd services/api
node scripts/generate-seed.mjs  > seed/001_demo.sql
node scripts/generate-icd10.mjs > seed/002_icd10.sql
```

To run one by hand against your own PostgreSQL, follow the template's `repo/README.md`. To exercise
the whole thing end to end against a running instance:

```bash
API_BASE=http://127.0.0.1:4000 node --test test/workflow.test.ts
```

A draft template lives at `templates/catalog/_<slug>/` and is hidden from the marketplace:

```bash
./scripts/preview-drafts.sh      # show drafts in the marketplace and restart the platform
./scripts/omnistack.sh restart   # back to the normal catalogue
```

**Screenshots.** Playwright is never a dependency of the platform or of a template; install it in a
scratch folder:

```bash
SCRATCH=$(mktemp -d)
npm i --prefix "$SCRATCH/pw" playwright
npx --prefix "$SCRATCH/pw" playwright install chromium-headless-shell

node scripts/capture-template-screens.mjs --template templates/catalog/care-clinic \
  --playwright "$SCRATCH/pw" --api http://127.0.0.1:4000 \
  --app patient=http://127.0.0.1:3101 --app doctor=http://127.0.0.1:3102 --app admin=http://127.0.0.1:3103
```

Run the template's apps as production builds against a freshly seeded database first; never capture
a dev server.

---

## 5. Component-Specific Development Commands

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

## 6. Verification & Quality Gates

Run these commands before committing any code:

```bash
task doctor           # Preflight toolchain check
task lint             # Static checks across Bash, Go, Python, TypeScript
bash scripts/test.sh  # Repository architectural contract tests
task verify           # Full suite verification (all unit & contract tests)
```
