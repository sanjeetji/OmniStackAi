"""R-435: exact-compatible Solution Pack recommendations in ecosystem planning."""

from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.intake import (
    DOMAIN_LIBRARY,
    plan_ecosystem,
    plan_ecosystem_from_prompt,
    propose_ecosystem,
    surface_to_ir,
)
from omnistackai_agent_engine.intake.ecosystem_plan import main as ecosystem_plan_main
from omnistackai_agent_engine.solution_packs import (
    DEFAULT_SOLUTION_PACK_REGISTRY,
    MINIMAL_BLOG_PACK,
    RIDESHARE_FAVOURITES_PACK,
    SolutionPackError,
    SolutionPackRecommendation,
)


def _example_prompt(domain: str) -> str:
    return next(entry.example_prompt for entry in DOMAIN_LIBRARY if entry.domain == domain)


class TargetAwareRegistryTests(TestCase):
    def test_target_compatibility_is_required_without_breaking_capability_selection(self) -> None:
        registry = DEFAULT_SOLUTION_PACK_REGISTRY
        self.assertEqual(
            registry.select(
                "blog-cms",
                required_targets=("nextjs-web", "backend-python"),
            ),
            MINIMAL_BLOG_PACK,
        )
        self.assertEqual(
            registry.select(
                "rideshare",
                required_capabilities=("favourites",),
                required_targets=("nextjs-web", "backend-go"),
            ),
            RIDESHARE_FAVOURITES_PACK,
        )
        self.assertIsNone(
            registry.select(
                "rideshare",
                required_targets=("nextjs-web", "backend-python"),
            )
        )

    def test_recommendation_is_frozen_canonical_and_json_safe(self) -> None:
        recommendation = DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
            "rideshare",
            required_capabilities=("web", "favourites"),
            required_targets=("nextjs-web", "backend-go"),
        )
        self.assertEqual(
            recommendation.required_capabilities,
            ("favourites", "web"),
        )
        self.assertEqual(
            recommendation.required_targets,
            ("backend-go", "nextjs-web"),
        )
        payload = recommendation.to_dict()
        self.assertEqual(payload["status"], "selected")
        self.assertEqual(payload["selection"]["pack_id"], "rideshare-favourites")
        self.assertEqual(payload["selection"]["version"], "1.0.0")
        self.assertEqual(payload["selection"]["ir_sha256"], RIDESHARE_FAVOURITES_PACK.ir_sha256)
        self.assertEqual(json.dumps(payload, sort_keys=True), json.dumps(recommendation.to_dict(), sort_keys=True))
        with self.assertRaises(FrozenInstanceError):
            recommendation.domain = "blog-cms"  # type: ignore[misc]

    def test_public_recommendation_rejects_an_incompatible_selection(self) -> None:
        with self.assertRaisesRegex(SolutionPackError, "incompatible"):
            SolutionPackRecommendation(
                domain="rideshare",
                required_capabilities=(),
                required_targets=("backend-python", "nextjs-web"),
                selection=RIDESHARE_FAVOURITES_PACK,
            )


class EcosystemRecommendationTests(TestCase):
    def test_blog_plan_recommends_the_exact_python_baseline(self) -> None:
        plan = plan_ecosystem_from_prompt(_example_prompt("blog-cms"))
        recommendation = plan.pack_recommendation
        self.assertEqual(recommendation.domain, "blog-cms")
        self.assertEqual(recommendation.required_capabilities, ())
        self.assertEqual(recommendation.required_targets, ("backend-python", "nextjs-web"))
        self.assertEqual(recommendation.selection, MINIMAL_BLOG_PACK)
        self.assertEqual(
            plan.to_dict()["solution_pack_recommendation"]["selection"]["pack_id"],
            "minimal-blog",
        )

    def test_rideshare_plan_reports_no_match_for_its_python_backend(self) -> None:
        plan = plan_ecosystem_from_prompt(_example_prompt("rideshare"))
        recommendation = plan.pack_recommendation
        self.assertEqual(recommendation.required_targets, ("backend-python", "nextjs-web"))
        self.assertIsNone(recommendation.selection)
        self.assertEqual(recommendation.to_dict()["status"], "no-exact-match")
        self.assertIsNone(
            plan.to_dict()["solution_pack_recommendation"]["selection"]
        )

    def test_unknown_domain_reports_no_match_without_fabricating_capabilities(self) -> None:
        plan = plan_ecosystem_from_prompt("zxqw nondescript widget thing")
        recommendation = plan.pack_recommendation
        self.assertEqual(recommendation.domain, "custom-application")
        self.assertEqual(recommendation.required_capabilities, ())
        self.assertIsNone(recommendation.selection)

    def test_recommendation_is_additive_to_the_existing_surface_irs(self) -> None:
        proposal = propose_ecosystem(_example_prompt("blog-cms"))
        plan = plan_ecosystem(proposal)
        expected = tuple(surface_to_ir(proposal, surface) for surface in proposal.surfaces)
        self.assertEqual(tuple(app.ir for app in plan.apps), expected)

    def test_plan_cli_exposes_selected_pack_and_no_match(self) -> None:
        for domain, expected_line in (
            ("blog-cms", "Solution Pack: minimal-blog@1.0.0"),
            ("rideshare", "Solution Pack: no exact compatible pack"),
        ):
            output = StringIO()
            with patch.object(sys, "argv", ["ecosystem-plan", _example_prompt(domain)]):
                with redirect_stdout(output):
                    ecosystem_plan_main()
            rendered = output.getvalue()
            self.assertIn(expected_line, rendered)
            self.assertIn('"solution_pack_recommendation"', rendered)


if __name__ == "__main__":
    import unittest

    unittest.main()
