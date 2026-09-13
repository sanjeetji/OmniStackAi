"""R-430: deterministic Ecosystem Scope Compiler.

The Scope Compiler turns a plain-English business prompt into a structured, framework-neutral
ScopeProposal (detected domain + actors + multi-surface ecosystem + build-scope options + <=3
materiality questions). Classification is a deterministic curated keyword heuristic: no model, no
network, byte-identical for equal input, so it runs under `task verify`.
"""

from __future__ import annotations

import json
import unittest

from omnistackai_agent_engine.intake import (
    DOMAIN_LIBRARY,
    Actor,
    AppSurface,
    ScopeOption,
    ScopeProposal,
    classify_domain,
    propose_ecosystem,
)


class ScopeCompilerTests(unittest.TestCase):
    def test_food_delivery_detects_full_ecosystem(self) -> None:
        proposal = propose_ecosystem("Create a food delivery app where users order from restaurants")
        self.assertEqual(proposal.domain, "food-delivery")
        actor_names = {a.name for a in proposal.actors}
        # A food-delivery marketplace has more than a single customer actor.
        self.assertIn("Merchant", actor_names)
        self.assertIn("Driver", actor_names)
        self.assertIn("Admin", actor_names)
        self.assertGreaterEqual(len(proposal.surfaces), 3)
        self.assertTrue(proposal.matched_keywords, "expected at least one matched keyword")

    def test_rideshare_and_blog_classify_distinctly(self) -> None:
        self.assertEqual(
            propose_ecosystem("A rideshare app connecting riders with drivers for trips").domain,
            "rideshare",
        )
        self.assertEqual(
            propose_ecosystem("A blog CMS where authors publish articles and readers comment").domain,
            "blog-cms",
        )

    def test_unknown_prompt_falls_back_to_custom_application(self) -> None:
        proposal = propose_ecosystem("Some entirely nondescript zxqw widget thing")
        self.assertEqual(proposal.domain, "custom-application")
        self.assertEqual(proposal.matched_keywords, ())
        # The fallback is still a usable single-app ecosystem, not empty.
        self.assertGreaterEqual(len(proposal.surfaces), 1)
        self.assertTrue(any(o.recommended for o in proposal.options))

    def test_complete_option_is_recommended_and_carries_all_surfaces(self) -> None:
        proposal = propose_ecosystem("food delivery marketplace with restaurants and couriers")
        complete = next(o for o in proposal.options if o.id == "complete")
        self.assertTrue(complete.recommended)
        self.assertEqual(len(complete.surfaces), len(proposal.surfaces))

    def test_customer_only_option_has_only_customer_surfaces(self) -> None:
        proposal = propose_ecosystem("food delivery app with restaurants and drivers")
        customer_only = next(o for o in proposal.options if o.id == "customer-only")
        self.assertTrue(customer_only.surfaces, "customer-only should not be empty")
        self.assertTrue(all(s.audience == "customer" for s in customer_only.surfaces))
        # It must be a strict subset (the platform also has operator surfaces here).
        self.assertLess(len(customer_only.surfaces), len(proposal.surfaces))

    def test_at_most_three_materiality_questions(self) -> None:
        for entry in DOMAIN_LIBRARY:
            proposal = propose_ecosystem(entry.example_prompt)
            self.assertLessEqual(len(proposal.questions), 3, f"{entry.domain} asked >3 questions")

    def test_deterministic_and_pure(self) -> None:
        prompt = "Create a food delivery app with restaurants, couriers and an admin console"
        first = propose_ecosystem(prompt).to_dict()
        second = propose_ecosystem(prompt).to_dict()
        self.assertEqual(first, second)

    def test_proposal_is_json_serializable(self) -> None:
        proposal = propose_ecosystem("A healthcare clinic booking app for patients and doctors")
        blob = json.dumps(proposal.to_dict(), sort_keys=True)
        self.assertIn(proposal.domain, blob)
        # round-trips through JSON without loss of the top-level shape
        restored = json.loads(blob)
        self.assertEqual(restored["domain"], proposal.domain)
        self.assertIn("options", restored)
        self.assertIn("surfaces", restored)

    def test_classify_domain_returns_match_or_none(self) -> None:
        match = classify_domain("food delivery app with restaurants and drivers")
        self.assertIsNotNone(match)
        self.assertEqual(match.domain, "food-delivery")
        self.assertGreater(match.score, 0)
        self.assertIsNone(classify_domain("zxqw nondescript widget"))

    def test_every_domain_classifies_its_own_example(self) -> None:
        for entry in DOMAIN_LIBRARY:
            match = classify_domain(entry.example_prompt)
            self.assertIsNotNone(match, f"{entry.domain} example did not classify")
            self.assertEqual(match.domain, entry.domain, f"{entry.domain} example misclassified")

    def test_public_types_are_exported(self) -> None:
        # dataclasses used by callers/UI must be importable from the package root.
        self.assertTrue(issubclass(ScopeProposal, object))
        self.assertTrue(issubclass(ScopeOption, object))
        self.assertTrue(issubclass(AppSurface, object))
        self.assertTrue(issubclass(Actor, object))


if __name__ == "__main__":
    unittest.main()
