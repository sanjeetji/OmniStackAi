"""R-556: two products in one archetype must not render the same page.

R-543 stopped a shop, a blog and a booking site looking alike. Two shops still did:
`_public_home_page` rendered one structure — centred hero, offering grid, browse row, footer —
and only the words changed. Two people building storefronts got the same page with different nouns.

The two properties here are in tension, and both matter: **two different products differ**, and
**one product is stable across runs**. Randomness gives the first and destroys the second; a fixed
default gives the second and never the first. A seed derived from the product gives both.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import BrandTokens, example_ir
from omnistackai_agent_engine.codegen.archetype import HOME_COPY, PUBLIC_ARCHETYPES, Archetype
from omnistackai_agent_engine.codegen.layout import (
    ARCHETYPE_LAYOUTS,
    LAYOUTS,
    Layout,
    layout_for,
    pick_layout,
)
from omnistackai_agent_engine.codegen.llm_ui import clean_and_validate_jsx
from omnistackai_agent_engine.codegen.nextjs import _public_home_page

BASE = example_ir("minimal-blog")


def _page(name: str, archetype: Archetype, **kw) -> str:
    return _public_home_page(dataclasses.replace(BASE, name=name, **kw), archetype)


def _name_for(layout: Layout) -> str:
    """A product name that maps to `layout`, so every variant can be exercised."""
    for candidate in (chr(c) for c in range(65, 91)):
        if layout_for(candidate, None).layout is layout:
            return candidate
    raise AssertionError(f"no name maps to {layout}")


class TwoProductsDiffer(TestCase):
    SHOPS = ("Bakery Shop", "Corner Store", "Urban Threads", "Bean & Leaf")

    def test_storefronts_do_not_all_render_the_same_page(self) -> None:
        pages = {name: _page(name, Archetype.STOREFRONT) for name in self.SHOPS}
        self.assertEqual(len(set(pages.values())), len(pages))

    def test_they_differ_structurally_not_just_in_wording(self) -> None:
        """Swapping a noun is not variety. Two of these must use different arrangements."""
        layouts = {layout_for(name, "storefront").layout for name in self.SHOPS}
        self.assertGreater(len(layouts), 1, layouts)

    def test_one_product_is_stable_across_runs(self) -> None:
        first = _page("Bakery Shop", Archetype.STOREFRONT)
        second = _page("Bakery Shop", Archetype.STOREFRONT)
        self.assertEqual(first, second)

    def test_the_choice_itself_is_deterministic(self) -> None:
        self.assertEqual(pick_layout("Bakery Shop").layout, pick_layout("Bakery Shop").layout)

    def test_adjacent_names_are_not_forced_onto_one_layout(self) -> None:
        """A `len(name) % n` scheme would collapse these; hashing does not."""
        names = ("Bakery One", "Bakery Two", "Bakery Six")
        self.assertGreater(len({pick_layout(n).layout for n in names}), 1)


class EveryVariantIsShippable(TestCase):
    def test_each_one_is_valid_jsx(self) -> None:
        """The same validator the engine applies to model-written pages."""
        for layout in LAYOUTS:
            with self.subTest(layout=layout.value):
                page = _page(_name_for(layout), Archetype.MARKETING)
                valid, _cleaned, reason = clean_and_validate_jsx(page)
                self.assertTrue(valid, f"{layout.value}: {reason}")

    def test_each_one_survives_an_ir_with_nothing_in_it(self) -> None:
        for layout in LAYOUTS:
            with self.subTest(layout=layout.value):
                page = _page(_name_for(layout), Archetype.MARKETING, entities=(), screens=(), apis=())
                valid, _cleaned, reason = clean_and_validate_jsx(page)
                self.assertTrue(valid, f"{layout.value}: {reason}")
                self.assertIn("<main", page)

    def test_none_of_them_is_a_client_component(self) -> None:
        """A landing page needs no client JavaScript, in any arrangement."""
        for layout in LAYOUTS:
            with self.subTest(layout=layout.value):
                page = _page(_name_for(layout), Archetype.MARKETING)
                self.assertNotIn('"use client"', page)
                self.assertNotIn("useList", page)

    def test_each_one_still_renders_the_brand(self) -> None:
        """A variant that stopped using the brand colour would undo R-544 silently."""
        for layout in LAYOUTS:
            with self.subTest(layout=layout.value):
                page = _page(_name_for(layout), Archetype.MARKETING, brand=BrandTokens(primary_color="#dc2626"))
                self.assertIn("var(--color-primary)", page)


class TheArchetypeStillWins(TestCase):
    def test_every_archetype_keeps_its_own_call_to_action(self) -> None:
        """Variety must not cost the archetype its language — that was R-543's whole point."""
        for archetype in PUBLIC_ARCHETYPES:
            with self.subTest(archetype=archetype.value):
                page = _page("Some Product", archetype)
                self.assertIn(HOME_COPY[archetype]["cta"], page)
                self.assertIn(HOME_COPY[archetype]["section"], page)

    def test_an_archetype_only_gets_arrangements_that_suit_it(self) -> None:
        """Forcing variety at the cost of fit produces something different but worse: a
        publication is wrong as a product grid, a storefront wrong as an index."""
        self.assertNotIn(Layout.EDITORIAL, ARCHETYPE_LAYOUTS["storefront"])
        self.assertIn(Layout.EDITORIAL, ARCHETYPE_LAYOUTS["publication"])

    def test_a_publication_never_renders_as_a_banner(self) -> None:
        for name in ("The Daily", "Minimal Blog", "Longform", "Dispatch", "Gazette"):
            with self.subTest(name=name):
                self.assertIn(layout_for(name, "publication").layout, ARCHETYPE_LAYOUTS["publication"])


class AddingAVariantDoesNotReshuffleExistingProjects(TestCase):
    def test_the_order_is_stable(self) -> None:
        """`LAYOUTS` is indexed by the seed, so appending is safe and reordering is not."""
        self.assertEqual(LAYOUTS[0], Layout.CENTERED)
        self.assertEqual(len(set(LAYOUTS)), len(LAYOUTS))
