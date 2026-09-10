"""Task R-291: Optimistic Subcollection Child Delete with Rollback.

Deleting a child row in a subcollection (master-detail) list hides it immediately via a per-subcollection
deleting overlay and rolls it back (row reappears + error toast) if the server rejects; a reconcile
effect prunes ids once the subcollection refetch removes them. Applies in both the collection
master-detail screen and the dedicated detail screen.
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


def _ir(with_child_delete: bool = True, description: str = "Blog") -> ApplicationIR:
    apis = [
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", response_schema="Comment"),
    ]
    if with_child_delete:
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/comments/{id}", response_schema="Comment"))
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
        apis=tuple(apis),
        screens=(
            Screen("post_list", "member", components=("list",), actions=("open",)),
            Screen("post_detail", "member", components=("detail",), actions=("view",)),
        ),
    )


def _list_page(**kw) -> str:
    ir = _ir(**kw)
    return render_screen_page(next(s for s in ir.screens if s.id == "post_list"), ir)


def _detail_page(**kw) -> str:
    ir = _ir(**kw)
    return render_screen_page(next(s for s in ir.screens if s.id == "post_detail"), ir)


class OptimisticSubcollectionDeleteChecks:
    def _check(self, page: str) -> None:
        # per-subcollection deleting overlay + reconcile effect
        self.assertIn("const [commentsSubcolDeleting, setCommentsSubcolDeleting] = useState<string[]>([]);", page)
        self.assertIn(
            "setCommentsSubcolDeleting((prev) => prev.filter((did) => (commentsSubcol.data ?? []).some((x: any) => String(x.id) === did)));",
            page,
        )
        self.assertIn("}, [commentsSubcol.data]);", page)
        # optimistic add before the awaited remove; rollback in catch
        add_at = page.index("setCommentsSubcolDeleting((prev) => [...prev, String(id)]);")
        remove_at = page.index("await removeComment(id);")
        self.assertLess(add_at, remove_at, "must hide the child row before awaiting remove")
        self.assertIn("setCommentsSubcolDeleting((prev) => prev.filter((x) => x !== String(id)));", page)
        # child row map iterates the deleting-filtered list
        self.assertIn(
            "(commentsSubcol.data ?? []).filter((child: any) => !commentsSubcolDeleting.includes(String((child as any).id))).map((child, cIdx) => (",
            page,
        )
        self.assertNotIn("{commentsSubcol.data.map((child, cIdx) => (", page)
        # success path preserved
        self.assertIn("commentsSubcol.refetch();", page)


class CollectionMasterDetailTests(TestCase, OptimisticSubcollectionDeleteChecks):
    def test_collection_master_detail_child_delete_optimistic(self) -> None:
        self._check(_list_page())


class DetailScreenTests(TestCase, OptimisticSubcollectionDeleteChecks):
    def test_detail_screen_child_delete_optimistic(self) -> None:
        self._check(_detail_page())


class ScopeAndSafetyTests(TestCase):
    def test_non_deletable_child_emits_no_deleting_overlay(self) -> None:
        for page in (_list_page(with_child_delete=False), _detail_page(with_child_delete=False)):
            self.assertNotIn("commentsSubcolDeleting", page)
            self.assertIn("{commentsSubcol.data.map((child, cIdx) => (", page)

    def test_diff_invariance_across_ir_description(self) -> None:
        for fn in (_list_page, _detail_page):
            self.assertEqual(fn(description="First"), fn(description="A different description"))

    def test_generated_project_renders_optimistic_child_delete(self) -> None:
        # End-to-end via the adapter, using an IR whose subcollection child is deletable.
        proj = NextjsWebAdapter().generate(_ir(with_child_delete=True))
        pages = [proj.get(p).content for p in proj.paths() if p.endswith("page.tsx")]
        self.assertTrue(any("commentsSubcolDeleting" in p for p in pages))

    def test_example_projects_still_generate(self) -> None:
        # The bundled examples have no deletable subcollection child; generation must remain unaffected.
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            for p in proj.paths():
                if p.endswith("page.tsx"):
                    self.assertNotIn("SubcolDeleting", proj.get(p).content)


if __name__ == "__main__":
    import unittest

    unittest.main()
