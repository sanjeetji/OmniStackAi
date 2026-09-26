#!/usr/bin/env bash
# OmniStackAI — one script to run the whole platform locally.
#
#   ./scripts/omnistack.sh up        # start everything (preview mode ON by default)
#   ./scripts/omnistack.sh status    # what is running, where, and is it healthy
#   ./scripts/omnistack.sh logs studio -f
#   ./scripts/omnistack.sh down      # stop everything (the database volume is kept)
#
# Why this exists: the platform is four processes (PostgreSQL, control-plane, agent-engine
# Studio, console) and the agent-engine has two modes. Starting them by hand, in the right
# order, with the right environment, was four commands and a footgun - the Studio's live
# preview only exists in preview mode, so "Preview isn't working" was usually "the Studio was
# started in build-only mode". `up` starts preview mode unless you ask for --no-preview.
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
run_dir="$repo_root/.run"
env_file="$repo_root/.env"
compose_file="$repo_root/infra/environments/local/compose.yaml"

# Services managed as background processes (Docker handles postgres/control-plane itself).
PROC_SERVICES=(studio console)

# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------

log()  { printf '%s\n' "$*"; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mok\033[0m    %s\n' "$*"; }
warn() { printf '  \033[33mwarn\033[0m  %s\n' "$*"; }
fail() { printf '  \033[31mfail\033[0m  %s\n' "$*"; }
die()  { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

# Read a key from .env without sourcing it (values may contain characters we do not want to run).
env_value() {
  local key="$1" fallback="${2:-}" line
  if [[ -f "$env_file" ]]; then
    line="$(grep -E "^${key}=" "$env_file" | tail -1 || true)"
    if [[ -n "$line" ]]; then
      line="${line#*=}"
      line="${line%\"}"; line="${line#\"}"
      line="${line%\'}"; line="${line#\'}"
      if [[ -n "$line" ]]; then printf '%s' "$line"; return; fi
    fi
  fi
  printf '%s' "$fallback"
}

compose() { docker compose --env-file "$env_file" -f "$compose_file" "$@"; }

pid_file() { printf '%s/%s.pid' "$run_dir" "$1"; }
log_file() { printf '%s/%s.log' "$run_dir" "$1"; }

service_pid() {
  local name="$1" file pid
  file="$(pid_file "$name")"
  [[ -f "$file" ]] || return 1
  pid="$(cat "$file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  printf '%s' "$pid"
}

port_listener() {
  # Prints "<command> <pid>" for whatever is listening on the port, or nothing.
  # `lsof` exits 1 when nothing matches, and this script runs with `pipefail`, so the trailing
  # `|| true` is required: without it, "the port is free" would abort the caller under `set -e`.
  { lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true; } | tail -n +2 | awk 'NR==1 {print $1" "$2}'
}

http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$1" 2>/dev/null || printf '000'; }

wait_http() {
  # wait_http <url> <seconds> [expected-prefix]
  local url="$1" timeout="${2:-60}" want="${3:-2}" waited=0 code
  while (( waited < timeout * 2 )); do
    code="$(http_code "$url")"
    [[ "$code" == "$want"* ]] && return 0
    # A redirect from a gated page still proves the server answers.
    [[ "$want" == "2" && "$code" == 3* ]] && return 0
    sleep 0.5
    waited=$((waited + 1))
  done
  return 1
}

start_bg() {
  # start_bg <name> <command...>
  # `set -m` inside the subshell turns on job control, so the background job becomes the leader
  # of its OWN process group. That matters for stop_service: we can then signal the whole group
  # (wrapper script + python/next child) without ever signalling this script's own group.
  local name="$1"; shift
  mkdir -p "$run_dir"
  : > "$(log_file "$name")"
  ( set -m; "$@" >>"$(log_file "$name")" 2>&1 & printf '%s' "$!" > "$(pid_file "$name")" )
}

stop_service() {
  local name="$1" pid pgid self_pgid
  if pid="$(service_pid "$name")"; then
    pgid="$({ ps -o pgid= "$pid" 2>/dev/null || true; } | tr -d ' ')"
    self_pgid="$({ ps -o pgid= $$ 2>/dev/null || true; } | tr -d ' ')"
    if [[ -n "$pgid" && "$pgid" != "$self_pgid" ]]; then
      kill -TERM -- "-$pgid" 2>/dev/null || true
    else
      # Same group as this script (should not happen with start_bg): signal only the process
      # and its direct children, never the group.
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
    fi
    local waited=0
    while kill -0 "$pid" 2>/dev/null && (( waited < 20 )); do sleep 0.25; waited=$((waited + 1)); done
    if kill -0 "$pid" 2>/dev/null; then
      if [[ -n "$pgid" && "$pgid" != "$self_pgid" ]]; then kill -KILL -- "-$pgid" 2>/dev/null || true; fi
      kill -KILL "$pid" 2>/dev/null || true
    fi
    ok "$name stopped (pid $pid)"
  else
    log "  --    $name was not running"
  fi
  rm -f "$(pid_file "$name")"
}

# ---------------------------------------------------------------------------------------------
# Resolved configuration
# ---------------------------------------------------------------------------------------------

CONSOLE_PORT="$(env_value OMNISTACKAI_CONSOLE_PORT 4321)"
STUDIO_PORT="$(env_value OMNISTACKAI_STUDIO_PORT 4173)"
CONTROL_PLANE_PORT="$(env_value OMNISTACKAI_CONTROL_PLANE_PORT 8080)"
POSTGRES_PORT="$(env_value OMNISTACKAI_POSTGRES_PORT 5432)"
OLLAMA_URL="$(env_value OMNISTACKAI_OLLAMA_BASE_URL http://127.0.0.1:11434)"

console_url() { printf 'http://127.0.0.1:%s' "$CONSOLE_PORT"; }
studio_url() { printf 'http://127.0.0.1:%s' "$STUDIO_PORT"; }
control_plane_url() { printf 'http://127.0.0.1:%s' "$CONTROL_PLANE_PORT"; }

# R-552: the local model actually loaded, for the endpoint table. Best effort: an unreachable or
# model-less Ollama must not make a status command fail.
ollama_model() {
  # Pure shell on purpose: a status command must not depend on the interpreter whose brokenness
  # `doctor` exists to report. Takes the first "name" field; empty when Ollama is unreachable.
  curl -fsS --max-time 2 "$OLLAMA_URL/api/tags" 2>/dev/null \
    | tr ',' '\n' \
    | sed -n 's/.*"name" *: *"\([^"]*\)".*/\1/p' \
    | head -1
}

# R-552: every address a person might need, printed the same way by `start` and by `status`.
# Two copies of this drifted apart before; one function cannot.
# Keep one installed node_modules for generated web apps, so build-time type-checking is free.
# Exported for the studio through the environment, which is where verify_and_repair_build reads it.
warm_web_modules() {
  # The directory has to be *named* node_modules. TypeScript resolves through a symlink's real
  # path, and nested lookups only recognise a directory by that name -- so a cache called anything
  # else makes `next`'s own types unresolvable and reports invented errors in correct code. That is
  # worse than not checking at all, and it took an A/B of two identical caches to see it.
  local cache="${OMNISTACKAI_WEB_NODE_MODULES:-$HOME/.omnistackai/web-typecheck/node_modules}"
  if [[ -x "$cache/.bin/tsc" ]]; then
    export OMNISTACKAI_WEB_NODE_MODULES="$cache"
    return 0
  fi
  if ! command -v pnpm >/dev/null 2>&1; then
    warn "pnpm not found - generated code will not be type-checked at build time"
    return 0
  fi
  step "Warming the type-checker (one install, shared by every generated project)"
  local work
  work="$(mktemp -d)"
  if ! bash "$repo_root/scripts/agent-engine.sh" emit-web-package "$work" >/dev/null 2>&1; then
    warn "could not prepare the type-check cache - builds will report as not type-checked"
    rm -rf "$work"
    return 0
  fi
  if (cd "$work" && pnpm install --ignore-scripts --ignore-workspace >/dev/null 2>&1); then
    mkdir -p "$(dirname "$cache")"
    rm -rf "$cache"
    mv "$work/node_modules" "$cache"
    export OMNISTACKAI_WEB_NODE_MODULES="$cache"
    ok "type-checker ready ($cache)"
  else
    warn "type-check cache install failed - builds will report as not type-checked"
  fi
  rm -rf "$work"
}

# The same for the Expo apps (founder, 2026-09-26: "what about the app side?"): one install shared
# by every generated mobile app, so builds type-check them instead of reporting "not installed".
# Its package.json is kept beside it; when the generated dependencies change, it is rebuilt.
warm_api_env() {
  step "Warming the generated-API environment (one install, shared by every generated Python API)"
  if bash "$repo_root/scripts/agent-engine.sh" warm-api-env >/dev/null 2>&1; then
    ok "generated-API environment ready"
  else
    warn "could not prepare the shared API environment - each preview will install its own"
  fi
}

warm_mobile_modules() {
  local cache="${OMNISTACKAI_MOBILE_NODE_MODULES:-$HOME/.omnistackai/mobile-typecheck/node_modules}"
  local work
  work="$(mktemp -d)"
  if ! bash "$repo_root/scripts/agent-engine.sh" emit-mobile-package "$work" >/dev/null 2>&1; then
    warn "could not prepare the mobile type-check cache - mobile apps will report as not type-checked"
    rm -rf "$work"
    return 0
  fi
  if [[ -x "$cache/.bin/tsc" ]] && cmp -s "$work/package.json" "$(dirname "$cache")/package.json"; then
    export OMNISTACKAI_MOBILE_NODE_MODULES="$cache"
    rm -rf "$work"
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    warn "npm not found - generated mobile apps will not be type-checked at build time"
    rm -rf "$work"
    return 0
  fi
  step "Warming the mobile type-checker (one Expo install, shared by every generated app)"
  if (cd "$work" && npm install --no-audit --no-fund --legacy-peer-deps --ignore-scripts >/dev/null 2>&1); then
    mkdir -p "$(dirname "$cache")"
    rm -rf "$cache"
    mv "$work/node_modules" "$cache"
    cp "$work/package.json" "$(dirname "$cache")/package.json"
    export OMNISTACKAI_MOBILE_NODE_MODULES="$cache"
    ok "mobile type-checker ready ($cache)"
  else
    warn "mobile type-check cache install failed - mobile apps will report as not type-checked"
  fi
  rm -rf "$work"
}

print_endpoints() {
  local lan; lan="$(lan_address)"
  log ""
  log "  Open this"
  log "    Console            $(console_url)"
  [[ -n "$lan" ]] && log "    On this network    http://$lan:$CONSOLE_PORT"
  log ""
  log "  APIs"
  log "    Studio             $(studio_url)            health $(studio_url)/healthz"
  log "    Control-plane      $(control_plane_url)            health $(control_plane_url)/healthz"
  log ""
  log "  Data and models"
  log "    PostgreSQL         127.0.0.1:$POSTGRES_PORT  db $(postgres_db)  user $(postgres_user)"
  local model; model="$(ollama_model)"
  if [[ -n "$model" ]]; then
    log "    Ollama (local)     $OLLAMA_URL  model $model"
  else
    log "    Ollama (local)     $OLLAMA_URL  (not reachable - cloud providers will be used)"
  fi
  log ""
  log "  A generated project's apps"
  log "    Preview            $(console_url)/preview/<project-id>/<app>"
  log "    where <app> is one of: web, admin, api  (a mobile app is opened by QR, not in a frame)"
}

lan_address() {
  # Best-effort LAN IPv4, for the "open it on your phone" hint. Never used for binding.
  ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true
}

require_env_file() {
  [[ -f "$env_file" ]] || die "Missing $env_file. Copy .env.example to .env and set a local-only database password."
}

# ---------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------

# Every version trap that has actually cost someone an afternoon lives here, so a new machine
# fails loudly at `doctor` instead of deep inside a build. See docs/SETUP.md.
at_least() { # at_least <have> <want>: true when <have> is >= <want>
  [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" == "$2" ]]
}

cmd_doctor() {
  local problems=0
  step "Tools"
  for tool in docker python3 pnpm node curl go task rg; do
    if ! have "$tool"; then fail "$tool is missing (see docs/SETUP.md)"; problems=$((problems + 1)); continue; fi
    # `go --version` is an error; go wants a subcommand.
    if [[ "$tool" == "go" ]]; then ok "go  $(go version 2>&1 | head -1)"; else ok "$tool  $("$tool" --version 2>&1 | head -1)"; fi
  done
  if have python3; then
    local py; py="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || echo 0)"
    if [[ "${py%%.*}.$(printf '%s' "${py#*.}" | cut -d. -f1)" == "3.13" ]]; then
      ok "python3 is 3.13 ($py)"
    else
      fail "python3 is $py, but the agent-engine requires 3.13.x."
      log "        A working 3.13 is easiest via uv: brew install uv && uv python install 3.13"
      log '        then: ln -sf "$(uv python find 3.13)" ~/.local/bin/python3'
      log '        and put ~/.local/bin first on PATH.'
      problems=$((problems + 1))
    fi

    # R-551: a version string says nothing about whether the interpreter WORKS. Homebrew's
    # python@3.13 and @3.14 on this machine both ship a pyexpat that fails to dlopen, which breaks
    # plistlib, which empties platform.mac_ver(), which makes pip's vendored truststore raise on
    # int(''). Every Python-backend preview failed while doctor reported the toolchain was fine.
    # These two checks are what actually has to hold, so they are what is checked.
    if ! python3 -c 'import xml.parsers.expat' >/dev/null 2>&1; then
      fail "python3 cannot import pyexpat, so plistlib and anything parsing XML will fail."
      log "        This is a broken interpreter build, not your project. Symptom: platform.mac_ver()"
      log "        returns empty strings, pip then raises on int(''), and 'python3 -m venv' fails, so"
      log "        no Python-backend preview can start."
      log "        Fix: brew install uv && uv python install 3.13"
      log '              ln -sf "$(uv python find 3.13)" ~/.local/bin/python3'
      log '              export PATH="$HOME/.local/bin:$PATH"'
      problems=$((problems + 1))
    else
      local venv_probe; venv_probe="$(mktemp -d)"
      if python3 -m venv "$venv_probe/v" >/dev/null 2>&1 && [[ -x "$venv_probe/v/bin/pip" ]]; then
        ok "python3 can create a virtualenv with pip (generated backends will install)"
      else
        fail "python3 cannot create a working virtualenv, so every generated Python backend will fail to start."
        log "        Reproduce with: python3 -m venv /tmp/probe"
        log "        Fix: brew install uv && uv python install 3.13"
        log '              ln -sf "$(uv python find 3.13)" ~/.local/bin/python3'
        log '              export PATH="$HOME/.local/bin:$PATH"'
        problems=$((problems + 1))
      fi
      rm -rf "$venv_probe"
    fi
  fi
  if have node; then
    local nodev; nodev="$(node --version 2>/dev/null | tr -d 'v')"
    if at_least "$nodev" 22.18; then ok "node is new enough for template APIs ($nodev)"; else fail "node $nodev is older than 22.18, which template APIs need to run TypeScript directly"; problems=$((problems + 1)); fi
  fi
  if have docker; then
    if docker compose version >/dev/null 2>&1; then
      ok "docker compose plugin"
    else
      fail 'docker compose plugin not found — add {"cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]} to ~/.docker/config.json'
      problems=$((problems + 1))
    fi
  fi

  step "Configuration"
  if [[ -f "$env_file" ]]; then
    ok ".env present"
    # scripts/console.sh sources .env, so an unquoted value with spaces takes the whole start-up
    # down with a confusing "command not found" (.env.example ships one: R-530).
    if (set -a; source "$env_file") >/dev/null 2>&1; then
      ok ".env can be sourced"
    else
      fail ".env has a line the shell cannot read — quote values containing spaces or ':'"
      (set -a; source "$env_file") 2>&1 | head -2 | sed 's/^/        /'
      problems=$((problems + 1))
    fi
    local engine_url; engine_url="$(env_value OMNISTACKAI_AGENT_ENGINE_URL "")"
    if [[ "$engine_url" == *"127.0.0.1"* || "$engine_url" == *"localhost"* ]]; then
      fail "OMNISTACKAI_AGENT_ENGINE_URL is $engine_url, which inside the control-plane container means the container itself"
      log "        use http://host.docker.internal:$STUDIO_PORT"
      problems=$((problems + 1))
    fi
  else
    fail ".env missing (cp .env.example .env, then set a local-only password — see docs/SETUP.md)"
    problems=$((problems + 1))
  fi
  if docker info >/dev/null 2>&1; then ok "docker daemon reachable"; else fail "docker daemon not reachable (start it with: colima start)"; problems=$((problems + 1)); fi
  # A cloud model whose safe input plus maximum output exceeds its context window cannot be built,
  # and the platform then quietly falls back to Ollama and reports "Ollama is unavailable" (R-530).
  local ctx_window safe_in max_out
  ctx_window="$(env_value OMNISTACKAI_CLOUD_CONTEXT_WINDOW_TOKENS 128000)"
  safe_in="$(env_value OMNISTACKAI_CLOUD_SAFE_INPUT_TOKENS 0)"
  max_out="$(env_value OMNISTACKAI_CLOUD_MAX_OUTPUT_TOKENS 0)"
  if [[ "$safe_in" =~ ^[0-9]+$ && "$max_out" =~ ^[0-9]+$ && "$ctx_window" =~ ^[0-9]+$ ]] && (( safe_in + max_out > ctx_window )); then
    fail "cloud token budget does not fit: safe input $safe_in + max output $max_out > context window $ctx_window"
    log "        lower OMNISTACKAI_CLOUD_SAFE_INPUT_TOKENS, or raise OMNISTACKAI_CLOUD_CONTEXT_WINDOW_TOKENS"
    problems=$((problems + 1))
  fi
  if [[ -d "$repo_root/apps/console-web/node_modules" ]]; then ok "console dependencies installed"; else warn "console dependencies missing - run: $0 build"; fi
  if [[ -d "$repo_root/apps/console-web/.next" ]]; then ok "console production build present"; else warn "no console build yet - run: $0 build"; fi

  step "Model provider"
  local cloud_provider; cloud_provider="$(env_value OMNISTACKAI_CLOUD_PROVIDER none)"
  if [[ "$(http_code "$OLLAMA_URL/api/version")" == "200" ]]; then
    local models=""; models="$(curl -fsS --max-time 5 "$OLLAMA_URL/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | paste -sd' ' - || true)"
    if [[ -n "$models" ]]; then
      ok "local Ollama reachable with: $models"
    else
      warn "local Ollama is running but has no model — pull one, e.g.: ollama pull qwen2.5-coder:7b"
    fi
  elif [[ "$cloud_provider" == "none" || -z "$cloud_provider" ]]; then
    warn "no model provider: Ollama is not running and OMNISTACKAI_CLOUD_PROVIDER is none."
    log "        Builds and chat edits need one; templates, previews and task verify do not."
  else
    local key_name="" key_value=""
    case "$cloud_provider" in
      google) key_name=GOOGLE_API_KEY ;;
      anthropic) key_name=ANTHROPIC_API_KEY ;;
      openai) key_name=OPENAI_API_KEY ;;
      openrouter) key_name=OPENROUTER_API_KEY ;;
      *) key_name="" ;;
    esac
    if [[ -n "$key_name" ]]; then key_value="$(env_value "$key_name" "")"; fi
    if [[ -n "$key_name" && -z "$key_value" ]]; then
      fail "OMNISTACKAI_CLOUD_PROVIDER=$cloud_provider but $key_name is empty in .env"
      problems=$((problems + 1))
    else
      ok "cloud provider $cloud_provider configured (Ollama not running, so it handles every call)"
    fi
  fi

  step "Ports"
  for entry in "console:$CONSOLE_PORT" "studio:$STUDIO_PORT" "control-plane:$CONTROL_PLANE_PORT" "postgres:$POSTGRES_PORT"; do
    local name="${entry%%:*}" port="${entry##*:}" who
    who="$(port_listener "$port")"
    if [[ -n "$who" ]]; then log "  used  $name ($port) by $who"; else ok "$name ($port) free"; fi
  done

  printf '\n'
  if (( problems > 0 )); then die "$problems blocking problem(s) above."; fi
  log "Ready. Start everything with: $0 up"
}

cmd_build() {
  require_env_file
  step "Building the console (snapshot + next build)"
  bash "$repo_root/scripts/console.sh" build
  ok "console built"
}

cmd_up() {
  local preview=1 with_console=1 dev_console=0
  while (( $# > 0 )); do
    case "$1" in
      --no-preview) preview=0 ;;
      --no-console) with_console=0 ;;
      --dev)        dev_console=1 ;;
      *) die "Unknown option for up: $1" ;;
    esac
    shift
  done

  require_env_file
  have docker || die "docker is required"
  docker info >/dev/null 2>&1 || die "docker daemon is not running"
  mkdir -p "$run_dir"

  step "PostgreSQL + control-plane (Docker)"
  # --build: the control-plane runs from an image, so without a rebuild `up` silently serves
  # whatever Go code was baked in last time. That hid a startup panic and every route added in
  # R-499..R-517 (found in R-518). Docker's layer cache keeps an unchanged rebuild to seconds.
  log "  building the control-plane image from source (cached layers make this quick)"
  compose up -d --build --wait postgres control-plane >/dev/null
  if wait_http "http://127.0.0.1:$CONTROL_PLANE_PORT/healthz" 60; then
    ok "control-plane healthy on :$CONTROL_PLANE_PORT (postgres :$POSTGRES_PORT)"
  else
    die "control-plane did not become healthy on :$CONTROL_PLANE_PORT - see: docker compose logs control-plane"
  fi

  # R-560: the build path type-checks generated code, which needs node_modules. Installing per
  # build would add minutes to a path someone is watching, so one warm install is shared by every
  # project and linked in instantly. Without this the platform runs, builds, and honestly reports
  # every project as "not type-checked" -- correct, but not the point of having the check.
  warm_web_modules
  warm_mobile_modules
  warm_api_env

  step "Agent-engine Studio"
  if service_pid studio >/dev/null; then
    ok "already running (pid $(service_pid studio)) on :$STUDIO_PORT"
  elif [[ -n "$(port_listener "$STUDIO_PORT")" ]]; then
    warn "port $STUDIO_PORT is already in use by $(port_listener "$STUDIO_PORT") - not started by this script"
  else
    if (( preview )); then
      start_bg studio bash "$repo_root/scripts/agent-engine.sh" studio-preview
      log "  mode  preview (generated apps are installed and run locally)"
    else
      start_bg studio bash "$repo_root/scripts/agent-engine.sh" studio-serve
      log "  mode  build-only (no generated code is executed; the Preview tab stays disabled)"
    fi
    if wait_http "http://127.0.0.1:$STUDIO_PORT/healthz" 90; then
      ok "studio healthy on :$STUDIO_PORT (pid $(service_pid studio || echo '?'))"
    else
      fail "studio did not answer on :$STUDIO_PORT - last lines of its log:"
      tail -20 "$(log_file studio)" 2>/dev/null | sed 's/^/        /'
      die "startup failed"
    fi
  fi

  if (( with_console )); then
    step "Console"
    if service_pid console >/dev/null; then
      ok "already running (pid $(service_pid console)) on :$CONSOLE_PORT"
    elif [[ -n "$(port_listener "$CONSOLE_PORT")" ]]; then
      warn "port $CONSOLE_PORT is already in use by $(port_listener "$CONSOLE_PORT") - not started by this script"
    else
      if (( dev_console )); then
        start_bg console bash "$repo_root/scripts/console.sh" dev
      else
        [[ -d "$repo_root/apps/console-web/.next" ]] || cmd_build
        start_bg console bash "$repo_root/scripts/console.sh" start
      fi
      if wait_http "$(console_url)/login" 90; then
        ok "console healthy on :$CONSOLE_PORT (pid $(service_pid console || echo '?'))"
      else
        fail "console did not answer on :$CONSOLE_PORT - last lines of its log:"
        tail -20 "$(log_file console)" 2>/dev/null | sed 's/^/        /'
        die "startup failed"
      fi
    fi
  fi

  step "Ready"
  print_endpoints
  log ""
  log "  Next"
  log "    Check everything   $0 status"
  log "    Follow a log       $0 logs studio -f"
  log "    Stop               $0 stop"
}

cmd_down() {
  local keep_db=0
  while (( $# > 0 )); do
    case "$1" in
      --keep-db) keep_db=1 ;;
      *) die "Unknown option for down: $1" ;;
    esac
    shift
  done

  step "Stopping application processes"
  for name in "${PROC_SERVICES[@]}"; do stop_service "$name"; done

  # A process started by hand (not by `up`) has no pidfile; say so instead of pretending the
  # port is free, and never kill something this script did not start.
  for entry in "studio:$STUDIO_PORT" "console:$CONSOLE_PORT"; do
    local svc="${entry%%:*}" port="${entry##*:}" who
    who="$(port_listener "$port")"
    # `if`, not `[[ … ]] && …`: a trailing && that evaluates false is the loop's last command,
    # and under `set -e` that aborts the whole function (it silently skipped the Docker step).
    if [[ -n "$who" ]]; then
      warn "$svc port $port is still held by $who (started outside this script; stop it with: kill ${who##* })"
    fi
  done

  if (( keep_db )); then
    step "Leaving PostgreSQL and the control-plane running (--keep-db)"
  else
    step "Stopping PostgreSQL + control-plane (Docker)"
    require_env_file
    compose down >/dev/null 2>&1 || true
    ok "containers stopped; the named data volume is preserved"
  fi
}

cmd_restart() { cmd_down --keep-db; cmd_up "$@"; }

# Database access for the admin commands. The control-plane owns the schema; these talk to the
# same PostgreSQL it runs against.
postgres_user() { env_value OMNISTACKAI_POSTGRES_USER omnistackai; }
postgres_db() { env_value OMNISTACKAI_POSTGRES_DB omnistackai; }
postgres_password() { env_value OMNISTACKAI_POSTGRES_PASSWORD ""; }

database_url() {
  printf 'postgres://%s:%s@127.0.0.1:%s/%s?sslmode=disable' \
    "$(postgres_user)" "$(postgres_password)" "$POSTGRES_PORT" "$(postgres_db)"
}

cmd_admin() {
  require_env_file
  local password
  password="$(postgres_password)"
  [[ -n "$password" ]] || die "OMNISTACKAI_POSTGRES_PASSWORD is not set in $env_file"
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'postgres'; then
    die "PostgreSQL is not running. Start it with: $0 up"
  fi
  ( cd "$repo_root/services/control-plane" && DATABASE_URL="$(database_url)" go run ./cmd/platformctl "$@" )
}

cmd_fresh() {
  local assume_yes=0 owner_email="" owner_name="" owner_password=""
  while (( $# > 0 )); do
    case "$1" in
      --yes|-y)   assume_yes=1 ;;
      --email)    shift; owner_email="${1:-}" ;;
      --name)     shift; owner_name="${1:-}" ;;
      --password) shift; owner_password="${1:-}" ;;
      *) die "Unknown option for fresh: $1" ;;
    esac
    shift
  done

  require_env_file

  printf '\n'
  warn "fresh DESTROYS every byte of local platform data:"
  printf '    - the PostgreSQL volume: accounts, projects, sessions, billing, analytics\n'
  printf '    - every generated project and its git history under the Studio workspace\n'
  printf '    - running previews and their databases\n'
  printf '  Templates in templates/catalog are part of the repository and are NOT touched.\n\n'

  if (( ! assume_yes )); then
    local answer
    read -r -p "  Type 'wipe' to confirm: " answer
    [[ "$answer" == "wipe" ]] || die "Nothing was deleted."
  fi

  step "Stopping everything"
  cmd_down >/dev/null 2>&1 || true

  step "Removing the database volume and the workspace"
  compose down -v >/dev/null 2>&1 || true
  local workspace
  workspace="$(env_value OMNISTACKAI_STUDIO_WORKSPACE_ROOT "$repo_root/.omnistackai/workspaces")"
  if [[ -d "$workspace" && "$workspace" == "$repo_root"/* ]]; then
    rm -rf "$workspace"
    ok "workspace removed: ${workspace#"$repo_root"/}"
  fi
  ok "database volume removed"

  step "Starting a clean platform"
  cmd_up

  # The control-plane applies its migrations on start-up, so the schema exists by now.
  step "Creating the platform owner"
  if [[ -z "$owner_email" ]]; then
    read -r -p "  Owner email: " owner_email
    [[ -n "$owner_email" ]] || die "An owner email is required."
  fi
  if [[ -z "$owner_name" ]]; then
    read -r -p "  Owner name (optional): " owner_name || true
  fi

  local args=(create-owner --email "$owner_email")
  [[ -n "$owner_name" ]] && args+=(--name "$owner_name")
  [[ -n "$owner_password" ]] && args+=(--password "$owner_password")

  ( cd "$repo_root/services/control-plane" && DATABASE_URL="$(database_url)" go run ./cmd/platformctl "${args[@]}" )

  printf '\n'
  ok "the platform is fresh and you are its owner"
  printf '  Sign in at %s with that email and password.\n' "$(console_url)"
  printf '  Manage accounts with: %s admin list-users\n\n' "$0"
}

cmd_status() {
  step "OmniStackAI"
  local code who pid

  code="$(http_code "$(control_plane_url)/healthz")"
  if [[ "$code" == "200" ]]; then ok "control-plane   $(control_plane_url)  healthy (docker)"; else fail "control-plane   $(control_plane_url)  not answering ($code)  - start it with: $0 start"; fi

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'postgres'; then
    ok "postgres        127.0.0.1:$POSTGRES_PORT  up (docker)  db $(postgres_db)"
  else
    fail "postgres        127.0.0.1:$POSTGRES_PORT  not running  - start it with: $0 start"
  fi

  code="$(http_code "http://127.0.0.1:$STUDIO_PORT/healthz")"
  pid="$(service_pid studio || true)"
  who="$(port_listener "$STUDIO_PORT")"
  if [[ "$code" == "200" ]]; then
    # Authoritative mode probe: /api/preview exists only when the preview manager is wired in.
    local mode="build-only (Preview tab disabled)"
    [[ "$(http_code "http://127.0.0.1:$STUDIO_PORT/api/preview")" == "200" ]] && mode="preview (generated apps can run)"
    ok "studio          $(studio_url)  healthy  ${pid:+pid $pid }${who:+[$who]}  mode: $mode"
  else
    fail "studio          $(studio_url)  not answering ($code)  - start it with: $0 start"
  fi

  code="$(http_code "$(console_url)/login")"
  pid="$(service_pid console || true)"
  who="$(port_listener "$CONSOLE_PORT")"
  if [[ "$code" == 2* || "$code" == 3* ]]; then
    ok "console         $(console_url)  healthy  ${pid:+pid $pid }${who:+[$who]}"
  else
    fail "console         $(console_url)  not answering ($code)  - start it with: $0 start"
  fi

  code="$(http_code "$OLLAMA_URL/api/version")"
  if [[ "$code" == "200" ]]; then
    local model; model="$(ollama_model)"
    ok "ollama (local)  $OLLAMA_URL  reachable${model:+  model $model}"
  else
    warn "ollama (local)  $OLLAMA_URL  not reachable (cloud providers will be used)"
  fi

  print_endpoints
}

cmd_logs() {
  local name="${1:-}" follow=0
  shift || true
  while (( $# > 0 )); do
    case "$1" in
      -f|--follow) follow=1 ;;
      *) die "Unknown option for logs: $1" ;;
    esac
    shift
  done
  case "$name" in
    studio|console)
      local file; file="$(log_file "$name")"
      [[ -f "$file" ]] || die "No log yet for $name (it was not started by this script)."
      if (( follow )); then tail -f "$file"; else tail -100 "$file"; fi
      ;;
    control-plane|postgres)
      require_env_file
      if (( follow )); then compose logs -f "$name"; else compose logs --tail 100 "$name"; fi
      ;;
    ""|*)
      die "Usage: $0 logs {studio|console|control-plane|postgres} [-f]"
      ;;
  esac
}

cmd_verify() {
  step "Repository gates"
  ( cd "$repo_root" && bash scripts/test.sh )
  ( cd "$repo_root" && task verify )
  ( cd "$repo_root" && task lint )
  ( cd "$repo_root" && task security:quick )
  ( cd "$repo_root" && task env:check )
  ok "all gates passed"
}

cmd_open() {
  local url; url="$(console_url)"
  if have open; then open "$url"; else log "$url"; fi
}

usage() {
  cat <<USAGE
OmniStackAI - local platform runner

Usage: $0 <command> [options]

Running the platform

  start | up [--no-preview] [--no-console] [--dev]
                    Start PostgreSQL, the control-plane, the agent-engine Studio and the console.
                    Preview mode is ON by default: generated apps are installed and run locally so
                    previews, multi-app template projects and publishing all work. --no-preview
                    starts the build-only mode that never executes generated code.
  stop | down [--keep-db]
                    Stop the console and Studio, then the containers. The database volume is kept.
  restart [...]     stop --keep-db, then start (accepts the same options as start).
  status            Every component, its port and its health.
  open              Open the console in a browser.
  logs <svc> [-f]   Tail a log: studio | console | control-plane | postgres.

Data and accounts
  fresh [--yes] [--email E] [--name N] [--password P]
                    DESTROY every byte of local platform data (the database volume and every
                    generated project), start clean, and create the platform owner. Asks for
                    confirmation and for the owner's details unless they are given.
  admin <cmd> ...   Administer accounts: list-users, create-owner, set-role, set-plan,
                    grant-credits. Run '$0 admin help' for the details.

Development

  doctor            Check tools, .env, dependencies, the local model and the ports. This also
                    verifies that python3 can actually create a virtualenv — a version number
                    alone does not mean the interpreter works, and a broken one silently breaks
                    every generated Python backend.
  verify            Run the repository's full gate set (contract tests, task verify, lint,
                    security and the environment contract).
  build             Build the console for production (snapshot + next build).
  help              This message.

Files: PIDs and logs live in .run/ (gitignored).
USAGE
}

case "${1:-help}" in
  # R-551: `start` and `stop` are what people reach for. They are the same commands, not aliases
  # that drift: both names dispatch to one implementation.
  up|start) shift; cmd_up "$@" ;;
  down|stop) shift; cmd_down "$@" ;;
  restart)  shift; cmd_restart "$@" ;;
  status)   shift; cmd_status "$@" ;;
  fresh)    shift; cmd_fresh "$@" ;;
  admin)    shift; cmd_admin "$@" ;;
  logs)     shift; cmd_logs "$@" ;;
  build)    shift; cmd_build "$@" ;;
  doctor)   shift; cmd_doctor "$@" ;;
  verify)   shift; cmd_verify "$@" ;;
  open)     shift; cmd_open "$@" ;;
  help|-h|--help) usage ;;
  *) usage; exit 2 ;;
esac
