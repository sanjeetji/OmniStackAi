"""Task R-293: Loading skeletons for the form initial-load banner and the detail record-selector list.

Completes the R-292 skeleton coverage for the two remaining plain "Loading..." spots.
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
        entities=(Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
            ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
            ApiEndpoint(HttpMethod.PUT, "/posts/{id}", request_schema="Post", response_schema="Post"),
        ),
        screens=(
            Screen("post_form", "member", components=("form",), actions=("create", "update"), navigation=("post_detail",)),
            Screen("post_detail", "member", components=("detail",), actions=("view",)),
        ),
    )


def _form_page(description: str = "Blog") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "post_form"), ir)


def _detail_page(description: str = "Blog") -> str:
    ir = _ir(description)
    return render_screen_page(next(s for s in ir.screens if s.id == "post_detail"), ir)


class FormInitialLoadSkeletonTests(TestCase):
    def setUp(self) -> None:
        self.page = _form_page()

    def test_form_initial_load_renders_skeletons(self) -> None:
        self.assertIn("{isEdit && fetchingInitial && (", self.page)
        self.assertIn("{[0, 1, 2].map((i) => (", self.page)
        self.assertIn('<div key={i} style={{ height: 34, background: "#e2e8f0", borderRadius: 6, opacity: 1 - i * 0.2 }} />', self.page)

    def test_form_initial_load_text_removed(self) -> None:
        self.assertNotIn("Loading post details...", self.page)
        self.assertNotIn("details...", self.page)


class DetailRecordSelectorSkeletonTests(TestCase):
    def setUp(self) -> None:
        self.page = _detail_page()

    def test_record_selector_loading_renders_skeleton_cards(self) -> None:
        self.assertIn("{loadingList && (", self.page)
        self.assertIn('<div key={i} style={{ height: 56, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2 }} />', self.page)

    def test_record_selector_loading_text_removed(self) -> None:
        self.assertNotIn("Loading Posts...", self.page)


class SafetyTests(TestCase):
    def test_diff_invariance_across_ir_description(self) -> None:
        for fn in (_form_page, _detail_page):
            self.assertEqual(fn("First"), fn("A different description"))

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest

    unittest.main()
