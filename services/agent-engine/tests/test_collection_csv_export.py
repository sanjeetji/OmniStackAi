"""Task R-271: CSV Data Export & Bulk Export in Generated Next.js Collection Screens.

Covers:
1. Collection screen emits handleExportCsv helper function
2. Top toolbar renders 'Export CSV' button calling handleExportCsv(false)
3. Top toolbar 'Export CSV' button is disabled when data is null/empty
4. Bulk Actions Bar renders 'Export Selected' button calling handleExportCsv(true)
5. handleExportCsv implements RFC 4180 escaping (null/undefined -> '""', quotes -> '""')
6. All declared entity fields are included in CSV headers
7. All declared entity fields are mapped via toCsvVal in row generation
8. Blob creation uses text/csv;charset=utf-8; MIME type
9. URL.createObjectURL and URL.revokeObjectURL lifecycle is maintained
10. Download anchor lifecycle (create, href, download attr, append, click, remove)
11. Download filename matches {plural.lower()}_export.csv
12. handleExportCsv filters by checkedIds when selectedOnly=true
13. handleExportCsv early-returns when itemsToExport.length === 0
14. Bulk export button is present even when entity does not have DELETE action
15. Bulk export button and Delete Selected coexist when entity has DELETE action
16. Strict diff invariance across ir.description modifications
17. Full project generation via NextjsWebAdapter succeeds with CSV export in collection screens
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
    render_screen_page,
)


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


class CollectionCsvExportTests(unittest.TestCase):
    """Test suite verifying RFC 4180 CSV export and bulk export in Next.js collection screens."""

    def test_csv_export_helper_rendered(self) -> None:
        """Verify handleExportCsv helper function is generated in the collection screen."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("const handleExportCsv = (selectedOnly: boolean = false) => {", content)

    def test_top_toolbar_export_csv_button_rendered(self) -> None:
        """Verify top toolbar contains 'Export CSV' button calling handleExportCsv(false)."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("handleExportCsv(false)", content)
        self.assertIn("Export CSV", content)

    def test_top_toolbar_export_button_disabled_state(self) -> None:
        """Verify top toolbar Export CSV button is disabled when data is null/empty."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("disabled={!data || data.length === 0}", content)
        self.assertIn('cursor: (!data || data.length === 0) ? "default" : "pointer"', content)

    def test_bulk_toolbar_export_selected_button_rendered(self) -> None:
        """Verify contextual bulk toolbar contains 'Export Selected' button calling handleExportCsv(true)."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("handleExportCsv(true)", content)
        self.assertIn("Export Selected (${checkedIds.length})", content)

    def test_rfc4180_escaping_logic_rendered(self) -> None:
        """Verify RFC 4180 escaping and null/undefined handling in toCsvVal."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("if (val === null || val === undefined) return '\"\"';", content)
        self.assertIn('replace(/"/g, \'""\')', content)
        self.assertIn('typeof val === "object" ? JSON.stringify(val) : String(val)', content)

    def test_all_entity_fields_in_headers(self) -> None:
        """Verify all declared entity fields are included in CSV headers."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('const headers = ["id", "title", "content", "published"];', content)

    def test_all_entity_fields_in_rows(self) -> None:
        """Verify all declared entity fields are mapped via toCsvVal in rows."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("toCsvVal((item as any).id)", content)
        self.assertIn("toCsvVal((item as any).title)", content)
        self.assertIn("toCsvVal((item as any).content)", content)
        self.assertIn("toCsvVal((item as any).published)", content)

    def test_blob_and_object_url_lifecycle(self) -> None:
        """Verify Blob creation with UTF-8 CSV MIME type and URL object lifecycle."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('new Blob([csvContent], { type: "text/csv;charset=utf-8;" })', content)
        self.assertIn("URL.createObjectURL(blob)", content)
        self.assertIn("URL.revokeObjectURL(url)", content)

    def test_download_anchor_lifecycle(self) -> None:
        """Verify dynamic anchor creation, download attribute, DOM append, click, and removal."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('document.createElement("a")', content)
        self.assertIn('link.setAttribute("href", url)', content)
        self.assertIn('link.setAttribute("download", "posts_export.csv")', content)
        self.assertIn("document.body.appendChild(link)", content)
        self.assertIn("link.click()", content)
        self.assertIn("document.body.removeChild(link)", content)

    def test_download_filename_format(self) -> None:
        """Verify download filename is formatted as {plural.lower()}_export.csv."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('"posts_export.csv"', content)

    def test_selected_only_filtering_logic(self) -> None:
        """Verify handleExportCsv filters items by checkedIds when selectedOnly is true."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("const itemsToExport = selectedOnly", content)
        self.assertIn("(data ?? []).filter((item: any) => checkedIds.includes(item.id))", content)
        self.assertIn(": (data ?? []);", content)

    def test_empty_data_early_return(self) -> None:
        """Verify handleExportCsv returns early if there are no items to export."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("if (itemsToExport.length === 0) return;", content)

    def test_bulk_export_present_without_delete_capability(self) -> None:
        """Verify bulk Export Selected button is rendered even if entity does not support deletion."""
        ir = _make_test_ir(with_delete=False)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("checkedIds.length > 0", content)
        self.assertIn("Export Selected (${checkedIds.length})", content)
        self.assertNotIn("Delete Selected", content)
        self.assertNotIn("handleBatchDelete", content)

    def test_bulk_export_present_with_delete_capability(self) -> None:
        """Verify both Export Selected and Delete Selected buttons render when entity supports deletion."""
        ir = _make_test_ir(with_delete=True)
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("Export Selected (${checkedIds.length})", content)
        self.assertIn("Delete Selected (${checkedIds.length})", content)
        self.assertIn("handleBatchDelete", content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """Verify changing ir.description does not change generated collection screen code."""
        ir1 = _make_test_ir(with_delete=True, description="Description Alpha")
        ir2 = _make_test_ir(with_delete=True, description="Description Beta 12345")

        screen1 = ir1.screens[0]
        screen2 = ir2.screens[0]

        content1 = render_screen_page(screen1, ir1)
        content2 = render_screen_page(screen2, ir2)

        self.assertEqual(content1, content2, "Collection screen must not depend on ir.description!")

    def test_full_project_generation_succeeds(self) -> None:
        """Verify full project generation succeeds and contains collection page with CSV export."""
        adapter = NextjsWebAdapter()
        for ir_name in ("minimal-blog", "rideshare-favourites"):
            ir = example_ir(ir_name)
            project = adapter.generate(ir)
            self.assertGreater(len(project.paths()), 5)
            for screen in ir.screens:
                if screen.components and "list" in screen.components:
                    path = f"app/{screen.id}/page.tsx"
                    self.assertIn(path, project.paths())
                    f = project.get(path)
                    self.assertIn("handleExportCsv", f.content)
                    self.assertIn("Export CSV", f.content)
                    self.assertIn("Export Selected", f.content)


if __name__ == "__main__":
    unittest.main()
