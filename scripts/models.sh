#!/usr/bin/env bash
# PC-126: which model does which job (plans, page design), in what order, and which providers are out
# right now (a spent free quota, a limit, an outage) and when they are back. Never prints a key.
#
#   scripts/models.sh            # the routing
#   scripts/models.sh --clear    # forget every mark (after adding credit or a new key)
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python="python3"
[ -x "$HOME/.local/bin/python3" ] && python="$HOME/.local/bin/python3"
PYTHONPATH="$repo_root/services/agent-engine/src" exec "$python" -m omnistackai_agent_engine.model_gateway.routing "$@"
