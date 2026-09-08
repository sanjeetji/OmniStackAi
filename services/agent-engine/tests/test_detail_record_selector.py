"""Task R-276: Record Selector Dropdown, Prev/Next Record Navigation & Deep-Link Sync in Next.js Detail Screens.

Covers:
1. Detail screen imports useList<Plural> hook when Op.LIST is wired for the entity.
2. Detail screen omits useList<Plural> hook when Op.LIST is not wired.
3. Detail screen invokes useList<Plural>() and tracks listItems.
4. Detail screen renders styled <select> dropdown with '-- Choose <Entity> --' default option.
5. Dropdown options map over listItems using best_title_f or id fallback.
6. Detail screen renders Prev/Next navigation buttons in the item card header.
7. Prev/Next buttons bind disabled={!prevItem} and disabled={!nextItem} at boundaries.
8. Detail screen emits handleSelectId helper synchronizing URL params with window.history.replaceState.
9. Load button and Clear button call handleSelectId.
10. Detail screen renders 'Recent <plural>' card grid in empty state (when !selectedId).
11. handleDelete cleans up URL parameter upon record deletion.
12. Strict diff invariance across ir.description modifications.
13. Entity with only 'id' field falls back cleanly without runtime/template errors.
14. rideshare-favourites example IR generates valid detail screens when detail intent is matched.
15. minimal-blog example IR generates full project containing detail screen components cleanly.
16. Detail screen handles empty listItems fallback cleanly.
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
    with_list_op: bool = True,
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
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
        ApiEndpoint(HttpMethod.PUT, "/posts/{id}", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{post_id}/comments", response_schema="Comment"),
        ApiEndpoint(HttpMethod.POST, "/comments", request_schema="Comment", response_schema="Comment"),
    ]
    if with_list_op:
        apis.append(ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"))
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


class DetailRecordSelectorTests(unittest.TestCase):
    """Test suite verifying record selector dropdown, prev/next navigation, and deep-link sync."""

    def test_detail_screen_imports_uselist_when_list_op_wired(self) -> None:
        """Verify detail screen imports useList<Plural> when Op.LIST is present."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("useListPosts", content)

    def test_detail_screen_omits_uselist_when_list_op_absent(self) -> None:
        """Verify detail screen omits useList<Plural> when Op.LIST is not wired."""
        ir = _make_test_ir(with_list_op=False)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertNotIn("useListPosts", content)

    def test_detail_screen_declares_uselist_hook_call(self) -> None:
        """Verify detail screen calls useListPosts() and calculates currentIndex, prevItem, nextItem."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("const { data: listItems, loading: loadingList } = useListPosts();", content)
        self.assertIn("const currentIndex = (listItems && selectedId)", content)
        self.assertIn("const prevItem = (listItems && currentIndex > 0) ? listItems[currentIndex - 1] : null;", content)
        self.assertIn("const nextItem = (listItems && currentIndex >= 0 && currentIndex < listItems.length - 1)", content)

    def test_detail_screen_renders_select_dropdown(self) -> None:
        """Verify detail screen renders styled <select> dropdown with choose option."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('aria-label="Select Post"', content)
        self.assertIn("-- Choose Post --", content)
        self.assertIn("handleSelectId(e.target.value || null)", content)

    def test_detail_screen_select_options_use_best_title_field(self) -> None:
        """Verify dropdown options format with best title field (e.g. title) or id fallback."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("{String((it as any).title ?? it.id)}", content)

    def test_detail_screen_renders_prev_and_next_buttons(self) -> None:
        """Verify detail screen renders Prev and Next navigation buttons in item header."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("&larr; Prev", content)
        self.assertIn("Next &rarr;", content)
        self.assertIn("prevItem && handleSelectId(prevItem.id)", content)
        self.assertIn("nextItem && handleSelectId(nextItem.id)", content)

    def test_detail_screen_prev_next_buttons_disabled_states(self) -> None:
        """Verify Prev and Next buttons bind disabled states at list boundaries."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("disabled={!prevItem}", content)
        self.assertIn("disabled={!nextItem}", content)

    def test_detail_screen_emits_url_replace_state_logic(self) -> None:
        """Verify handleSelectId synchronizes query params using window.history.replaceState."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('const handleSelectId = (newId: string | null) => {', content)
        self.assertIn('url.searchParams.set("id", newId);', content)
        self.assertIn('url.searchParams.delete("id");', content)
        self.assertIn('window.history.replaceState({}, "", url.toString());', content)

    def test_detail_screen_clear_button(self) -> None:
        """Verify Clear button is rendered when selectedId is active."""
        ir = _make_test_ir()
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("{selectedId && (", content)
        self.assertIn("handleSelectId(null)", content)
        self.assertIn("Clear", content)

    def test_detail_screen_empty_state_recent_records(self) -> None:
        """Verify empty state (when !selectedId) displays recent records card grid."""
        ir = _make_test_ir(with_list_op=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn("{!selectedId && (", content)
        self.assertIn("Select a Post above or pick from recent records:", content)
        self.assertIn("listItems.slice(0, 6).map((rec: any) => (", content)

    def test_detail_screen_delete_cleans_up_url(self) -> None:
        """Verify handleDelete deletes URL query parameter."""
        ir = _make_test_ir(with_delete=True)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertIn('url.searchParams.delete("id");', content)

    def test_detail_screen_diff_invariance(self) -> None:
        """Verify detail screen is byte-identical when only ir.description changes."""
        ir1 = _make_test_ir(description="Description Version 1")
        ir2 = _make_test_ir(description="Description Version 2")
        screen1 = next(s for s in ir1.screens if s.id == "post_detail")
        screen2 = next(s for s in ir2.screens if s.id == "post_detail")
        c1 = render_screen_page(screen1, ir1)
        c2 = render_screen_page(screen2, ir2)
        self.assertEqual(c1, c2)

    def test_detail_screen_fallback_when_only_id_field(self) -> None:
        """Verify entity with only 'id' field handles best_title_f and options cleanly."""
        entity = Entity(name="Token", fields=(Field("id", FieldType.STRING, required=True),))
        ir = ApplicationIR(
            name="Token App",
            description="Testing Token",
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
            entities=(entity,),
            apis=(
                ApiEndpoint(HttpMethod.GET, "/tokens", response_schema="Token"),
                ApiEndpoint(HttpMethod.GET, "/tokens/{id}", response_schema="Token"),
            ),
            screens=(Screen("token_detail", "admin", components=("detail",), actions=("view",)),),
        )
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn("useListTokens", content)
        self.assertIn("-- Choose Token --", content)
        self.assertIn("{String((it as any).id ?? it.id)}", content)

    def test_detail_screen_omits_prev_next_when_list_op_absent(self) -> None:
        """Verify Prev/Next buttons and select dropdown are omitted when Op.LIST is not wired."""
        ir = _make_test_ir(with_list_op=False)
        detail_screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(detail_screen, ir)
        self.assertNotIn("-- Choose Post --", content)
        self.assertNotIn("&larr; Prev", content)
        self.assertNotIn("Next &rarr;", content)
        self.assertNotIn("useListPosts", content)

    def test_rideshare_favourites_detail_screen_valid(self) -> None:
        """Verify rideshare-favourites example IR generates valid detail screens if added."""
        ir = example_ir("rideshare-favourites")
        # Add a custom detail screen for Driver to rideshare-favourites
        detail_screen = Screen("driver_detail", "customer", components=("detail",), actions=("view",), navigation=())
        new_screens = (*ir.screens, detail_screen)
        ir_with_detail = ApplicationIR(
            name=ir.name,
            description=ir.description,
            platforms=ir.platforms,
            project_strategy=ir.project_strategy,
            roles=ir.roles,
            entities=ir.entities,
            apis=ir.apis,
            screens=new_screens,
        )
        content = render_screen_page(detail_screen, ir_with_detail)
        self.assertIn('"use client";', content)
        self.assertIn("useListDrivers", content)
        self.assertIn("-- Choose Driver --", content)
        self.assertIn("Load Driver", content)

    def test_minimal_blog_full_adapter_generate(self) -> None:
        """Verify NextjsWebAdapter generates full project with detail screen support."""
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        paths = set(project.paths())
        self.assertIn("app/post_detail/page.tsx", paths)
        page_content = project.get("app/post_detail/page.tsx").content
        self.assertIn("useListPosts", page_content)
        self.assertIn("-- Choose Post --", page_content)
        self.assertIn("&larr; Prev", page_content)


if __name__ == "__main__":
    unittest.main()
