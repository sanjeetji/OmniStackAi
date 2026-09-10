"""Task R-296: Generated Web App Accessibility Pass.

Verifies semantic WAI-ARIA roles, live regions, table sort state, and accessible search/pagination controls.
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
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_screen_page


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(description: str = "Publishing platform.") -> ApplicationIR:
    return ApplicationIR(
        name="Article Platform",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("author"),),
        entities=(
            Entity(
                "Article",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("status", FieldType.STRING, validation=("enum:draft|published",)),
                ),
                relations=(Relation("comments", "Comment", RelationKind.ONE_TO_MANY),),
            ),
            Entity(
                "Comment",
                (
                    Field("id", FieldType.UUID),
                    Field("article_id", FieldType.UUID, required=True),
                    Field("body", FieldType.TEXT, required=True),
                ),
                relations=(Relation("article", "Article", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.DELETE, "/articles/{id}"),
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.DELETE, "/comments/{id}"),
        ),
        screens=(
            Screen("article_list", "author", components=("list",), actions=("view",)),
            Screen("article_detail", "author", components=("detail",), actions=("view",)),
            Screen("article_editor", "author", components=("form",), actions=("create", "edit")),
        ),
    )


def _collection_page(description: str = "Publishing platform.") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "article_list"), ir)


def _detail_page(description: str = "Publishing platform.") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "article_detail"), ir)


def _form_page(description: str = "Publishing platform.") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "article_editor"), ir)


class ErrorBannerAccessibilityTests(TestCase):
    def test_collection_error_banner_has_alert_role_and_assertive_live(self) -> None:
        page = _collection_page()
        self.assertIn('<div role="alert" aria-live="assertive"', page)

    def test_detail_main_error_banner_has_alert_role_and_assertive_live(self) -> None:
        page = _detail_page()
        self.assertIn('<div role="alert" aria-live="assertive"', page)

    def test_subcollection_error_banner_has_alert_role_and_assertive_live(self) -> None:
        col_page = _collection_page()
        detail_page = _detail_page()
        # Both subcollection render sites must have role="alert" aria-live="assertive"
        self.assertIn('<div role="alert" aria-live="assertive" style={{ padding: "8px 12px"', col_page)
        self.assertIn('<div role="alert" aria-live="assertive" style={{ padding: "8px 12px"', detail_page)

    def test_form_error_banner_has_alert_role_and_assertive_live(self) -> None:
        page = _form_page()
        self.assertIn('<div role="alert" aria-live="assertive"', page)


class SearchInputAccessibilityTests(TestCase):
    def test_collection_search_has_aria_label(self) -> None:
        page = _collection_page()
        self.assertIn('aria-label="Search Articles"', page)

    def test_subcollection_search_has_aria_label(self) -> None:
        page = _collection_page()
        self.assertIn('aria-label="Search comments"', page)
        detail_page = _detail_page()
        self.assertIn('aria-label="Search comments"', detail_page)


class TableHeaderSortAccessibilityTests(TestCase):
    def test_collection_sortable_headers_have_aria_sort(self) -> None:
        page = _collection_page()
        self.assertIn('aria-sort={params.sort === "title" ? (params.order === "desc" ? "descending" : "ascending") : "none"}', page)
        self.assertIn('aria-sort={params.sort === "status" ? (params.order === "desc" ? "descending" : "ascending") : "none"}', page)


class PaginationAccessibilityTests(TestCase):
    def test_collection_pagination_nav_and_button_labels(self) -> None:
        page = _collection_page()
        self.assertIn('<nav aria-label="Pagination"', page)
        self.assertIn('aria-label="Previous page"', page)
        self.assertIn('aria-label="Next page"', page)

    def test_subcollection_pagination_button_labels(self) -> None:
        page = _collection_page()
        detail_page = _detail_page()
        self.assertIn('aria-label="Previous page"', page)
        self.assertIn('aria-label="Next page"', page)
        self.assertIn('aria-label="Previous page"', detail_page)
        self.assertIn('aria-label="Next page"', detail_page)


class EmptyStateAccessibilityTests(TestCase):
    def test_collection_empty_states_have_status_role(self) -> None:
        page = _collection_page()
        self.assertIn('<div role="status">No Articles match the active filter criteria.</div>', page)
        self.assertIn('<div role="status">No Articles matching &ldquo;{searchInput}&rdquo;.</div>', page)
        self.assertIn('<div role="status">No Articles found yet.</div>', page)

    def test_subcollection_empty_state_has_status_role(self) -> None:
        for page in (_collection_page(), _detail_page()):
            self.assertIn('role="status"', page)
            self.assertIn('No comments found for this article.</div>', page)


class SafetyTests(TestCase):
    def test_diff_invariance_across_description(self) -> None:
        for fn in (_collection_page, _detail_page, _form_page):
            self.assertEqual(fn("First"), fn("A different description"))

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest

    unittest.main()
