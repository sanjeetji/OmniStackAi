"""Task R-289: Debounced Live Subcollection Search.

The generated subcollection (master-detail) search must be live + debounced (300ms), matching the
top-level collection search (R-280) and driven by the race-safe R-286 useList<Child>By<Parent> hook.
Applies to both the collection master-detail screen and the dedicated detail screen.
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


def _list_page() -> str:
    ir = _ir()
    return render_screen_page(next(s for s in ir.screens if s.id == "post_list"), ir)


def _detail_page() -> str:
    ir = _ir()
    return render_screen_page(next(s for s in ir.screens if s.id == "post_detail"), ir)


class DebouncedSubcollectionSearchChecks:
    """Assertions that must hold on any page rendering the Post->Comment subcollection search."""

    def _check(self, page: str) -> None:
        # per-subcollection controlled search state
        self.assertIn('const [commentsSubcolSearch, setCommentsSubcolSearch] = useState("");', page)
        # 300ms debounce effect committing to the hook's setSearch (guarded against redundant recommit)
        self.assertIn("const timer = setTimeout(() => {", page)
        self.assertIn('if (commentsSubcolSearch !== (commentsSubcol.params.q ?? "")) commentsSubcol.setSearch(commentsSubcolSearch.trim());', page)
        self.assertIn("}, 300);", page)
        self.assertIn("return () => clearTimeout(timer);", page)
        self.assertIn("}, [commentsSubcolSearch, commentsSubcol.params.q]);", page)
        # controlled input (value + onChange), no uncontrolled defaultValue / FormData anymore
        self.assertIn("value={commentsSubcolSearch}", page)
        self.assertIn("onChange={(e) => setCommentsSubcolSearch(e.target.value)}", page)
        self.assertNotIn('defaultValue={commentsSubcol.params.q ?? ""}', page)
        self.assertNotIn("new FormData(e.currentTarget)", page)
        # form submit still commits immediately (Enter)
        self.assertIn("commentsSubcol.setSearch(commentsSubcolSearch.trim());", page)


class CollectionMasterDetailDebounceTests(TestCase, DebouncedSubcollectionSearchChecks):
    def test_collection_master_detail_search_is_debounced(self) -> None:
        self._check(_list_page())


class DetailScreenDebounceTests(TestCase, DebouncedSubcollectionSearchChecks):
    def test_detail_screen_search_is_debounced(self) -> None:
        self._check(_detail_page())


class ScopeAndSafetyTests(TestCase):
    def test_no_subcollection_emits_no_search_state(self) -> None:
        ir = example_ir("rideshare-favourites")
        for screen in ir.screens:
            page = render_screen_page(screen, ir)
            self.assertNotIn("SubcolSearch", page)

    def test_diff_invariance_across_ir_description(self) -> None:
        a = _ir("First description")
        b = _ir("A totally different description")
        for sid in ("post_list", "post_detail"):
            self.assertEqual(
                render_screen_page(next(s for s in a.screens if s.id == sid), a),
                render_screen_page(next(s for s in b.screens if s.id == sid), b),
            )

    def test_demo_project_renders_debounced_subcollection_search(self) -> None:
        proj = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        pages = [proj.get(p).content for p in proj.paths() if p.endswith("page.tsx")]
        self.assertTrue(
            any('const [commentsSubcolSearch, setCommentsSubcolSearch] = useState("");' in p for p in pages),
            "minimal-blog should render a debounced subcollection search",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
