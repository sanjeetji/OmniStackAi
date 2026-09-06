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
bash "$repo_root/scripts/control-plane.sh" lint
bash "$repo_root/scripts/control-plane.sh" test
bash "$repo_root/scripts/control-plane.sh" build
bash "$repo_root/scripts/agent-engine.sh" lint
bash "$repo_root/scripts/agent-engine.sh" test

printf 'Stage 0 verification passed.\n'
