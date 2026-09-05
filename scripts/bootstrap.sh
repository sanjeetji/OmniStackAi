#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo_root"

pnpm install --offline --frozen-lockfile
printf 'Bootstrap completed without external services or cloud resources.\n'

