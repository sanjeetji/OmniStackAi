#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

required_directories=(
  apps/console-web
  services/control-plane services/agent-engine services/runner-manager
  modules/model-gateway modules/context-engine modules/code-intelligence modules/change-impact
  modules/git-service modules/preview-service modules/deployment-engine modules/release-publishing
  modules/billing-entitlements modules/audit-policy modules/integration-gateway modules/mcp-gateway
  workers/browser-runner workers/linux-runner workers/web-runner workers/flutter-runner
  workers/react-native-runner workers/android-runner workers/mac-runner-controller
  packages/contracts packages/policy-schemas packages/telemetry packages/ui packages/agent-sdk
  packages/runtime-sdk packages/provider-sdk
  ai/prompts ai/agents ai/tools ai/policies ai/evals ai/benchmark-cases ai/context-templates
  templates/flutter templates/react-native-expo templates/react-native-bare
  templates/android-compose templates/ios-swiftui templates/nextjs-web templates/nextjs-admin
  templates/backend-go templates/backend-python templates/backend-node
  infra/terraform infra/kubernetes infra/temporal infra/environments
  security/threat-models security/policies security/signing security/supply-chain
  docs/adr docs/runbooks docs/architecture scripts
)

for relative_path in "${required_directories[@]}"; do
  if [[ ! -d "$repo_root/$relative_path" ]]; then
    printf 'Missing Section 74 directory: %s\n' "$relative_path"
    exit 1
  fi
done

for task_name in doctor bootstrap lint test verify ai:status ai:handoff db:config db:up db:status db:verify db:down \
  ollama:config ollama:serve ollama:status ollama:models ollama:pull ollama:verify; do
  if ! rg -q "^  ${task_name}:" "$repo_root/Taskfile.yml"; then
    printf 'Missing Taskfile command: %s\n' "$task_name"
    exit 1
  fi
done

ollama_script="$repo_root/scripts/ollama.sh"
if [[ ! -f "$ollama_script" ]]; then
  printf 'Missing R-003 local Ollama contract file: %s\n' "$ollama_script"
  exit 1
fi

if ! rg -q 'http://127\.0\.0\.1:11434' "$repo_root/.env.example"; then
  printf 'Stage 0 Ollama endpoint must default to loopback.\n'
  exit 1
fi

if ! rg -q '^OMNISTACKAI_OLLAMA_MODEL=' "$repo_root/.env.example"; then
  printf 'The local model must be selected through environment configuration.\n'
  exit 1
fi

for endpoint in api/version api/tags api/generate; do
  if ! rg -q "$endpoint" "$ollama_script"; then
    printf 'Missing Ollama API contract endpoint: %s\n' "$endpoint"
    exit 1
  fi
done

if rg -qi 'api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com' "$ollama_script"; then
  printf 'R-003 must not call a cloud model provider.\n'
  exit 1
fi

compose_file="$repo_root/infra/environments/local/compose.yaml"
up_migration="$repo_root/services/control-plane/migrations/000001_platform_foundation.up.sql"
down_migration="$repo_root/services/control-plane/migrations/000001_platform_foundation.down.sql"

for required_file in "$compose_file" "$up_migration" "$down_migration" "$repo_root/scripts/db.sh"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-002 database contract file: %s\n' "$required_file"
    exit 1
  fi
done

service_count="$(awk '
  /^services:$/ { in_services = 1; next }
  in_services && /^[^ ]/ { in_services = 0 }
  in_services && /^  [a-zA-Z0-9_-]+:$/ { count += 1 }
  END { print count + 0 }
' "$compose_file")"
if [[ "$service_count" != "1" ]]; then
  printf 'R-002 Compose file must define exactly one service.\n'
  exit 1
fi

if ! rg -q 'pgvector/pgvector:0\.8\.6-pg18-trixie' "$compose_file"; then
  printf 'R-002 must pin the approved pgvector image.\n'
  exit 1
fi

if ! rg -q '127\.0\.0\.1:\$\{OMNISTACKAI_POSTGRES_PORT:-5432\}:5432' "$compose_file"; then
  printf 'PostgreSQL must bind only to loopback.\n'
  exit 1
fi

if ! rg -q 'omnistackai-postgres-data:/var/lib/postgresql$' "$compose_file"; then
  printf 'PostgreSQL 18 data volume must use its major-version-aware mount root.\n'
  exit 1
fi

if rg -qi '^  (redis|control-plane|agent-engine|temporal|kubernetes):' "$compose_file"; then
  printf 'R-002 Compose scope contains an unapproved service.\n'
  exit 1
fi

if ! rg -q '^BEGIN;$' "$up_migration" || ! rg -q '^COMMIT;$' "$up_migration"; then
  printf 'Initial migration must be transactional.\n'
  exit 1
fi

if ! rg -q '^CREATE EXTENSION IF NOT EXISTS vector;$' "$up_migration"; then
  printf 'Initial migration must enable pgvector.\n'
  exit 1
fi

if ! rg -q 'version = 1' "$down_migration"; then
  printf 'Down migration must target schema version 1.\n'
  exit 1
fi

printf 'Repository contract tests passed.\n'
