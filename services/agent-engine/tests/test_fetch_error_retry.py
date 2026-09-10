"""Task R-295: Consistent Error + Retry affordance across every generated fetch state.

The collection list already renders a "Retry" button (calling refetch()) in its error banner. This task
brings the detail-screen main error state and both subcollection (master-detail) error states to parity.
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
    MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
    BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
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
                (Field("id", FieldType.UUID), Field("title", FieldType.STRING, required=True)),
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
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
        ),
        screens=(
            Screen("article_list", "author", components=("list",), actions=("view",)),
            Screen("article_detail", "author", components=("detail",), actions=("view",)),
        ),
    )


def _collection_page(description: str = "Publishing platform.") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "article_list"), ir)


def _detail_page(description: str = "Publishing platform.") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "article_detail"), ir)


_SUBCOL_RETRY = "onClick={() => commentsSubcol.refetch()}"
_RETRY_BUTTON_TAIL = 'border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>Retry</button>'


class DetailMainErrorRetryTests(TestCase):
    def setUp(self) -> None:
        self.page = _detail_page()

    def test_detail_main_error_has_retry(self) -> None:
        self.assertIn("<span>Error loading Article: {error.message}</span>", self.page)
        self.assertIn("onClick={() => refetch()}", self.page)

    def test_detail_main_error_message_preserved(self) -> None:
        self.assertIn("{error.message}", self.page)


class SubcollectionErrorRetryTests(TestCase):
    def test_collection_master_detail_subcol_error_has_retry(self) -> None:
        page = _collection_page()
        self.assertIn(_SUBCOL_RETRY, page)
        self.assertIn("<span>Error: {commentsSubcol.error.message}</span>", page)

    def test_detail_subcol_error_has_retry(self) -> None:
        page = _detail_page()
        self.assertIn(_SUBCOL_RETRY, page)
        self.assertIn("commentsSubcol.error.message", page)


class RetryCountTests(TestCase):
    def test_collection_has_two_retry_buttons(self) -> None:
        # top-level list error (pre-existing) + subcollection error (new)
        self.assertEqual(_collection_page().count("Retry</button>"), 2)

    def test_detail_has_two_retry_buttons(self) -> None:
        # main detail error (new) + subcollection error (new)
        self.assertEqual(_detail_page().count("Retry</button>"), 2)


class SafetyTests(TestCase):
    def test_diff_invariance_across_description(self) -> None:
        for fn in (_collection_page, _detail_page):
            self.assertEqual(fn("First"), fn("A different description"))

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest

    unittest.main()
