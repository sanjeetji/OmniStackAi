"""R-555: a prompt that names a second kind of user builds the whole ecosystem.

R-554 could assemble a planned ecosystem into one monorepo, and nothing called it. Wiring it
forces a decision: the planner is keyword-driven and confident — it plans three surfaces for
"a simple blog" and two for "a todo list app" — so always building its `complete` option would
hand someone four directories they never asked for. That is a worse failure than building one
app: a user who wanted a blog can ask for more, but a user handed four apps has to work out which
ones to delete.

The rule, recorded here because it is a product decision and not an implementation detail: an
ecosystem is built when the prompt **names a second kind of person**. Neither a customer nor an
admin counts on its own, because a single app is already a customer-facing app plus an admin
console. A courier, a merchant or a doctor does.
"""

import tempfile
from unittest import TestCase

from omnistackai_agent_engine.intake.build_app import build_ecosystem_from_plan
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt
from omnistackai_agent_engine.intake.ecosystem_intent import detect_ecosystem_intent, named_actors


class TheRuleIsASecondKindOfPerson(TestCase):
    ECOSYSTEM = (
        "a food delivery app with customers, drivers and restaurants",
        "a salon booking system for customers and staff",
        "a marketplace where vendors list products and shoppers buy them",
        "a clinic app for patients and doctors",
        "a ride hailing app for passengers and drivers",
    )
    SINGLE = (
        "a simple blog",
        "a news website where I publish articles",
        "a todo list app",
        "a website to sell my product",
        "an online store to sell my products",
        "a dashboard for admins",
        "a blog with an admin panel",
    )

    def test_a_second_party_builds_an_ecosystem(self) -> None:
        for prompt in self.ECOSYSTEM:
            with self.subTest(prompt=prompt):
                self.assertTrue(detect_ecosystem_intent(prompt).build_ecosystem)

    def test_one_kind_of_user_builds_one_app(self) -> None:
        for prompt in self.SINGLE:
            with self.subTest(prompt=prompt):
                self.assertFalse(detect_ecosystem_intent(prompt).build_ecosystem)

    def test_an_admin_alone_is_not_a_second_party(self) -> None:
        """A single app already ships an admin console, so naming one changes nothing."""
        self.assertFalse(detect_ecosystem_intent("a dashboard for admins").build_ecosystem)
        self.assertFalse(detect_ecosystem_intent("a blog with an admin panel").build_ecosystem)

    def test_a_customer_alone_is_not_a_second_party(self) -> None:
        self.assertFalse(detect_ecosystem_intent("an app for customers").build_ecosystem)

    def test_a_word_naming_the_product_is_not_a_person(self) -> None:
        """"an online store" names the thing being built, not a merchant who uses it."""
        self.assertEqual(named_actors("an online store to sell my products"), ())
        self.assertEqual(named_actors("a shop for my business"), ())

    def test_matching_is_on_whole_words(self) -> None:
        """"driven" is not a driver, and "storage" is not a store."""
        self.assertEqual(named_actors("a driven data storage tool"), ())

    def test_the_decision_is_deterministic(self) -> None:
        prompt = "a food delivery app with customers, drivers and restaurants"
        first, second = detect_ecosystem_intent(prompt), detect_ecosystem_intent(prompt)
        self.assertEqual((first.build_ecosystem, first.actors, first.reason),
                         (second.build_ecosystem, second.actors, second.reason))

    def test_it_explains_itself(self) -> None:
        """"you got four apps" needs a because, and the user sees this."""
        intent = detect_ecosystem_intent("a food delivery app with customers, drivers and restaurants")
        self.assertIn("courier", intent.reason)
        self.assertIn("merchant", intent.reason)
        self.assertIn("one shared API and database", intent.reason)

    def test_it_maps_to_the_planners_own_options(self) -> None:
        self.assertEqual(detect_ecosystem_intent("customers and drivers").option_id, "complete")
        self.assertEqual(detect_ecosystem_intent("a simple blog").option_id, "customer-only")


class AnEcosystemMaterialisesAsOneRepo(TestCase):
    PROMPT = "a food delivery app with customers, drivers and restaurants"

    def setUp(self) -> None:
        intent = detect_ecosystem_intent(self.PROMPT)
        plan = plan_ecosystem_from_prompt(self.PROMPT, intent.option_id)
        self.result = build_ecosystem_from_plan(
            plan,
            tempfile.mkdtemp() + "/eco",
            author_name="Test",
            author_email="test@example.test",
            prompt=self.PROMPT,
            reason=intent.reason,
        )

    def test_it_is_one_git_repository(self) -> None:
        """One repo, because the apps share a database — separate repos would mean the courier
        could not see the customer's order."""
        import subprocess

        count = subprocess.run(
            ["git", "-C", self.result.target_dir, "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(count, "1")

    def test_it_reports_every_app_it_built(self) -> None:
        self.assertEqual(self.result.ecosystem_apps, ("web", "merchant", "driver", "admin"))

    def test_it_reports_why(self) -> None:
        self.assertIn("alongside the people they serve", self.result.ecosystem_reason)

    def test_the_result_ir_describes_the_whole_product(self) -> None:
        """Not one surface's view: the union the shared backend was generated from."""
        roles = {role.id for role in self.result.ir.roles}
        self.assertEqual(roles, {"admin", "customer", "driver", "merchant"})

    def test_the_repository_holds_the_apps_and_one_api(self) -> None:
        from pathlib import Path

        root = Path(self.result.target_dir)
        apps = sorted(p.name for p in (root / "apps").iterdir() if p.is_dir())
        self.assertEqual(apps, ["admin", "driver", "merchant", "web"])
        self.assertTrue((root / "services" / "api").is_dir())
        self.assertEqual([p.name for p in (root / "services").iterdir() if p.is_dir()], ["api"])

    def test_it_carries_one_brand_for_the_whole_product(self) -> None:
        from pathlib import Path

        self.assertTrue((Path(self.result.target_dir) / "brand.json").is_file())
