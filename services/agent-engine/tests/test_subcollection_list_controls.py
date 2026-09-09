"""Task R-281: pagination + sort + search controls on subcollection master-detail lists.

The generated subcollection lists (in both the collection master-detail screen and the dedicated detail
screen) must expose a search form, a sort <select>, and a Prev/Next pagination footer, all driven by the
already-generated useList<Child>By<Parent> hook (setSearch / setSort / setPage). No new component state
(the search input is uncontrolled). Diff invariant across ir.description.
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


def _ir(description: str = "Blog with posts and comments") -> ApplicationIR:
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
                (
                    Field("id", FieldType.UUID),
                    Field("body", FieldType.TEXT),
                    Field("author", FieldType.STRING),
                ),
                relations=(Relation("post", "Post", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.DELETE, "/comments/{id}", response_schema="Comment"),
        ),
        screens=(
            Screen("post_list", "member", components=("list",), actions=("open",)),
            Screen("post_detail", "member", components=("detail",), actions=("view",)),
        ),
    )


def _list_page() -> str:
    ir = _ir()
    return render_screen_page(next(s for s in ir.screens if s.id == "post_list"), ir)


def _detail_page() -> str:
    ir = _ir()
    return render_screen_page(next(s for s in ir.screens if s.id == "post_detail"), ir)


class SubcollectionControlsSharedChecks:
    """Assertions that must hold on any page rendering the Post->Comment subcollection."""

    def _check(self, page: str) -> None:
        # Search form: uncontrolled (defaultValue + FormData on submit) — no new component state.
        self.assertIn(
            'onSubmit={(e) => { e.preventDefault(); commentsSubcol.setSearch(((new FormData(e.currentTarget).get("q") as string) ?? "").trim()); }}',
            page,
        )
        self.assertIn('defaultValue={commentsSubcol.params.q ?? ""}', page)
        self.assertIn('placeholder="Search comments..."', page)
        # Sort select driven by setSort, showing id + display fields (body, author), both directions.
        self.assertIn('aria-label="Sort comments"', page)
        self.assertIn('const [sf, so] = e.target.value.split(":"); commentsSubcol.setSort(sf, so as "asc" | "desc");', page)
        for opt in ('value="id:asc"', 'value="id:desc"', 'value="body:asc"', 'value="author:desc"'):
            self.assertIn(opt, page)
        # Pagination footer driven by setPage / page / totalPages / total.
        self.assertIn("{commentsSubcol.totalPages > 1 && (", page)
        self.assertIn("commentsSubcol.setPage(commentsSubcol.page - 1)", page)
        self.assertIn("commentsSubcol.setPage(commentsSubcol.page + 1)", page)
        self.assertIn("Page {commentsSubcol.page} of {commentsSubcol.totalPages} ({commentsSubcol.total} total)", page)
        self.assertIn("disabled={commentsSubcol.page <= 1 || commentsSubcol.loading}", page)


class CollectionMasterDetailControlsTests(TestCase, SubcollectionControlsSharedChecks):
    def test_collection_master_detail_has_subcollection_controls(self) -> None:
        self._check(_list_page())


class DetailScreenControlsTests(TestCase, SubcollectionControlsSharedChecks):
    def test_detail_screen_has_subcollection_controls(self) -> None:
        self._check(_detail_page())


class ScopeAndSafetyTests(TestCase):
    def test_no_subcollections_emits_no_controls(self) -> None:
        # rideshare-favourites has no parent->child subcollection.
        ir = example_ir("rideshare-favourites")
        for screen in ir.screens:
            page = render_screen_page(screen, ir)
            self.assertNotIn("Subcol.setSearch", page)
            self.assertNotIn('aria-label="Sort', page)

    def test_controls_are_uncontrolled_no_extra_state(self) -> None:
        # The subcollection search must not introduce a useState-backed controlled input.
        page = _list_page()
        self.assertNotIn("subSearchInput", page)
        self.assertNotIn("setSubSearch", page)

    def test_diff_invariance_across_ir_description(self) -> None:
        a = _ir("First description")
        b = _ir("A totally different description")
        for sid in ("post_list", "post_detail"):
            self.assertEqual(
                render_screen_page(next(s for s in a.screens if s.id == sid), a),
                render_screen_page(next(s for s in b.screens if s.id == sid), b),
            )

    def test_demo_projects_render_subcollection_controls(self) -> None:
        proj = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        pages = [proj.get(p).content for p in proj.paths() if p.endswith("page.tsx")]
        self.assertTrue(
            any("commentsSubcol.totalPages > 1 && (" in p for p in pages),
            "minimal-blog should render subcollection pagination",
        )
        self.assertTrue(
            any("commentsSubcol.setSort(" in p for p in pages),
            "minimal-blog should render subcollection sort control",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
