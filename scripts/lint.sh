#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

bash -n "$repo_root"/scripts/*.sh
node -e 'JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"))' "$repo_root/package.json"

if rg --files "$repo_root" -g '*.md' -g '*.yaml' -g '*.yml' -g '*.json' -g '*.sh' \
  -g '!R_&_D/**' | while IFS= read -r file_path; do
    if [[ -s "$file_path" ]] && [[ "$(tail -c 1 "$file_path" | wc -l | tr -d ' ')" != "1" ]]; then
      printf 'Missing final newline: %s\n' "$file_path"
      exit 1
    fi
  done; then
  :
else
  exit 1
fi

printf 'Lint passed.\n'

