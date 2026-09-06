#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

bash "$repo_root/scripts/doctor.sh"
bash "$repo_root/scripts/lint.sh"
bash "$repo_root/scripts/test.sh"
bash "$repo_root/scripts/env-check.sh"
bash "$repo_root/scripts/security-quick.sh"
bash "$repo_root/scripts/db.sh" config
bash "$repo_root/scripts/ollama.sh" config

printf 'Stage 0 verification passed.\n'
