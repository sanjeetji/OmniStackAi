#!/usr/bin/env bash
# PC-122: build the benchmark prompts end to end and score them (build, runs, API, pages, completeness,
# designed pages), with screenshots, compared with the previous run. Calls real models (free tiers and
# local Ollama by default), so it is opt-in: never run by `task verify`. Needs the platform's Postgres
# running (./scripts/omnistack.sh up) for previews.
#
#   scripts/benchmark.sh                       # the quick set (8 prompts)
#   scripts/benchmark.sh --set full --design   # all 40, pages designed by the model
#   scripts/benchmark.sh --only clinic,blog
#   scripts/benchmark.sh --list
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python="python3"
[ -x "$HOME/.local/bin/python3" ] && python="$HOME/.local/bin/python3"
PYTHONPATH="$repo_root/services/agent-engine/src" exec "$python" -m omnistackai_agent_engine.benchmark "$@"
