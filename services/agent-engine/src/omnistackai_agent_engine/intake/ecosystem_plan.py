"""Deterministic ecosystem PLAN CLI (R-431, R-435): prompt -> IRs plus pack recommendation.

No model, no network, writes nothing to disk — it just shows the multi-app plan:

    task agent-engine:ecosystem:plan -- "Create a food delivery app with restaurants and couriers"

It prints the exact-compatible Solution Pack recommendation, then each selected surface's app name, entities,
and derived API/screen counts plus the full EcosystemPlan JSON. Use `task agent-engine:ecosystem:build` to
materialize the unchanged plan IRs as owned repos; R-435 does not apply the recommended pack.
"""

from __future__ import annotations

import json
import sys

from .ecosystem import plan_ecosystem_from_prompt

_DEFAULT_PROMPT = "Create a food delivery app where customers order from restaurants and couriers deliver"


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    plan = plan_ecosystem_from_prompt(prompt, "complete")
    print(f"Prompt: {prompt}")
    print(f"Domain: {plan.domain}  |  build scope: {plan.option_id}  |  apps: {len(plan.apps)}")
    selected_pack = plan.pack_recommendation.selection
    if selected_pack is None:
        print("Solution Pack: no exact compatible pack")
    else:
        print(f"Solution Pack: {selected_pack.pack_id}@{selected_pack.version}")
    print("\nEcosystem apps (each becomes its own owned repo):")
    for app in plan.apps:
        print(
            f"  - {app.ir.name} [{app.surface.audience}] "
            f"— {len(app.ir.entities)} entities, {len(app.ir.apis)} APIs, {len(app.ir.screens)} screens"
        )
        print(f"      entities: {', '.join(e.name for e in app.ir.entities)}")
    print("\n--- EcosystemPlan (JSON) ---")
    print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
