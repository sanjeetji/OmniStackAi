"""PC-099: every project gets a design direction of its own.

Before this task every project shared one byte-identical stylesheet, so all apps looked alike. The
direction is deterministic (same prompt, same look), varies with the domain, the style words and the
project's name, lets the prompt's explicit cues win, lives in the plan (so edits keep it), reaches
brand.json and the runtime CSS (fonts actually load), and is given to the page writer - which is
also told not to draw a second header under the app's navigation bar.
"""

import json
import tempfile
from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.ir import BrandTokens
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.brand_project import brand_json, web_brand_ts
from omnistackai_agent_engine.codegen.design_direction import (
    choose_direction,
    describe,
    page_brief,
    with_design_direction,
)
from omnistackai_agent_engine.codegen.llm_ui import build_ui_synthesis_prompt


def _ir(name: str = "Minimal Blog"):
    return replace(example_ir("minimal-blog"), name=name)


class EachProjectLooksLikeItself(TestCase):
    def test_the_same_prompt_always_gives_the_same_direction(self) -> None:
        first = with_design_direction(_ir("Glow"), "a luxury salon").brand
        again = with_design_direction(_ir("Glow"), "a luxury salon").brand
        self.assertEqual(first, again)

    def test_different_products_look_different(self) -> None:
        looks = {
            (d.style, d.primary, d.heading_font)
            for d in (
                choose_direction("a food delivery app", name="Food Hub", archetype="storefront"),
                choose_direction("a luxury salon", name="Glow", archetype="booking"),
                choose_direction("a clinic for patients", name="CarePoint", archetype="booking"),
                choose_direction("a playful chore tracker for kids", name="Chore Stars", archetype="tracker"),
                choose_direction("a news magazine", name="Daily Ledger", archetype="publication"),
            )
        }
        self.assertEqual(len(looks), 5, looks)

    def test_style_words_and_domain_decide(self) -> None:
        self.assertEqual(choose_direction("a luxury salon", name="x").style, "elegant")
        self.assertEqual(choose_direction("a playful app for kids", name="x").style, "playful")
        self.assertEqual(choose_direction("an app", name="x", archetype="tracker").style, "professional")
        self.assertIn(choose_direction("a food delivery app", name="x").primary,
                      {"#dc2626", "#ea580c", "#be123c"})

    def test_two_similar_products_are_not_identical(self) -> None:
        primaries = {choose_direction("a food delivery app", name=n, archetype="storefront").primary
                     for n in ("Food Hub", "QuickBite", "Tasty Now", "Meal Rush", "Dish Dash", "Grub Go")}
        self.assertGreater(len(primaries), 1)

    def test_what_the_prompt_says_outright_wins(self) -> None:
        brand = with_design_direction(_ir(), "a red online shop in Poppins with sharp corners").brand
        self.assertEqual((brand.primary_color, brand.font_family, brand.border_radius), ("#dc2626", "Poppins", "none"))
        self.assertTrue(brand.style and brand.accent_color)

    def test_a_brand_the_plan_already_has_is_never_replaced(self) -> None:
        own = replace(_ir(), brand=BrandTokens(primary_color="#00ff88"))
        self.assertEqual(with_design_direction(own, "a luxury salon"), own)


class TheDirectionIsKeptAndUsed(TestCase):
    def test_a_build_saves_the_direction_in_the_plan_so_edits_keep_it(self) -> None:
        from omnistackai_agent_engine.edit.diff import plan_edit
        from omnistackai_agent_engine.intake.build_app import app_build_result_to_dict, build_app_from_ir

        with tempfile.TemporaryDirectory() as tmp:
            result = build_app_from_ir(_ir("Glow"), tmp, author_name="t", author_email="t@t.t",
                                       prompt="a luxury salon", overwrite=True)
            self.assertEqual(result.ir.brand.style, "elegant")
            self.assertIn("Elegant design", app_build_result_to_dict(result)["design_direction"])
        # An edit assembles from the plan alone: the stylesheet must not change back.
        renamed = replace(result.ir, description="now with gift cards")
        self.assertNotIn("apps/web/styles/tokens.css", plan_edit(result.ir, renamed).modified())

    def test_brand_json_and_the_runtime_css_carry_it(self) -> None:
        ir = with_design_direction(_ir("Glow"), "a luxury salon")
        document = json.loads(brand_json(ir, "glow").content)
        self.assertEqual((document["headingFont"], document["style"]), ("Playfair Display", "elegant"))
        self.assertTrue(document["accentColor"].startswith("#"))
        bridge = web_brand_ts().content
        self.assertIn("fonts.googleapis.com/css2", bridge, "a named font must actually load")
        self.assertIn("--font-heading", bridge)
        self.assertIn("--color-accent", bridge)
        plain = json.loads(brand_json(_ir(), "blog").content)
        self.assertNotIn("style", plain, "a plan without a direction keeps the old brand.json")

    def test_both_apps_of_one_product_share_the_direction(self) -> None:
        project = assemble_project(_ir("Glow"), prompt="a luxury salon")
        self.assertEqual(project.get("apps/web/styles/tokens.css").content,
                         project.get("apps/admin/styles/tokens.css").content)

    def test_the_page_writer_gets_the_direction_and_no_second_header(self) -> None:
        ir = with_design_direction(_ir("Glow"), "a luxury salon")
        prompt = build_ui_synthesis_prompt(ir, "a luxury salon")
        self.assertIn("DESIGN DIRECTION", prompt)
        self.assertIn("do NOT add another top header", prompt)
        self.assertEqual(page_brief(BrandTokens()), "", "a plan without a direction adds nothing")
        self.assertIn("Playfair Display", describe(ir.brand))


class TheComponentsWearTheBrand(TestCase):
    """Found live: 76 of ~110 components were written in fixed blues - a burgundy salon still had
    a blue navigation bar."""

    def test_default_blues_become_the_brand_where_a_variable_works(self) -> None:
        from omnistackai_agent_engine.codegen.design_direction import theme_component

        out = theme_component('style={{ background: "#2563EB" }} <svg fill="#2563eb"/> '
                              'className="bg-[#1d4ed8]" linear-gradient(#2563eb, #4f46e5)')
        self.assertIn('background: "var(--color-primary)"', out)
        self.assertIn('fill="#2563eb"', out, "an SVG attribute cannot take a variable")
        self.assertIn("bg-[var(--color-primary-hover)]", out)
        self.assertIn("var(--color-accent)", out)
        canvas = 'ctx = el.getContext("2d"); ctx.fillStyle = "#2563eb";'
        self.assertEqual(theme_component(canvas), canvas, "a canvas cannot read a variable")

    def test_the_navigation_bar_follows_a_direction_and_old_projects_are_unchanged(self) -> None:
        directed = assemble_project(with_design_direction(_ir("Glow"), "a luxury salon"))
        navbar = directed.get("apps/web/components/navbar.tsx").content
        self.assertIn("var(--color-primary)", navbar)
        self.assertNotRegex(navbar, r'(?<!=")#2563eb')
        plain = assemble_project(_ir()).get("apps/web/components/navbar.tsx").content
        self.assertIn("#2563eb", plain, "a project without a direction is generated exactly as before")


class APlannedLoginScreenDoesNotBreakTheBuild(TestCase):
    """Found live: a plan with a "login" screen collided with the app's own sign-in page and the
    build failed with "duplicate generated path: app/login/page.tsx"."""

    def test_the_apps_own_sign_in_page_wins(self) -> None:
        from omnistackai_agent_engine.application_ir.ir import Screen
        from omnistackai_agent_engine.codegen.auth_guard import needs_auth

        ir = _ir()
        ir = replace(ir, screens=(*ir.screens, Screen(id="login", role="reader", components=("form",), actions=("save",), navigation=())))
        self.assertTrue(needs_auth(ir))
        project = assemble_project(ir)  # raised "duplicate generated path" before
        self.assertIn("apps/web/app/login/page.tsx", {f.path for f in project.files()})
