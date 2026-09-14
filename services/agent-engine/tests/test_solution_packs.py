"""R-434: immutable, versioned baseline Solution Pack registry."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from io import StringIO
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, validate_ir
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.projectplan import build_project_plan
from omnistackai_agent_engine.solution_packs import (
    BASELINE_SOLUTION_PACKS,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    MINIMAL_BLOG_PACK,
    RIDESHARE_FAVOURITES_PACK,
    SolutionPack,
    SolutionPackError,
    SolutionPackRegistry,
    canonical_ir_digest,
)
from omnistackai_agent_engine.solution_packs.cli import main as solution_packs_main


class BaselinePackTests(TestCase):
    def test_exact_baseline_packs_are_registered_and_frozen(self) -> None:
        self.assertEqual(
            {pack.pack_id for pack in BASELINE_SOLUTION_PACKS},
            {"minimal-blog", "rideshare-favourites"},
        )
        self.assertEqual(DEFAULT_SOLUTION_PACK_REGISTRY.packs, BASELINE_SOLUTION_PACKS)
        self.assertEqual(MINIMAL_BLOG_PACK.version, "1.0.0")
        self.assertEqual(RIDESHARE_FAVOURITES_PACK.version, "1.0.0")
        with self.assertRaises(FrozenInstanceError):
            MINIMAL_BLOG_PACK.version = "2.0.0"  # type: ignore[misc]

    def test_pins_load_fresh_valid_irs_with_exact_targets_and_verify_plans(self) -> None:
        for pack in BASELINE_SOLUTION_PACKS:
            first = DEFAULT_SOLUTION_PACK_REGISTRY.load_ir(pack.pack_id, pack.version)
            second = DEFAULT_SOLUTION_PACK_REGISTRY.load_ir(pack.pack_id, pack.version)
            self.assertIsInstance(first, ApplicationIR)
            self.assertIsNot(first, second)
            self.assertFalse(has_errors(validate_ir(first)))
            self.assertEqual(canonical_ir_digest(first), pack.ir_sha256)
            plan = build_project_plan(first)
            self.assertEqual(tuple(app.target for app in plan.apps), pack.targets)
            self.assertTrue(all(app.verify is not None for app in plan.apps))

    def test_descriptors_are_json_safe_and_deterministic(self) -> None:
        first = DEFAULT_SOLUTION_PACK_REGISTRY.to_dict()
        second = DEFAULT_SOLUTION_PACK_REGISTRY.to_dict()
        self.assertEqual(first, second)
        blob = json.dumps(first, sort_keys=True)
        self.assertIn('"ir_sha256"', blob)
        self.assertNotIn("secret", blob.lower())


class SelectionTests(TestCase):
    def test_exact_domain_and_capability_selection(self) -> None:
        registry = DEFAULT_SOLUTION_PACK_REGISTRY
        self.assertEqual(registry.select("blog-cms"), MINIMAL_BLOG_PACK)
        self.assertEqual(
            registry.select("rideshare", required_capabilities=("favourites",)),
            RIDESHARE_FAVOURITES_PACK,
        )
        self.assertIsNone(registry.select("healthcare-clinic"))
        self.assertIsNone(
            registry.select("rideshare", required_capabilities=("subscriptions",))
        )
        self.assertIsNone(registry.get("does-not-exist"))

    def test_newest_semantic_version_wins_deterministically(self) -> None:
        newer = replace(MINIMAL_BLOG_PACK, version="2.0.0")
        registry = SolutionPackRegistry((*BASELINE_SOLUTION_PACKS, newer))
        self.assertEqual(registry.get("minimal-blog"), newer)
        self.assertEqual(registry.select("blog-cms"), newer)
        self.assertEqual(registry.to_dict(), registry.to_dict())


class FailClosedValidationTests(TestCase):
    def test_duplicate_version_missing_example_and_pin_drift_are_rejected(self) -> None:
        with self.assertRaisesRegex(SolutionPackError, "duplicate"):
            SolutionPackRegistry((MINIMAL_BLOG_PACK, MINIMAL_BLOG_PACK))
        with self.assertRaisesRegex(SolutionPackError, "unknown example"):
            SolutionPackRegistry(
                (replace(MINIMAL_BLOG_PACK, example_ir_ref="missing-example"),)
            )
        with self.assertRaisesRegex(SolutionPackError, "digest"):
            SolutionPackRegistry((replace(MINIMAL_BLOG_PACK, ir_sha256="0" * 64),))
        with self.assertRaisesRegex(SolutionPackError, "targets"):
            SolutionPackRegistry(
                (replace(MINIMAL_BLOG_PACK, targets=("nextjs-web",)),)
            )

    def test_malformed_descriptor_values_are_rejected(self) -> None:
        cases = (
            {"pack_id": "Bad ID"},
            {"version": "latest"},
            {"domains": ()},
            {"capabilities": ("web", "web")},
            {"ir_sha256": "abc"},
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(SolutionPackError):
                replace(MINIMAL_BLOG_PACK, **changes)


class CliTests(TestCase):
    def test_cli_lists_and_selects_without_live_work(self) -> None:
        listed = StringIO()
        self.assertEqual(solution_packs_main([], stdout=listed), 0)
        list_payload = json.loads(listed.getvalue())
        self.assertEqual(len(list_payload["packs"]), 2)

        selected = StringIO()
        self.assertEqual(
            solution_packs_main(
                ["--domain", "rideshare", "--capability", "favourites"],
                stdout=selected,
            ),
            0,
        )
        selection_payload = json.loads(selected.getvalue())
        self.assertEqual(selection_payload["selection"]["pack_id"], "rideshare-favourites")
        self.assertEqual(selection_payload["selection"]["version"], "1.0.0")


if __name__ == "__main__":
    import unittest

    unittest.main()
