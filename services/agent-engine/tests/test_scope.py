"""PC-127: the platform decides the scope from the prompt, shows it with reasons, and builds the edited one."""

import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import AdminStrategy, ApplicationIR, MobileProfile, WebStrategy
from omnistackai_agent_engine.intake.scope import ProjectScope, apply_to_ir, propose_scope, with_choices

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _apps(prompt: str) -> dict[str, bool]:
    return {a.id: a.included for a in propose_scope(prompt).apps}


class TheShapeFollowsThePrompt(TestCase):
    def test_one_product(self) -> None:
        blog = propose_scope("A simple blog with posts, categories and comments.")
        self.assertEqual((blog.shape, blog.plan), ("single_admin", "product"))
        self.assertEqual(_apps("A simple blog with posts, categories and comments."),
                         {"web": True, "admin": True, "mobile": False, "site": False})

    def test_a_phone_app_when_asked_or_used_on_the_move(self) -> None:
        self.assertTrue(_apps("An online store with an admin panel and a mobile app for customers")["mobile"])
        self.assertEqual(propose_scope("An online store with an admin panel and a mobile app").shape, "few")
        habits = _apps("Track my daily habits and see my streaks.")
        self.assertTrue(habits["mobile"])
        self.assertFalse(habits["admin"], "a personal app is managed from inside it")
        self.assertFalse(habits["site"], "nobody to win over")

    def test_an_internal_tool(self) -> None:
        self.assertEqual(_apps("An internal tool for our warehouse team to count stock"),
                         {"web": False, "admin": True, "mobile": False, "site": False})

    def test_an_ecosystem_names_its_apps_and_why(self) -> None:
        scope = propose_scope("A food delivery app: customers order from restaurants and couriers deliver them.")
        self.assertEqual((scope.shape, scope.plan), ("ecosystem", "ecosystem"))
        kinds = {a.id: a.kind for a in scope.apps}
        self.assertEqual(kinds["driver"], "mobile", "a courier works from a phone")
        self.assertEqual(kinds["admin"], "admin")
        self.assertTrue(all(a.reason for a in scope.apps))
        self.assertTrue(dict((a.id, a.included) for a in scope.apps)["site"], "customers find it through a website")

    def test_one_user_and_their_staff_is_not_an_ecosystem(self) -> None:
        scope = propose_scope("An HR tool where employees request leave and managers approve or reject it.")
        self.assertEqual(scope.shape, "single_admin")
        self.assertFalse(dict((a.id, a.included) for a in scope.apps)["site"])

    def test_the_benchmark_prompts_all_get_a_scope(self) -> None:
        from omnistackai_agent_engine.benchmark.cases import CASES

        for case in CASES:
            with self.subTest(case=case.id):
                scope = propose_scope(case.prompt)
                self.assertTrue(scope.included())
                self.assertTrue(scope.summary.startswith("We'll build "))
                ProjectScope.from_dict(json.loads(json.dumps(scope.to_dict())))


class EditingTheScope(TestCase):
    def test_switching_apps(self) -> None:
        scope = with_choices(propose_scope("A simple blog."), {"mobile": True, "admin": False})
        self.assertEqual(scope.shape, "few")
        self.assertIn("Phone app", scope.summary)
        self.assertNotIn("Admin console", scope.summary)

    def test_the_build_follows_a_confirmed_scope(self) -> None:
        ir = ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))
        scope = with_choices(propose_scope("A simple blog."), {"web": True, "admin": False, "mobile": True})
        strategy = apply_to_ir(ir, scope).project_strategy
        self.assertEqual((strategy.web_strategy, strategy.admin_strategy, strategy.mobile_profile),
                         (WebStrategy.NEXTJS, AdminStrategy.NONE, MobileProfile.REACT_NATIVE))
        nothing = with_choices(scope, {"web": False, "admin": False, "mobile": False})
        self.assertEqual(apply_to_ir(ir, nothing).project_strategy.web_strategy, WebStrategy.NEXTJS, "never nothing")

    def test_an_unconfirmed_scope_leaves_the_planner_alone(self) -> None:
        from omnistackai_agent_engine.intake.build_app import _scoped_ir

        ir = ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))
        scope = with_choices(propose_scope("A simple blog."), {"admin": False})
        self.assertIs(_scoped_ir(ir, scope, confirmed=False), ir)
        self.assertEqual(_scoped_ir(ir, scope, confirmed=True).project_strategy.admin_strategy, AdminStrategy.NONE)

    def test_an_ecosystem_without_one_of_its_apps(self) -> None:
        from omnistackai_agent_engine.intake.build_app import _chosen_scope, _scoped_ecosystem_plan
        from omnistackai_agent_engine.intake.ecosystem_intent import detect_ecosystem_intent

        prompt = "A food delivery app: customers order from restaurants and couriers deliver them."
        edited = with_choices(propose_scope(prompt), {"driver": False}).to_dict()
        plan = _scoped_ecosystem_plan(prompt, detect_ecosystem_intent(prompt), _chosen_scope(prompt, edited))
        self.assertNotIn("Courier Dispatch App", [a.ir.name for a in plan.apps])
        self.assertIn("Merchant Portal", [a.ir.name for a in plan.apps])
        whole = _scoped_ecosystem_plan(prompt, detect_ecosystem_intent(prompt), _chosen_scope(prompt, None))
        self.assertEqual(len(whole.apps), len(plan.apps) + 1)

    def test_a_scope_that_cannot_be_read_falls_back_to_the_proposal(self) -> None:
        from omnistackai_agent_engine.intake.build_app import _chosen_scope

        self.assertEqual(_chosen_scope("A simple blog.", {"apps": "nonsense"}).to_dict(),
                         propose_scope("A simple blog.").to_dict())


class TheRealBuildFollowsIt(TestCase):
    """Found in PC-127's live run: the build result could not carry the scope (a frozen record)."""

    def test_a_confirmed_scope_through_build_app_from_prompt(self) -> None:
        import asyncio
        import tempfile
        from types import SimpleNamespace

        from omnistackai_agent_engine.intake.build_app import build_app_from_prompt

        class Model:
            provider_id = "fake"

            async def generate(self, request):
                return SimpleNamespace(text=FIXTURE.read_text())

        prompt = "Sales analytics dashboard for a small online shop showing orders, customers and revenue by product."
        scope = with_choices(propose_scope(prompt), {"admin": False, "mobile": True}).to_dict()
        import os
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OMNISTACKAI_PLAN_REVIEW": "0",
                                                                                "OMNISTACKAI_BUILD_VERIFY": "off"}):
            built = asyncio.run(build_app_from_prompt(prompt, Model(), Path(tmp) / "repo", model_id="m", author_name="t",
                                                      author_email="t@example.com", scope=scope))
            self.assertTrue((Path(tmp) / "repo" / "apps" / "mobile" / "package.json").exists())
            self.assertFalse((Path(tmp) / "repo" / "apps" / "admin").exists())
        self.assertEqual(built.scope["shape"], "few")
