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
  ollama-verify|gateway-run)
    configure_python
    export OMNISTACKAI_OLLAMA_BASE_URL="$(config_value OMNISTACKAI_OLLAMA_BASE_URL http://127.0.0.1:11434)"
    export OMNISTACKAI_OLLAMA_MODEL="$(config_value OMNISTACKAI_OLLAMA_MODEL qwen2.5-coder:14b)"
    export OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS="$(config_value OMNISTACKAI_OLLAMA_CONTEXT_WINDOW_TOKENS 4096)"
    export OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS="$(config_value OMNISTACKAI_OLLAMA_SAFE_INPUT_TOKENS 3072)"
    export OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS="$(config_value OMNISTACKAI_OLLAMA_MAX_OUTPUT_TOKENS 1024)"
    export OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS="$(config_value OMNISTACKAI_OLLAMA_REQUEST_TIMEOUT_SECONDS 300)"
    export OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS="$(config_value OMNISTACKAI_OLLAMA_HEALTH_TIMEOUT_SECONDS 5)"
    export OMNISTACKAI_OLLAMA_MAX_CONCURRENCY="$(config_value OMNISTACKAI_OLLAMA_MAX_CONCURRENCY 1)"
    if [[ "$command_name" == "ollama-verify" ]]; then
      python3 -m omnistackai_agent_engine.model_gateway.live_verify
    else
      export OMNISTACKAI_GATEWAY_PROMPT="$(config_value OMNISTACKAI_GATEWAY_PROMPT 'Reply with exactly: gateway routed to local model')"
      python3 -m omnistackai_agent_engine.model_gateway.live_gateway
    fi
    ;;
  preview-plan)
    configure_python
    target="${2:-nextjs-web}"
    PYTHONPATH="$source_root" python3 - "$target" <<'PY'
import sys
from omnistackai_agent_engine.runtime import LocalRuntimeProvider

target = sys.argv[1]
app_dir = "apps/web" if target.startswith("nextjs") else "services/api"
plan = LocalRuntimeProvider().preview_plan(app_dir, target)
print(f"Local preview plan for '{plan.target}' (Tier 0/1):")
for step in plan.steps:
    print(f"  {step.label}: {step.command.display()}   (run in {plan.app_dir})")
print(f"Then open: {plan.url}")
print("Run these in the generated project on a machine with the toolchain + internet.")
PY
    ;;
  platform-status)
    configure_python
    export OMNISTACKAI_TIER="$(config_value OMNISTACKAI_TIER 0)"
    export OMNISTACKAI_RUNTIME_PROVIDER="$(config_value OMNISTACKAI_RUNTIME_PROVIDER local)"
    export OMNISTACKAI_DEPLOY_PROVIDER="$(config_value OMNISTACKAI_DEPLOY_PROVIDER none)"
    for key_name in E2B_API_KEY DAYTONA_API_KEY FLY_API_TOKEN VERCEL_TOKEN RENDER_API_KEY NETLIFY_AUTH_TOKEN; do
      export "$key_name"="$(config_value "$key_name" '')"
    done
    PYTHONPATH="$source_root" python3 -c "from omnistackai_agent_engine.runtime import format_status; print(format_status())"
    ;;
  *)
    printf 'Usage: %s {lint|test|ollama-verify|gateway-run|preview-plan [target]|platform-status}\n' "$0"
    exit 2
    ;;
esac
