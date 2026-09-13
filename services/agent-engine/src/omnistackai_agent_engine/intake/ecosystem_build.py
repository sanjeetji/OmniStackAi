"""Opt-in ecosystem BUILD CLI (R-431): prompt -> MULTIPLE owned Git repos, one per app surface.

Deterministic (no model/network) but writes real repos to disk, so it is opt-in (never run by
`task verify`). One prompt materializes the whole business platform as owned code:

    task agent-engine:ecosystem:build -- "Create a food delivery app with restaurants and couriers"

Output directory: OMNISTACKAI_ECOSYSTEM_OUT_DIR if set, else a fresh temp directory. Each app is a
customer-owned Git repo under <out>/<slug>/, first commit authored sanjeetji <sk698166@gmail.com>.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

from .ecosystem import build_ecosystem, plan_ecosystem_from_prompt

_DEFAULT_PROMPT = "Create a food delivery app where customers order from restaurants and couriers deliver"


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    out_dir = os.environ.get("OMNISTACKAI_ECOSYSTEM_OUT_DIR", "").strip() or tempfile.mkdtemp(
        prefix="omnistackai-ecosystem-"
    )
    plan = plan_ecosystem_from_prompt(prompt, "complete")
    result = build_ecosystem(
        plan,
        out_dir,
        author_name="sanjeetji",
        author_email="sk698166@gmail.com",
        overwrite=True,
    )
    print(f"Prompt: {prompt}")
    print(f"Domain: {result.domain}  |  build scope: {result.option_id}")
    print(f"Materialized {len(result.apps)} owned app repos into:\n  {result.root_dir}\n")
    for app in result.apps:
        print(f"  - {app.app_name} [{app.surface_kind}] -> {app.target_dir}")
        print(f"      {app.file_count} files, first commit {app.commit_sha[:12]} (author: sanjeetji)")
    print("\n--- EcosystemBuildResult (JSON) ---")
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
