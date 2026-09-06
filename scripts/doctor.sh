#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
errors=0

required_files=(
  AGENTS.md
  docs/START_HERE.md
  .ai/PROJECT_STATE.yaml
  .ai/CURRENT_TASK.yaml
  .ai/HANDOFF.md
  Taskfile.yml
  .env.example
  package.json
  pnpm-workspace.yaml
)

required_commands=(git node pnpm python3 docker go)
optional_commands=(uv ollama)

for relative_path in "${required_files[@]}"; do
  if [[ ! -f "$repo_root/$relative_path" ]]; then
    printf 'ERROR missing required file: %s\n' "$relative_path"
    errors=$((errors + 1))
  fi
done

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    printf 'OK command: docker compose\n'
  else
    printf 'ERROR missing required command: docker compose\n'
    errors=$((errors + 1))
  fi
fi

for command_name in "${required_commands[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'ERROR missing required command: %s\n' "$command_name"
    errors=$((errors + 1))
  else
    printf 'OK command: %s\n' "$command_name"
  fi
done

for command_name in "${optional_commands[@]}"; do
  if command -v "$command_name" >/dev/null 2>&1; then
    printf 'OK optional command: %s\n' "$command_name"
  else
    printf 'WARN optional command not installed yet: %s\n' "$command_name"
  fi
done

if ! git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'ERROR repository is not initialized with Git\n'
  errors=$((errors + 1))
fi

if [[ "$errors" -ne 0 ]]; then
  printf 'Doctor failed with %d error(s).\n' "$errors"
  exit 1
fi

printf 'Doctor passed.\n'
