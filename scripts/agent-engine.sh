#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
service_root="$repo_root/services/agent-engine"
source_root="$service_root/src"
test_root="$service_root/tests"
command_name="${1:-help}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1"
    exit 1
  fi
}

configure_python() {
  require_command python3
  export PYTHONPATH="$source_root"
  export PYTHONPYCACHEPREFIX="/tmp/omnistackai-agent-engine-pycache"
  python3 -c 'import sys; raise SystemExit(0 if (3, 13) <= sys.version_info[:2] < (3, 14) else "Python 3.13.x is required")'
}

case "$command_name" in
  lint)
    configure_python
    require_command rg
    python3 -m compileall -q "$source_root" "$test_root"
    python3 -c '
import pathlib
import sys
import tomllib

project = tomllib.loads(pathlib.Path(sys.argv[1]).read_text())
if project["project"]["dependencies"]:
    raise SystemExit("R-005 must not add external Python dependencies")
if project["project"]["requires-python"] != ">=3.13,<3.14":
    raise SystemExit("R-005 requires the Python 3.13 toolchain contract")
' "$service_root/pyproject.toml"
    if rg -n --glob '*.py' '^\s*(from|import)\s+(anthropic|google|ollama|openai)(\.|\s|$)' "$source_root"; then
      printf 'Provider SDK import found outside an adapter task.\n'
      exit 1
    fi
    printf 'Agent-engine contract lint passed.\n'
    ;;
  test)
    configure_python
    (
      cd "$service_root"
      python3 -m unittest discover -s tests -v
    )
    ;;
  *)
    printf 'Usage: %s {lint|test}\n' "$0"
    exit 2
    ;;
esac
