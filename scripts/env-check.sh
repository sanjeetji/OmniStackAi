#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

required_names=(
  OMNISTACKAI_ENV
  OMNISTACKAI_LOG_LEVEL
  OMNISTACKAI_OLLAMA_BASE_URL
  OMNISTACKAI_OLLAMA_MODEL
  OMNISTACKAI_POSTGRES_DB
  OMNISTACKAI_POSTGRES_USER
  OMNISTACKAI_POSTGRES_PASSWORD
  OMNISTACKAI_POSTGRES_PORT
)
for config_name in "${required_names[@]}"; do
  if ! rg -q "^${config_name}=" "$repo_root/.env.example"; then
    printf 'Missing environment placeholder: %s\n' "$config_name"
    exit 1
  fi
done

if ! rg -q '^\.env\.\*$' "$repo_root/.gitignore" || ! rg -q '^!\.env\.example$' "$repo_root/.gitignore"; then
  printf 'Environment-file exclusions are incomplete.\n'
  exit 1
fi

printf 'Environment contract passed.\n'
