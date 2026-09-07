#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
app_root="$repo_root/apps/console-web"
source_root="$repo_root/services/agent-engine/src"
command_name="${1:-help}"
port="${OMNISTACKAI_CONSOLE_PORT:-4321}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1"
    exit 1
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

case "$command_name" in
  snapshot)
    snapshot
    ;;
  serve)
    snapshot
    require_command python3
    printf 'Serving OmniStackAI console at http://127.0.0.1:%s\n' "$port"
    (cd "$app_root" && python3 -m http.server "$port" --bind 127.0.0.1)
    ;;
  *)
    printf 'Usage: %s {snapshot|serve}\n' "$0"
    exit 2
    ;;
esac
