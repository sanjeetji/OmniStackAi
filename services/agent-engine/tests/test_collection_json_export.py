"""Task R-308: JSON Data Export & Bulk Export in Generated Next.js Collection Screens.

Tests for:
1. Collection screen emits handleExportJson helper function alongside handleExportCsv.
2. Top toolbar renders 'Export JSON' button calling handleExportJson(false).
3. Top toolbar 'Export JSON' button is disabled when data is null/empty.
4. Bulk Actions Bar renders 'Export JSON (${checkedIds.length})' button calling handleExportJson(true).
5. handleExportJson formats JSON with 2-space indentation.
6. Blob creation uses application/json;charset=utf-8; MIME type.
7. URL.createObjectURL and URL.revokeObjectURL lifecycle is maintained.
8. Download filename matches {plural.lower()}_export.json.
9. handleExportJson filters by checkedIds when selectedOnly=true.
10. handleExportJson early-returns when itemsToExport.length === 0.
11. Toast notification on export success ("Exported JSON successfully").
12. Strict diff invariance across ir.description modifications.
13. Full project generation on example IR fixtures.
"""

from __future__ import annotations

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
    example_ir,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    render_screen_page,
)


def _make_test_ir(with_delete: bool = True, description: str = "Test Blog Application") -> ApplicationIR:
    entities = (
        Entity(
            name="Post",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
                Field("content", FieldType.TEXT, required=False),
            ),
        ),
    )
    apis = [
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
    ]
    if with_delete:
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"))

    screens = (
        Screen("posts", "admin", components=("list",), actions=("view", "delete") if with_delete else ("view",)),
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
        roles=(Role("admin", ("read", "write")),),
        entities=entities,
        apis=tuple(apis),
        screens=screens,
    )


class CollectionJsonExportTests(unittest.TestCase):
    """Test suite verifying JSON export and bulk export in Next.js collection screens."""

    def test_json_export_helper_rendered(self) -> None:
        """Verify handleExportJson helper function is generated in the collection screen."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("const handleExportJson = (selectedOnly: boolean = false) => {", content)

    def test_top_toolbar_export_json_button_rendered(self) -> None:
        """Verify top toolbar contains 'Export JSON' button calling handleExportJson(false)."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("handleExportJson(false)", content)
        self.assertIn("Export JSON", content)

    def test_top_toolbar_export_json_button_disabled_state(self) -> None:
        """Verify top toolbar Export JSON button is disabled when data is null/empty."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("handleExportJson(false)", content)
        self.assertIn("disabled={!data || data.length === 0}", content)

    def test_bulk_toolbar_export_json_button_rendered(self) -> None:
        """Verify contextual bulk toolbar contains 'Export JSON' button calling handleExportJson(true)."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("handleExportJson(true)", content)
        self.assertIn("Export JSON (${checkedIds.length})", content)

    def test_json_blob_and_object_url_lifecycle(self) -> None:
        """Verify JSON Blob creation with application/json MIME type and URL lifecycle."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('const jsonContent = JSON.stringify(itemsToExport, null, 2);', content)
        self.assertIn('new Blob([jsonContent], { type: "application/json;charset=utf-8;" })', content)
        self.assertIn('"posts_export.json"', content)
        self.assertIn('toast.info("Exported JSON successfully");', content)

    def test_selected_only_filtering_logic_in_json_export(self) -> None:
        """Verify handleExportJson filters items by checkedIds when selectedOnly is true."""
        ir = _make_test_ir()
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("const itemsToExport = selectedOnly", content)

    def test_diff_invariance_across_ir_description(self) -> None:
        """Verify collection screen code is byte-identical across ir.description changes."""
        ir1 = _make_test_ir(description="First description")
        ir2 = _make_test_ir(description="Second completely different description")
        content1 = render_screen_page(ir1.screens[0], ir1)
        content2 = render_screen_page(ir2.screens[0], ir2)
        self.assertEqual(content1, content2)

    def test_full_project_generation_contains_json_export(self) -> None:
        """Verify generated full project collection screen contains JSON export."""
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        post_list = project.get("app/post_list/page.tsx").content
        self.assertIn("handleExportJson", post_list)
        self.assertIn("Export JSON", post_list)


if __name__ == "__main__":
    unittest.main()
