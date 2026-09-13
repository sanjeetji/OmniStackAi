"""R-431: Scope -> Application IRs (materialize a multi-app ecosystem from one prompt).

Every produced IR must be validate_ir-clean, the plan must match the chosen build-scope option, the derived
CRUD endpoints must WIRE to real repositories (not 501 stubs), and building must yield one owned repo per
surface. Deterministic and offline (no model/network), so it runs under `task verify`.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.application_ir import validate_ir
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.codegen import NextjsWebAdapter
from omnistackai_agent_engine.codegen.route_wiring import Op, wire_endpoint
from omnistackai_agent_engine.intake import (
    DOMAIN_ENTITIES,
    DOMAIN_LIBRARY,
    build_ecosystem,
    plan_ecosystem,
    plan_ecosystem_from_prompt,
    propose_ecosystem,
    surface_to_ir,
)


class EcosystemPlanTests(unittest.TestCase):
    def test_every_domain_produces_valid_irs(self) -> None:
        # Planning each domain's example (Complete scope) builds one clean IR per surface.
        for entry in DOMAIN_LIBRARY:
            plan = plan_ecosystem_from_prompt(entry.example_prompt, "complete")
            self.assertTrue(plan.apps, f"{entry.domain} planned no apps")
            for app in plan.apps:
                issues = validate_ir(app.ir)
                self.assertFalse(
                    has_errors(issues),
                    f"{entry.domain}/{app.ir.name} invalid: {[i.message for i in issues if i.severity.name == 'ERROR']}",
                )

    def test_unknown_prompt_still_plans_a_valid_custom_app(self) -> None:
        plan = plan_ecosystem_from_prompt("zxqw nondescript widget thing", "complete")
        self.assertEqual(plan.domain, "custom-application")
        self.assertTrue(plan.apps)
        for app in plan.apps:
            self.assertFalse(has_errors(validate_ir(app.ir)))

    def test_complete_vs_customer_only_app_counts(self) -> None:
        proposal = propose_ecosystem("food delivery app with restaurants and couriers")
        complete = plan_ecosystem(proposal, "complete")
        customer_only = plan_ecosystem(proposal, "customer-only")
        self.assertEqual(len(complete.apps), len(proposal.surfaces))
        customer_surfaces = [s for s in proposal.surfaces if s.audience == "customer"]
        self.assertEqual(len(customer_only.apps), len(customer_surfaces))
        self.assertLess(len(customer_only.apps), len(complete.apps))

    def test_food_delivery_yields_the_expected_apps(self) -> None:
        plan = plan_ecosystem_from_prompt(
            "Create a food delivery app where customers order from restaurants and couriers deliver",
            "complete",
        )
        self.assertEqual(plan.domain, "food-delivery")
        names = {a.ir.name for a in plan.apps}
        self.assertIn("Customer Ordering App", names)
        self.assertIn("Merchant Portal", names)
        self.assertIn("Super-Admin Dashboard", names)
        # Each app carries the curated food-delivery entities (normalize_ir may reorder them).
        for app in plan.apps:
            self.assertEqual(
                {e.name for e in app.ir.entities},
                {e.name for e in DOMAIN_ENTITIES["food-delivery"]},
            )

    def test_derived_crud_endpoints_wire_to_repositories(self) -> None:
        # The derived endpoints must resolve to real CRUD ops (not stay unwired -> 501).
        ir = surface_to_ir(
            propose_ecosystem("food delivery app with restaurants"),
            propose_ecosystem("food delivery app with restaurants").surfaces[0],
        )
        repo_entities = frozenset(e.name for e in ir.entities)
        fk_by_entity = {
            e.name: tuple(r.name for r in e.relations)
            for e in ir.entities
        }
        ops = set()
        for api in ir.apis:
            wiring = wire_endpoint(api, repo_entities, fk_by_entity)
            if wiring is not None:
                ops.add(wiring.op)
        for expected in (Op.LIST, Op.GET, Op.CREATE, Op.UPDATE, Op.DELETE):
            self.assertIn(expected, ops, f"{expected} endpoint did not wire")
        self.assertIn(Op.LIST_BY, ops, "sub-collection LIST_BY did not wire")

    def test_plan_is_deterministic(self) -> None:
        prompt = "Create a food delivery app with restaurants, couriers and an admin console"
        first = plan_ecosystem_from_prompt(prompt, "complete").to_dict()
        second = plan_ecosystem_from_prompt(prompt, "complete").to_dict()
        self.assertEqual(first, second)

    def test_plan_is_json_serializable(self) -> None:
        plan = plan_ecosystem_from_prompt("A booking app for appointments with providers", "complete")
        blob = json.dumps(plan.to_dict(), sort_keys=True)
        self.assertIn(plan.domain, blob)

    def test_fk_and_multi_subcollection_screens_avoid_compile_bug_classes(self) -> None:
        # A food-delivery surface exercises the FK-relation editor (menu_item/order -> restaurant), a
        # parent list with TWO sub-collections (Restaurant -> MenuItem, Order), and a filterable child
        # (MenuItem.available). These paths were never generated by minimal-blog/rideshare, and each
        # exposed a generator compile bug (R-431). Guard them offline (no tsc needed).
        proposal = propose_ecosystem("food delivery app where customers order from restaurants and couriers deliver")
        parent_surface = proposal.surfaces[0]  # Customer Ordering App (renders the Restaurant parent list)
        ir = surface_to_ir(proposal, parent_surface)
        project = NextjsWebAdapter().generate(ir)
        tsx = {f.path: f.content for f in project.files() if f.path.endswith((".tsx", ".ts"))}
        joined = "\n".join(tsx.values())
        # over-braced arrow handlers (FK <select> onChange) must not regress
        self.assertNotRegex(joined, r"=>\s*\{\{")
        # single-brace object-literal inline styles (child bool badge) must not regress
        self.assertNotRegex(joined, r"style=\{ [A-Za-z_$][\w$]*\s*:")
        # FK entities must expose the scalar `<relation>_id` column the editor/API use
        self.assertIn("restaurant_id?: string;", tsx["lib/types.ts"])
        # a parent list with 2+ sub-collections wraps its search+filter controls in a fragment (one root)
        restaurant_list = next((c for p, c in tsx.items() if p.endswith("restaurant_list/page.tsx")), "")
        self.assertIn("<>", restaurant_list)


class EcosystemBuildTests(unittest.TestCase):
    def test_build_materializes_one_repo_per_surface(self) -> None:
        plan = plan_ecosystem_from_prompt(
            "Create a food delivery app where customers order from restaurants and couriers deliver",
            "complete",
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = build_ecosystem(
                plan, tmp, author_name="sanjeetji", author_email="sk698166@gmail.com"
            )
            self.assertEqual(len(result.apps), len(plan.apps))
            slugs = [a.slug for a in result.apps]
            self.assertEqual(len(slugs), len(set(slugs)), "app slugs must be unique")
            for built in result.apps:
                repo = Path(built.target_dir)
                self.assertTrue((repo / "apps" / "web" / "package.json").is_file(), f"{built.slug} web app missing")
                self.assertTrue((repo / ".git").is_dir(), f"{built.slug} is not a git repo")
                self.assertGreater(built.file_count, 0)
                self.assertTrue(built.commit_sha)


if __name__ == "__main__":
    unittest.main()
