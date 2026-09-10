"""Task R-303: Generated Dashboard Overview Interactive Entity Links, Operational Health Badge & Metrics Chips.

Verifies:
1. Entity summary cards link to matching collection screen (href="/...") with aria-label and "View all →".
2. Entity summary cards without matching collection screen render as styled <div> cards.
3. Dashboard header renders "System Operational" badge with green status indicator.
4. Dashboard header renders summary metrics chips for entity and screen counts.
5. Screen nav cards render navigation arrow indicator.
6. Empty state message rendered when both entities and screens are empty.
7. Strict diff invariance across ir.description edits.
8. Full project generation via NextjsWebAdapter succeeds with enhanced overview page.
"""

from __future__ import annotations

import unittest

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter
from omnistackai_agent_engine.codegen.nextjs import _overview_page

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _make_ir(
    name: str = "Acme App",
    description: str = "An enterprise operational app.",
    with_collection: bool = True,
    with_unlinked_entity: bool = False,
) -> ApplicationIR:
    entities = [
        Entity(
            "Article",
            (
                Field("id", FieldType.UUID),
                Field("title", FieldType.STRING),
                Field("published", FieldType.BOOL),
            ),
        ),
    ]
    apis = [
        ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
    ]
    screens = []
    if with_collection:
        screens.append(
            Screen(
                "article_list",
                "user",
                components=("list",),
                actions=("view",),
            )
        )
    if with_unlinked_entity:
        entities.append(
            Entity(
                "LogEntry",
                (
                    Field("id", FieldType.UUID),
                    Field("message", FieldType.STRING),
                ),
            )
        )
        apis.append(ApiEndpoint(HttpMethod.GET, "/log-entries", response_schema="LogEntry"))

    return ApplicationIR(
        name=name,
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=(Role("user"),),
        entities=tuple(entities),
        apis=tuple(apis),
        screens=tuple(screens),
    )


class OverviewDashboardLinksAndHealthTests(unittest.TestCase):
    """Test suite verifying interactive entity cards, operational badge, and metrics on overview page."""

    def test_overview_page_entity_card_links_to_collection_screen(self) -> None:
        """Entity summary card wraps in Link when a collection screen matches the entity."""
        ir = _make_ir(with_collection=True)
        page = _overview_page(ir)

        # Entity card should link to article_list
        self.assertIn('href="/article_list"', page)
        self.assertIn('aria-label="View Articles collection"', page)
        self.assertIn("View all &rarr;", page)

    def test_overview_page_entity_card_without_collection_screen_is_div(self) -> None:
        """Entity summary card renders as div when no collection screen matches."""
        ir = _make_ir(with_collection=False, with_unlinked_entity=False)
        page = _overview_page(ir)

        # No screens exist, so no Link href should be generated for article
        self.assertNotIn('href="/article_list"', page)
        self.assertIn("ARTICLE", page.upper())
        self.assertIn("articleList.total", page)
        # Should not have "View all &rarr;" link
        self.assertNotIn("View all &rarr;", page)

    def test_overview_page_mixed_entity_cards(self) -> None:
        """One entity with collection links, one entity without collection renders as div."""
        ir = _make_ir(with_collection=True, with_unlinked_entity=True)
        page = _overview_page(ir)

        # Article has article_list
        self.assertIn('href="/article_list"', page)
        self.assertIn('aria-label="View Articles collection"', page)

        # LogEntry does not have a collection screen
        self.assertIn("LOGENTRY", page.upper())
        self.assertIn("logEntryList.total", page)
        self.assertNotIn('aria-label="View LogEntrys collection"', page)

    def test_overview_page_header_operational_badge(self) -> None:
        """Dashboard header renders 'System Operational' badge with green dot indicator."""
        ir = _make_ir()
        page = _overview_page(ir)

        self.assertIn("System Operational", page)
        self.assertIn("#22c55e", page)  # Green indicator dot
        self.assertIn("#f0fdf4", page)  # Pill background

    def test_overview_page_header_metric_chips(self) -> None:
        """Dashboard header renders entity count and screen count chips."""
        ir = _make_ir(with_collection=True, with_unlinked_entity=True)
        page = _overview_page(ir)

        self.assertIn("2 Entities", page)
        self.assertIn("1 Screen", page)

    def test_overview_page_screen_nav_cards_arrow_indicator(self) -> None:
        """Screen nav cards include navigation arrow (&rarr;)."""
        ir = _make_ir(with_collection=True)
        page = _overview_page(ir)

        self.assertIn("&rarr;", page)

    def test_overview_page_empty_state_zero_entities_and_screens(self) -> None:
        """When no entities or screens are configured, an accessible empty state card is rendered."""
        ir = ApplicationIR(
            name="Empty Workspace",
            description="Empty project description.",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            roles=(),
            entities=(),
            apis=(),
            screens=(),
        )
        page = _overview_page(ir)

        self.assertIn('"use client";', page)
        self.assertIn("export default function HomePage()", page)
        self.assertIn("Empty Workspace", page)
        self.assertIn("No entities or screens configured yet", page)

    def test_overview_page_diff_invariance_across_ir_description(self) -> None:
        """Changing ir.description produces 100% byte-identical app/page.tsx."""
        ir1 = _make_ir(description="Alpha version description text.")
        ir2 = _make_ir(description="Omega completely different description text.")

        page1 = _overview_page(ir1)
        page2 = _overview_page(ir2)

        self.assertEqual(page1, page2, "app/page.tsx must be 100% byte-identical regardless of ir.description")

    def test_full_project_generation_examples(self) -> None:
        """Full project generation via NextjsWebAdapter includes enhanced overview page."""
        for slug in ("minimal-blog", "rideshare-favourites"):
            ir = example_ir(slug)
            adapter = NextjsWebAdapter()
            proj = adapter.generate(ir)
            f = next((file for file in proj.files() if file.path == "app/page.tsx"), None)
            self.assertIsNotNone(f, f"app/page.tsx missing for {slug}")
            assert f is not None
            content = f.content
            self.assertIn("System Operational", content)
            self.assertIn("Entities", content)
            self.assertIn("Screens", content)


if __name__ == "__main__":
    unittest.main()
