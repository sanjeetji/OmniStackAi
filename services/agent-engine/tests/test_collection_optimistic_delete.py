"""Task R-290: Optimistic Delete with Rollback in the Generated Collection Screen.

Single (handleDelete) and batch (handleBatchDelete) deletions hide the affected rows immediately via a
pendingDeleteIds overlay and roll them back (row reappears + error toast) if the server rejects; a
reconcile effect prunes ids once refetch removes them. Self-contained in the collection screen.
"""

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
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_screen_page


def _make_ir(with_delete: bool = True, description: str = "Test App") -> ApplicationIR:
    apis = [
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
    ]
    if with_delete:
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"))
    return ApplicationIR(
        name="Blog App",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=(
            Entity("Post", (
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
            )),
        ),
        apis=tuple(apis),
        screens=(
            Screen("posts", "admin", components=("list",),
                   actions=("view", "delete") if with_delete else ("view",), navigation=()),
        ),
    )


def _list_page(with_delete: bool = True, description: str = "Test App") -> str:
    ir = _make_ir(with_delete=with_delete, description=description)
    return render_screen_page(ir.screens[0], ir)


class OptimisticDeleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = _list_page()

    def test_declares_pending_delete_state(self) -> None:
        self.assertIn("const [pendingDeleteIds, setPendingDeleteIds] = useState<string[]>([]);", self.page)

    def test_reconcile_effect_prunes_pending_on_data_change(self) -> None:
        self.assertIn(
            "setPendingDeleteIds((prev) => prev.filter((id) => (data ?? []).some((x: any) => String(x.id) === id)));",
            self.page,
        )
        self.assertIn("}, [data]);", self.page)

    def test_visible_rows_filters_pending(self) -> None:
        self.assertIn(
            "const visibleRows = displayData.filter((item: any) => !pendingDeleteIds.includes(String((item as any).id)));",
            self.page,
        )
        self.assertIn("visibleRows.map((item, idx) => (", self.page)
        # no longer maps the unfiltered source directly
        self.assertNotIn("{data && displayData.map((item, idx) => (", self.page)
        self.assertNotIn("{data && data.map((item, idx) => (", self.page)

    def test_single_delete_is_optimistic_with_rollback(self) -> None:
        # optimistic hide happens before the awaited remove
        add_at = self.page.index("setPendingDeleteIds((prev) => [...prev, String(id)]);")
        remove_at = self.page.index("await remove(id);")
        self.assertLess(add_at, remove_at, "must hide the row before awaiting remove")
        # rollback in catch (row reappears) precedes the error toast
        rollback_at = self.page.index("setPendingDeleteIds((prev) => prev.filter((x) => x !== String(id)));")
        toast_err_at = self.page.index('toast.error(err instanceof Error ? err.message : "Failed to delete Post");')
        self.assertLess(rollback_at, toast_err_at, "must roll back before showing the error toast")

    def test_batch_delete_is_optimistic_with_rollback(self) -> None:
        self.assertIn("const ids = checkedIds.map(String);", self.page)
        self.assertIn("setPendingDeleteIds((prev) => [...prev, ...ids]);", self.page)
        self.assertIn("setPendingDeleteIds((prev) => prev.filter((x) => !ids.includes(x)));", self.page)

    def test_success_path_preserved(self) -> None:
        # existing behaviour intact
        self.assertIn("refetch();", self.page)
        self.assertIn('toast.success("Post deleted successfully");', self.page)


class ScopeAndSafetyTests(unittest.TestCase):
    def test_no_delete_emits_no_optimistic_delete_handler(self) -> None:
        # The pending overlay is list-management state (emitted like checkedIds), but with no delete wired
        # there is no delete handler adding to it and no delete-triggered rollback.
        page = _list_page(with_delete=False)
        self.assertNotIn("setPendingDeleteIds((prev) => [...prev, String(id)]);", page)
        self.assertNotIn("const handleDelete = async (id: string) => {", page)
        self.assertNotIn("const handleBatchDelete", page)

    def test_diff_invariance_across_ir_description(self) -> None:
        self.assertEqual(_list_page(description="First"), _list_page(description="A different description"))

    def test_demo_project_generates(self) -> None:
        proj = NextjsWebAdapter().generate(_make_ir())
        pages = [proj.get(p).content for p in proj.paths() if p.endswith("page.tsx")]
        self.assertTrue(any("pendingDeleteIds" in p for p in pages))


if __name__ == "__main__":
    unittest.main()
