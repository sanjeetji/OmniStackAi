#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
service_root="$repo_root/services/control-plane"
compose_file="$repo_root/infra/environments/local/compose.yaml"
env_file="$repo_root/.env"
command_name="${1:-help}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1"
    exit 1
  fi
}

require_local_env() {
  if [[ ! -f "$env_file" ]]; then
    printf 'Missing %s. Copy .env.example to .env and set a local-only database password.\n' "$env_file"
    exit 1
  fi
}

compose() {
  docker compose --env-file "$env_file" -f "$compose_file" "$@"
}

case "$command_name" in
  lint)
    require_command gofmt
    require_command go
    unformatted="$(rg --files "$service_root" -g '*.go' | xargs gofmt -l)"
    if [[ -n "$unformatted" ]]; then
      printf 'Unformatted Go files:\n%s\n' "$unformatted"
      exit 1
    fi
    (cd "$service_root" && go vet ./...)
    printf 'Control-plane lint passed.\n'
    ;;
  test)
    require_command go
    (cd "$service_root" && go test ./...)
    ;;
  build)
    require_command go
    (cd "$service_root" && go build -trimpath -o /tmp/omnistackai-control-plane ./cmd/control-plane)
    printf 'Control-plane build passed.\n'
    ;;
  verify)
    require_local_env
    require_command docker
    require_command curl
    require_command node
    compose up -d --build --wait postgres control-plane

    health_json="$(curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/healthz)"
    ready_json="$(curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/readyz)"
    printf '%s\n%s' "$health_json" "$ready_json" | node -e '
      const fs = require("fs");
      const lines = fs.readFileSync(0, "utf8").trim().split("\n").map(JSON.parse);
      if (lines.length !== 2) process.exit(1);
      const [health, ready] = lines;
      if (health.service !== "control-plane" || health.status !== "ok") process.exit(1);
      if (ready.service !== "control-plane" || ready.status !== "ready") process.exit(1);
    '
    printf 'Live control-plane verification passed: health=ok readiness=ready.\n'
    ;;
  *)
    printf 'Usage: %s {lint|test|build|verify}\n' "$0"
    exit 2
    ;;
esac
