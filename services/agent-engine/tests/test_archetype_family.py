"""R-543: a real archetype family, so different products get different pages.

Before this there were two archetypes and eight prompt keywords that defaulted to `admin_panel`.
Two consequences these tests lock shut:

* "a website to sell my product" matched none of the keywords and so generated an internal
  dashboard for a shop;
* every public site that *was* recognised got one identical landing page, whether it sold shoes,
  published articles or took bookings.

Detection reads the IR as well as the prompt, because entity names survive paraphrasing: a project
with `Product`, `Order` and `Cart` is a shop whatever sentence produced it.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Platform,
    ProjectStrategy,
    Screen,
    example_ir,
)
from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    BackendStrategy,
    DatabaseStrategy,
    MobileProfile,
    RepoStrategy,
    WebStrategy,
)
from omnistackai_agent_engine.codegen.archetype import (
    HOME_COPY,
    PUBLIC_ARCHETYPES,
    Archetype,
    detect_archetype,
    score_archetypes,
)
from omnistackai_agent_engine.codegen.llm_ui import build_ui_synthesis_prompt, clean_and_validate_jsx
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _public_home_page


def _ir_with(name: str, entities: tuple[str, ...], screens: tuple[str, ...] = ()) -> ApplicationIR:
    return ApplicationIR(
        name=name,
        description="A generated product.",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=tuple(
            Entity(e, (Field("id", FieldType.UUID), Field("title", FieldType.STRING))) for e in entities
        ),
        apis=(ApiEndpoint(HttpMethod.GET, "/things", auth=False),),
        screens=tuple(Screen(s, "public", components=("list",)) for s in screens),
    )


class TheFoundersExample(TestCase):
    def test_a_website_to_sell_my_product_is_a_shop_not_a_console(self) -> None:
        """The exact phrase that used to produce an admin dashboard."""
        self.assertEqual(detect_archetype(None, "create a website to sell my product"), Archetype.STOREFRONT)

    def test_it_is_never_an_admin_panel_by_default(self) -> None:
        """The old detector defaulted to `admin_panel`, which is how a shop became a console."""
        for prompt in ("", "zxqw nondescript widget thing", "something for my business"):
            with self.subTest(prompt=prompt):
                self.assertNotEqual(detect_archetype(None, prompt), Archetype.ADMIN_PANEL)


class DetectionReadsTheProduct(TestCase):
    CASES = (
        ("a news website where I can publish articles in categories", Archetype.PUBLICATION),
        ("a salon where customers book appointments", Archetype.BOOKING),
        ("a directory of local plumbers", Archetype.DIRECTORY),
        ("a landing page for my startup", Archetype.MARKETING),
        ("a dashboard for my team to track projects", Archetype.SAAS),
        ("an online store for handmade jewellery", Archetype.STOREFRONT),
    )

    def test_prompts_resolve_to_their_archetype(self) -> None:
        for prompt, expected in self.CASES:
            with self.subTest(prompt=prompt):
                self.assertEqual(detect_archetype(None, prompt), expected)

    def test_entities_decide_even_when_the_wording_does_not(self) -> None:
        """The strongest signal: a shop's IR is a shop however the request was phrased."""
        ir = _ir_with("Thing", ("Product", "Order", "Cart"))
        self.assertEqual(detect_archetype(ir, "a thing for my business"), Archetype.STOREFRONT)

    def test_entities_outweigh_a_single_stray_phrase(self) -> None:
        """"a blog to sell my art prints" is a shop: three shop entities beat one blog word."""
        ir = _ir_with("Prints", ("Product", "Order", "Cart"))
        scores = score_archetypes(ir, "a blog to sell my art prints")
        self.assertGreater(scores[Archetype.STOREFRONT], scores[Archetype.PUBLICATION])

    def test_detection_is_deterministic(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(detect_archetype(ir, "a blog"), detect_archetype(ir, "a blog"))

    def test_no_evidence_is_a_landing_page_not_a_dashboard(self) -> None:
        self.assertEqual(detect_archetype(_ir_with("X", ("Widget",)), ""), Archetype.MARKETING)


class EachArchetypeLooksDifferent(TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.pages = {a: _public_home_page(self.ir, a) for a in PUBLIC_ARCHETYPES}

    def test_every_archetype_renders_a_distinct_page(self) -> None:
        self.assertEqual(len(set(self.pages.values())), len(self.pages))

    def test_every_archetype_is_valid_jsx(self) -> None:
        """The same validator the engine applies to model-written pages."""
        for archetype, page in self.pages.items():
            with self.subTest(archetype=archetype.value):
                valid, _cleaned, reason = clean_and_validate_jsx(page)
                self.assertTrue(valid, f"{archetype.value}: {reason}")

    def test_each_archetype_speaks_its_own_language(self) -> None:
        for archetype, page in self.pages.items():
            with self.subTest(archetype=archetype.value):
                self.assertIn(HOME_COPY[archetype]["eyebrow"], page)
                self.assertIn(HOME_COPY[archetype]["cta"], page)

    def test_a_shop_invites_you_to_shop_and_a_publication_to_read(self) -> None:
        self.assertIn("Start shopping", self.pages[Archetype.STOREFRONT])
        self.assertIn("Start reading", self.pages[Archetype.PUBLICATION])
        self.assertIn("Book now", self.pages[Archetype.BOOKING])
        self.assertNotIn("Start shopping", self.pages[Archetype.PUBLICATION])

    def test_none_of_them_is_the_staff_dashboard(self) -> None:
        for archetype, page in self.pages.items():
            with self.subTest(archetype=archetype.value):
                self.assertNotIn("useList", page)
                self.assertNotIn('"use client"', page)


class TheModelIsToldTheSameThing(TestCase):
    def test_every_archetype_has_its_own_instructions(self) -> None:
        ir = example_ir("minimal-blog")
        headings = set()
        for archetype in (*PUBLIC_ARCHETYPES, Archetype.ADMIN_PANEL):
            prompt = build_ui_synthesis_prompt(ir, "x", archetype=archetype.value)
            heading = next(line for line in prompt.splitlines() if line.startswith("ARCHETYPE:"))
            headings.add(heading)
        self.assertEqual(len(headings), len(PUBLIC_ARCHETYPES) + 1, headings)

    def test_the_deterministic_page_and_the_model_prompt_agree(self) -> None:
        """Both sides resolve the archetype the same way, so a model failure is not a genre change."""
        ir = example_ir("minimal-blog")
        resolved = detect_archetype(ir, "a blog")
        page = NextjsWebAdapter().generate(ir, prompt="a blog").get("app/page.tsx").content
        self.assertIn(HOME_COPY[resolved]["cta"], page)


class OutputStaysReproducible(TestCase):
    def test_the_page_is_byte_stable_across_runs(self) -> None:
        ir = example_ir("minimal-blog")
        first = NextjsWebAdapter().generate(ir, prompt="an online store").get("app/page.tsx").content
        second = NextjsWebAdapter().generate(ir, prompt="an online store").get("app/page.tsx").content
        self.assertEqual(first, second)

    def test_an_empty_ir_still_renders(self) -> None:
        ir = dataclasses.replace(example_ir("minimal-blog"), entities=(), screens=(), apis=())
        for archetype in PUBLIC_ARCHETYPES:
            with self.subTest(archetype=archetype.value):
                page = _public_home_page(ir, archetype)
                valid, _cleaned, reason = clean_and_validate_jsx(page)
                self.assertTrue(valid, reason)
