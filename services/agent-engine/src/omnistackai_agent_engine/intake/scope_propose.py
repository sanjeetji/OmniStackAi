"""Deterministic Ecosystem Scope Compiler CLI (R-430).

Prints the proposed multi-app ecosystem for a business prompt as JSON. Fully deterministic — no model,
no network — so it is safe to run anywhere:

    task agent-engine:scope:propose -- "Create a food delivery app with restaurants and couriers"

It classifies the domain, then proposes the actors, app surfaces, and build-scope options (Complete
Business Platform / Customer Experience Only / Custom) plus up to 3 high-materiality questions.
"""

from __future__ import annotations

import json
import sys

from .scope_compiler import propose_ecosystem

_DEFAULT_PROMPT = "Create a food delivery app where customers order from restaurants and couriers deliver"


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    proposal = propose_ecosystem(prompt)
    print(f"Prompt: {prompt}")
    print(f"Domain: {proposal.domain}  (confidence {proposal.domain_confidence})")
    print(f"Business model: {proposal.business_model}")
    if proposal.matched_keywords:
        print(f"Matched keywords: {', '.join(proposal.matched_keywords)}")
    print("\nProposed ecosystem (app surfaces):")
    for surface in proposal.surfaces:
        print(f"  - [{surface.audience}] {surface.name} ({surface.actor}): {surface.description}")
    print("\nBuild-scope options:")
    for option in proposal.options:
        star = " (recommended)" if option.recommended else ""
        names = ", ".join(s.name for s in option.surfaces)
        print(f"  - {option.label}{star}: {names}")
    if proposal.questions:
        print("\nClarifying questions (at most 3):")
        for question in proposal.questions:
            print(f"  - {question}")
    print("\n--- ScopeProposal (JSON) ---")
    print(json.dumps(proposal.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
