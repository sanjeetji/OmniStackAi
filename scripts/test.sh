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

# R-470's "no UI/component-library dependency in the console" gate was retired in R-491 with the
# founder's explicit "Full UI overhaul now" decision (2026-09-19) - the console now standardizes on
# Tailwind v4 + shadcn/ui (see the R-491 block below, which asserts their presence instead).

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
# studio-form.tsx was retired in R-477, replaced by studio-chat.tsx (its contract block below).
for required_file in \
  "$console_root/app/studio/page.tsx" \
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

# R-475: Studio visual foundation. (Its hand-drawn studio-icons.tsx was retired in R-494 - every
# Studio file now imports Lucide directly; the R-494 block below asserts the file is gone.)
for required_file in \
  "$console_root/app/studio/layout.tsx"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-475 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q 'getCurrentUser' "$console_root/app/studio/layout.tsx"; then
  printf 'R-475 must move the /studio auth gate into layout.tsx.\n'
  exit 1
fi

# (R-475's --surface-2 alias and its .spinner/.pill--accent classes were retired in R-496 once no
# screen rendered them; the radius scale it introduced is still the console's - see @theme inline.)
for design_token in '\-\-radius-sm' '\-\-radius-md' '\-\-radius-lg'; do
  if ! rg -q -- "$design_token" "$console_root/app/globals.css"; then
    printf 'R-475 must add the %s design token/class to globals.css.\n' "$design_token"
    exit 1
  fi
done

# R-476: backend - multi-turn edit bridge.
for route in 'POST /jobs/build/{id}/edit' 'GET /jobs/build/{id}/turns'; do
  if ! rg -qF "$route" "$control_plane_root/internal/jobs/handler.go"; then
    printf 'R-476 control-plane must register: %s\n' "$route"
    exit 1
  fi
done

if ! rg -q 'usage_ledger = UsageLedger\(\)' "$agent_engine_root/src/omnistackai_agent_engine/studio/live_serve.py"; then
  printf 'R-476 must thread a real UsageLedger through _edit() (live_serve.py).\n'
  exit 1
fi

if [[ "$(rg -c 'record_turn' "$agent_engine_root/src/omnistackai_agent_engine/studio/live_serve.py" 2>/dev/null || echo 0)" -lt 4 ]]; then
  printf 'R-476 must make _build() record its own turn (session_store.record_turn), not just _edit().\n'
  exit 1
fi

# R-477: Console chat UI.
for required_file in \
  "$console_root/app/studio/studio-chat.tsx" \
  "$console_root/app/studio/studio-workspace.tsx" \
  "$console_root/app/api/jobs/build/[id]/edit/route.ts" \
  "$console_root/app/api/jobs/build/[id]/turns/route.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-477 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if [[ -f "$console_root/app/studio/studio-form.tsx" ]]; then
  printf 'R-477 must retire studio-form.tsx (replaced by studio-chat.tsx/studio-workspace.tsx).\n'
  exit 1
fi

if ! rg -q 'editBuild|getBuildTurns' "$console_root/lib/control-plane.ts"; then
  printf 'R-477 must add editBuild()/getBuildTurns() clients to lib/control-plane.ts.\n'
  exit 1
fi

if ! rg -q '\.studio-grid' "$console_root/app/globals.css"; then
  printf 'R-477 must add the .studio-grid layout to globals.css.\n'
  exit 1
fi

# R-478: backend - live preview proxy (local-only).
for route in 'GET /jobs/preview' 'POST /jobs/preview/stop' 'POST /jobs/preview/restart' 'POST /jobs/build/{id}/preview'; do
  if ! rg -qF "$route" "$control_plane_root/internal/jobs/handler.go"; then
    printf 'R-478 control-plane must register: %s\n' "$route"
    exit 1
  fi
done

if ! rg -q 'defaultPreviewTimeout' "$control_plane_root/internal/jobs/types.go"; then
  printf 'R-478 must add a defaultPreviewTimeout constant to types.go.\n'
  exit 1
fi

# R-479: console - live preview UI.
for required_file in \
  "$console_root/app/studio/studio-preview.tsx" \
  "$console_root/app/api/preview/route.ts" \
  "$console_root/app/api/preview/stop/route.ts" \
  "$console_root/app/api/preview/restart/route.ts" \
  "$console_root/app/api/jobs/build/[id]/preview/route.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-479 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q 'getPreviewStatus|stopPreview|restartPreview|previewBuild' "$console_root/lib/control-plane.ts"; then
  printf 'R-479 must add getPreviewStatus()/stopPreview()/restartPreview()/previewBuild() clients to lib/control-plane.ts.\n'
  exit 1
fi

if ! rg -q 'StudioPreview' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-479 must wire <StudioPreview> into studio-chat.tsx.\n'
  exit 1
fi

# R-480: backend - Problems/compile-report support.
if [[ ! -f "$agent_engine_root/src/omnistackai_agent_engine/studio/problems.py" ]]; then
  printf 'Missing R-480 contract file: studio/problems.py\n'
  exit 1
fi

if ! rg -q 'problems_check_fn|problems_get_fn' "$agent_engine_root/src/omnistackai_agent_engine/studio/server.py"; then
  printf 'R-480 must wire problems_check_fn/problems_get_fn into studio/server.py.\n'
  exit 1
fi

for route in 'POST /jobs/build/{id}/problems' 'GET /jobs/build/{id}/problems'; do
  if ! rg -qF "$route" "$control_plane_root/internal/jobs/handler.go"; then
    printf 'R-480 control-plane must register: %s\n' "$route"
    exit 1
  fi
done

if ! rg -q 'defaultProblemsTimeout' "$control_plane_root/internal/jobs/types.go"; then
  printf 'R-480 must add a defaultProblemsTimeout constant to types.go.\n'
  exit 1
fi

# R-481: tabbed workspace (Preview/Files/Code/Problems).
for required_file in \
  "$console_root/app/studio/studio-tabs.tsx" \
  "$console_root/app/studio/code-highlight.ts" \
  "$console_root/app/api/jobs/build/[id]/problems/route.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-481 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q 'checkBuildProblems|getBuildProblems' "$console_root/lib/control-plane.ts"; then
  printf 'R-481 must add checkBuildProblems()/getBuildProblems() clients to lib/control-plane.ts.\n'
  exit 1
fi

if ! rg -q 'StudioTabs' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-481 must wire <StudioTabs> into studio-chat.tsx.\n'
  exit 1
fi

for tab_label in '"Preview"' '"Files"' '"Code"' '"Problems"'; do
  if ! rg -qF "$tab_label" "$console_root/app/studio/studio-tabs.tsx"; then
    printf 'R-481 must include the %s tab in studio-tabs.tsx.\n' "$tab_label"
    exit 1
  fi
done

# R-482: Model Provider settings UI.
for required_file in \
  "$console_root/app/settings/layout.tsx" \
  "$console_root/app/settings/page.tsx" \
  "$console_root/app/api/providers/route.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-482 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -q 'getProviderStatus' "$console_root/lib/control-plane.ts"; then
  printf 'R-482 must add getProviderStatus() client to lib/control-plane.ts.\n'
  exit 1
fi

if ! rg -q 'GET /jobs/providers' "$control_plane_root/internal/jobs/handler.go"; then
  printf 'R-482 control-plane must register: GET /jobs/providers\n'
  exit 1
fi

if ! rg -q 'providers_fn' "$agent_engine_root/src/omnistackai_agent_engine/studio/server.py"; then
  printf 'R-482 must wire providers_fn into studio/server.py.\n'
  exit 1
fi

# R-484: real-time build streaming (SSE) - backend only, console UI is R-485.
if ! rg -qF 'def generate_ir_stream' "$agent_engine_root/src/omnistackai_agent_engine/intake/nl_to_ir.py"; then
  printf 'R-484 must add generate_ir_stream() to intake/nl_to_ir.py.\n'
  exit 1
fi

if ! rg -qF 'def build_app_from_prompt_stream' "$agent_engine_root/src/omnistackai_agent_engine/intake/build_app.py"; then
  printf 'R-484 must add build_app_from_prompt_stream() to intake/build_app.py.\n'
  exit 1
fi

if ! rg -qF '"/api/build/stream"' "$agent_engine_root/src/omnistackai_agent_engine/studio/server.py"; then
  printf 'R-484 must register POST /api/build/stream in studio/server.py.\n'
  exit 1
fi

if ! rg -qF 'async def stream' "$agent_engine_root/src/omnistackai_agent_engine/model_gateway/recording.py"; then
  printf 'R-484 must add RecordingProvider.stream() so a real streamed build is usage-recorded.\n'
  exit 1
fi

if ! rg -qF 'POST /jobs/build/stream' "$control_plane_root/internal/jobs/handler.go"; then
  printf 'R-484 control-plane must register: POST /jobs/build/stream\n'
  exit 1
fi

# R-485: console streaming build UI.
if [[ ! -f "$console_root/app/api/jobs/build/stream/route.ts" ]]; then
  printf 'Missing R-485 contract file: %s/app/api/jobs/build/stream/route.ts\n' "$console_root"
  exit 1
fi

if ! rg -qF 'streamBuildApp' "$console_root/lib/control-plane.ts"; then
  printf 'R-485 must add streamBuildApp() client to lib/control-plane.ts.\n'
  exit 1
fi

if ! rg -qF 'sendBuildStream' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-485 must wire sendBuildStream() into studio-chat.tsx.\n'
  exit 1
fi

# R-486: real sandbox lifecycle contract + E2B driver (first of the R-486..R-490 isolation sequence).
for required_file in \
  "$agent_engine_root/src/omnistackai_agent_engine/runtime/sandbox_http.py" \
  "$agent_engine_root/src/omnistackai_agent_engine/runtime/e2b.py"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-486 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -qF 'class SandboxLifecycleProvider' "$agent_engine_root/src/omnistackai_agent_engine/runtime/contracts.py"; then
  printf 'R-486 must add the SandboxLifecycleProvider contract to runtime/contracts.py.\n'
  exit 1
fi

if ! rg -qF 'class E2BSandboxProvider' "$agent_engine_root/src/omnistackai_agent_engine/runtime/e2b.py"; then
  printf 'R-486 must add a real E2BSandboxProvider driver to runtime/e2b.py.\n'
  exit 1
fi

# R-487: real Vercel Sandbox driver (second of the R-486..R-490 isolation sequence).
if [[ ! -f "$agent_engine_root/src/omnistackai_agent_engine/runtime/vercel_sandbox.py" ]]; then
  printf 'Missing R-487 contract file: %s/src/omnistackai_agent_engine/runtime/vercel_sandbox.py\n' "$agent_engine_root"
  exit 1
fi

if ! rg -qF 'class VercelSandboxProvider' "$agent_engine_root/src/omnistackai_agent_engine/runtime/vercel_sandbox.py"; then
  printf 'R-487 must add a real VercelSandboxProvider driver to runtime/vercel_sandbox.py.\n'
  exit 1
fi

if ! rg -qF '"vercel-sandbox"' "$agent_engine_root/src/omnistackai_agent_engine/runtime/providers.py"; then
  printf 'R-487 must register a vercel-sandbox entry in runtime/providers.py RUNTIME_SPECS.\n'
  exit 1
fi

# R-488: real Daytona driver (third of the R-486..R-490 isolation sequence).
if [[ ! -f "$agent_engine_root/src/omnistackai_agent_engine/runtime/daytona.py" ]]; then
  printf 'Missing R-488 contract file: %s/src/omnistackai_agent_engine/runtime/daytona.py\n' "$agent_engine_root"
  exit 1
fi

if ! rg -qF 'class DaytonaSandboxProvider' "$agent_engine_root/src/omnistackai_agent_engine/runtime/daytona.py"; then
  printf 'R-488 must add a real DaytonaSandboxProvider driver to runtime/daytona.py.\n'
  exit 1
fi

# R-489: free, self-hosted gVisor driver (fourth of the R-486..R-490 isolation sequence).
for required_file in \
  "$agent_engine_root/src/omnistackai_agent_engine/runtime/docker_socket.py" \
  "$agent_engine_root/src/omnistackai_agent_engine/runtime/gvisor.py"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-489 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -qF 'class GVisorSandboxProvider' "$agent_engine_root/src/omnistackai_agent_engine/runtime/gvisor.py"; then
  printf 'R-489 must add a real GVisorSandboxProvider driver to runtime/gvisor.py.\n'
  exit 1
fi

# R-490: sandbox provider-selection surface (fifth and final task of the R-486..R-490 sequence).
if [[ ! -f "$agent_engine_root/src/omnistackai_agent_engine/runtime/sandbox_selection.py" ]]; then
  printf 'Missing R-490 contract file: %s/src/omnistackai_agent_engine/runtime/sandbox_selection.py\n' "$agent_engine_root"
  exit 1
fi

if ! rg -qF 'def build_sandbox_from_env' "$agent_engine_root/src/omnistackai_agent_engine/runtime/sandbox_selection.py"; then
  printf 'R-490 must add build_sandbox_from_env() to runtime/sandbox_selection.py.\n'
  exit 1
fi

if ! rg -qF 'class SandboxSelectionError' "$agent_engine_root/src/omnistackai_agent_engine/runtime/errors.py"; then
  printf 'R-490 must add SandboxSelectionError to runtime/errors.py.\n'
  exit 1
fi

# R-491: console UI foundation - Tailwind v4 + shadcn/ui + Geist (the R-470 gate above was retired
# with the founder's explicit "Full UI overhaul now" decision, 2026-09-19).
for required_file in \
  "$console_root/postcss.config.mjs" \
  "$console_root/components.json" \
  "$console_root/lib/utils.ts" \
  "$console_root/components/ui/button.tsx" \
  "$console_root/app/theme-provider.tsx" \
  "$console_root/app/icon.svg"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-491 contract file: %s\n' "$required_file"
    exit 1
  fi
done

for dependency in tailwindcss '@tailwindcss/postcss' shadcn next-themes lucide-react; do
  if ! rg -qF "\"$dependency\"" "$console_root/package.json"; then
    printf 'R-491 console must depend on %s.\n' "$dependency"
    exit 1
  fi
done

if ! rg -qF '@import "tailwindcss"' "$console_root/app/globals.css"; then
  printf 'R-491 must import Tailwind in app/globals.css.\n'
  exit 1
fi

if ! rg -qF 'Geist_Mono' "$console_root/app/layout.tsx"; then
  printf 'R-491 must load Geist and Geist Mono via next/font in app/layout.tsx.\n'
  exit 1
fi

# R-492: console auth screens + shared app shell (nav with current-page state, user menu,
# skip-to-content link, branded 404, home dashboard).
for required_file in \
  "$console_root/components/app-shell.tsx" \
  "$console_root/components/app-nav.tsx" \
  "$console_root/components/user-menu.tsx" \
  "$console_root/components/brand-mark.tsx" \
  "$console_root/components/auth-screen.tsx" \
  "$console_root/components/field.tsx" \
  "$console_root/app/not-found.tsx" \
  "$console_root/app/login/login-form.tsx" \
  "$console_root/app/register/register-form.tsx"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-492 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if [[ -f "$console_root/app/logout-button.tsx" ]]; then
  printf 'R-492 retired app/logout-button.tsx into components/user-menu.tsx.\n'
  exit 1
fi

if ! rg -qF 'href="#main"' "$console_root/components/app-shell.tsx"; then
  printf 'R-492 app shell must include a skip-to-content link targeting #main.\n'
  exit 1
fi

for nav_marker in usePathname aria-current; do
  if ! rg -qF "$nav_marker" "$console_root/components/app-nav.tsx"; then
    printf 'R-492 app nav must mark the current page (%s).\n' "$nav_marker"
    exit 1
  fi
done

for auth_form in login/login-form.tsx register/register-form.tsx; do
  for marker in aria-invalid 'role="alert"' noValidate; do
    if ! rg -qF "$marker" "$console_root/app/$auth_form"; then
      printf 'R-492 %s must validate inline (%s).\n' "$auth_form" "$marker"
      exit 1
    fi
  done
done

for shell_consumer in app/page.tsx app/studio/layout.tsx app/settings/layout.tsx app/fabric/page.tsx; do
  if ! rg -qF 'AppShell' "$console_root/$shell_consumer"; then
    printf 'R-492 %s must render inside the shared AppShell.\n' "$shell_consumer"
    exit 1
  fi
done

# R-493: Studio core - chat rail + workspace shell on shadcn primitives and Lucide.
if rg -qF 'from "./studio-icons"' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-493 studio-chat.tsx must use Lucide directly, not the studio-icons shim.\n'
  exit 1
fi

# (R-493 turned studio-icons.tsx into a Lucide shim; R-494 then retired the file entirely - see
# the R-494 block, which asserts it is gone and that no Studio file imports it.)

for marker in 'role="log"' 'EXAMPLE_PROMPTS' 'New app' 'aria-label="Send"' 'formatServerError' 'studio-progress'; do
  if ! rg -qF "$marker" "$console_root/app/studio/studio-chat.tsx"; then
    printf 'R-493 studio-chat.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

if ! rg -qF 'layout="full"' "$console_root/app/studio/layout.tsx"; then
  printf 'R-493 the Studio layout must use the full-width AppShell layout.\n'
  exit 1
fi

if ! rg -q 'layout\?: "contained" \| "full"' "$console_root/components/app-shell.tsx"; then
  printf 'R-493 AppShell must expose the layout prop.\n'
  exit 1
fi

for dead_block in '.studio-topbar' '.chat-rail' '.studio-main' '.chat-composer' '.workspace-empty'; do
  if rg -qF "$dead_block {" "$console_root/app/globals.css"; then
    printf 'R-493 must remove the dead legacy Studio CSS block: %s\n' "$dead_block"
    exit 1
  fi
done

for live_block in '.studio-grid {' '.studio-progress {' '@keyframes studio-progress'; do
  if ! rg -qF "$live_block" "$console_root/app/globals.css"; then
    printf 'R-493 globals.css must define %s.\n' "$live_block"
    exit 1
  fi
done

# R-494: Studio tabs - Preview chrome, Files tree, Code viewer, Problems on shadcn Tabs + Lucide.
if [[ -f "$console_root/app/studio/studio-icons.tsx" ]]; then
  printf 'R-494 retired app/studio/studio-icons.tsx (Lucide is imported directly everywhere).\n'
  exit 1
fi

if [[ ! -f "$console_root/app/studio/file-tree.tsx" ]]; then
  printf 'Missing R-494 contract file: %s/app/studio/file-tree.tsx\n' "$console_root"
  exit 1
fi

if rg -q 'studio-icons' "$console_root/app/studio"/*.tsx; then
  printf 'R-494: no Studio file may still import studio-icons.\n'
  exit 1
fi

if ! rg -qF 'buildFileTree' "$console_root/app/studio/file-tree.tsx"; then
  printf 'R-494 file-tree.tsx must export buildFileTree().\n'
  exit 1
fi

for marker in '@/components/ui/tabs' 'TabsTrigger' 'FileTree' 'Check for problems' 'parseDiagnostic'; do
  if ! rg -qF "$marker" "$console_root/app/studio/studio-tabs.tsx"; then
    printf 'R-494 studio-tabs.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

for marker in 'WIDTH_PRESETS' 'aria-pressed' 'Open in new tab'; do
  if ! rg -qF "$marker" "$console_root/app/studio/studio-preview.tsx"; then
    printf 'R-494 studio-preview.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

if ! rg -qF 'fetchBuildFiles' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-494 studio-chat.tsx must fetch the file list on ?build= hydration.\n'
  exit 1
fi

for dead_block in '.tab-bar' '.file-list' '.code-viewer-content' '.problems-tab' '.preview-frame'; do
  if rg -qF "$dead_block {" "$console_root/app/globals.css"; then
    printf 'R-494 must remove the dead legacy tab CSS block: %s\n' "$dead_block"
    exit 1
  fi
done

# R-495: Settings + Fabric on the R-491 stack; the legacy class family is swept (only the
# R-475-pinned .pill/.pill--accent/.spinner survive until R-496).
if [[ ! -f "$console_root/components/theme-switcher.tsx" ]]; then
  printf 'Missing R-495 contract file: %s/components/theme-switcher.tsx\n' "$console_root"
  exit 1
fi

for marker in 'useTheme' 'aria-pressed' 'role="group"'; do
  if ! rg -qF "$marker" "$console_root/components/theme-switcher.tsx"; then
    printf 'R-495 theme-switcher.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

for marker in 'ThemeSwitcher' 'keyEnv' 'id="account"' 'id="appearance"' 'id="providers"' 'getProviderStatus'; do
  if ! rg -qF "$marker" "$console_root/app/settings/page.tsx"; then
    printf 'R-495 settings/page.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

for marker in 'snapshotVersion' 'DiffBlock' 'AppShell' '<caption'; do
  if ! rg -qF "$marker" "$console_root/app/fabric/page.tsx"; then
    printf 'R-495 fabric/page.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

if rg -q 'className="(wrap|masthead|panel|studio-intro|settings-active-now)' "$console_root/app" "$console_root/components"; then
  printf 'R-495: no page may still use the legacy .wrap/.masthead/.panel class family.\n'
  exit 1
fi

for dead_block in '.wrap' '.masthead' '.panel' '.badge' '.stat' '.settings-active-now' '.studio-intro'; do
  if rg -qF "$dead_block {" "$console_root/app/globals.css"; then
    printf 'R-495 must remove the dead legacy CSS block: %s\n' "$dead_block"
    exit 1
  fi
done

# R-496: motion, states & polish - loading/error boundaries, OG/meta, .reveal motion, and the
# last legacy CSS retired.
for required_file in \
  "$console_root/app/studio/loading.tsx" \
  "$console_root/app/settings/loading.tsx" \
  "$console_root/app/error.tsx" \
  "$console_root/app/global-error.tsx" \
  "$console_root/app/opengraph-image.tsx" \
  "$console_root/app/twitter-image.tsx" \
  "$console_root/lib/motion.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-496 contract file: %s\n' "$required_file"
    exit 1
  fi
done

for error_file in app/error.tsx app/global-error.tsx; do
  for marker in '"use client"' 'retry' 'digest'; do
    if ! rg -qF "$marker" "$console_root/$error_file"; then
      printf 'R-496 %s must include %s.\n' "$error_file" "$marker"
      exit 1
    fi
  done
done

for marker in 'metadataBase' 'openGraph' 'twitter' 'OMNISTACKAI_CONSOLE_PUBLIC_URL'; do
  if ! rg -qF "$marker" "$console_root/app/layout.tsx"; then
    printf 'R-496 app/layout.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

if ! rg -qF 'OMNISTACKAI_CONSOLE_PUBLIC_URL=' "$repo_root/.env.example"; then
  printf 'R-496 must document OMNISTACKAI_CONSOLE_PUBLIC_URL in .env.example.\n'
  exit 1
fi

if ! rg -qF 'ImageResponse' "$console_root/app/opengraph-image.tsx"; then
  printf 'R-496 opengraph-image.tsx must render with ImageResponse from next/og.\n'
  exit 1
fi

for live_block in '.reveal {' '@keyframes rise' '--shadow-tint'; do
  if ! rg -qF -- "$live_block" "$console_root/app/globals.css"; then
    printf 'R-496 globals.css must define %s.\n' "$live_block"
    exit 1
  fi
done

for dead in '.pill {' '.pill--accent {' '.spinner {' '@keyframes spin' '--bg: var(' '--panel: var(' '--surface-2: var(' '--accent-soft-bg:' '--ok-bg:' '--error-fg:'; do
  if rg -qF -- "$dead" "$console_root/app/globals.css"; then
    printf 'R-496 must retire the legacy CSS: %s\n' "$dead"
    exit 1
  fi
done

# No root app/loading.tsx on purpose: a Suspense boundary above the auth gates would turn their
# redirect() into a streamed 200 + client redirect (found live in R-496). The slow provider fetch
# streams inside the pages instead, below the gate.
if [[ -f "$console_root/app/loading.tsx" ]]; then
  printf 'R-496: no root app/loading.tsx - it breaks the auth redirects (see the note above).\n'
  exit 1
fi

for streaming_page in app/page.tsx app/settings/page.tsx; do
  if ! rg -qF '<Suspense' "$console_root/$streaming_page"; then
    printf 'R-496 %s must stream its provider status inside a Suspense boundary.\n' "$streaming_page"
    exit 1
  fi
done

for reveal_consumer in app/page.tsx app/settings/page.tsx app/fabric/page.tsx; do
  if ! rg -qF 'revealStyle' "$console_root/$reveal_consumer"; then
    printf 'R-496 %s must use the staggered reveal motion.\n' "$reveal_consumer"
    exit 1
  fi
done

# R-497: Lovable-grade pass - prompt-first home, ?prompt= auto-start through the existing submit
# path, prose replies + follow-up chips, file search in the tree.
if [[ ! -f "$console_root/components/home-composer.tsx" ]]; then
  printf 'Missing R-497 contract file: %s/components/home-composer.tsx\n' "$console_root"
  exit 1
fi

if ! rg -qF 'HomeComposer' "$console_root/app/page.tsx"; then
  printf 'R-497 the home page must render the HomeComposer.\n'
  exit 1
fi

if ! rg -qF '/studio?prompt=' "$console_root/components/home-composer.tsx"; then
  printf 'R-497 the home composer must hand its prompt to /studio?prompt=.\n'
  exit 1
fi

for marker in 'searchParams.get("prompt")' 'requestSubmit' 'FOLLOW_UP_PROMPTS' 'autoStarted'; do
  if ! rg -qF "$marker" "$console_root/app/studio/studio-chat.tsx"; then
    printf 'R-497 studio-chat.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

for marker in 'FileFilter' 'Search files' 'Read only'; do
  if ! rg -qF "$marker" "$console_root/app/studio/studio-tabs.tsx"; then
    printf 'R-497 studio-tabs.tsx must include %s.\n' "$marker"
    exit 1
  fi
done

# The example prompts stay identical between the home page and the Studio empty state.
if ! rg -qF 'A task tracker where users create projects and each project has tasks with due dates' "$console_root/components/home-composer.tsx" \
  || ! rg -qF 'A task tracker where users create projects and each project has tasks with due dates' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-497 the home and Studio example prompts must match.\n'
  exit 1
fi

# R-498: platform buildout plan + the single-command local runtime. The plan is a deliverable:
# it is what lets a paused session resume cold, so its files are pinned like any other contract.
if [[ ! -f "$repo_root/scripts/omnistack.sh" ]]; then
  printf 'Missing R-498 contract file: scripts/omnistack.sh\n'
  exit 1
fi

for runtime_command in 'up)' 'down)' 'restart)' 'status)' 'logs)' 'doctor)' 'build)' 'verify)'; do
  if ! rg -qF -- "  $runtime_command" "$repo_root/scripts/omnistack.sh"; then
    printf 'R-498 scripts/omnistack.sh must implement the %s command.\n' "${runtime_command%)}"
    exit 1
  fi
done

# Preview mode is the default for `up`: starting build-only by accident is what made the Studio's
# Preview tab look broken. --no-preview must stay available as the explicit safe mode.
if ! rg -qF -- '--no-preview' "$repo_root/scripts/omnistack.sh"; then
  printf 'R-498 scripts/omnistack.sh must keep --no-preview as the explicit build-only mode.\n'
  exit 1
fi

if ! rg -q '^\.run/$' "$repo_root/.gitignore"; then
  printf 'R-498 must gitignore the runtime state directory: .run/\n'
  exit 1
fi

if [[ ! -f "$repo_root/R_&_D/OmniStackAI_Platform_Buildout_v1.md" ]]; then
  printf 'Missing R-498 contract file: R_&_D/OmniStackAI_Platform_Buildout_v1.md\n'
  exit 1
fi

for spec in F-01-projects F-02-preview F-03-git F-04-skills F-05-secrets F-06-ai-usage \
  F-07-seo F-08-logs-chat F-09-database F-10-security-tests \
  G-01-publish G-02-domains G-03-connectors G-04-payments G-05-analytics; do
  if [[ ! -f "$repo_root/R_&_D/specs/$spec.md" ]]; then
    printf 'Missing R-498 platform spec: R_&_D/specs/%s.md\n' "$spec"
    exit 1
  fi
done
# R-499: Projects & Workspaces Persistence (F-01-projects spec).
for required_file in \
  "$control_plane_root/migrations/000004_projects.up.sql" \
  "$control_plane_root/migrations/000004_projects.down.sql" \
  "$control_plane_root/internal/projects/store.go" \
  "$control_plane_root/internal/projects/handler.go" \
  "$control_plane_root/internal/projects/projects_test.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/workspace.py" \
  "$agent_engine_root/tests/test_studio_workspace.py" \
  "$console_root/app/projects/page.tsx" \
  "$console_root/app/studio/[projectId]/page.tsx" \
  "$console_root/app/studio/[projectId]/manage/page.tsx" \
  "$console_root/components/project-card.tsx" \
  "$console_root/components/project-dialogs.tsx" \
  "$console_root/components/project-switcher.tsx" \
  "$console_root/components/home-projects.tsx" \
  "$console_root/lib/time.ts"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-499 contract file: %s\n' "$required_file"
    exit 1
  fi
done

for project_route in \
  "$console_root/app/api/projects/route.ts" \
  "$console_root/app/api/projects/[id]/route.ts" \
  "$console_root/app/api/projects/[id]/opened/route.ts" \
  "$console_root/app/api/projects/[id]/build/stream/route.ts" \
  "$console_root/app/api/projects/[id]/edit/route.ts" \
  "$console_root/app/api/projects/[id]/turns/route.ts" \
  "$console_root/app/api/projects/[id]/files/route.ts" \
  "$console_root/app/api/projects/[id]/file/route.ts" \
  "$console_root/app/api/projects/[id]/preview/route.ts" \
  "$console_root/app/api/projects/[id]/problems/route.ts"; do
  if [[ ! -f "$project_route" ]]; then
    printf 'Missing R-499 API route: %s\n' "$project_route"
    exit 1
  fi
done

if ! rg -qF 'HomeProjects' "$console_root/app/page.tsx"; then
  printf 'R-499 home page must render HomeProjects.\n'
  exit 1
fi

if ! rg -qF 'ProjectSwitcher' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-499 studio-chat.tsx must render ProjectSwitcher.\n'
  exit 1
fi

if ! rg -qF 'projects.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-499 control-plane main.go must mount projects handler.\n'
  exit 1
fi

if ! rg -qF 'class StudioWorkspaceStore' "$agent_engine_root/src/omnistackai_agent_engine/studio/workspace.py"; then
  printf 'R-499 agent-engine must define StudioWorkspaceStore.\n'
  exit 1
fi

# R-500: Multi-Process Preview & Diagnostics Service (F-02-preview spec).
for required_file in \
  "$console_root/app/preview/[projectId]/[[...path]]/route.ts" \
  "$console_root/app/api/projects/[id]/preview/stop/route.ts" \
  "$agent_engine_root/tests/test_studio_workspace_preview.py"; do
  if [[ ! -f "$required_file" ]]; then
    printf 'Missing R-500 contract file: %s\n' "$required_file"
    exit 1
  fi
done

if ! rg -qF 'GET /projects/{id}/preview' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-500 control-plane must register GET /projects/{id}/preview route.\n'
  exit 1
fi

if ! rg -qF 'POST /projects/{id}/preview/stop' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-500 control-plane must register POST /projects/{id}/preview/stop route.\n'
  exit 1
fi

if ! rg -qF './scripts/omnistack.sh up' "$console_root/app/studio/studio-preview.tsx"; then
  printf 'R-500 studio-preview.tsx must suggest ./scripts/omnistack.sh up in build-only mode.\n'
  exit 1
fi

if ! rg -qF 'def start_workspace' "$agent_engine_root/src/omnistackai_agent_engine/studio/preview.py"; then
  printf 'R-500 agent-engine StudioPreviewManager must define start_workspace.\n'
  exit 1
fi

# R-501: Code ownership — download, connect GitHub, push (F-03-git spec).
for required_git_file in \
  "$control_plane_root/migrations/000005_git_connections.up.sql" \
  "$control_plane_root/migrations/000005_git_connections.down.sql" \
  "$control_plane_root/internal/crypto/gcm.go" \
  "$control_plane_root/internal/crypto/gcm_test.go" \
  "$control_plane_root/internal/git/handler.go" \
  "$control_plane_root/internal/git/github.go" \
  "$control_plane_root/internal/git/store.go" \
  "$control_plane_root/internal/git/git_test.go" \
  "$agent_engine_root/tests/test_studio_workspace_git.py" \
  "$console_root/app/api/projects/[id]/export/route.ts" \
  "$console_root/app/api/git/status/route.ts" \
  "$console_root/app/api/git/connection/route.ts" \
  "$console_root/app/api/git/github/authorize/route.ts" \
  "$console_root/app/api/projects/[id]/git/route.ts" \
  "$console_root/app/api/projects/[id]/git/repo/route.ts" \
  "$console_root/app/api/projects/[id]/git/push/route.ts"; do
  if [[ ! -f "$required_git_file" ]]; then
    printf 'Missing R-501 contract file: %s\n' "$required_git_file"
    exit 1
  fi
done

if ! rg -qF 'CREATE TABLE IF NOT EXISTS git_connections' "$control_plane_root/migrations/000005_git_connections.up.sql"; then
  printf 'R-501 migration must create git_connections table.\n'
  exit 1
fi

if ! rg -qF 'git.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-501 control-plane main.go must mount git handler.\n'
  exit 1
fi

if ! rg -qF 'def export_zip' "$agent_engine_root/src/omnistackai_agent_engine/studio/workspace.py"; then
  printf 'R-501 agent-engine workspace must define export_zip.\n'
  exit 1
fi

if ! rg -qF 'def git_push' "$agent_engine_root/src/omnistackai_agent_engine/studio/workspace.py"; then
  printf 'R-501 agent-engine workspace must define git_push.\n'
  exit 1
fi

if ! rg -qF 'Download code' "$console_root/app/studio/studio-workspace.tsx"; then
  printf 'R-501 studio-workspace.tsx must provide Download code action.\n'
  exit 1
fi

if ! rg -qF 'Connect GitHub' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-501 manage page must provide Connect GitHub action.\n'
  exit 1
fi

# R-502: Knowledge & Skills — custom instructions & domain templates (F-04-skills spec).
for required_skills_file in \
  "$control_plane_root/migrations/000006_skills.up.sql" \
  "$control_plane_root/migrations/000006_skills.down.sql" \
  "$control_plane_root/internal/skills/store.go" \
  "$control_plane_root/internal/skills/handler.go" \
  "$control_plane_root/internal/skills/skills_test.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/intake/context.py" \
  "$agent_engine_root/tests/test_skills_context.py" \
  "$console_root/components/skills-library.tsx" \
  "$console_root/app/api/skills/route.ts" \
  "$console_root/app/api/skills/[id]/route.ts" \
  "$console_root/app/api/projects/[id]/knowledge/route.ts" \
  "$console_root/app/api/projects/[id]/skills/route.ts" \
  "$console_root/app/api/projects/[id]/skills/[skillId]/route.ts"; do
  if [[ ! -f "$required_skills_file" ]]; then
    printf 'Missing R-502 contract file: %s\n' "$required_skills_file"
    exit 1
  fi
done

if ! rg -qF 'CREATE TABLE IF NOT EXISTS skills' "$control_plane_root/migrations/000006_skills.up.sql"; then
  printf 'R-502 migration must create skills table.\n'
  exit 1
fi

if ! rg -qF 'CREATE TABLE IF NOT EXISTS project_skills' "$control_plane_root/migrations/000006_skills.up.sql"; then
  printf 'R-502 migration must create project_skills table.\n'
  exit 1
fi

if ! rg -qF 'ADD COLUMN IF NOT EXISTS knowledge' "$control_plane_root/migrations/000006_skills.up.sql"; then
  printf 'R-502 migration must add knowledge column to projects.\n'
  exit 1
fi

if ! rg -qF 'skills.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-502 control-plane main.go must mount skills handler.\n'
  exit 1
fi

if ! rg -qF 'ResolveContext' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-502 control-plane projects handler must call ResolveContext.\n'
  exit 1
fi

if ! rg -qF 'def assemble_context' "$agent_engine_root/src/omnistackai_agent_engine/intake/context.py"; then
  printf 'R-502 agent-engine must define assemble_context.\n'
  exit 1
fi

if ! rg -qF 'OMNISTACKAI_CONTEXT_MAX_CHARS' "$agent_engine_root/src/omnistackai_agent_engine/intake/context.py"; then
  printf 'R-502 agent-engine context.py must reference OMNISTACKAI_CONTEXT_MAX_CHARS.\n'
  exit 1
fi

if ! rg -qF 'context_truncated' "$agent_engine_root/src/omnistackai_agent_engine/intake/nl_to_ir.py"; then
  printf 'R-502 agent-engine nl_to_ir.py must handle context_truncated.\n'
  exit 1
fi

if ! rg -qF 'context_truncated' "$agent_engine_root/src/omnistackai_agent_engine/intake/app_delta.py"; then
  printf 'R-502 agent-engine app_delta.py must handle context_truncated.\n'
  exit 1
fi

if ! rg -qF 'Skills library' "$console_root/app/settings/page.tsx"; then
  printf 'R-502 settings page must include Skills library section.\n'
  exit 1
fi

if ! rg -qF 'Project Knowledge' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-502 manage page must include Project Knowledge.\n'
  exit 1
fi

if ! rg -qF 'Project Skills' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-502 manage page must include Project Skills.\n'
  exit 1
fi

if ! rg -qF 'computeMentionSkills' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-502 studio-chat.tsx must define computeMentionSkills.\n'
  exit 1
fi

# R-503: F-05 Secrets — encrypted per-project configuration.
for required_secrets_file in \
  "$control_plane_root/migrations/000007_project_secrets.up.sql" \
  "$control_plane_root/migrations/000007_project_secrets.down.sql" \
  "$control_plane_root/internal/secrets/store.go" \
  "$control_plane_root/internal/secrets/handler.go" \
  "$control_plane_root/internal/secrets/secrets_test.go" \
  "$agent_engine_root/tests/test_studio_workspace_secrets.py" \
  "$console_root/app/api/projects/[id]/secrets/route.ts" \
  "$console_root/app/api/projects/[id]/secrets/[key]/route.ts" \
  "$console_root/app/api/projects/[id]/secrets/reveal/[key]/route.ts"; do
  if [[ ! -f "$required_secrets_file" ]]; then
    printf 'Missing R-503 contract file: %s\n' "$required_secrets_file"
    exit 1
  fi
done

if ! rg -qF 'CREATE TABLE IF NOT EXISTS project_secrets' "$control_plane_root/migrations/000007_project_secrets.up.sql"; then
  printf 'R-503 migration must create project_secrets table.\n'
  exit 1
fi

if ! rg -qF 'DROP TABLE IF EXISTS project_secrets' "$control_plane_root/migrations/000007_project_secrets.down.sql"; then
  printf 'R-503 down migration must drop project_secrets table.\n'
  exit 1
fi

if ! rg -qF 'secrets.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-503 control-plane main.go must mount secrets handler.\n'
  exit 1
fi

if ! rg -qF 'SecretsStore' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-503 control-plane projects handler must wire SecretsStore.\n'
  exit 1
fi

if ! rg -qF 'SecretsKeyPrevious' "$control_plane_root/internal/config/config.go"; then
  printf 'R-503 control-plane config must support SecretsKeyPrevious for key rotation.\n'
  exit 1
fi

if ! rg -qF 'extra_env' "$agent_engine_root/src/omnistackai_agent_engine/localrun/plan.py"; then
  printf 'R-503 agent-engine plan.py must support extra_env.\n'
  exit 1
fi

if ! rg -qF 'getProjectSecrets' "$console_root/lib/control-plane.ts"; then
  printf 'R-503 lib/control-plane.ts must define getProjectSecrets.\n'
  exit 1
fi

if ! rg -qF 'revealProjectSecret' "$console_root/lib/control-plane.ts"; then
  printf 'R-503 lib/control-plane.ts must define revealProjectSecret.\n'
  exit 1
fi

if ! rg -qF 'Stored encrypted with AES-256-GCM' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-503 manage page must include encrypted secrets notice.\n'
  exit 1
fi

# R-504: F-06 AI — model configuration and usage (BYOK, model pinning, audit ledger).
for required_ai_file in \
  "$control_plane_root/migrations/000008_ai_usage.up.sql" \
  "$control_plane_root/migrations/000008_ai_usage.down.sql" \
  "$control_plane_root/internal/ai/store.go" \
  "$control_plane_root/internal/ai/handler.go" \
  "$control_plane_root/internal/ai/resolution.go" \
  "$control_plane_root/internal/ai/ai_test.go" \
  "$agent_engine_root/tests/test_studio_workspace_ai.py" \
  "$console_root/components/ai-keys-manager.tsx" \
  "$console_root/components/account-usage-viewer.tsx" \
  "$console_root/components/project-ai-manage.tsx" \
  "$console_root/app/api/ai/providers/route.ts" \
  "$console_root/app/api/ai/keys/[providerId]/route.ts" \
  "$console_root/app/api/ai/keys/[providerId]/test/route.ts" \
  "$console_root/app/api/projects/[id]/model/route.ts" \
  "$console_root/app/api/projects/[id]/usage/route.ts" \
  "$console_root/app/api/usage/route.ts"; do
  if [[ ! -f "$required_ai_file" ]]; then
    printf 'Missing R-504 contract file: %s\n' "$required_ai_file"
    exit 1
  fi
done

if ! rg -qF 'CREATE TABLE IF NOT EXISTS user_provider_keys' "$control_plane_root/migrations/000008_ai_usage.up.sql"; then
  printf 'R-504 migration must create user_provider_keys table.\n'
  exit 1
fi

if ! rg -qF 'CREATE TABLE IF NOT EXISTS model_calls' "$control_plane_root/migrations/000008_ai_usage.up.sql"; then
  printf 'R-504 migration must create model_calls table.\n'
  exit 1
fi

if ! rg -qF 'DROP TABLE IF EXISTS user_provider_keys' "$control_plane_root/migrations/000008_ai_usage.down.sql"; then
  printf 'R-504 down migration must drop user_provider_keys table.\n'
  exit 1
fi

if ! rg -qF 'DROP TABLE IF EXISTS model_calls' "$control_plane_root/migrations/000008_ai_usage.down.sql"; then
  printf 'R-504 down migration must drop model_calls table.\n'
  exit 1
fi

if ! rg -qF 'ai.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-504 control-plane main.go must register AI handlers.\n'
  exit 1
fi

if ! rg -qF 'AIStore' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-504 control-plane projects handler must wire AIStore.\n'
  exit 1
fi

if ! rg -qF 'AIStore' "$control_plane_root/internal/jobs/types.go"; then
  printf 'R-504 control-plane jobs types must wire AIStore.\n'
  exit 1
fi

if ! rg -qF 'ResolveModel' "$control_plane_root/internal/ai/resolution.go"; then
  printf 'R-504 control-plane must implement ResolveModel.\n'
  exit 1
fi

if ! rg -qF 'RecordUsageCalls' "$control_plane_root/internal/ai/resolution.go"; then
  printf 'R-504 control-plane must implement RecordUsageCalls.\n'
  exit 1
fi

if ! rg -qF 'getUserKeys' "$console_root/lib/control-plane.ts"; then
  printf 'R-504 lib/control-plane.ts must define getUserKeys.\n'
  exit 1
fi

if ! rg -qF 'getAccountUsage' "$console_root/lib/control-plane.ts"; then
  printf 'R-504 lib/control-plane.ts must define getAccountUsage.\n'
  exit 1
fi

if ! rg -qF 'getProjectModel' "$console_root/lib/control-plane.ts"; then
  printf 'R-504 lib/control-plane.ts must define getProjectModel.\n'
  exit 1
fi

if ! rg -qF 'AIKeysManager' "$console_root/app/settings/page.tsx"; then
  printf 'R-504 settings page must render AIKeysManager.\n'
  exit 1
fi

if ! rg -qF 'AccountUsageViewer' "$console_root/app/settings/page.tsx"; then
  printf 'R-504 settings page must render AccountUsageViewer.\n'
  exit 1
fi

if ! rg -qF 'ProjectAIManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-504 manage page must render ProjectAIManage.\n'
  exit 1
fi

# R-505: F-07 SEO & AI search.
for required_seo_file in \
  "$control_plane_root/migrations/000009_seo.up.sql" \
  "$control_plane_root/migrations/000009_seo.down.sql" \
  "$control_plane_root/internal/seo/store.go" \
  "$control_plane_root/internal/seo/handler.go" \
  "$control_plane_root/internal/seo/seo_test.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/seo/audit.py" \
  "$agent_engine_root/tests/test_seo_codegen_and_audit.py" \
  "$console_root/components/project-seo-manage.tsx" \
  "$console_root/app/api/projects/[id]/seo/route.ts" \
  "$console_root/app/api/projects/[id]/seo/pages/route.ts" \
  "$console_root/app/api/projects/[id]/seo/pages/[...route]/route.ts" \
  "$console_root/app/api/projects/[id]/seo/audit/route.ts" \
  "$console_root/app/api/projects/[id]/seo/suggest/route.ts"; do
  if [[ ! -f "$required_seo_file" ]]; then
    printf 'Missing R-505 contract file: %s\n' "$required_seo_file"
    exit 1
  fi
done

if ! rg -qF 'CREATE TABLE IF NOT EXISTS project_seo' "$control_plane_root/migrations/000009_seo.up.sql"; then
  printf 'R-505 migration must create project_seo table.\n'
  exit 1
fi

if ! rg -qF 'CREATE TABLE IF NOT EXISTS project_page_seo' "$control_plane_root/migrations/000009_seo.up.sql"; then
  printf 'R-505 migration must create project_page_seo table.\n'
  exit 1
fi

if ! rg -qF 'DROP TABLE IF EXISTS project_page_seo' "$control_plane_root/migrations/000009_seo.down.sql"; then
  printf 'R-505 down migration must drop project_page_seo table.\n'
  exit 1
fi

if ! rg -qF 'DROP TABLE IF EXISTS project_seo' "$control_plane_root/migrations/000009_seo.down.sql"; then
  printf 'R-505 down migration must drop project_seo table.\n'
  exit 1
fi

if ! rg -qF 'seo.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-505 control-plane main.go must register SEO handlers.\n'
  exit 1
fi

if ! rg -qF 'getProjectSEO' "$console_root/lib/control-plane.ts"; then
  printf 'R-505 lib/control-plane.ts must define getProjectSEO.\n'
  exit 1
fi

if ! rg -qF 'getProjectPageSEOs' "$console_root/lib/control-plane.ts"; then
  printf 'R-505 lib/control-plane.ts must define getProjectPageSEOs.\n'
  exit 1
fi

if ! rg -qF 'auditProjectSEO' "$console_root/lib/control-plane.ts"; then
  printf 'R-505 lib/control-plane.ts must define auditProjectSEO.\n'
  exit 1
fi

if ! rg -qF 'suggestProjectSEOCopy' "$console_root/lib/control-plane.ts"; then
  printf 'R-505 lib/control-plane.ts must define suggestProjectSEOCopy.\n'
  exit 1
fi

if ! rg -qF 'ProjectSEOManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-505 manage page must render ProjectSEOManage.\n'
  exit 1
fi

# R-506: F-08 Logs & Live Chat Streaming.
for required_logs_file in \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/logs.py" \
  "$agent_engine_root/tests/test_logs_and_cancellation.py" \
  "$console_root/components/project-logs-manage.tsx" \
  "$console_root/app/api/projects/[id]/logs/route.ts" \
  "$console_root/app/api/projects/[id]/logs/stream/route.ts" \
  "$console_root/app/api/projects/[id]/build/cancel/route.ts"; do
  if [[ ! -f "$required_logs_file" ]]; then
    printf 'Missing R-506 contract file: %s\n' "$required_logs_file"
    exit 1
  fi
done

if ! rg -qF 'StudioLogManager' "$agent_engine_root/src/omnistackai_agent_engine/studio/logs.py"; then
  printf 'R-506 agent-engine must define StudioLogManager.\n'
  exit 1
fi

if ! rg -qF 'getProjectLogs' "$console_root/lib/control-plane.ts"; then
  printf 'R-506 lib/control-plane.ts must define getProjectLogs.\n'
  exit 1
fi

if ! rg -qF 'cancelProjectBuild' "$console_root/lib/control-plane.ts"; then
  printf 'R-506 lib/control-plane.ts must define cancelProjectBuild.\n'
  exit 1
fi

if ! rg -qF 'streamProjectLogs' "$console_root/lib/control-plane.ts"; then
  printf 'R-506 lib/control-plane.ts must define streamProjectLogs.\n'
  exit 1
fi

if ! rg -qF 'ProjectLogsManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-506 manage page must render ProjectLogsManage.\n'
  exit 1
fi

if ! rg -qF 'handleCancel' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-506 studio-chat.tsx must implement handleCancel.\n'
  exit 1
fi

if ! rg -qF 'handleFileSelect' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-506 studio-chat.tsx must implement handleFileSelect for attachments.\n'
  exit 1
fi

if ! rg -qF 'toggleListening' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-506 studio-chat.tsx must implement toggleListening for voice input.\n'
  exit 1
fi

for required_db_file in \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/database.py" \
  "$console_root/components/project-db-manage.tsx" \
  "$console_root/app/api/projects/[id]/db/tables/route.ts" \
  "$console_root/app/api/projects/[id]/db/tables/[table]/route.ts" \
  "$console_root/app/api/projects/[id]/db/query/route.ts" \
  "$console_root/app/api/projects/[id]/db/schema/route.ts"; do
  if [[ ! -f "$required_db_file" ]]; then
    printf 'Missing R-507 contract file: %s\n' "$required_db_file"
    exit 1
  fi
done

if ! rg -qF 'list_tables' "$agent_engine_root/src/omnistackai_agent_engine/studio/database.py"; then
  printf 'R-507 database.py must define list_tables.\n'
  exit 1
fi

if ! rg -qF 'execute_query' "$agent_engine_root/src/omnistackai_agent_engine/studio/database.py"; then
  printf 'R-507 database.py must define execute_query.\n'
  exit 1
fi

if ! rg -qF 'getProjectDBTables' "$console_root/lib/control-plane.ts"; then
  printf 'R-507 lib/control-plane.ts must define getProjectDBTables.\n'
  exit 1
fi

if ! rg -qF 'executeProjectDBQuery' "$console_root/lib/control-plane.ts"; then
  printf 'R-507 lib/control-plane.ts must define executeProjectDBQuery.\n'
  exit 1
fi

if ! rg -qF 'ProjectDbManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-507 manage page must render ProjectDbManage.\n'
  exit 1
fi

if ! rg -qF '/db/tables' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-507 control-plane must register /db/tables route.\n'
  exit 1
fi

if ! rg -qF '/db/query' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-507 control-plane must register /db/query route.\n'
  exit 1
fi

for required_sec_test_file in \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/security.py" \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/tests_runner.py" \
  "$console_root/components/project-security-manage.tsx" \
  "$console_root/components/project-tests-manage.tsx" \
  "$console_root/app/api/projects/[id]/security/scan/route.ts" \
  "$console_root/app/api/projects/[id]/security/route.ts" \
  "$console_root/app/api/projects/[id]/tests/run/route.ts" \
  "$console_root/app/api/projects/[id]/tests/route.ts"; do
  if [[ ! -f "$required_sec_test_file" ]]; then
    printf 'Missing R-508 contract file: %s\n' "$required_sec_test_file"
    exit 1
  fi
done

if ! rg -qF 'run_security_scan' "$agent_engine_root/src/omnistackai_agent_engine/studio/security.py"; then
  printf 'R-508 security.py must define run_security_scan.\n'
  exit 1
fi

if ! rg -qF 'get_last_security_report' "$agent_engine_root/src/omnistackai_agent_engine/studio/security.py"; then
  printf 'R-508 security.py must define get_last_security_report.\n'
  exit 1
fi

if ! rg -qF 'run_project_tests' "$agent_engine_root/src/omnistackai_agent_engine/studio/tests_runner.py"; then
  printf 'R-508 tests_runner.py must define run_project_tests.\n'
  exit 1
fi

if ! rg -qF 'get_last_test_report' "$agent_engine_root/src/omnistackai_agent_engine/studio/tests_runner.py"; then
  printf 'R-508 tests_runner.py must define get_last_test_report.\n'
  exit 1
fi

if ! rg -qF 'runProjectSecurityScan' "$console_root/lib/control-plane.ts"; then
  printf 'R-508 lib/control-plane.ts must define runProjectSecurityScan.\n'
  exit 1
fi

if ! rg -qF 'runProjectTests' "$console_root/lib/control-plane.ts"; then
  printf 'R-508 lib/control-plane.ts must define runProjectTests.\n'
  exit 1
fi

if ! rg -qF 'ProjectSecurityManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-508 manage page must render ProjectSecurityManage.\n'
  exit 1
fi

if ! rg -qF 'ProjectTestsManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-508 manage page must render ProjectTestsManage.\n'
  exit 1
fi

if ! rg -qF '/security/scan' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-508 control-plane must register /security/scan route.\n'
  exit 1
fi

if ! rg -qF '/tests/run' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-508 control-plane must register /tests/run route.\n'
  exit 1
fi

# R-509 (G-01 Publish v1): deployments migration, deploy package, publish evaluator, and console-web publish UI
for required_deploy_file in \
  "$control_plane_root/migrations/000010_deployments.up.sql" \
  "$control_plane_root/migrations/000010_deployments.down.sql" \
  "$control_plane_root/internal/deploy/store.go" \
  "$control_plane_root/internal/deploy/provider.go" \
  "$control_plane_root/internal/deploy/handler.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/publish.py" \
  "$console_root/components/hosting-keys-manager.tsx" \
  "$console_root/components/publish-dialog.tsx" \
  "$console_root/components/project-publish-manage.tsx" \
  "$console_root/app/api/deploy/connections/[provider]/route.ts" \
  "$console_root/app/api/projects/[id]/publish/route.ts" \
  "$console_root/app/api/projects/[id]/deployments/route.ts"; do
  if [[ ! -f "$required_deploy_file" ]]; then
    printf 'Missing R-509 contract file: %s\n' "$required_deploy_file"
    exit 1
  fi
done

if ! rg -qF 'evaluate_publish_readiness' "$agent_engine_root/src/omnistackai_agent_engine/studio/publish.py"; then
  printf 'R-509 publish.py must define evaluate_publish_readiness.\n'
  exit 1
fi

if ! rg -qF '/publish/readiness' "$agent_engine_root/src/omnistackai_agent_engine/studio/server.py"; then
  printf 'R-509 agent-engine must route /publish/readiness.\n'
  exit 1
fi

if ! rg -qF 'getDeployConnection' "$console_root/lib/control-plane.ts"; then
  printf 'R-509 lib/control-plane.ts must define getDeployConnection.\n'
  exit 1
fi

if ! rg -qF 'triggerPublish' "$console_root/lib/control-plane.ts"; then
  printf 'R-509 lib/control-plane.ts must define triggerPublish.\n'
  exit 1
fi

if ! rg -qF 'HostingKeysManager' "$console_root/app/settings/page.tsx"; then
  printf 'R-509 settings page must render HostingKeysManager.\n'
  exit 1
fi

if ! rg -qF 'PublishDialog' "$console_root/app/studio/studio-workspace.tsx"; then
  printf 'R-509 studio workspace must render PublishDialog.\n'
  exit 1
fi

if ! rg -qF 'ProjectPublishManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-509 manage page must render ProjectPublishManage.\n'
  exit 1
fi

if ! rg -qF 'deploy.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-509 control-plane main must register deploy routes.\n'
  exit 1
fi

# R-510 (G-02 Custom Domains): domains migration, domains package, verifier, and console-web domain UI
for required_domain_file in \
  "$control_plane_root/migrations/000011_domains.up.sql" \
  "$control_plane_root/migrations/000011_domains.down.sql" \
  "$control_plane_root/internal/domains/store.go" \
  "$control_plane_root/internal/domains/verifier.go" \
  "$control_plane_root/internal/domains/handler.go" \
  "$console_root/components/project-domain-manage.tsx" \
  "$console_root/app/api/projects/[id]/domains/route.ts" \
  "$console_root/app/api/projects/[id]/domains/[domainId]/route.ts" \
  "$console_root/app/api/projects/[id]/domains/[domainId]/verify/route.ts"; do
  if [[ ! -f "$required_domain_file" ]]; then
    printf 'Missing R-510 contract file: %s\n' "$required_domain_file"
    exit 1
  fi
done

if ! rg -qF 'UNIQUE' "$control_plane_root/migrations/000011_domains.up.sql"; then
  printf 'R-510 000011_domains.up.sql must enforce UNIQUE hostname constraint for anti-hijacking.\n'
  exit 1
fi

if ! rg -qF 'listProjectDomains' "$console_root/lib/control-plane.ts"; then
  printf 'R-510 lib/control-plane.ts must define listProjectDomains.\n'
  exit 1
fi

if ! rg -qF 'verifyProjectDomain' "$console_root/lib/control-plane.ts"; then
  printf 'R-510 lib/control-plane.ts must define verifyProjectDomain.\n'
  exit 1
fi

if ! rg -qF 'ProjectDomainManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-510 manage page must render ProjectDomainManage.\n'
  exit 1
fi

if ! rg -qF 'domains.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-510 control-plane main must register domains routes.\n'
  exit 1
fi

# R-511 (G-03 Connectors v1): connectors migration, control-plane package, agent-engine codegen, and console-web UI
for required_connector_file in \
  "$control_plane_root/migrations/000012_connectors.up.sql" \
  "$control_plane_root/migrations/000012_connectors.down.sql" \
  "$control_plane_root/internal/connectors/catalog.go" \
  "$control_plane_root/internal/connectors/store.go" \
  "$control_plane_root/internal/connectors/handler.go" \
  "$control_plane_root/internal/connectors/connectors_test.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py" \
  "$agent_engine_root/tests/test_connectors.py" \
  "$console_root/components/project-connectors-manage.tsx" \
  "$console_root/app/api/connectors/route.ts" \
  "$console_root/app/api/projects/[id]/connectors/route.ts" \
  "$console_root/app/api/projects/[id]/connectors/[provider]/route.ts" \
  "$console_root/app/api/projects/[id]/connectors/[provider]/test/route.ts"; do
  if [[ ! -f "$required_connector_file" ]]; then
    printf 'Missing R-511 contract file: %s\n' "$required_connector_file"
    exit 1
  fi
done

if ! rg -qF 'project_connectors' "$control_plane_root/migrations/000012_connectors.up.sql"; then
  printf 'R-511 000012_connectors.up.sql must create project_connectors table.\n'
  exit 1
fi

if ! rg -qF 'connector_accounts' "$control_plane_root/migrations/000012_connectors.up.sql"; then
  printf 'R-511 000012_connectors.up.sql must create connector_accounts table.\n'
  exit 1
fi

if ! rg -qF 'connectors.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-511 control-plane main must register connectors routes.\n'
  exit 1
fi

if ! rg -qF 'apply_connector' "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-511 connectors.py must define apply_connector.\n'
  exit 1
fi

if ! rg -qF 'remove_connector' "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-511 connectors.py must define remove_connector.\n'
  exit 1
fi

if ! rg -qF 'ProjectConnectorsManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-511 manage page must render ProjectConnectorsManage.\n'
  exit 1
fi

# R-512 (G-04 Payments in Generated Apps — Stripe & Razorpay): migration, control-plane package, agent-engine codegen, and console-web UI
for required_payment_file in \
  "$control_plane_root/migrations/000013_project_payments.up.sql" \
  "$control_plane_root/migrations/000013_project_payments.down.sql" \
  "$control_plane_root/internal/payments/store.go" \
  "$control_plane_root/internal/payments/handler.go" \
  "$control_plane_root/internal/payments/payments_test.go" \
  "$agent_engine_root/src/omnistackai_agent_engine/studio/payments.py" \
  "$agent_engine_root/tests/test_payments.py" \
  "$console_root/components/project-payments-manage.tsx" \
  "$console_root/app/api/projects/[id]/payments/route.ts"; do
  if [[ ! -f "$required_payment_file" ]]; then
    printf 'Missing R-512 contract file: %s\n' "$required_payment_file"
    exit 1
  fi
done

if ! rg -qF 'payment_gateway' "$control_plane_root/migrations/000013_project_payments.up.sql"; then
  printf 'R-512 000013_project_payments.up.sql must add payment_gateway column.\n'
  exit 1
fi

if ! rg -qF 'payments.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-512 control-plane main must register payments routes.\n'
  exit 1
fi

if ! rg -qF 'apply_payments' "$agent_engine_root/src/omnistackai_agent_engine/studio/payments.py"; then
  printf 'R-512 payments.py must define apply_payments.\n'
  exit 1
fi

if ! rg -qF 'remove_payments' "$agent_engine_root/src/omnistackai_agent_engine/studio/payments.py"; then
  printf 'R-512 payments.py must define remove_payments.\n'
  exit 1
fi

if ! rg -qF '_handle_workspace_payments_apply' "$agent_engine_root/src/omnistackai_agent_engine/studio/server.py"; then
  printf 'R-512 server.py must route workspace payments apply.\n'
  exit 1
fi

if ! rg -qF 'ProjectPaymentsManage' "$console_root/app/studio/[projectId]/manage/page.tsx"; then
  printf 'R-512 manage page must render ProjectPaymentsManage.\n'
  exit 1
fi

# R-515 (Team / Org model — multi-member workspaces, shared projects): migration, workspaces package, member RBAC, invitations, console-web switcher & management
for required_workspace_file in \
  "$control_plane_root/migrations/000015_organizations_workspaces.up.sql" \
  "$control_plane_root/migrations/000015_organizations_workspaces.down.sql" \
  "$control_plane_root/internal/workspaces/store.go" \
  "$control_plane_root/internal/workspaces/handler.go" \
  "$control_plane_root/internal/workspaces/workspaces_test.go" \
  "$console_root/components/workspace-switcher.tsx" \
  "$console_root/components/workspace-manage.tsx" \
  "$console_root/app/api/workspaces/route.ts" \
  "$console_root/app/api/workspaces/[id]/route.ts" \
  "$console_root/app/api/workspaces/[id]/members/route.ts" \
  "$console_root/app/api/workspaces/[id]/invites/route.ts" \
  "$console_root/app/api/workspaces/invites/[token]/accept/route.ts" \
  "$console_root/app/invite/[token]/page.tsx"; do
  if [[ ! -f "$required_workspace_file" ]]; then
    printf 'Missing R-515 contract file: %s\n' "$required_workspace_file"
    exit 1
  fi
done

if ! rg -qF 'workspaces.Register' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-515 control-plane main must register workspaces routes.\n'
  exit 1
fi

if ! rg -qF 'workspace_members' "$control_plane_root/migrations/000015_organizations_workspaces.up.sql"; then
  printf 'R-515 000015_organizations_workspaces.up.sql must create workspace_members table.\n'
  exit 1
fi

if ! rg -qF 'listWorkspaces' "$console_root/lib/control-plane.ts"; then
  printf 'R-515 lib/control-plane.ts must define listWorkspaces.\n'
  exit 1
fi

if ! rg -qF 'inviteWorkspaceMember' "$console_root/lib/control-plane.ts"; then
  printf 'R-515 lib/control-plane.ts must define inviteWorkspaceMember.\n'
  exit 1
fi

if ! rg -qF 'WorkspaceSwitcher' "$console_root/components/app-shell.tsx"; then
  printf 'R-515 app-shell must render WorkspaceSwitcher.\n'
  exit 1
fi

if ! rg -qF 'WorkspaceManage' "$console_root/app/settings/page.tsx"; then
  printf 'R-515 settings page must render WorkspaceManage.\n'
  exit 1
fi

# R-516 (Email feature — SMTP / Resend integration in generated apps):
# pure Node.js standard-library socket client, Resend REST client, email templates, contact form UI, zero npm dependencies
if ! rg -qF 'EMAIL_TEMPLATES_TS' "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-516 connectors.py must define EMAIL_TEMPLATES_TS.\n'
  exit 1
fi

if ! rg -qF 'CONTACT_FORM_TSX' "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-516 connectors.py must define CONTACT_FORM_TSX.\n'
  exit 1
fi

if ! rg -qF 'welcomeEmailTemplate' "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-516 connectors.py must export welcomeEmailTemplate.\n'
  exit 1
fi

if ! rg -qF 'otpVerificationTemplate' "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-516 connectors.py must export otpVerificationTemplate.\n'
  exit 1
fi

if ! rg -qF "node:net" "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-516 SMTP client must use node:net with zero external npm dependencies.\n'
  exit 1
fi

if ! rg -qF "STARTTLS" "$agent_engine_root/src/omnistackai_agent_engine/studio/connectors.py"; then
  printf 'R-516 SMTP client must implement STARTTLS handshake.\n'
  exit 1
fi

if ! rg -qF "lib/email-templates.ts" "$control_plane_root/internal/connectors/catalog.go"; then
  printf 'R-516 catalog.go must declare lib/email-templates.ts in generated files.\n'
  exit 1
fi

if ! rg -qF "components/contact-form.tsx" "$control_plane_root/internal/connectors/catalog.go"; then
  printf 'R-516 catalog.go must declare components/contact-form.tsx in generated files.\n'
  exit 1
fi

# R-517 (Node.js backend codegen — Express/Hono alongside Python/Go):
# First-class TypeScript Node.js backend generation with Express and Hono support
if [[ ! -f "$agent_engine_root/src/omnistackai_agent_engine/codegen/backend_node.py" ]]; then
  printf 'Missing R-517 contract file: codegen/backend_node.py\n'
  exit 1
fi

if [[ ! -f "$agent_engine_root/tests/test_backend_node.py" ]]; then
  printf 'Missing R-517 contract file: tests/test_backend_node.py\n'
  exit 1
fi

if ! rg -qF 'class NodeBackendAdapter' "$agent_engine_root/src/omnistackai_agent_engine/codegen/backend_node.py"; then
  printf 'R-517 backend_node.py must define NodeBackendAdapter.\n'
  exit 1
fi

if ! rg -qF 'class ExpressBackendAdapter' "$agent_engine_root/src/omnistackai_agent_engine/codegen/backend_node.py"; then
  printf 'R-517 backend_node.py must define ExpressBackendAdapter.\n'
  exit 1
fi

if ! rg -qF 'class HonoBackendAdapter' "$agent_engine_root/src/omnistackai_agent_engine/codegen/backend_node.py"; then
  printf 'R-517 backend_node.py must define HonoBackendAdapter.\n'
  exit 1
fi

if ! rg -qF '"NodeBackendAdapter"' "$agent_engine_root/src/omnistackai_agent_engine/codegen/__init__.py"; then
  printf 'R-517 codegen/__init__.py must export NodeBackendAdapter.\n'
  exit 1
fi

if ! rg -qF 'BACKEND_NODE = "backend-node"' "$agent_engine_root/src/omnistackai_agent_engine/codegen/adapter.py"; then
  printf 'R-517 adapter.py GenerationTarget must define BACKEND_NODE.\n'
  exit 1
fi

if ! rg -qF 'NodeBackendAdapter' "$agent_engine_root/src/omnistackai_agent_engine/codegen/assembler.py"; then
  printf 'R-517 assembler.py default_registry must register NodeBackendAdapter.\n'
  exit 1
fi

if [[ ! -d "$repo_root/templates/backend-node" ]]; then
  printf 'R-517 templates/backend-node directory must exist.\n'
  exit 1
fi

# R-518 (Stabilise the core - the control-plane starts, and prompt -> build -> edit works live):
if ! rg -qF 'func newMux(' "$control_plane_root/cmd/control-plane/main.go" || [[ ! -f "$control_plane_root/cmd/control-plane/main_test.go" ]]; then
  printf 'R-518 main.go must build routes in newMux() and main_test.go must test the full route table.\n'
  exit 1
fi
if ! rg -qF '"POST /projects/{id}/opened"' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-518 the control-plane must serve POST /projects/{id}/opened.\n'
  exit 1
fi
if rg -q '"POST /projects/\{id\}/seo/(audit|suggest)"' "$control_plane_root/internal/projects/handler.go"; then
  printf 'R-518 POST seo/audit|suggest belong to internal/seo only (duplicates panic the ServeMux).\n'
  exit 1
fi
if rg -q '\bu\.name\b' "$control_plane_root/internal" "$control_plane_root/migrations"; then
  printf 'R-518 the users column is full_name, never u.name.\n'
  exit 1
fi
if ! rg -qF 'compose up -d --build --wait' "$repo_root/scripts/omnistack.sh"; then
  printf 'R-518 omnistack.sh up must build the control-plane image from source.\n'
  exit 1
fi
if [[ ! -x "$repo_root/scripts/smoke-core.sh" ]]; then
  printf 'R-518 scripts/smoke-core.sh (live core-loop smoke) must exist and be executable.\n'
  exit 1
fi
if rg -q 'diff\.(added_files|modified_files|deleted_files)' "$agent_engine_root/src"; then
  printf 'R-518 ProjectDiff exposes added()/modified()/deleted(), not *_files attributes.\n'
  exit 1
fi

# R-519 (Phase T, T-1 - template format + registry: the original stays read-only, "use" makes the user's own copy):
if [[ ! -f "$repo_root/templates/catalog/README.md" ]]; then
  printf 'R-519 templates/catalog/README.md must document the template format.\n'
  exit 1
fi
if ! rg -qF 'def instantiate_template(' "$agent_engine_root/src/omnistackai_agent_engine/studio/templates.py" \
  || ! rg -qF '"kind": "template"' "$agent_engine_root/src/omnistackai_agent_engine/studio/templates.py"; then
  printf 'R-519 studio/templates.py must instantiate templates into kind=template workspaces.\n'
  exit 1
fi
if [[ "$(rg -c '_refuse_template_workspace\(workspace_store, ws_id' "$agent_engine_root/src/omnistackai_agent_engine/studio/live_serve.py")" != "2" ]]; then
  # R-525: the third (IR edit) path now routes template projects to the code-edit agent.
  printf 'R-519 prompt builds and streamed builds must both refuse template workspaces.\n'
  exit 1
fi
if ! rg -qF '"POST /templates/{slug}/use"' "$control_plane_root/internal/templates/handler.go" \
  || ! rg -qF 'templates.Register(mux' "$control_plane_root/cmd/control-plane/main.go"; then
  printf 'R-519 the control-plane must serve the template routes.\n'
  exit 1
fi
if ! rg -qF 'CREATE TABLE IF NOT EXISTS project_templates' "$control_plane_root/migrations/000016_project_templates.up.sql"; then
  printf 'R-519 migration 000016 must create project_templates.\n'
  exit 1
fi
if [[ ! -f "$agent_engine_root/tests/fixtures/templates/corner-shop/template.json" ]]; then
  printf 'R-519 the corner-shop test fixture template must exist.\n'
  exit 1
fi

# R-520 (Phase T, T-2 - multi-app preview for template projects):
multiapp_py="$agent_engine_root/src/omnistackai_agent_engine/localrun/multiapp.py"
if ! rg -qF 'def build_multiapp_plan(' "$multiapp_py" || ! rg -qF 'start_new_session=True' "$multiapp_py" \
  || ! rg -qF 'os.killpg' "$multiapp_py"; then
  printf 'R-520 localrun/multiapp.py must plan apps and run each in its own process group.\n'
  exit 1
fi
if rg -q 'os\.environ\)' "$multiapp_py" || ! rg -qF 'def base_environment(' "$multiapp_py"; then
  printf 'R-520 template app processes must get a minimal environment, never the full Studio env.\n'
  exit 1
fi
if ! rg -qF '_start_multiapp_workspace' "$agent_engine_root/src/omnistackai_agent_engine/studio/preview.py"; then
  printf 'R-520 the preview manager must start template projects asynchronously.\n'
  exit 1
fi
if ! rg -qF 'PROJECT_MANIFEST' "$agent_engine_root/src/omnistackai_agent_engine/studio/templates.py"; then
  printf 'R-520 use-template must write omnistack.json into the project.\n'
  exit 1
fi
if ! rg -qF 'proxyMultiApp' "$repo_root/apps/console-web/app/preview/[projectId]/[[...path]]/route.ts" \
  || ! rg -qF 'MultiAppPreview' "$repo_root/apps/console-web/app/studio/studio-preview.tsx"; then
  printf 'R-520 the console must proxy and show multi-app previews.\n'
  exit 1
fi

# R-521 (generated apps run again: web compiles, previews seed, sign-up/login work, safely):
codegen_dir="$agent_engine_root/src/omnistackai_agent_engine/codegen"
if [[ ! -f "$agent_engine_root/tests/test_generated_web_app_integrity.py" ]]; then
  printf 'R-521 the generated web app integrity tests must exist.\n'
  exit 1
fi
if rg -qF 'get_db_pool' "$codegen_dir/auth_guard.py" || rg -qF 'body.role' "$codegen_dir/auth_guard.py"; then
  printf 'R-521 the generated auth router must use app.db.connect and never trust a client-sent role.\n'
  exit 1
fi
if ! rg -qF 'password_reset_not_configured' "$codegen_dir/auth_guard.py"; then
  printf 'R-521 password reset by email alone must stay refused until emailed reset links exist.\n'
  exit 1
fi
if ! rg -qF 'def _uuid_for(' "$codegen_dir/seed_sql.py"; then
  printf 'R-521 seed SQL must map labels in uuid columns to stable UUIDs.\n'
  exit 1
fi
if ! rg -qF 'SMOKE_SKIP_PREVIEW' "$repo_root/scripts/smoke-core.sh"; then
  printf 'R-521 the core smoke must check that the generated app preview loads.\n'
  exit 1
fi
if [[ "$(rg -c '^def _forgot_password_page' "$codegen_dir/nextjs.py")" != "1" ]]; then
  printf 'R-521 nextjs.py must define _forgot_password_page exactly once.\n'
  exit 1
fi

# R-523 (Phase T, T-3 - template marketplace in the console):
console_root="$repo_root/apps/console-web"
for required in "app/templates/page.tsx" "app/templates/[slug]/page.tsx" "app/api/templates/[slug]/use/route.ts" \
  "app/template-assets/[slug]/[...path]/route.ts" "components/template-use-button.tsx" "components/template-catalog.tsx"; do
  if [[ ! -f "$console_root/$required" ]]; then
    printf 'R-523 console file missing: %s\n' "$required"
    exit 1
  fi
done
if ! rg -qF 'href: "/templates"' "$console_root/components/app-nav.tsx"; then
  printf 'R-523 the primary nav must link to /templates.\n'
  exit 1
fi
if ! rg -qF 'def asset(' "$agent_engine_root/src/omnistackai_agent_engine/studio/templates.py" \
  || ! rg -qF '"GET /templates/{slug}/assets/{path...}"' "$control_plane_root/internal/templates/handler.go"; then
  printf 'R-523 template assets must be served (declared files only) through the control-plane.\n'
  exit 1
fi
if ! rg -qF 'startedFromTemplate' "$console_root/app/studio/studio-chat.tsx"; then
  printf 'R-523 the Studio must explain template projects instead of failing chat edits.\n'
  exit 1
fi

# R-525 (Phase T, T-4 - code-edit agent for template projects):
code_edit_py="$agent_engine_root/src/omnistackai_agent_engine/studio/code_edit.py"
if [[ ! -f "$code_edit_py" ]] || ! rg -qF 'async def run_code_edit(' "$code_edit_py"; then
  printf 'R-525 studio/code_edit.py must provide run_code_edit.\n'
  exit 1
fi
if rg -q '"add", "-A"\)' "$code_edit_py" || ! rg -qF '"add", "-A", "--", *paths' "$code_edit_py"; then
  printf 'R-525 code edits must stage only the touched paths, never the whole tree.\n'
  exit 1
fi
if ! rg -qF 'restore(repo, original)' "$code_edit_py"; then
  printf 'R-525 a failed code edit must restore every touched file.\n'
  exit 1
fi
if ! rg -qF '_workspace_code_edit' "$agent_engine_root/src/omnistackai_agent_engine/studio/live_serve.py"; then
  printf 'R-525 template workspace edits must route to the code-edit agent.\n'
  exit 1
fi

# R-526 (Phase T, T-6 part 1 - RideNow API, database and demo data):
ride_now_api="$repo_root/templates/catalog/_ride-now/repo/services/api"
[[ -d "$repo_root/templates/catalog/ride-now" ]] && ride_now_api="$repo_root/templates/catalog/ride-now/repo/services/api"
for required in src/index.ts src/services/dispatch.ts src/services/trips.ts src/lib/trip-state.ts src/openapi.ts \
  migrations/001_core.sql migrations/005_support.sql seed/001_demo.sql scripts/generate-seed.mjs test/workflow.test.ts; do
  if [[ ! -f "$ride_now_api/$required" ]]; then
    printf 'R-526 RideNow API file missing: %s\n' "$required"
    exit 1
  fi
done
if [[ ! -f "$agent_engine_root/tests/test_template_ride_now.py" ]]; then
  printf 'R-526 the RideNow unit tests and seed check must run in the offline suite.\n'
  exit 1
fi

# R-527 (Phase T, T-6 part 2 - RideNow rider web app, shared package, preview fixes):
ride_now_repo="$(dirname "$(dirname "$ride_now_api")")"
for required in apps/rider/app/page.tsx "apps/rider/app/(app)/ride/page.tsx" "apps/rider/app/(app)/trip/[id]/page.tsx" \
  "apps/rider/app/(app)/wallet/page.tsx" "apps/rider/app/(app)/help/[id]/page.tsx" packages/shared/src/api.ts packages/shared/src/city-map.tsx; do
  if [[ ! -f "$ride_now_repo/$required" ]]; then
    printf 'R-527 RideNow file missing: %s\n' "$required"
    exit 1
  fi
done
if ! rg -qF 'def reap_stale_processes(' "$agent_engine_root/src/omnistackai_agent_engine/localrun/multiapp.py" \
  || ! rg -qF 'signal.signal(signal.SIGTERM, _terminate)' "$agent_engine_root/src/omnistackai_agent_engine/studio/live_serve.py"; then
  printf 'R-527 template previews must not outlive a Studio restart.\n'
  exit 1
fi
if ! rg -qF 'headers.set("origin", target.origin)' "$repo_root/apps/console-web/app/preview/[projectId]/[[...path]]/route.ts"; then
  printf 'R-527 the preview proxy must present template UI requests as their own origin (Next 16 dev origins).\n'
  exit 1
fi

# R-528 (Phase T, T-6 part 3 - RideNow driver app, a PWA):
for required in apps/driver/app/page.tsx apps/driver/app/trip/page.tsx apps/driver/app/earnings/page.tsx \
  apps/driver/app/wallet/page.tsx "apps/driver/app/trips/[id]/page.tsx" apps/driver/app/account/page.tsx \
  apps/driver/app/apply/page.tsx apps/driver/app/manifest.ts apps/driver/lib/driver.tsx apps/driver/components/offer-sheet.tsx; do
  if [[ ! -f "$ride_now_repo/$required" ]]; then
    printf 'R-528 RideNow driver file missing: %s\n' "$required"
    exit 1
  fi
done
if ! rg -qF 'driverRoutes.get("/zones"' "$ride_now_api/src/routes/driver.ts" \
  || ! rg -qF 'test_every_api_path_used_by_the_apps_exists' "$agent_engine_root/tests/test_template_ride_now.py"; then
  printf 'R-528 every API path the RideNow apps call must exist, and a test must keep it that way.\n'
  exit 1
fi
if ! rg -qF 'driver payouts: one at a time' "$ride_now_api/test/workflow.test.ts"; then
  printf 'R-528 the live workflow must cover driver payouts.\n'
  exit 1
fi

# R-529 (Phase T handoff document and draft-template demo):
if [[ ! -f "$repo_root/R_&_D/OmniStackAI_Template_Marketplace_Plan_v1.md" ]] \
  || ! rg -qF '## 5. The publish checklist' "$repo_root/R_&_D/OmniStackAI_Template_Marketplace_Plan_v1.md" \
  || ! rg -qF '## 8. Demo guide' "$repo_root/R_&_D/OmniStackAI_Template_Marketplace_Plan_v1.md"; then
  printf 'R-529 the Phase T handoff document (method, publish checklist, demo guide) is required.\n'
  exit 1
fi
if [[ ! -x "$repo_root/scripts/preview-drafts.sh" ]] || ! bash -n "$repo_root/scripts/preview-drafts.sh" \
  || ! rg -qF -- '--exclude node_modules' "$repo_root/scripts/preview-drafts.sh"; then
  printf 'R-529 scripts/preview-drafts.sh must exist, parse, and never copy dependencies into a catalogue.\n'
  exit 1
fi
if [[ -d "$repo_root/templates/catalog/_ride-now" ]] && ! python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['slug']=='ride-now' and {a['id'] for a in d['apps']} >= {'rider','driver','api'}" "$repo_root/templates/catalog/_ride-now/template.json"; then
  printf 'R-529 the RideNow draft needs its template.json (slug ride-now, rider/driver/api apps).\n'
  exit 1
fi

printf 'Repository contract tests passed.\n'
