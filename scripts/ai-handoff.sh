#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
handoff_file="$repo_root/.ai/HANDOFF.md"

for heading in '# Current Handoff' '## Completed' '## Verification' \
  '## Blockers and risks' '## Next action' '## Next command'; do
  if ! rg -qF "$heading" "$handoff_file"; then
    printf 'Missing handoff section: %s\n' "$heading"
    exit 1
  fi
done

bash "$repo_root/scripts/ai-status.sh"
printf '\n'
cat "$handoff_file"

