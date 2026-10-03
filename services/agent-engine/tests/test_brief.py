"""PC-128: a few questions after the prompt - different for each prompt, every answer pre-filled."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR, BackendStrategy
from omnistackai_agent_engine.intake.brief import Brief, apply_brief, plan_prompt, propose_brief, removed_capabilities

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"
SHOP = "A shop where customers order products."


def _questions(prompt: str, **kw) -> dict[str, str]:
    return {q.id: q.answer for q in propose_brief(prompt, **kw).questions}


def _on(prompt: str) -> set[str]:
    return {f.id for f in propose_brief(prompt).features if f.included}


class TheQuestionsFollowThePrompt(TestCase):
    def test_different_prompts_different_questions(self) -> None:
        food = _questions("A food delivery app: customers order from restaurants and couriers deliver them.")
        self.assertEqual(food, {"payment_method": "online", "commission": "10", "signup": "anyone"})
        clinic = propose_brief("A clinic booking system: patients book appointments with doctors.")
        self.assertIn("When should people be reminded of an appointment?", [q.question for q in clinic.questions])
        self.assertEqual(_questions("An internal tool for our warehouse team to count stock"), {"signup": "invite"})
        self.assertEqual(_questions("Track my daily habits and see my streaks."), {}, "a personal app asks nothing")

    def test_what_the_prompt_already_says_is_not_asked(self) -> None:
        self.assertNotIn("payment_method", _questions("Customers order online and pay by card or cash."))
        self.assertNotIn("commission", _questions("A marketplace where sellers sell and the platform keeps 12% of each sale."))
        self.assertNotIn("reminder", _questions("Patients book appointments; remind them 2 hours before."))

    def test_features_from_the_prompt_and_from_the_kind_of_product(self) -> None:
        brief = propose_brief("A recipe app where people post recipes with photos and rate them.")
        features = {f.id: f for f in brief.features}
        self.assertTrue(features["uploads"].from_prompt and features["reviews"].from_prompt)
        self.assertIn("you mentioned", features["uploads"].reason)
        self.assertTrue(features["reviews"].included)
        self.assertFalse(features["messages"].included, "offered, not ticked")
        self.assertIn("reminders", _on("Track my daily habits and see my streaks."), "habits suggest a daily reminder")
        self.assertNotIn("live", _on("Track my daily habits and see my streaks."), "tracking habits is not live tracking")
        self.assertIn("push", _on("A gym app for members on their phones."))


class RegionBrandAndName(TestCase):
    def test_the_browser_sets_the_region(self) -> None:
        self.assertEqual(propose_brief(SHOP, locale="en-IN", timezone="Asia/Kolkata").region,
                         {"languages": ["English"], "currency": "INR", "timezone": "Asia/Kolkata"})
        self.assertEqual(propose_brief(SHOP, locale="de-DE").region["currency"], "EUR")
        self.assertEqual(propose_brief("A shop with prices in dollars", locale="en-IN").region["currency"], "USD",
                         "the prompt wins over the browser")
        self.assertEqual(propose_brief("A school app in Hindi and English").region["languages"], ["English", "Hindi"])

    def test_brand_and_name(self) -> None:
        brief = propose_brief("A marketplace for handmade jewellery called Kaari, where sellers list products.")
        self.assertEqual(brief.name, "Kaari")
        self.assertTrue(brief.brand["primary_color"].startswith("#") and brief.brand["style"])


class TheAnswersBecomeThePlansFacts(TestCase):
    def test_the_readers_understand_the_brief(self) -> None:
        from omnistackai_agent_engine.intake.nl_to_ir import _with_prompt_ownership

        brief = propose_brief(SHOP)
        answers = {"live": True, "notifications": True, "payments": True}
        brief = Brief.from_dict({**brief.to_dict(), "features": [{**f.to_dict(), "included": answers.get(f.id, f.included)}
                                                                 for f in brief.features]})
        text = plan_prompt(brief)
        self.assertIn("Project brief (confirmed by the owner):", text)
        ir, _notes = _with_prompt_ownership(ApplicationIR.from_dict(json.loads(FIXTURE.read_text())), text)
        kinds = {c.kind for c in ir.capabilities}
        self.assertLessEqual({"money", "realtime", "notifications"}, kinds, kinds)

    def test_answers_change_the_facts(self) -> None:
        brief = propose_brief("A food delivery app: customers order from restaurants and couriers deliver them.")
        edited = Brief.from_dict({**brief.to_dict(), "questions": [
            {"id": "payment_method", "answer": "cash"}, {"id": "commission", "answer": "15"}, {"id": "signup", "answer": "anyone"}]})
        text = plan_prompt(edited)
        self.assertIn("pay in cash", text)
        self.assertIn("15% commission", text)
        nonsense = Brief.from_dict({**brief.to_dict(), "questions": [{"id": "commission", "answer": "999"}]})
        self.assertEqual({q.id: q.answer for q in nonsense.questions}["commission"], "10", "an unknown answer keeps the default")

    def test_the_owners_words_cannot_be_switched_off(self) -> None:
        brief = propose_brief("A recipe app where people post recipes with photos.")
        edited = Brief.from_dict({**brief.to_dict(), "features": [{"id": "uploads", "included": False}]})
        self.assertTrue(next(f for f in edited.features if f.id == "uploads").included)

    def test_name_brand_backend_and_switched_off_blocks(self) -> None:
        ir = ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))
        ir = ApplicationIR.from_dict({**ir.to_dict(), "capabilities": [
            {"kind": "realtime", "name": "live_updates", "config": {"entities": ["Order"]}}]})
        brief = propose_brief(SHOP)
        brief = Brief.from_dict({**brief.to_dict(), "name": "Kaari Shop", "brand": {"primary_color": "#123456", "style": "bold"},
                                 "advanced": {"backend": "go"},
                                 "features": [{**f.to_dict(), "included": False if f.id == "live" else f.included}
                                              for f in brief.features]})
        self.assertIn("realtime", removed_capabilities(brief))
        out = apply_brief(ir, brief)
        self.assertEqual(out.name, "Kaari Shop")
        self.assertEqual(out.brand.primary_color, "#123456")
        self.assertEqual(out.project_strategy.backend_strategy, BackendStrategy.GO)
        self.assertNotIn("realtime", {c.kind for c in out.capabilities})


class TheRealBuildFollowsTheBrief(TestCase):
    def test_build_app_from_prompt_with_a_brief(self) -> None:
        from omnistackai_agent_engine.intake.build_app import build_app_from_prompt

        seen = []

        class Model:
            provider_id = "fake"

            async def generate(self, request):
                seen.append(request.messages[-1].content)
                return SimpleNamespace(text=FIXTURE.read_text())

        brief = propose_brief(SHOP)
        brief = Brief.from_dict({**brief.to_dict(), "name": "Corner Shop", "advanced": {"backend": "go"},
                                 "features": [{**f.to_dict(), "included": True if f.id == "live" else f.included}
                                              for f in brief.features]})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OMNISTACKAI_PLAN_REVIEW": "0",
                                                                                "OMNISTACKAI_BUILD_VERIFY": "off"}):
            built = asyncio.run(build_app_from_prompt(SHOP, Model(), Path(tmp) / "repo", model_id="m", author_name="t",
                                                      author_email="t@example.com", brief=brief.to_dict()))
            self.assertTrue((Path(tmp) / "repo" / "services" / "api" / "go.mod").exists(), "the Go backend was built")
        self.assertIn("Orders update live", seen[0], "the planner is told the brief")
        self.assertEqual(built.ir.name, "Corner Shop")
        self.assertIn("realtime", {c.kind for c in built.ir.capabilities})
        self.assertEqual(built.scope["plan"], "product")
