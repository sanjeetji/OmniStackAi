"""Task R-272: Deep-Linking & Entity Lifecycle in Next.js Detail Screens.

Covers:
1. Detail screen imports useSearchParams and useEffect
2. Detail screen reads searchParams.get("id") and initializes state
3. Detail screen runs useEffect to synchronize when queryId changes
4. Detail screen binds to use<Entity>(selectedId) hook
5. Detail screen renders 'Edit <Entity>' link to form screen when edit is supported
6. Detail screen omits 'Edit <Entity>' link when form screen is absent
7. Detail screen imports and wires useDelete<Entity>() hook and handleDelete when deletable
8. Detail screen renders 'Delete <Entity>' button with confirmation dialog and loading state
9. Detail screen omits delete hook and button when entity lacks DELETE route
10. Detail screen renders 'Export JSON' button with Blob/anchor download lifecycle
11. Detail screen renders breadcrumb link back to collection screen
12. Detail screen falls back to Overview breadcrumb when no collection screen exists
13. Collection screen renders 'View' link button to dedicated detail screen
14. Collection screen omits 'View' detail link when no detail screen is defined
15. Strict diff invariance across ir.description modifications
16. Full project generation via NextjsWebAdapter succeeds with detail screen
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


def _make_test_ir(
    with_delete: bool = True,
    with_detail_screen: bool = True,
    with_form_screen: bool = True,
    with_collection_screen: bool = True,
    description: str = "Test Blog Application",
) -> ApplicationIR:
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

    screens_list = []
    if with_collection_screen:
        screens_list.append(
            Screen("posts", "admin", components=("list",), actions=("view", "delete") if with_delete else ("view",), navigation=("post_form",))
        )
    if with_form_screen:
        screens_list.append(
            Screen("post_form", "admin", components=("form",), actions=("create", "update"), navigation=("posts",))
        )
    if with_detail_screen:
        screens_list.append(
            Screen("post_detail", "admin", components=("detail",), actions=("view", "delete") if with_delete else ("view",), navigation=("posts",))
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
        screens=tuple(screens_list),
    )


class DetailScreenLifecycleTests(unittest.TestCase):
    """Test suite verifying deep-linking and lifecycle in Next.js detail screens."""

    def test_detail_screen_imports_search_params_and_effect(self) -> None:
        """Verify detail screen imports useSearchParams and useEffect."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('import { useState, useEffect } from "react";', content)
        self.assertIn('import { useSearchParams } from "next/navigation";', content)

    def test_detail_screen_reads_query_id(self) -> None:
        """Verify detail screen initializes state from searchParams.get('id')."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("const searchParams = useSearchParams();", content)
        self.assertIn('const queryId = searchParams.get("id");', content)
        self.assertIn('const [idInput, setIdInput] = useState<string>(queryId ?? "");', content)
        self.assertIn("const [selectedId, setSelectedId] = useState<string | null>(queryId ?? null);", content)

    def test_detail_screen_auto_load_effect(self) -> None:
        """Verify useEffect synchronizes state when queryId changes."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("useEffect(() => {", content)
        self.assertIn("if (queryId) {", content)
        self.assertIn("setSelectedId(queryId);", content)
        self.assertIn("setIdInput(queryId);", content)

    def test_detail_screen_wires_use_entity(self) -> None:
        """Verify detail screen binds to use<Entity>(selectedId)."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("usePost(selectedId)", content)

    def test_detail_screen_renders_edit_action(self) -> None:
        """Verify detail screen renders Edit link to form screen."""
        ir = _make_test_ir(with_form_screen=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('href={`/post_form?id=${selectedId}`}', content)
        self.assertIn("Edit Post", content)

    def test_detail_screen_omits_edit_when_no_form(self) -> None:
        """Verify detail screen omits Edit link when form screen is absent."""
        ir = _make_test_ir(with_form_screen=False)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertNotIn("Edit Post", content)

    def test_detail_screen_wires_delete_hook_and_handler(self) -> None:
        """Verify detail screen wires useDeletePost and handleDelete."""
        ir = _make_test_ir(with_delete=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("useDeletePost", content)
        self.assertIn("const handleDelete = async () => {", content)
        # R-304: delete now uses accessible async confirmAsync() modal instead of window.confirm().
        self.assertIn('confirmAsync("Delete Post"', content)
        self.assertNotIn('confirm("Are you sure you want to delete this Post?")', content)
        self.assertIn("await removeMain(selectedId);", content)
        self.assertIn("setSelectedId(null);", content)

    def test_detail_screen_renders_delete_button(self) -> None:
        """Verify detail screen renders Delete button with loading indicator."""
        ir = _make_test_ir(with_delete=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("onClick={handleDelete}", content)
        self.assertIn('deletingMain ? "Deleting..." : "Delete Post"', content)

    def test_detail_screen_omits_delete_when_not_deletable(self) -> None:
        """Verify detail screen omits delete hook and button when entity lacks DELETE route."""
        ir = _make_test_ir(with_delete=False)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertNotIn("useDeletePost()", content)
        self.assertNotIn("Delete Post", content)

    def test_detail_screen_renders_export_json_button(self) -> None:
        """Verify detail screen renders Export JSON button with Blob and link download."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("Export JSON", content)
        self.assertIn("handleExportJson", content)
        self.assertIn('new Blob([JSON.stringify(item, null, 2)], { type: "application/json" })', content)
        self.assertIn("URL.createObjectURL(blob)", content)
        self.assertIn("URL.revokeObjectURL(url)", content)

    def test_detail_screen_collection_breadcrumb(self) -> None:
        """Verify detail screen breadcrumbs link back to collection screen."""
        ir = _make_test_ir(with_collection_screen=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('href="/posts"', content)
        self.assertIn("&larr; Back to Posts", content)

    def test_detail_screen_overview_breadcrumb_fallback(self) -> None:
        """Verify detail screen falls back to Overview breadcrumb when collection screen is absent."""
        ir = _make_test_ir(with_collection_screen=False)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('href="/"', content)
        self.assertIn("&larr; Overview", content)

    def test_collection_screen_links_to_detail_screen(self) -> None:
        """Verify collection screen table rows render 'View' link navigating to detail screen."""
        ir = _make_test_ir(with_detail_screen=True)
        collection_screen = next(s for s in ir.screens if s.id == "posts")
        content = render_screen_page(collection_screen, ir)
        self.assertIn('href={`/post_detail?id=${(item as any).id}`}', content)
        self.assertIn("View\n                  </Link>", content)

    def test_collection_screen_omits_detail_link_when_no_detail_screen(self) -> None:
        """Verify collection screen omits 'View' link when no detail screen is defined."""
        ir = _make_test_ir(with_detail_screen=False)
        collection_screen = next(s for s in ir.screens if s.id == "posts")
        content = render_screen_page(collection_screen, ir)
        self.assertNotIn("/post_detail", content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """Verify changing ir.description does not change generated detail screen code."""
        ir1 = _make_test_ir(description="Alpha Blog Description")
        ir2 = _make_test_ir(description="Beta Blog Description 98765")

        screen1 = next(s for s in ir1.screens if s.id == "post_detail")
        screen2 = next(s for s in ir2.screens if s.id == "post_detail")

        content1 = render_screen_page(screen1, ir1)
        content2 = render_screen_page(screen2, ir2)

        self.assertEqual(content1, content2, "Detail screen must not depend on ir.description!")

    def test_full_project_generation_with_detail_screen(self) -> None:
        """Verify full project generation succeeds with detail screen in IR."""
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("app/post_detail/page.tsx", project.paths())
        detail_file = project.get("app/post_detail/page.tsx")
        self.assertIn("usePost", detail_file.content)
        self.assertIn("Export JSON", detail_file.content)
        self.assertIn("searchParams.get", detail_file.content)


if __name__ == "__main__":
    unittest.main()
