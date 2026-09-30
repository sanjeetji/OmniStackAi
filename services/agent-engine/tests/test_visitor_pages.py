"""PC-108: the web app's list and detail pages are written for the people who use the app.

Seen in the PC-101 benchmark screenshots: the web app's list was an admin table (density toggles,
CSV/JSON export, bulk selection) and its detail page offered an ID box, "Copy ID", "Export JSON" and
prev/next buttons; the landing hero showed an empty image box. The web app now gets cards and a
reading view; the admin app keeps the operator pages. Every generated web and admin app of the
fixture plans type-checks with the shared cache (checked when this was built).
"""

import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.reachable_references import with_detail_screens, with_reachable_references

_FIXTURES = Path(__file__).parent / "fixtures" / "ir"


def _files(ir) -> dict[str, str]:
    return {f.path: f.content for f in assemble_project(with_detail_screens(with_reachable_references(ir))).files()}


class TheWebListIsCards(TestCase):
    def setUp(self) -> None:
        self.files = _files(example_ir("minimal-blog"))
        self.page = self.files["apps/web/app/post_list/page.tsx"]

    def test_cards_with_a_title_summary_and_a_link_to_read_one(self) -> None:
        self.assertIn('className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3"', self.page)
        self.assertIn('{String(item.title ?? "Untitled")}', self.page)
        self.assertIn("line-clamp-3", self.page)
        self.assertIn("href={`/post_detail?id=${encodeURIComponent(String(item.id))}`}", self.page)

    def test_search_pages_loading_error_and_an_empty_state_that_says_what_next(self) -> None:
        for piece in ('role="search"', 'aria-label="Pages"', 'aria-busy="true"', "Try again",
                      '"No posts yet"', "Add the first post"):
            self.assertIn(piece, self.page)

    def test_no_operator_tools_for_visitors_and_the_admin_keeps_them(self) -> None:
        for tool in ("Export CSV", "Export JSON", "Table display density", "checkedIds"):
            self.assertNotIn(tool, self.page)
        self.assertIn("Export CSV", self.files["apps/admin/app/post_list/page.tsx"])


class TheWebDetailIsAReadingView(TestCase):
    def test_title_body_related_records_and_no_id_tools(self) -> None:
        page = _files(example_ir("minimal-blog"))["apps/web/app/post_detail/page.tsx"]
        self.assertIn('<h1 className="text-3xl font-bold', page)
        self.assertIn("All posts", page)
        self.assertIn("useListCommentsByPost(id)", page, "a post's comments are listed below it")
        for tool in ("Copy ID", "Export JSON", "Load Post", "prevItem"):
            self.assertNotIn(tool, page)
        self.assertIn("<Suspense", page, "useSearchParams needs a boundary")

    def test_edit_and_delete_only_where_the_api_allows_them(self) -> None:
        ir = ApplicationIR.from_dict(json.loads((_FIXTURES / "hiring_portal.json").read_text()))
        files = _files(ir)
        # This plan's *_detail screens are editors, so the cards open them to edit.
        cards = files["apps/web/app/product_list/page.tsx"]
        self.assertIn("href={`/product_detail?id=${encodeURIComponent(String(item.id))}`}", cards)
        self.assertIn('<Link href="/product_detail"', cards, "New goes to the plan's form")
        blog_detail = _files(example_ir("minimal-blog"))["apps/web/app/post_detail/page.tsx"]
        self.assertNotIn("Delete", blog_detail, "the blog's API has no delete")


class TheLandingHasNoEmptyBox(TestCase):
    def test_the_split_hero_panel_leads_into_the_sections(self) -> None:
        from omnistackai_agent_engine.codegen.archetype import Archetype
        from omnistackai_agent_engine.codegen.layout import Layout, layout_for
        from omnistackai_agent_engine.codegen.nextjs import _public_home_page

        blog = with_detail_screens(example_ir("minimal-blog"))
        split = next((a for a in Archetype if layout_for(blog.name, a.value).layout is Layout.SPLIT), None)
        if split is None:
            self.skipTest("no archetype uses the split layout for this name")
        page = _public_home_page(blog, split)
        self.assertNotIn('<div aria-hidden="true" className', page.split("-hero")[1].split("</section>")[0])
        self.assertIn('aria-label="Sections"', page)
