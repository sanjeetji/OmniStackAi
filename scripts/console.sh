#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
app_root="$repo_root/apps/console-web"
source_root="$repo_root/services/agent-engine/src"
env_file="$repo_root/.env"
command_name="${1:-help}"
port="${OMNISTACKAI_CONSOLE_PORT:-4321}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1"
    exit 1
  fi
}

# The console (a real Next.js app as of R-470) does not read .env files of its own - the repo
# root .env stays the single source of truth. Export the handful of names it needs before running
# any Next.js command.
load_env() {
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

snapshot() {
  require_command python3
  PYTHONPATH="$source_root" python3 - "$app_root/data/overview.json" <<'PY'
import json
import pathlib
import sys

from omnistackai_agent_engine.console_snapshot import platform_console_snapshot

out = pathlib.Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(platform_console_snapshot(), indent=2) + "\n", encoding="utf-8")
print(f"Wrote console overview snapshot to {out}")
PY
}

run_pnpm() {
  require_command pnpm
  load_env
  (cd "$app_root" && pnpm run "$1")
}

case "$command_name" in
  snapshot)
    snapshot
    ;;
  lint)
    run_pnpm lint
    ;;
  typecheck)
    run_pnpm typecheck
    ;;
  build)
    snapshot
    run_pnpm build
    ;;
  start)
    require_command pnpm
    load_env
    printf 'Starting OmniStackAI console at http://127.0.0.1:%s\n' "$port"
    (cd "$app_root" && pnpm exec next start -p "$port")
    ;;
  dev|serve)
    snapshot
    require_command pnpm
    load_env
    printf 'Serving OmniStackAI console (dev) at http://127.0.0.1:%s\n' "$port"
    (cd "$app_root" && pnpm exec next dev -p "$port")
    ;;
  *)
    printf 'Usage: %s {snapshot|lint|typecheck|build|start|dev|serve}\n' "$0"
    exit 2
    ;;
esac
