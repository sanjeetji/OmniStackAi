# Setting up OmniStackAI on a new machine

Everything needed to run the platform locally, in the order to do it, with the traps that have
actually cost time. Written on macOS (Apple silicon, macOS 26); the Linux differences are at the
end.

**Short version:** install the tools, start Docker (Colima), create `.env`, install dependencies,
run `./scripts/omnistack.sh doctor`, then `./scripts/omnistack.sh up`.

---

## 1. What the platform needs, and why

| Tool | Version | What breaks without it |
|---|---|---|
| **Git** | any recent | Nothing works; project history is how the platform tracks customer code |
| **Homebrew** | any | The way every other tool below is installed |
| **Node.js** | **22.18 or newer** | Template APIs run TypeScript directly with no build step; older Node cannot |
| **pnpm** | 10 or newer | The console and every template are pnpm workspaces |
| **Go** | 1.27 or newer | The control-plane (auth, projects, billing, templates) is Go |
| **Python** | **exactly 3.13.x** | The agent-engine refuses to start on anything else |
| **Task** (`go-task`) | 3.x | `task verify`, `task lint` and the rest of the command interface |
| **ripgrep** (`rg`) | any | `task lint` and the contract tests fail immediately |
| **Colima** | any | The Docker engine. **Not** Docker Desktop |
| **Docker CLI + docker-compose** | 27+ / v5 | PostgreSQL and the control-plane run as containers |
| **curl** | ships with macOS | Health checks in the scripts |

Optional, but you want at least one model provider:

| Optional | Why |
|---|---|
| **Ollama** + a coder model | Free, local, private, no rate limits. Needed for prompt→app builds and chat edits |
| A cloud key (Google, Anthropic, OpenAI, OpenRouter) | Faster and stronger than a small local model |
| **Playwright** in a scratch folder | Only to capture template screenshots (`scripts/capture-template-screens.mjs`). Never a platform dependency |

**Nothing in the template marketplace needs a model.** Browsing templates, *Use template*, previews,
running an app, and `task verify` all work with no provider at all. Only building an app from a
prompt and editing by chat call a model.

---

## 2. Install

```bash
# 1. Xcode command line tools (gives you git)
xcode-select --install

# 2. Homebrew — https://brew.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. The toolchain (one command)
brew install node pnpm go go-task python@3.13 ripgrep colima docker docker-compose

# 4. Optional: a local model (free, no keys, no limits)
brew install ollama && brew services start ollama
ollama pull qwen2.5-coder:7b     # 4.7 GB; use :14b only if you have 24 GB+ of RAM
```

Then three pieces of configuration that are easy to miss:

```bash
# Python 3.13 must be the `python3` on PATH. Homebrew does not do this for you.
echo 'export PATH="/opt/homebrew/opt/python@3.13/libexec/bin:$PATH"' >> ~/.zshrc
exec zsh

# Docker must be able to find the compose plugin Homebrew installed.
mkdir -p ~/.docker && cat > ~/.docker/config.json <<'JSON'
{ "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"] }
JSON

# Start the Docker engine. 4 GB leaves room for a local model on a 16 GB Mac;
# use --memory 6 (or more) if you are not running Ollama.
colima start --cpu 4 --memory 4 --disk 40
```

Colima keeps running between reboots with `brew services start colima`, or start it by hand each
session with `colima start`.

---

## 3. The repository

```bash
git clone https://github.com/sanjeetji/OmniStackAi.git
cd OmniStackAi
cp .env.example .env
pnpm install                 # ~700 packages; on a slow link add --fetch-timeout=900000
```

Now edit `.env`. Two values have no safe default and must be set:

```bash
OMNISTACKAI_POSTGRES_PASSWORD=<any local-only password>
OMNISTACKAI_SECRETS_KEY=<64 hex characters: openssl rand -hex 32>
```

Two things the example already gets right, worth knowing if you edit them:

- `OMNISTACKAI_AGENT_ENGINE_URL` must stay `host.docker.internal`, never `127.0.0.1`: the
  control-plane reads it from inside a container, where `127.0.0.1` means the container itself, and
  every build hangs.
- Any value containing spaces or a colon must be **quoted**. `scripts/console.sh` sources `.env`,
  so an unquoted one kills start-up with `line 14: with: command not found`.

Choose a model provider:

```bash
# Local (recommended for day-to-day work: free, private, no rate limits)
OMNISTACKAI_CLOUD_PROVIDER=none
OMNISTACKAI_OLLAMA_MODEL=qwen2.5-coder:7b
OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS=32768
OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS=24576
OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS=4096
OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS=900

# or cloud (faster, stronger; costs money and can be rate limited)
OMNISTACKAI_CLOUD_PROVIDER=google
GOOGLE_API_KEY=AIza...
OMNISTACKAI_GOOGLE_MODEL=gemini-3-flash-preview
```

What to expect from a local model: on an M-series laptop, `qwen2.5-coder:7b` takes a few minutes
per chat edit, where a cloud model takes about half a minute. It is free, private and never rate
limited, but you must raise `OMNISTACKAI_AGENT_CALL_TIMEOUT`, or the control-plane gives up after
five minutes and reports "could not reach the control-plane" while the edit is still running.
Bigger models are better at editing but need much more memory: the 7b needs about 5.5 GB while
loaded, the 14b about 10 GB, so on a 16 GB Mac the 14b competes with Docker and the preview apps.

---

## 4. Check, then start

```bash
./scripts/omnistack.sh doctor     # every requirement above, with the exact fix for each failure
./scripts/omnistack.sh up         # PostgreSQL + control-plane + Studio + console
./scripts/omnistack.sh status
open http://127.0.0.1:4321
```

`doctor` is the thing to run first on any new machine: it checks the tool versions, that `python3`
really is 3.13, that Node is new enough for template APIs, that the compose plugin is reachable,
that `.env` exists and can be sourced, that the agent-engine URL is container-safe, that the Docker
daemon answers, and which model provider (if any) is usable.

First start builds the console, so it takes a few minutes. After that `up` takes seconds.

Verify the install properly:

```bash
task verify          # ~4,000 offline tests, no model calls, no network
task lint
./scripts/smoke-core.sh   # the full prompt → app → preview → chat edit loop (needs a model)
```

---

## 5. Using it

- **Templates** (no model needed): *Templates* → RideNow → *Use template* → *Preview*. The preview
  installs dependencies, creates a fresh database with demo data, builds each app and serves it.
  First run of a template takes about a minute; later runs about 35 seconds.
- **From a prompt** (needs a model): type what you want on the home page.
- **Chat edits** (needs a model): open a project and ask for a change. Start the preview **before**
  editing — the agent type-checks against the project's installed dependencies, which arrive with
  the first preview.

Stop everything with `./scripts/omnistack.sh down`, and `colima stop` before shutting the machine
down.

Every command — running, administering accounts, starting over, verifying, working on a template —
is in [COMMANDS.md](../COMMANDS.md).

---

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `line 14: with: command not found` on start-up | Unquoted `OMNISTACKAI_GATEWAY_PROMPT` in `.env`. Quote it |
| `Python 3.13.x is required` | `python3` is macOS's 3.9. Put `/opt/homebrew/opt/python@3.13/libexec/bin` first on PATH |
| `rg: command not found` during lint or tests | `brew install ripgrep` |
| `docker daemon not reachable` | `colima start` |
| `docker compose` unknown command | Add `cliPluginsExtraDirs` to `~/.docker/config.json` (§2) |
| Builds hang, control-plane logs show it cannot reach the agent-engine | `OMNISTACKAI_AGENT_ENGINE_URL` points at `127.0.0.1`; use `host.docker.internal` |
| `pnpm install` fails with `The operation was aborted due to timeout` | Slow link. `pnpm install --fetch-timeout=900000` (the repo's `.npmrc` already raises retries) |
| Homebrew downloads crawl (~20 KB/s) | Its CDN (ghcr.io) is slow from some networks. Leave it running; it does finish |
| `Ollama is unavailable` in a build | `brew services start ollama`, and check `ollama list` has a model |
| Cloud provider returns 503 / 429 / 402 | Provider-side: capacity, quota or credit. Switch model or use Ollama |
| Chat edit fails with "could not reach the control-plane" after exactly 5 minutes | The upstream budget expired while a local model was still writing. Set `OMNISTACKAI_AGENT_CALL_TIMEOUT=30m` and restart |
| Next edit returns 409 "workspace is currently locked" | The previous edit is still running upstream (see the row above). Wait for it, or restart the Studio |
| Chat edit says it cannot type-check | Start the project's preview once, so its dependencies exist |
| A generated **Python** backend fails to start its virtualenv (`ensurepip` error) | Homebrew's Python 3.13 on macOS 26 ships a `pyexpat` linked against a newer `libexpat` than the OS provides, so XML parsing fails and pip's TLS setup crashes. Use a Python from python.org or `uv` for generated backends, or rebuild: `brew reinstall --build-from-source python@3.13` |
| Preview page loads but clicking a link feels like a full reload | Known limit: the console is itself a Next app and answers the preview's client-side navigation requests first. Pages, forms and buttons work normally |

---

## 7. Screenshots for a template (optional)

Playwright is never a dependency of the platform or of a template; install it in a scratch folder:

```bash
SCRATCH=$(mktemp -d)
npm i --prefix "$SCRATCH/pw" playwright
npx --prefix "$SCRATCH/pw" playwright install chromium-headless-shell

node scripts/capture-template-screens.mjs --template templates/catalog/ride-now \
  --playwright "$SCRATCH/pw" --api http://127.0.0.1:4000 \
  --app rider=http://127.0.0.1:3101 --app driver=http://127.0.0.1:3102 --app admin=http://127.0.0.1:3103
```

Run the template's apps as production builds against a freshly seeded database first; never capture
a dev server. Each template describes its own capture in `templates/catalog/<slug>/capture.mjs`.

---

## 8. Linux

Same list, without Colima: install Docker Engine and the compose plugin from your distribution, and
`host.docker.internal` works because the compose file already maps it to the host gateway. Node, Go,
pnpm, ripgrep and Task come from your package manager; Python 3.13 from your distribution or
`uv python install 3.13`. Everything else is identical.
