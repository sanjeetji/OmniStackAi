"""R-558: the generated pages use the design system they ship with.

The project carried a real design system -- 59 colour tokens, a type scale, a space scale, six
shadows, seven motion tokens -- and the pages used almost none of it. Measured on a generated home
page before this change: `--shadow-*` 0 times, `--transition-*` 0, `--font-size-*` 0, `--space-*`
0, against 26 hardcoded pixel values and **zero hover or focus states**. It looked flat and static
because it was.

Part of that was structural rather than a matter of taste, which is why the fix is a stylesheet
and not better inline values: **inline React styles cannot express `:hover`, `:focus-visible` or a
media query at all.** No amount of tuning `style={{...}}` would have produced an interface that
responds to a cursor or a keyboard.

Two of the assertions here are about the people who use the result rather than about tidiness:
focus must be *styled* rather than removed, because a keyboard user who cannot see where they are
cannot use the page at all; and motion must be suppressed under `prefers-reduced-motion`, which is
a comfort setting for some people and a medical one for others.

These assert on the **generated CSS and the generated page**, never on the source text of the
module. A grep for `outline: none` over the source matches the docstring explaining why we never
write `outline: none` -- the same prose false-positive that already bit R-543 and R-546.
"""

import dataclasses
import re
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    BrandTokens,
    MobileProfile,
    Platform,
    ProjectStrategy,
    AdminStrategy,
    BackendStrategy,
    DatabaseStrategy,
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen.archetype import Archetype
from omnistackai_agent_engine.codegen.layout import LAYOUTS, Layout, layout_for
from omnistackai_agent_engine.codegen.llm_ui import clean_and_validate_jsx
from omnistackai_agent_engine.codegen.nextjs import _public_home_page
from omnistackai_agent_engine.codegen.page_style import PREFIX, page_stylesheet


def _empty_ir() -> ApplicationIR:
    """An IR with no entities and no screens.

    The page still has to render rather than crash or leave holes: there is nothing to put in the
    offering grid and nothing to browse, so those sections must simply not appear. (The IR itself
    requires a description, so "empty" here means empty of content, not an invalid IR.)
    """
    return ApplicationIR(
        name="Nothing",
        description="an app with nothing in it yet",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
    )


def _named(name: str) -> ApplicationIR:
    return dataclasses.replace(example_ir("minimal-blog"), name=name)


class TheStylesheetUsesTheSystemItShipsWith(TestCase):
    """The measurement that opened this task, turned into a gate."""

    def setUp(self) -> None:
        self.css = page_stylesheet()

    def test_depth_and_motion_come_from_tokens(self) -> None:
        # Hardcoding a shadow would leave it behind when a user rebrands through brand.json.
        for family in ("--shadow-", "--transition-duration-", "--font-size-", "--space-", "--radius-"):
            self.assertIn(
                f"var({family}", self.css, f"the page must use the shipped {family}* tokens"
            )

    def test_no_hardcoded_hex_colours(self) -> None:
        # A literal colour in the stylesheet is a colour a rebrand cannot reach.
        self.assertEqual(
            re.findall(r"#[0-9a-fA-F]{3,8}\b", self.css),
            [],
            "colours must come from the brand tokens, never from literals in the stylesheet",
        )

    def test_interaction_states_exist_at_all(self) -> None:
        # The thing inline styles could not do, which is why this file exists.
        self.assertIn(":hover", self.css)
        self.assertGreaterEqual(self.css.count(":hover"), 4, "interactive elements need hover feedback")

    def test_focus_is_styled_not_removed(self) -> None:
        self.assertIn(":focus-visible", self.css, "keyboard users need a visible focus state")
        self.assertRegex(
            self.css,
            r":focus-visible\s*\{[^}]*outline:\s*\d",
            "focus-visible must draw an outline rather than suppress one",
        )
        self.assertNotRegex(
            self.css,
            r"outline:\s*none",
            "a removed focus outline makes the page unusable without a mouse",
        )

    def test_motion_is_suppressed_for_people_who_ask_for_that(self) -> None:
        self.assertIn("prefers-reduced-motion: reduce", self.css)
        block = self.css.split("prefers-reduced-motion: reduce", 1)[1]
        self.assertIn("transition-duration: 0.01ms", block)
        self.assertIn("transform: none", block, "hover lifts must stop too, not just fade faster")


class EveryArrangementStillRenders(TestCase):
    """R-556's four arrangements survived the redesign, including against an empty IR."""

    def _page_for(self, layout: Layout, ir: ApplicationIR) -> str:
        # Reach each arrangement through a name that seeds it, so this exercises the real
        # selection path rather than a branch the generator would never take.
        for i in range(400):
            candidate = dataclasses.replace(ir, name=f"{ir.name} {i}")
            if layout_for(candidate.name, Archetype.MARKETING.value).layout is layout:
                return _public_home_page(candidate, Archetype.MARKETING)
        self.fail(f"no seed produced {layout} within 400 tries")

    def test_every_layout_is_valid_jsx(self) -> None:
        for layout in LAYOUTS:
            for label, ir in (("full", _named("Demo")), ("empty", _empty_ir())):
                with self.subTest(layout=layout, ir=label):
                    page = self._page_for(layout, ir)
                    ok, _cleaned, error = clean_and_validate_jsx(page)
                    self.assertTrue(ok, f"{layout} on an {label} IR produced invalid JSX: {error}")

    def test_every_layout_stays_a_server_component(self) -> None:
        # A home page that opts into client JavaScript for a hover state would be a regression;
        # the stylesheet is precisely what makes that unnecessary.
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                self.assertNotIn('"use client"', self._page_for(layout, _named("Demo")))

    def test_every_layout_ships_the_stylesheet_and_no_dependency(self) -> None:
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                page = self._page_for(layout, _named("Demo"))
                self.assertIn(f'className="{PREFIX}-page"', page)
                self.assertIn(":focus-visible", page, "the page must carry its own focus styles")
                # No CSS-in-JS library, no import beyond what Next already gives the project.
                imports = re.findall(r'^import .* from "([^"]+)";', page, re.MULTILINE)
                self.assertTrue(
                    all(i.startswith(("next/", "./", "../", "@/")) for i in imports),
                    f"{layout} pulled in a dependency: {imports}",
                )

    def test_two_products_get_different_structure(self) -> None:
        # The R-556 promise, re-checked after the redesign: the class attributes on elements must
        # differ, not just the words inside them.
        def shape(page: str) -> list[str]:
            body = page.split("` }} />", 1)[-1]  # drop the stylesheet; it is identical by design
            return re.findall(r'className="([^"]+)"', body)

        centred = shape(self._page_for(Layout.CENTERED, _named("Demo")))
        editorial = shape(self._page_for(Layout.EDITORIAL, _named("Demo")))
        self.assertNotEqual(centred, editorial, "two arrangements rendered the same structure")


class TheOutputStaysPredictable(TestCase):
    def test_one_product_renders_identically_twice(self) -> None:
        ir = _named("Bakery Shop")
        self.assertEqual(_public_home_page(ir), _public_home_page(ir))

    def test_the_product_name_reaches_the_page(self) -> None:
        self.assertIn("Bakery Shop", _public_home_page(_named("Bakery Shop")))

    def test_the_brand_colour_still_drives_the_page(self) -> None:
        # The page never names a colour; it names tokens, and brand.json supplies them. That is
        # what lets a rebrand move the whole page, shadows included.
        page = _public_home_page(
            dataclasses.replace(_named("Bakery Shop"), brand=BrandTokens(primary_color="#dc2626"))
        )
        self.assertNotIn("#dc2626", page)
        self.assertIn("var(--color-primary)", page)
