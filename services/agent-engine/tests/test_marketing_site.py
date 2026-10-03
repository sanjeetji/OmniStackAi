"""PC-131: the product's public website - words by the model, code by the platform, honest."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.codegen import marketing_site as site

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"
COPY = {
    "hero": {"headline": "Your shop, open all day", "subheadline": "Take orders and payments online.", "cta": "Start selling"},
    "features": [{"title": "Orders", "body": "See every order.", "icon": "Package"},
                 {"title": "Payments", "body": "Get paid online.", "icon": "CreditCard"},
                 {"title": "Customers", "body": "Know your buyers.", "icon": "NotAnIcon"}],
    "steps": [{"title": "Sign up", "body": "One minute."}],
    "faq": [{"q": "Is it free to try?", "a": "Yes."}],
    "cta": {"headline": "Open your shop", "body": "Today.", "button": "Get started"},
    "seo": {"title": "Shop", "description": "An online shop."},
}


def _ir() -> ApplicationIR:
    return ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))


class TheCopy(TestCase):
    def test_checked_and_normalised(self) -> None:
        copy, why = site.validate_copy(COPY)
        self.assertEqual(why, "")
        self.assertEqual(copy["features"][2]["icon"], "Sparkles", "an icon not in the set is replaced")

    def test_nothing_invented(self) -> None:
        for claim in ("Trusted by 10,000 customers", "Rated 5 stars by 2,000 reviews", "Award-winning: our award", "What our testimonials say"):
            with self.subTest(claim=claim):
                bad = json.loads(json.dumps(COPY))
                bad["hero"]["subheadline"] = claim
                self.assertIsNone(site.validate_copy(bad)[0])

    def test_too_little_is_refused(self) -> None:
        thin = {**COPY, "features": COPY["features"][:2]}
        self.assertIsNone(site.validate_copy(thin)[0])
        self.assertIsNone(site.validate_copy("not a dict")[0])

    def test_without_a_model_the_plan_writes_it(self) -> None:
        copy, writer = asyncio.run(site.write_copy(_ir(), "A shop", ["Online payments", "Reviews"], None, None))
        self.assertEqual(writer, "plan")
        self.assertEqual(site.validate_copy(copy)[1], "")
        self.assertEqual([f["title"] for f in copy["features"]][:2], ["Online payments", "Reviews"])
        self.assertGreaterEqual(len(copy["features"]), 3)


class TheSite(TestCase):
    def test_the_web_apps_scaffolding_and_seo(self) -> None:
        from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter

        files = {f.path: f.content for f in site.site_files(_ir(), site.validate_copy(COPY)[0])}
        web_package = json.loads(next(f.content for f in NextjsWebAdapter().generate(_ir()).files() if f.path == "package.json"))
        site_package = json.loads(files["apps/site/package.json"])
        self.assertEqual(site_package["dependencies"], web_package["dependencies"], "the shared type-check cache applies")
        self.assertTrue(site_package["name"].endswith("-site"))
        for path in ("apps/site/app/page.tsx", "apps/site/app/layout.tsx", "apps/site/app/sitemap.ts", "apps/site/app/robots.ts",
                     "apps/site/content/site.json", "apps/site/lib/brand.ts"):
            with self.subTest(path=path):
                self.assertIn(path, files)
        self.assertIn('"Shop"', files["apps/site/app/layout.tsx"])
        self.assertIn('import copy from "@/content/site.json";', files["apps/site/app/page.tsx"])
        self.assertNotIn("testimonial", files["apps/site/app/page.tsx"].lower())


class TheBuildAddsIt(TestCase):
    def _build(self, scope):
        from omnistackai_agent_engine.intake.build_app import build_app_from_prompt

        class Model:
            provider_id = "fake"

            def __init__(self):
                self.calls = 0

            async def generate(self, request):
                self.calls += "marketing website" in request.messages[-1].content
                return SimpleNamespace(text=json.dumps(COPY) if "marketing website" in request.messages[-1].content
                                       else FIXTURE.read_text())

        model = Model()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OMNISTACKAI_PLAN_REVIEW": "0",
                                                                                "OMNISTACKAI_BUILD_VERIFY": "off"}):
            built = asyncio.run(build_app_from_prompt("An online shop where customers order products", model, Path(tmp) / "repo",
                                                      model_id="m", author_name="t", author_email="t@example.com", scope=scope))
            present = (Path(tmp) / "repo" / "apps" / "site" / "content" / "site.json").exists()
            text = (Path(tmp) / "repo" / "apps" / "site" / "content" / "site.json").read_text() if present else ""
        return built, present, text, model.calls

    def test_a_confirmed_scope_with_the_site(self) -> None:
        from omnistackai_agent_engine.intake.scope import propose_scope, with_choices

        scope = with_choices(propose_scope("An online shop where customers order products"), {"site": True}).to_dict()
        built, present, text, calls = self._build(scope)
        self.assertTrue(present)
        self.assertIn("Your shop, open all day", text)
        self.assertEqual(built.scope["site"], {"app": "apps/site", "copy_by": "model"})
        self.assertEqual(calls, 1, "one request for the copy")

    def test_no_site_unless_confirmed_and_ticked(self) -> None:
        from omnistackai_agent_engine.intake.scope import propose_scope, with_choices

        _, present, _, calls = self._build(None)
        self.assertFalse(present, "an unconfirmed scope keeps the apps it always had")
        self.assertEqual(calls, 0)
        off = with_choices(propose_scope("An online shop where customers order products"), {"site": False}).to_dict()
        self.assertFalse(self._build(off)[1])
