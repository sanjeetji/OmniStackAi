#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

required_names=(
  OMNISTACKAI_ENV
  OMNISTACKAI_LOG_LEVEL
  OMNISTACKAI_OLLAMA_BASE_URL
  OMNISTACKAI_OLLAMA_MODEL
  OMNISTACKAI_CONTROL_PLANE_ADDRESS
  OMNISTACKAI_CONTROL_PLANE_PORT
  OMNISTACKAI_DATABASE_PING_TIMEOUT
  OMNISTACKAI_SHUTDOWN_TIMEOUT
  OMNISTACKAI_SESSION_TTL
  OMNISTACKAI_SIGNUP_CREDIT_GRANT
  OMNISTACKAI_AGENT_ENGINE_URL
  OMNISTACKAI_CREDITS_PER_USD
  OMNISTACKAI_POSTGRES_HOST
  OMNISTACKAI_POSTGRES_DB
  OMNISTACKAI_POSTGRES_USER
  OMNISTACKAI_POSTGRES_PASSWORD
  OMNISTACKAI_POSTGRES_PORT
  OMNISTACKAI_SECRETS_KEY
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
