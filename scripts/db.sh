#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
compose_file="$repo_root/infra/environments/local/compose.yaml"
env_file="$repo_root/.env"
command_name="${1:-help}"

compose() {
  docker compose --env-file "$env_file" -f "$compose_file" "$@"
}

require_local_env() {
  if [[ ! -f "$env_file" ]]; then
    printf 'Missing %s. Copy .env.example to .env and set a local-only database password.\n' "$env_file"
    exit 1
  fi
}

case "$command_name" in
  config)
    if [[ ! -f "$env_file" ]]; then
      env_file="$repo_root/.env.example"
    fi
    compose config --quiet
    printf 'Local database Compose configuration is valid.\n'
    ;;
  up)
    require_local_env
    compose up -d --wait postgres
    printf 'Local PostgreSQL is healthy and bound to the configured loopback port.\n'
    ;;
  status)
    require_local_env
    compose ps postgres
    ;;
  verify)
    require_local_env
    compose up -d --wait postgres
    extension_version="$(compose exec -T postgres sh -c \
      'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --command "SELECT extversion FROM pg_extension WHERE extname = '\''vector'\'';"')"
    migration_version="$(compose exec -T postgres sh -c \
      'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --command "SELECT version FROM schema_migrations WHERE version = 1;"')"

    if [[ "$extension_version" != "0.8.6" ]]; then
      printf 'Expected pgvector 0.8.6, got %s.\n' "${extension_version:-missing}"
      exit 1
    fi
    if [[ "$migration_version" != "1" ]]; then
      printf 'Expected migration version 1, got %s.\n' "${migration_version:-missing}"
      exit 1
    fi
    printf 'Database verification passed: PostgreSQL healthy, pgvector %s, migration %s.\n' \
      "$extension_version" "$migration_version"
    ;;
  down)
    require_local_env
    compose down
    printf 'Local database container and network stopped; named data volume preserved.\n'
    ;;
  *)
    printf 'Usage: %s {config|up|status|verify|down}\n' "$0"
    exit 2
    ;;
esac
