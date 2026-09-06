#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
env_file="$repo_root/.env"
command_name="${1:-help}"

config_value() {
  local key="$1"
  local default_value="$2"
  local value="${!key:-}"

  if [[ -z "$value" ]] && [[ -f "$env_file" ]]; then
    value="$(awk -F= -v expected="$key" '$1 == expected { sub(/^[^=]*=/, ""); print; exit }' "$env_file")"
  fi
  printf '%s' "${value:-$default_value}"
}

base_url="$(config_value OMNISTACKAI_OLLAMA_BASE_URL http://127.0.0.1:11434)"
model="$(config_value OMNISTACKAI_OLLAMA_MODEL qwen2.5-coder:14b)"

validate_config() {
  case "$base_url" in
    http://127.0.0.1:11434|http://localhost:11434)
      ;;
    *)
      printf 'Stage 0 requires a loopback Ollama URL on port 11434; got %s.\n' "$base_url"
      exit 1
      ;;
  esac

  if [[ -z "$model" ]] || [[ "$model" =~ [[:space:]] ]]; then
    printf 'OMNISTACKAI_OLLAMA_MODEL must be a non-empty Ollama model name without spaces.\n'
    exit 1
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1"
    exit 1
  fi
}

require_runtime() {
  require_command curl
  if ! curl --fail --silent --show-error --max-time 5 "$base_url/api/version" >/dev/null; then
    printf 'Ollama is not reachable at %s. Run task ollama:serve or start Ollama.app.\n' "$base_url"
    exit 1
  fi
}

case "$command_name" in
  config)
    validate_config
    printf 'Local Ollama configuration is valid: endpoint=%s model=%s.\n' "$base_url" "$model"
    ;;
  serve)
    validate_config
    require_command ollama
    OLLAMA_HOST="${base_url#http://}" exec ollama serve
    ;;
  status)
    validate_config
    require_runtime
    require_command node
    version_json="$(curl --fail --silent --show-error --max-time 5 "$base_url/api/version")"
    version="$(printf '%s' "$version_json" | node -e '
      const fs = require("fs");
      const value = JSON.parse(fs.readFileSync(0, "utf8")).version;
      if (typeof value !== "string" || value.length === 0) process.exit(1);
      process.stdout.write(value);
    ')"
    printf 'Ollama is healthy at %s (version %s).\n' "$base_url" "$version"
    ;;
  models)
    validate_config
    require_runtime
    require_command node
    curl --fail --silent --show-error --max-time 10 "$base_url/api/tags" | node -e '
      const fs = require("fs");
      const payload = JSON.parse(fs.readFileSync(0, "utf8"));
      for (const entry of payload.models || []) console.log(entry.name || entry.model);
    '
    ;;
  pull)
    validate_config
    require_runtime
    require_command ollama
    OLLAMA_HOST="${base_url#http://}" ollama pull "$model"
    ;;
  verify)
    validate_config
    require_runtime
    require_command node

    tags_json="$(curl --fail --silent --show-error --max-time 10 "$base_url/api/tags")"
    printf '%s' "$tags_json" | node -e '
      const fs = require("fs");
      const target = process.argv[1];
      const payload = JSON.parse(fs.readFileSync(0, "utf8"));
      const found = (payload.models || []).some((entry) => entry.name === target || entry.model === target);
      if (!found) {
        console.error(`Configured model is not pulled: ${target}`);
        process.exit(1);
      }
    ' "$model"

    request_json="$(node -e '
      process.stdout.write(JSON.stringify({
        model: process.argv[1],
        prompt: "Return one short line confirming local inference is working.",
        stream: false,
        keep_alive: 0,
        options: { temperature: 0, num_predict: 24 }
      }));
    ' "$model")"
    response_json="$(curl --fail --silent --show-error --max-time 300 \
      --header 'Content-Type: application/json' \
      --data "$request_json" \
      "$base_url/api/generate")"
    eval_count="$(printf '%s' "$response_json" | node -e '
      const fs = require("fs");
      const payload = JSON.parse(fs.readFileSync(0, "utf8"));
      if (payload.done !== true || typeof payload.response !== "string" || payload.response.trim().length === 0) {
        console.error("Ollama inference did not return a completed non-empty response.");
        process.exit(1);
      }
      if (!Number.isInteger(payload.eval_count) || payload.eval_count < 1) {
        console.error("Ollama inference did not report generated tokens.");
        process.exit(1);
      }
      process.stdout.write(String(payload.eval_count));
    ')"
    printf 'Local Ollama inference passed: model=%s generated_tokens=%s cloud_calls=0.\n' "$model" "$eval_count"
    ;;
  *)
    printf 'Usage: %s {config|serve|status|models|pull|verify}\n' "$0"
    exit 2
    ;;
esac
