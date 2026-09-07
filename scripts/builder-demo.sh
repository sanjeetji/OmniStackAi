#!/usr/bin/env bash
set -euo pipefail

# Generate a real customer app from an example Application IR into a Git repo and show the result.
# Usage: bash scripts/builder-demo.sh [example-name] [output-dir]
#   example-name: rideshare-favourites (default) | minimal-blog
#   output-dir:   where to write the generated repo (default: a fresh temp dir)

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
source_root="$repo_root/services/agent-engine/src"
example="${1:-rideshare-favourites}"
out_dir="${2:-$(mktemp -d -t omnistackai-demo-XXXXXX)}"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }

PYTHONPATH="$source_root" python3 - "$example" "$out_dir" <<'PY'
import sys
from pathlib import Path

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import assemble_project
from omnistackai_agent_engine.git_service import create_repository
from omnistackai_agent_engine.verify import verify_plans_for_ir

name, out_dir = sys.argv[1], sys.argv[2]
ir = example_ir(name)

project = assemble_project(ir)
result = create_repository(
    project, out_dir, author_name="sanjeetji", author_email="sk698166@gmail.com",
    commit_message=f"Initial commit: {ir.name}", overwrite=True,
)

print(f"\n=== OmniStackAI builder demo — '{ir.name}' ===")
print(ir.description)
print(f"\nGenerated {result.file_count} files into an owned Git repo at:\n  {result.target_dir}")
print(f"First commit: {result.commit_sha[:12]}  (author: sanjeetji)")

print("\n--- File tree ---")
root = Path(result.target_dir)
for path in sorted(p for p in root.rglob('*') if p.is_file() and '.git/' not in str(p.relative_to(root))):
    print(f"  {path.relative_to(root)}")

migration = root / "services/api/migrations/0001_init.sql"
if migration.exists():
    print("\n--- Generated PostgreSQL schema (services/api/migrations/0001_init.sql) ---")
    print(migration.read_text())

print("--- Verify plans the generated code is engineered to pass ---")
for plan in verify_plans_for_ir(ir):
    gates = ", ".join(k.value for k in plan.gates())
    print(f"  {plan.app_dir} ({plan.target}): {gates}")

print(f"\nOpen the repo:  cd {result.target_dir} && git log --stat")
print("Run it (needs the toolchain + internet on a real machine):")
print("  cd apps/web && pnpm install && pnpm dev        # -> http://127.0.0.1:3000")
print("  cd services/api && (uvicorn app.main:app  |  go run .)")
PY
