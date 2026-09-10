"""Task R-292: Loading Skeletons for Generated Next.js Screens.

The collection table, subcollection (master-detail) lists, and detail-screen main content render
layout-preserving skeleton placeholders while loading, instead of a plain "Loading..." line.
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


def _ir(description: str = "Blog") -> ApplicationIR:
    return ApplicationIR(
        name="Blog App",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("member"),),
        entities=(
            Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
            Entity(
                "Comment",
                (Field("id", FieldType.UUID), Field("body", FieldType.TEXT)),
                relations=(Relation("post", "Post", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", response_schema="Comment"),
        ),
        screens=(
            Screen("post_list", "member", components=("list",), actions=("open",)),
            Screen("post_detail", "member", components=("detail",), actions=("view",)),
        ),
    )


def _list_page(description: str = "Blog") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "post_list"), ir)


def _detail_page(description: str = "Blog") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "post_detail"), ir)


class CollectionSkeletonTests(TestCase):
    def setUp(self) -> None:
        self.page = _list_page()

    def test_collection_loading_renders_skeleton_bars(self) -> None:
        self.assertIn("{loading && !data && (", self.page)
        self.assertIn("{[0, 1, 2, 3, 4].map((i) => (", self.page)
        self.assertIn('<div key={i} style={{ height: 14, background: "#e2e8f0", borderRadius: 4, margin: "10px 0", opacity: 1 - i * 0.15 }} />', self.page)

    def test_collection_loading_text_removed(self) -> None:
        self.assertNotIn("Loading Posts... ", self.page)

    def test_refresh_button_label_unchanged(self) -> None:
        # the Refresh button still shows a textual loading label — not part of this task
        self.assertIn('{loading ? "Loading..." : "Refresh"}', self.page)


class SubcollectionSkeletonTests(TestCase):
    def _check(self, page: str) -> None:
        self.assertIn("{commentsSubcol.loading && !commentsSubcol.data && (", page)
        self.assertIn("{[0, 1, 2].map((i) => (", page)
        self.assertIn('<div key={i} style={{ height: 44, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2 }} />', page)
        self.assertNotIn("Loading comments...", page)

    def test_collection_master_detail_subcollection_skeleton(self) -> None:
        self._check(_list_page())

    def test_detail_screen_subcollection_skeleton(self) -> None:
        self._check(_detail_page())


class DetailSkeletonTests(TestCase):
    def setUp(self) -> None:
        self.page = _detail_page()

    def test_detail_main_loading_renders_skeleton_lines(self) -> None:
        self.assertIn("{loading && (", self.page)
        self.assertIn("{[0, 1, 2, 3].map((i) => (", self.page)
        self.assertIn('<div key={i} style={{ height: 14, background: "#e2e8f0", borderRadius: 4, width: `${88 - i * 14}%` }} />', self.page)

    def test_detail_main_loading_text_removed(self) -> None:
        # the singular detail-main "Loading Post..." is gone (the plural record-selector text is separate)
        self.assertNotIn("Loading Post...</div>", self.page)


class SafetyTests(TestCase):
    def test_diff_invariance_across_ir_description(self) -> None:
        for fn in (_list_page, _detail_page):
            self.assertEqual(fn("First"), fn("A different description"))

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest

    unittest.main()
