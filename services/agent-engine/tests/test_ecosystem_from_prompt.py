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


class BothBuildPathsTakeTheSameBranch(TestCase):
    """R-555: the console streams its builds, so it calls `build_app_from_prompt_stream`.

    Wiring only the non-streaming twin left the product on the single-app branch while every
    offline test passed — they called the function that had been wired, not the one the console
    uses. A live run through the console exposed it in one attempt. These tests exist so the two
    paths cannot drift apart again.
    """

    PROMPT = "a food delivery app with customers, drivers and restaurants"

    def _stream(self, prompt: str):
        import asyncio

        from omnistackai_agent_engine.intake.build_app import build_app_from_prompt_stream

        async def run():
            items = []
            async for item in build_app_from_prompt_stream(
                prompt,
                None,  # the ecosystem branch is deterministic and needs no provider
                tempfile.mkdtemp() + "/eco",
                model_id="unused",
                author_name="Test",
                author_email="test@example.test",
            ):
                items.append(item)
            return items

        return asyncio.run(run())

    def test_the_streaming_path_builds_the_ecosystem_too(self) -> None:
        result = self._stream(self.PROMPT)[-1]
        self.assertEqual(result.ecosystem_apps, ("web", "merchant", "driver", "admin"))

    def test_it_needs_no_model_at_all(self) -> None:
        """The ecosystem is planned deterministically, so it cannot fail on an invalid IR — the
        failure mode that stopped the single-app path in the live run."""
        result = self._stream(self.PROMPT)[-1]
        self.assertGreater(result.file_count, 100)

    def test_it_says_what_it_is_doing(self) -> None:
        """There is no model stream to relay, so without this the console goes silent for the
        whole build."""
        messages = [i for i in self._stream(self.PROMPT) if isinstance(i, str)]
        self.assertTrue(any("4 apps over one API" in m for m in messages), messages)
        self.assertTrue(any("alongside the people they serve" in m for m in messages), messages)

    def test_a_single_app_prompt_still_reaches_the_model_path(self) -> None:
        """It must not swallow prompts that should be compiled by a model: with no provider the
        single-app branch is expected to fail rather than silently build something."""
        with self.assertRaises(Exception):
            self._stream("a simple blog")


class TheDecisionReachesTheConsole(TestCase):
    """R-557: the result carried `ecosystem_apps` and `ecosystem_reason`, and
    `app_build_result_to_dict` dropped both — so a user who received four apps saw four
    directories and no reason for them."""

    def _dict_for(self, prompt: str) -> dict:
        import asyncio

        from omnistackai_agent_engine.intake.build_app import (
            app_build_result_to_dict,
            build_app_from_prompt_stream,
        )

        async def run():
            items = []
            async for item in build_app_from_prompt_stream(
                prompt, None, tempfile.mkdtemp() + "/eco",
                model_id="unused", author_name="T", author_email="t@example.test",
            ):
                items.append(item)
            return items[-1]

        return app_build_result_to_dict(asyncio.run(run()))

    def test_an_ecosystem_build_carries_its_apps_and_its_reason(self) -> None:
        payload = self._dict_for("a food delivery app with customers, drivers and restaurants")
        self.assertEqual(payload["ecosystem_apps"], ["web", "merchant", "driver", "admin"])
        self.assertIn("alongside the people they serve", payload["ecosystem_reason"])

    def test_the_reason_is_plain_text(self) -> None:
        """The console renders it as text, never as HTML. Generated copy has no business being
        able to inject markup, and asserting it here keeps that true at the source."""
        payload = self._dict_for("a food delivery app with customers, drivers and restaurants")
        for char in ("<", ">", "&lt;"):
            self.assertNotIn(char, payload["ecosystem_reason"])

    def test_a_single_app_build_carries_neither(self) -> None:
        """Absence is what tells the console to render nothing: an empty panel reading "1 app"
        would be noise on every ordinary build."""
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.intake.build_app import (
            app_build_result_to_dict,
            build_app_from_ir,
        )

        result = build_app_from_ir(
            example_ir("minimal-blog"), tempfile.mkdtemp() + "/one",
            author_name="T", author_email="t@example.test",
        )
        payload = app_build_result_to_dict(result)
        self.assertNotIn("ecosystem_apps", payload)
        self.assertNotIn("ecosystem_reason", payload)
