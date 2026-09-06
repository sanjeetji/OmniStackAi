#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo_root"

pnpm install --offline --frozen-lockfile
(
  cd "$repo_root/services/control-plane"
  go mod download
)
printf 'Bootstrap completed without external services or cloud resources.\n'
