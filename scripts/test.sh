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
  ollama:config ollama:serve ollama:status ollama:models ollama:pull ollama:verify \
  control-plane:lint control-plane:test control-plane:build control-plane:verify \
  agent-engine:lint agent-engine:test; do
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
if [[ "$service_count" != "2" ]]; then
  printf 'R-004 Compose file must define exactly PostgreSQL and control-plane.\n'
  exit 1
fi

for service_name in postgres control-plane; do
  if ! rg -q "^  ${service_name}:$" "$compose_file"; then
    printf 'Missing approved Stage 0 Compose service: %s\n' "$service_name"
    exit 1
  fi
done

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

if rg -qi '^  (redis|agent-engine|runner-manager|nats|temporal|kubernetes):' "$compose_file"; then
  printf 'R-004 Compose scope contains an unapproved service.\n'
  exit 1
fi

if ! rg -q '127\.0\.0\.1:\$\{OMNISTACKAI_CONTROL_PLANE_PORT:-8080\}:8080' "$compose_file"; then
  printf 'The control-plane must publish only on loopback.\n'
  exit 1
fi

control_plane_root="$repo_root/services/control-plane"
for required_file in go.mod go.sum Dockerfile cmd/control-plane/main.go internal/config/config.go internal/health/handler.go; do
  if [[ ! -f "$control_plane_root/$required_file" ]]; then
    printf 'Missing R-004 control-plane contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q '^FROM golang:1\.27\.1-alpine3\.24 AS build$' "$control_plane_root/Dockerfile" \
  || ! rg -q '^FROM alpine:3\.24\.1$' "$control_plane_root/Dockerfile"; then
  printf 'Control-plane build and runtime images must use approved exact tags.\n'
  exit 1
fi

for route in /healthz /readyz; do
  if ! rg -q "$route" "$control_plane_root/internal/health/handler.go"; then
    printf 'Missing control-plane health route: %s\n' "$route"
    exit 1
  fi
done

agent_engine_root="$repo_root/services/agent-engine"
for required_file in \
  pyproject.toml \
  src/omnistackai_agent_engine/model_gateway/contracts.py \
  src/omnistackai_agent_engine/model_gateway/errors.py \
  src/omnistackai_agent_engine/model_gateway/registry.py \
  tests/test_contracts.py \
  tests/test_registry.py; do
  if [[ ! -f "$agent_engine_root/$required_file" ]]; then
    printf 'Missing R-005 agent-engine contract file: %s\n' "$required_file"
    exit 1
  fi
done

if rg -n --glob '*.py' '^\s*(from|import)\s+(anthropic|google|ollama|openai)(\.|\s|$)' \
  "$agent_engine_root/src"; then
  printf 'R-005 must not import a model-provider SDK.\n'
  exit 1
fi

# Provider adapters behind the ModelProvider boundary are sanctioned from R-006 (local Ollama) and
# R-008 (cloud) onward. The durable invariants are the SDK-import exclusion above plus: the gateway,
# cloud adapters, and env bootstrap exist, and cloud providers are opt-in and default to local-only.
for required_file in \
  src/omnistackai_agent_engine/model_gateway/gateway.py \
  src/omnistackai_agent_engine/model_gateway/cloud.py \
  src/omnistackai_agent_engine/model_gateway/bootstrap.py; do
  if [[ ! -f "$agent_engine_root/$required_file" ]]; then
    printf 'Missing R-007/R-008 model-gateway contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q '^OMNISTACKAI_CLOUD_PROVIDER=none$' "$repo_root/.env.example"; then
  printf 'Cloud model providers must be opt-in and default to none.\n'
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

# R-469: control-plane foundation - users, auth, plans, credits.
users_up_migration="$control_plane_root/migrations/000002_users_auth_billing.up.sql"
users_down_migration="$control_plane_root/migrations/000002_users_auth_billing.down.sql"
for required_file in \
  "$users_up_migration" \
  "$users_down_migration" \
  "$control_plane_root/migrations/migrations.go" \
  "$control_plane_root/internal/password/password.go" \
  "$control_plane_root/internal/auth/handler.go" \
  "$control_plane_root/internal/users/store.go"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-469 control-plane contract file: %s\n' "$required_file"
    exit 1
  fi
done

for required_table in users credit_ledger sessions; do
  if ! rg -q "CREATE TABLE IF NOT EXISTS ${required_table} " "$users_up_migration"; then
    printf 'R-469 migration must create table: %s\n' "$required_table"
    exit 1
  fi
done

if ! rg -q 'version = 2' "$users_down_migration"; then
  printf 'R-469 down migration must target schema version 2.\n'
  exit 1
fi

for route in /auth/register /auth/login /auth/logout /auth/me; do
  if ! rg -q "$route" "$control_plane_root/internal/auth/handler.go"; then
    printf 'Missing control-plane auth route: %s\n' "$route"
    exit 1
  fi
done

# Password hashing must stay standard-library only: go.mod's direct require block must still be
# exactly the one pre-existing pgx dependency (golang.org/x/crypto/bcrypt or any other new direct
# dependency would fail this).
direct_dependency_count="$(awk '
  /^require \(/ { in_block = 1; next }
  in_block && /^\)/ { in_block = 0; next }
  in_block && !/\/\/ indirect/ && NF { count += 1; next }
  /^require [^(]/ { count += 1 }
  END { print count + 0 }
' "$control_plane_root/go.mod")"
if [[ "$direct_dependency_count" != "1" ]]; then
  printf 'R-469 password hashing must stay standard-library only (go.mod must have exactly one direct dependency).\n'
  exit 1
fi

# R-470: real Next.js console-web, wired to R-469's auth API.
console_root="$repo_root/apps/console-web"
for required_file in \
  "$console_root/package.json" \
  "$console_root/next.config.ts" \
  "$console_root/app/layout.tsx" \
  "$console_root/app/page.tsx" \
  "$console_root/app/login/page.tsx" \
  "$console_root/app/register/page.tsx" \
  "$console_root/app/fabric/page.tsx" \
  "$console_root/app/api/auth/register/route.ts" \
  "$console_root/app/api/auth/login/route.ts" \
  "$console_root/app/api/auth/logout/route.ts" \
  "$console_root/lib/control-plane.ts" \
  "$console_root/lib/session.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-470 console contract file: %s\n' "$required_file"
    exit 1
  fi
done

for removed_file in index.html app.js styles.css; do
  if [[ -f "$console_root/$removed_file" ]]; then
    printf 'R-470 must remove the Stage-0 static console file: %s\n' "$removed_file"
    exit 1
  fi
done

if rg -qi 'tailwind|shadcn|styled-components|@emotion|bootstrap|material-ui|@mui' "$console_root/package.json"; then
  printf 'R-470 must not add a UI/component-library dependency to the console.\n'
  exit 1
fi

if ! rg -q '^\.next/$' "$repo_root/.gitignore"; then
  printf 'Missing .gitignore entry for the console build output: .next/\n'
  exit 1
fi

# R-472: control-plane Job API bridge to the agent-engine - real credit debiting.
for required_file in \
  "$control_plane_root/internal/jobs/types.go" \
  "$control_plane_root/internal/jobs/handler.go" \
  "$control_plane_root/internal/jobs/handler_test.go" \
  "$control_plane_root/internal/users/store_test.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/model_gateway/recording.py" \
  "$agent_engine_root/tests/test_recording_provider.py"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-472 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q 'POST /jobs/build' "$control_plane_root/internal/jobs/handler.go"; then
  printf 'R-472 control-plane must register POST /jobs/build.\n'
  exit 1
fi

if ! rg -q 'func RequireUser' "$control_plane_root/internal/auth/handler.go"; then
  printf 'R-472 must expose an exported auth.RequireUser helper.\n'
  exit 1
fi

if ! rg -q 'func \(s \*Store\) DebitCredits' "$control_plane_root/internal/users/store.go"; then
  printf 'R-472 must expose an exported users.Store.DebitCredits helper.\n'
  exit 1
fi

if ! rg -q 'class RecordingProvider' "$agent_engine_root/src/omnistackai_agent_engine/model_gateway/recording.py"; then
  printf 'R-472 must define model_gateway.RecordingProvider.\n'
  exit 1
fi

if ! rg -q '"RecordingProvider"' "$agent_engine_root/src/omnistackai_agent_engine/model_gateway/__init__.py"; then
  printf 'R-472 must export RecordingProvider from model_gateway/__init__.py.\n'
  exit 1
fi

if ! rg -q 'usage_ledger' "$agent_engine_root/src/omnistackai_agent_engine/intake/provider_resolution.py"; then
  printf 'R-472 must add an optional usage_ledger parameter to resolve_generation_provider_from_env.\n'
  exit 1
fi

if ! rg -q 'cost_micros_usd' "$agent_engine_root/src/omnistackai_agent_engine/studio/live_serve.py"; then
  printf 'R-472 must surface a JSON-safe usage summary (cost_micros_usd) from studio/live_serve.py.\n'
  exit 1
fi

if rg -qi '^  (redis|agent-engine|runner-manager|nats|temporal|kubernetes):' "$compose_file"; then
  printf 'R-472 must not add agent-engine (or any of the still-forbidden services) as a Docker Compose service.\n'
  exit 1
fi

# R-473: Studio v1 in the console - build an app from the product, not curl.
for required_file in \
  "$console_root/app/studio/page.tsx" \
  "$console_root/app/studio/studio-form.tsx" \
  "$console_root/app/api/jobs/build/route.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-473 console contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q 'buildApp' "$console_root/lib/control-plane.ts"; then
  printf 'R-473 must add a buildApp() client to lib/control-plane.ts.\n'
  exit 1
fi

if ! rg -q 'getSessionToken' "$console_root/app/api/jobs/build/route.ts"; then
  printf 'R-473 must authenticate POST /api/jobs/build via the session cookie before proxying.\n'
  exit 1
fi

# R-474: file browser in the console Studio - see what a build actually produced.
for required_file in \
  "$control_plane_root/internal/jobs/handler.go" \
  "$console_root/app/api/jobs/build/[id]/files/route.ts" \
  "$console_root/app/api/jobs/build/[id]/file/route.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-474 contract file: %s\n' "$required_file"
    exit 1
  fi
done

for route in 'GET /jobs/build/{id}/files' 'GET /jobs/build/{id}/file'; do
  if ! rg -qF "$route" "$control_plane_root/internal/jobs/handler.go"; then
    printf 'R-474 control-plane must register: %s\n' "$route"
    exit 1
  fi
done

if ! rg -q 'listBuildFiles|readBuildFile' "$console_root/lib/control-plane.ts"; then
  printf 'R-474 must add listBuildFiles()/readBuildFile() clients to lib/control-plane.ts.\n'
  exit 1
fi

printf 'Repository contract tests passed.\n'
