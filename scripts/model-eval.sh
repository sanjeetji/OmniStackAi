#!/usr/bin/env bash
# PC-085: score every configured model provider on the platform's own jobs and write the scorecard
# builds route by. Calls real models (free tiers and local Ollama), so it is opt-in: never run by
# `task verify`.
#
#   scripts/model-eval.sh                    # every configured provider, plan + code, once
#   scripts/model-eval.sh --only groq        # re-score one provider; the others keep their scores
#   scripts/model-eval.sh --tasks plan --runs 2
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
PYTHONPATH="$repo_root/services/agent-engine/src" exec python3 -m omnistackai_agent_engine.model_gateway.evals "$@"
