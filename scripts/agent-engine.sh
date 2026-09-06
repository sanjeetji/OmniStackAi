#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
service_root="$repo_root/services/agent-engine"
source_root="$service_root/src"
test_root="$service_root/tests"
env_file="$repo_root/.env"
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

config_value() {
  local key="$1"
  local default_value="$2"
  local value="${!key:-}"

  if [[ -z "$value" ]] && [[ -f "$env_file" ]]; then
    value="$(awk -F= -v expected="$key" '$1 == expected { sub(/^[^=]*=/, ""); print; exit }' "$env_file")"
  fi
  printf '%s' "${value:-$default_value}"
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
    raise SystemExit("The Stage 0 agent-engine must not add external Python dependencies")
if project["project"]["requires-python"] != ">=3.13,<3.14":
    raise SystemExit("The agent-engine requires the Python 3.13 toolchain contract")
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
  ollama-verify)
    configure_python
    export OMNISTACKAI_OLLAMA_BASE_URL="$(config_value OMNISTACKAI_OLLAMA_BASE_URL http://127.0.0.1:11434)"
    export OMNISTACKAI_OLLAMA_MODEL="$(config_value OMNISTACKAI_OLLAMA_MODEL qwen2.5-coder:14b)"
    export OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS="$(config_value OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS 4096)"
    export OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS="$(config_value OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS 3072)"
    export OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS="$(config_value OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS 1024)"
    export OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS="$(config_value OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS 300)"
    export OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS="$(config_value OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS 5)"
    export OMNISTACKAI_OLLAMA_MAX_CONCURRENCY="$(config_value OMNISTACKAI_OLLAMA_MAX_CONCURRENCY 1)"
    python3 -m omnistackai_agent_engine.model_gateway.live_verify
    ;;
  *)
    printf 'Usage: %s {lint|test|ollama-verify}\n' "$0"
    exit 2
    ;;
esac
