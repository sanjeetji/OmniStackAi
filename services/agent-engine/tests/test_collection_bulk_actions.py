"""Task R-270: Bulk Selection & Batch Deletion in Generated Next.js Collection Screens.

Covers:
1. Collection screen declares row selection state (selectedIds, allCurrentIds, isAllSelected)
2. Collection screen emits handleSelectAll, handleToggleRow, and handleClearSelection handlers
3. Table header <thead> renders master checkbox with aria-label="Select all", checked={isAllSelected}, and onChange={handleSelectAll}
4. Table body <tbody> rows render item checkbox with checked={selectedIds.includes((item as any).id)} and onChange
5. Row checkbox cell stops event propagation so row selection doesn't trigger row onClick
6. Contextual Bulk Actions Bar is conditionally rendered when selectedIds.length > 0
7. Bulk Actions Bar renders selection count badge ("{selectedIds.length} {name/plural} selected")
8. Bulk Actions Bar renders "Deselect all" button bound to handleClearSelection
9. Bulk Actions Bar renders "Delete Selected" button when Op.DELETE is wired
10. Bulk Actions Bar omits "Delete Selected" button when Op.DELETE is absent
11. handleBatchDelete prompts user with confirmation dialog including record count
12. handleBatchDelete tracks batchDeleting loading state and disables action button
13. handleBatchDelete catches errors and renders a dismissible batchDeleteError alert banner
14. Individual handleDelete cleans up deleted record ID from selectedIds
15. Loading and empty state colSpan values correctly account for the checkbox column (+1)
16. Strict diff invariance maintained across ir.description modifications
17. Full project generation via NextjsWebAdapter succeeds with zero errors
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
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    _collection_screen_page,
    render_screen_page,
)
from omnistackai_agent_engine.codegen.route_wiring import Op


def _make_test_ir(with_delete: bool = True, description: str = "Test Blog Application") -> ApplicationIR:
    """Construct an IR with posts, comments, forms, and relations."""
    entities = (
        Entity(
            name="Post",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
                Field("content", FieldType.TEXT, required=False),
                Field("published", FieldType.BOOL, required=False),
            ),
            relations=(
                Relation("comments", "Comment", RelationKind.ONE_TO_MANY),
            ),
        ),
        Entity(
            name="Comment",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("post_id", FieldType.STRING, required=True),
                Field("author", FieldType.STRING, required=True),
                Field("body", FieldType.TEXT, required=True),
            ),
            relations=(
                Relation("post", "Post", RelationKind.MANY_TO_ONE),
            ),
        ),
    )

    apis = [
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
        ApiEndpoint(HttpMethod.PUT, "/posts/{id}", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{post_id}/comments", response_schema="Comment"),
        ApiEndpoint(HttpMethod.POST, "/comments", request_schema="Comment", response_schema="Comment"),
    ]
    if with_delete:
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"))
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/comments/{id}", response_schema="Comment"))

    screens = (
        Screen("posts", "admin", components=("list",), actions=("view", "delete") if with_delete else ("view",), navigation=("post_form",)),
        Screen("post_form", "admin", components=("form",), actions=("create", "update"), navigation=("posts",)),
        Screen("comment_form", "admin", components=("form",), actions=("create",), navigation=("posts",)),
    )

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
        entities=entities,
        apis=tuple(apis),
        screens=screens,
    )


class CollectionBulkActionsTests(unittest.TestCase):
    """Test suite for bulk selection & batch deletion in Next.js collection screens."""

    def test_collection_screen_declares_selection_state(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("const [checkedIds, setCheckedIds] = useState<string[]>([]);", content)
        self.assertIn("const allCurrentIds = (data ?? []).map((item: any) => item.id).filter(Boolean);", content)
        self.assertIn("const isAllChecked = allCurrentIds.length > 0 && allCurrentIds.every((id: string) => checkedIds.includes(id));", content)

    def test_collection_screen_emits_select_all_and_toggle_handlers(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("const handleCheckAll = () => {", content)
        self.assertIn("if (isAllChecked) {", content)
        self.assertIn("setCheckedIds((prev) => prev.filter((id) => !allCurrentIds.includes(id)));", content)
        self.assertIn("setCheckedIds((prev) => Array.from(new Set([...prev, ...allCurrentIds])));", content)

        self.assertIn("const handleToggleRow = (id: string) => {", content)
        self.assertIn("setCheckedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));", content)

        self.assertIn("const handleClearSelection = () => {", content)
        self.assertIn("setCheckedIds([]);", content)

    def test_collection_screen_table_header_emits_select_all_checkbox(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn('aria-label="Select all"', content)
        self.assertIn("checked={isAllChecked}", content)
        self.assertIn("onChange={handleCheckAll}", content)

    def test_collection_screen_table_row_emits_item_checkbox(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("aria-label={`Select ${(item as any).id ?? idx}`}", content)
        self.assertIn("checked={checkedIds.includes((item as any).id)}", content)
        self.assertIn("onChange={() => handleToggleRow((item as any).id)}", content)

    def test_collection_screen_checkbox_stops_propagation(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        # The td wrapping the row checkbox must stop propagation to prevent row click
        self.assertIn('onClick={(e) => e.stopPropagation()}', content)

    def test_collection_screen_renders_bulk_actions_bar_when_selected(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("{checkedIds.length > 0 && (", content)
        self.assertIn('{checkedIds.length} {checkedIds.length === 1 ? "Post" : "Posts"} selected', content)

    def test_collection_screen_emits_clear_selection_button(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("Clear selection", content)
        self.assertIn("onClick={handleClearSelection}", content)

    def test_collection_screen_emits_batch_delete_button_when_delete_op_wired(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("const [batchDeleting, setBatchDeleting] = useState<boolean>(false);", content)
        self.assertIn("const [batchDeleteError, setBatchDeleteError] = useState<string | null>(null);", content)
        self.assertIn("const handleBatchDelete = async () => {", content)
        self.assertIn("onClick={handleBatchDelete}", content)
        self.assertIn('{batchDeleting ? "Deleting..." : `Delete Selected (${checkedIds.length})`}', content)

    def test_collection_screen_no_batch_delete_button_when_delete_op_absent(self) -> None:
        ir = _make_test_ir(with_delete=False)
        content = render_screen_page(ir.screens[0], ir)

        self.assertNotIn("handleBatchDelete", content)
        self.assertNotIn("Delete Selected", content)
        self.assertNotIn("batchDeleting", content)
        # But selection state & clear selection still exist for viewing/bulk workflows
        self.assertIn("const [checkedIds, setCheckedIds] = useState<string[]>([]);", content)
        self.assertIn("Clear selection", content)

    def test_collection_screen_batch_delete_confirmation_prompt(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn(
            'const confirmMsg = `Are you sure you want to delete ${checkedIds.length} ${checkedIds.length === 1 ? "Post" : "Posts"}?`;',
            content,
        )
        self.assertIn("if (!confirm(confirmMsg)) return;", content)

    def test_collection_screen_batch_delete_loading_state(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("setBatchDeleting(true);", content)
        self.assertIn("setBatchDeleting(false);", content)
        self.assertIn("disabled={batchDeleting}", content)

    def test_collection_screen_batch_delete_error_handling(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        self.assertIn("setBatchDeleteError(err instanceof Error ? err.message : \"Failed to delete selected items\");", content)
        self.assertIn("{batchDeleteError && (", content)
        self.assertIn("<span>Error deleting selected items: {batchDeleteError}</span>", content)
        self.assertIn("onClick={() => setBatchDeleteError(null)}", content)

    def test_collection_screen_individual_delete_cleans_selection(self) -> None:
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)

        # When individual handleDelete runs, it removes the deleted id from checkedIds
        self.assertIn("setCheckedIds((prev) => prev.filter((x) => x !== id));", content)

    def test_collection_screen_col_span_accounts_for_checkbox_column(self) -> None:
        ir = _make_test_ir(with_delete=True)
        screen = ir.screens[0]
        entity = ir.entities[0]
        ops = {Op.LIST, Op.DELETE, Op.GET, Op.UPDATE}

        content = _collection_screen_page(screen, entity, ir, ops)
        # display fields: title, content, published = 3 fields
        # actions col: 1
        # checkbox col: 1
        # total colSpan: 1 + 3 + 1 = 5
        self.assertIn("colSpan={5}", content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir1 = _make_test_ir(with_delete=True, description="Description Alpha")
        ir2 = _make_test_ir(with_delete=True, description="Description Beta 12345")

        screen1 = ir1.screens[0]
        screen2 = ir2.screens[0]

        content1 = render_screen_page(screen1, ir1)
        content2 = render_screen_page(screen2, ir2)

        self.assertEqual(content1, content2, "Collection screen must not depend on ir.description!")

    def test_full_project_generation_succeeds(self) -> None:
        adapter = NextjsWebAdapter()
        for ir_name in ("minimal-blog", "rideshare-favourites"):
            ir = example_ir(ir_name)
            project = adapter.generate(ir)
            self.assertGreater(len(project.paths()), 5)
            # Verify collection screens in example IRs include selection
            for screen in ir.screens:
                if screen.components and "list" in screen.components:
                    path = f"app/{screen.id}/page.tsx"
                    self.assertIn(path, project.paths())
                    f = project.get(path)
                    self.assertIn("checkedIds", f.content)
                    self.assertIn("handleCheckAll", f.content)


if __name__ == "__main__":
    unittest.main()
