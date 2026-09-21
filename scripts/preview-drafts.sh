#!/usr/bin/env bash
# Show draft templates in the marketplace, for demos and live testing before they are published.
#
# Drafts live in templates/catalog/_<slug>/ (the catalogue ignores names starting with "_").
# This copies every published template plus every draft that has a template.json into a
# separate catalogue (drafts lose their "_"), then restarts the platform pointed at it.
# The repository is not changed. Run ./scripts/omnistack.sh restart to go back to the
# normal catalogue.
#
# usage: ./scripts/preview-drafts.sh            build the catalogue and restart the platform
#        ./scripts/preview-drafts.sh --no-restart  only build it and print its path
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$repo_root/templates/catalog"
tmp="${TMPDIR:-/tmp}"
target="${OMNISTACKAI_DRAFT_CATALOG:-${tmp%/}/omnistackai-draft-catalog}"
target="${target%/}"

rm -rf "$target"
mkdir -p "$target"
listed=()
for dir in "$source_dir"/*/; do
  [[ -d "$dir" && -f "$dir/template.json" ]] || continue
  name="$(basename "$dir")"
  slug="${name#_}"
  # Same exclusions the template validator enforces: no dependencies or build output.
  rsync -a --exclude node_modules --exclude .next --exclude .turbo --exclude __pycache__ \
    --exclude .env --exclude '*.tsbuildinfo' "$dir" "$target/$slug/"
  [[ "$name" == _* ]] && listed+=("$slug (draft)") || listed+=("$slug")
done

printf 'Template catalogue: %s\n' "$target"
printf '  %s\n' "${listed[@]:-none}"
if [[ "${1:-}" == "--no-restart" ]]; then
  exit 0
fi
OMNISTACKAI_TEMPLATE_CATALOG="$target" exec "$repo_root/scripts/omnistack.sh" restart
