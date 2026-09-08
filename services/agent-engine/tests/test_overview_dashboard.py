"""Task R-275: Rich App Dashboard Overview Page in Generated Next.js Web App.

Tests:
1.  Overview page is a client component (starts with "use client";).
2.  Overview page imports useList hooks for entities with Op.LIST.
3.  Overview page renders entity name in count card section.
4.  Overview page renders screen IDs as href values in nav cards.
5.  Overview page renders Quick Actions with '+ Create' link to form screen.
6.  Overview page does NOT embed ir.description in the output.
7.  Overview page references .total for live count display.
8.  Overview page falls back cleanly when ir.entities is empty.
9.  Overview page falls back cleanly when ir.screens is empty.
10. Overview page produces byte-identical output for different ir.description values.
11. Overview page renders collection screen navigation card.
12. Overview page renders form screen in Quick Actions section.
13. Overview page renders role badge for non-public screens.
14. Overview page emits no hook for an entity without Op.LIST wired.
15. Full Next.js project generation includes app/page.tsx.
16. Detail screens are excluded from the screen navigation card grid.
"""

from unittest import TestCase

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


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _dashboard_ir(description: str = "A test platform.") -> ApplicationIR:
    """IR with Articles (full CRUD), Comments (list only), and Tags (create only).

    Screens:
     - article_list (collection, public)
     - article_editor (form, author role)
     - article_detail (detail, public) — should be EXCLUDED from nav cards
     - comment_list (collection, public)
     - tag_editor (form, admin role)
    """
    return ApplicationIR(
        name="Test Platform",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("public"), Role("author"), Role("admin")),
        entities=(
            Entity(
                "Article",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("content", FieldType.TEXT),
                ),
            ),
            Entity(
                "Comment",
                (
                    Field("id", FieldType.UUID),
                    Field("body", FieldType.TEXT, required=True),
                ),
            ),
            Entity(
                "Tag",
                (
                    Field("id", FieldType.UUID),
                    Field("label", FieldType.STRING, required=True),
                ),
            ),
        ),
        apis=(
            # Article: full CRUD
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.DELETE, "/articles/{id}"),
            # Comment: list only (no Op.CREATE / Op.DELETE)
            ApiEndpoint(HttpMethod.GET, "/comments", response_schema="Comment"),
            # Tag: create only (no Op.LIST)
            ApiEndpoint(HttpMethod.POST, "/tags", request_schema="Tag", response_schema="Tag"),
        ),
        screens=(
            Screen("article_list", "public", components=("list",), actions=("view",)),
            Screen("article_editor", "author", components=("form",), actions=("create", "update")),
            Screen("article_detail", "public", components=("detail",), actions=("view",)),
            Screen("comment_list", "public", components=("list",), actions=("view",)),
            Screen("tag_editor", "admin", components=("form",), actions=("create",)),
        ),
    )


def _get_overview_page(ir: ApplicationIR) -> str:
    """Generate the full Next.js project and return the content of app/page.tsx."""
    adapter = NextjsWebAdapter()
    project = adapter.generate(ir)
    return project.get("app/page.tsx").content


class OverviewDashboardTests(TestCase):
    """Tests for the rich dashboard overview page (R-275)."""

    # ── Test 1: client component ──────────────────────────────────────────────

    def test_overview_page_is_client_component(self) -> None:
        """app/page.tsx must start with "use client"; to enable React hooks."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        self.assertTrue(
            page.startswith('"use client";'),
            f'Expected page to start with \'"use client";\' but got: {page[:60]!r}',
        )

    # ── Test 2: hook imports ──────────────────────────────────────────────────

    def test_overview_page_imports_uselist_hooks(self) -> None:
        """Overview imports useList hooks for entities with Op.LIST (Article, Comment)."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        # Article and Comment have Op.LIST; Tag does not.
        self.assertIn("useListArticles", page)
        self.assertIn("useListComments", page)

    # ── Test 3: entity card section ───────────────────────────────────────────

    def test_overview_page_has_entity_cards(self) -> None:
        """Entity names with Op.LIST appear in the count card section."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        # Both should appear as card labels
        self.assertIn("Article", page)
        self.assertIn("Comment", page)

    # ── Test 4: screen nav hrefs ──────────────────────────────────────────────

    def test_overview_page_has_screen_nav_links(self) -> None:
        """Primary screen IDs appear as href values in screen navigation cards."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        self.assertIn('href="/article_list"', page)
        self.assertIn('href="/comment_list"', page)
        self.assertIn('href="/tag_editor"', page)

    # ── Test 5: quick actions ─────────────────────────────────────────────────

    def test_overview_page_has_quick_actions(self) -> None:
        """Quick Actions section renders '+ Create Article' link for article_editor screen."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        self.assertIn("Quick Actions", page)
        self.assertIn("+ Create Article", page)

    # ── Test 6: no ir.description ─────────────────────────────────────────────

    def test_overview_page_no_ir_description(self) -> None:
        """ir.description must NOT appear in app/page.tsx (diff invariance fix)."""
        description = "UNIQUE_SENTINEL_DESCRIPTION_XYZ_12345"
        ir = _dashboard_ir(description=description)
        page = _get_overview_page(ir)
        self.assertNotIn(
            description,
            page,
            "ir.description must not be embedded in app/page.tsx — it lives in README.md.",
        )

    # ── Test 7: .total reference ──────────────────────────────────────────────

    def test_overview_page_shows_total_count(self) -> None:
        """Page references .total from useList hook state for live count display."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        self.assertIn(".total", page)

    # ── Test 8: no entities fallback ──────────────────────────────────────────

    def test_overview_page_no_entities_fallback(self) -> None:
        """Page renders without errors or broken imports when ir.entities is empty."""
        ir = ApplicationIR(
            name="Empty App",
            description="No entities.",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            roles=(),
            entities=(),
            apis=(),
            screens=(),
        )
        page = _get_overview_page(ir)
        # Must still be a valid file: starts with "use client"; and has HomePage
        self.assertIn('"use client";', page)
        self.assertIn("export default function HomePage()", page)
        # No broken hook imports
        self.assertNotIn("useList", page)

    # ── Test 9: no screens fallback ───────────────────────────────────────────

    def test_overview_page_no_screens_fallback(self) -> None:
        """Page renders cleanly when ir.screens is empty."""
        ir = ApplicationIR(
            name="No Screens App",
            description="Has entities but no screens.",
            platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=_STRATEGY,
            roles=(),
            entities=(
                Entity("Article", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
            ),
            apis=(ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),),
            screens=(),
        )
        page = _get_overview_page(ir)
        self.assertIn('"use client";', page)
        self.assertIn("export default function HomePage()", page)
        # No screen nav section
        self.assertNotIn("href=", page)

    # ── Test 10: diff invariance ──────────────────────────────────────────────

    def test_overview_page_diff_invariance(self) -> None:
        """Changing ir.description must produce byte-identical app/page.tsx output."""
        ir_a = _dashboard_ir(description="First description value.")
        ir_b = _dashboard_ir(description="Completely different description value!")
        page_a = _get_overview_page(ir_a)
        page_b = _get_overview_page(ir_b)
        self.assertEqual(
            page_a,
            page_b,
            "app/page.tsx must not change when only ir.description changes.",
        )

    # ── Test 11: collection screen card ──────────────────────────────────────

    def test_overview_page_link_to_collection_screen(self) -> None:
        """Collection screen renders as a nav card with correct href and label."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        self.assertIn('href="/article_list"', page)
        self.assertIn("Collection", page)

    # ── Test 12: form screen quick action ─────────────────────────────────────

    def test_overview_page_link_to_form_screen(self) -> None:
        """Form screen appears in Quick Actions with '+ Create' CTA."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        self.assertIn('href="/article_editor"', page)
        self.assertIn("+ Create", page)

    # ── Test 13: role badge ───────────────────────────────────────────────────

    def test_overview_page_role_badge_on_restricted_screen(self) -> None:
        """Non-public screens (e.g. 'author', 'admin') render a role badge in nav card."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        # article_editor has role='author', tag_editor has role='admin'
        self.assertIn("author", page)
        self.assertIn("admin", page)

    # ── Test 14: entity without Op.LIST — no hook ─────────────────────────────

    def test_overview_page_entity_without_list_op_no_hook(self) -> None:
        """No useListTags hook emitted because Tag has no Op.LIST endpoint."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        # Tag only has Op.CREATE; its hook must NOT be imported
        self.assertNotIn("useListTags", page)

    # ── Test 15: full project generation ─────────────────────────────────────

    def test_full_project_overview_page_present(self) -> None:
        """NextjsWebAdapter.generate() includes app/page.tsx for example IRs."""
        for ir in (example_ir("rideshare-favourites"), example_ir("minimal-blog")):
            adapter = NextjsWebAdapter()
            project = adapter.generate(ir)
            paths = set(project.paths())
            self.assertIn("app/page.tsx", paths, f"app/page.tsx missing for {ir.name}")

    # ── Test 16: detail screens excluded ─────────────────────────────────────

    def test_overview_page_no_detail_screens_in_nav(self) -> None:
        """Detail screens (article_detail) must NOT appear as nav cards in the overview."""
        ir = _dashboard_ir()
        page = _get_overview_page(ir)
        # article_detail is a detail screen — its id must not appear as a nav href
        self.assertNotIn('href="/article_detail"', page)
