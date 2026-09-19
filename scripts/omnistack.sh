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

cmd_doctor() {
  local problems=0
  step "Tools"
  for tool in docker python3 pnpm node curl; do
    if have "$tool"; then ok "$tool  $("$tool" --version 2>&1 | head -1)"; else fail "$tool is missing"; problems=$((problems + 1)); fi
  done

  step "Configuration"
  if [[ -f "$env_file" ]]; then ok ".env present"; else fail ".env missing (cp .env.example .env)"; problems=$((problems + 1)); fi
  if docker info >/dev/null 2>&1; then ok "docker daemon reachable"; else fail "docker daemon not reachable"; problems=$((problems + 1)); fi
  if [[ -d "$repo_root/apps/console-web/node_modules" ]]; then ok "console dependencies installed"; else warn "console dependencies missing - run: $0 build"; fi
  if [[ -d "$repo_root/apps/console-web/.next" ]]; then ok "console production build present"; else warn "no console build yet - run: $0 build"; fi

  step "Model provider"
  if [[ "$(http_code "$OLLAMA_URL/api/version")" == "200" ]]; then
    ok "local Ollama reachable at $OLLAMA_URL (free tier)"
  else
    warn "local Ollama not reachable at $OLLAMA_URL - cloud provider keys in .env will be used"
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
  compose up -d --wait postgres control-plane >/dev/null
  if wait_http "http://127.0.0.1:$CONTROL_PLANE_PORT/healthz" 60; then
    ok "control-plane healthy on :$CONTROL_PLANE_PORT (postgres :$POSTGRES_PORT)"
  else
    die "control-plane did not become healthy on :$CONTROL_PLANE_PORT - see: docker compose logs control-plane"
  fi

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
  log "  Console        $(console_url)"
  log "  Studio API     http://127.0.0.1:$STUDIO_PORT"
  log "  Control-plane  http://127.0.0.1:$CONTROL_PLANE_PORT"
  local lan; lan="$(lan_address)"
  if [[ -n "$lan" ]]; then
    log ""
    log "  On this network the console also answers at http://$lan:$CONSOLE_PORT"
    log "  Note: a generated app's live preview binds to 127.0.0.1, so its iframe only loads"
    log "  on this machine until the preview-reachability task ships."
  fi
  log ""
  log "  Logs: $0 logs studio -f    Stop: $0 down"
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

cmd_status() {
  step "OmniStackAI"
  local code who pid

  code="$(http_code "http://127.0.0.1:$CONTROL_PLANE_PORT/healthz")"
  if [[ "$code" == "200" ]]; then ok "control-plane   :$CONTROL_PLANE_PORT  healthy (docker)"; else fail "control-plane   :$CONTROL_PLANE_PORT  not answering ($code)"; fi

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'postgres'; then
    ok "postgres        :$POSTGRES_PORT  up (docker)"
  else
    fail "postgres        :$POSTGRES_PORT  not running"
  fi

  code="$(http_code "http://127.0.0.1:$STUDIO_PORT/healthz")"
  pid="$(service_pid studio || true)"
  who="$(port_listener "$STUDIO_PORT")"
  if [[ "$code" == "200" ]]; then
    # Authoritative mode probe: /api/preview exists only when the preview manager is wired in.
    local mode="build-only (Preview tab disabled)"
    [[ "$(http_code "http://127.0.0.1:$STUDIO_PORT/api/preview")" == "200" ]] && mode="preview (generated apps can run)"
    ok "studio          :$STUDIO_PORT  healthy  ${pid:+pid $pid }${who:+[$who]}  mode: $mode"
  else
    fail "studio          :$STUDIO_PORT  not answering ($code)  - start it with: $0 up"
  fi

  code="$(http_code "$(console_url)/login")"
  pid="$(service_pid console || true)"
  who="$(port_listener "$CONSOLE_PORT")"
  if [[ "$code" == 2* || "$code" == 3* ]]; then
    ok "console         :$CONSOLE_PORT  healthy  ${pid:+pid $pid }${who:+[$who]}"
  else
    fail "console         :$CONSOLE_PORT  not answering ($code)  - start it with: $0 up"
  fi

  code="$(http_code "$OLLAMA_URL/api/version")"
  if [[ "$code" == "200" ]]; then ok "ollama (local)  $OLLAMA_URL  reachable"; else warn "ollama (local)  $OLLAMA_URL  not reachable (cloud providers will be used)"; fi

  printf '\n'
  log "  Open $(console_url)"
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

  up [--no-preview] [--no-console] [--dev]
                    Start PostgreSQL, the control-plane, the agent-engine Studio and the console.
                    Preview mode is ON by default: generated apps are installed and run locally so
                    the Studio's Preview tab works. --no-preview starts the build-only mode that
                    never executes generated code.
  down [--keep-db]  Stop the console and Studio, then the containers. The database volume is kept.
  restart [...]     down --keep-db, then up (accepts the same options as up).
  status            Show every component, its port and health.
  logs <svc> [-f]   Tail a log: studio | console | control-plane | postgres.
  build             Build the console for production (snapshot + next build).
  doctor            Check tools, .env, dependencies, the local model and the ports.
  verify            Run the repository's full gate set.
  open              Open the console in a browser.
  help              This message.

Files: PIDs and logs live in .run/ (gitignored).
USAGE
}

case "${1:-help}" in
  up)       shift; cmd_up "$@" ;;
  down)     shift; cmd_down "$@" ;;
  restart)  shift; cmd_restart "$@" ;;
  status)   shift; cmd_status "$@" ;;
  logs)     shift; cmd_logs "$@" ;;
  build)    shift; cmd_build "$@" ;;
  doctor)   shift; cmd_doctor "$@" ;;
  verify)   shift; cmd_verify "$@" ;;
  open)     shift; cmd_open "$@" ;;
  help|-h|--help) usage ;;
  *) usage; exit 2 ;;
esac
