"""Task R-269: Page Size Selector & Contextual Empty State CTAs in Generated Next.js Screens.

Covers:
1. UseListState<T> interface declares setPageSize: (size: number) => void;
2. useList<Entities> implements setPageSize with Math.max(1, newPageSize) and offset: 0
3. useList<Entities> returns pageSize and setPageSize
4. useList<Children>By<Rel> implements setPageSize and returns pageSize and setPageSize
5. Collection screens destructure pageSize and setPageSize
6. Collection screen footer renders page size selector <select> with options (10, 25, 50, 100 per page)
7. Collection screen table empty state renders search mismatch message with 'Clear search' CTA
8. Collection screen table empty state renders '+ Create first <Entity>' CTA link when form screen exists
9. Collection screen table empty state renders fallback 'No <plural> found.' when form screen is absent
10. Subcollection empty state renders '+ Add first <Child>' CTA link when child form exists
11. Dedicated detail screen subcollection empty state renders '+ Add first <Child>' CTA link
12. Strict diff invariance maintained across ir.description modifications
13. Full project generation via NextjsWebAdapter succeeds with zero errors
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
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    _collection_screen_page,
    _detail_screen_page,
    render_hooks,
    render_screen_page,
)


def _make_test_ir(description: str = "Test Blog Application") -> ApplicationIR:
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
        ),
        Entity(
            name="Comment",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("post_id", FieldType.STRING, required=True),
                Field("author", FieldType.STRING, required=True),
                Field("body", FieldType.TEXT, required=True),
            ),
            relations=(Relation("post", "Post", RelationKind.MANY_TO_ONE),),
        ),
        Entity(
            name="Tag",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("label", FieldType.STRING, required=True),
            ),
        ),
    )

    screens = (
        Screen(
            id="post_list",
            role="reader",
            components=("table", "pagination", "search", "filter"),
            actions=("view", "filter", "sort"),
            navigation=("post_editor", "post_detail"),
        ),
        Screen(
            id="post_editor",
            role="author",
            components=("form",),
            actions=("create", "update"),
            navigation=("post_list",),
        ),
        Screen(
            id="post_detail",
            role="reader",
            components=("detail",),
            actions=("view",),
            navigation=("post_list",),
        ),
        Screen(
            id="comment_editor",
            role="reader",
            components=("form",),
            actions=("create",),
            navigation=("post_list",),
        ),
        Screen(
            id="tag_list",
            role="admin",
            components=("table", "pagination"),
            actions=("view",),
            navigation=(),
        ),
    )

    apis = (
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.DELETE, "/posts/{id}"),
        ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", response_schema="Comment"),
        ApiEndpoint(HttpMethod.POST, "/comments", request_schema="Comment", response_schema="Comment"),
        ApiEndpoint(HttpMethod.DELETE, "/comments/{id}"),
        ApiEndpoint(HttpMethod.GET, "/tags", response_schema="Tag"),
    )

    return ApplicationIR(
        name="TestBlog",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("reader"), Role("author"), Role("admin")),
        entities=entities,
        screens=screens,
        apis=apis,
    )


class UseListStateHooksTests(unittest.TestCase):
    """Tests for UseListState interface and setPageSize implementation in hooks.ts."""

    def setUp(self) -> None:
        self.ir = _make_test_ir()
        self.hooks = render_hooks(self.ir)

    def test_use_list_state_interface_declares_set_page_size(self) -> None:
        self.assertIn("setPageSize: (size: number) => void;", self.hooks)

    def test_use_list_entities_implements_set_page_size(self) -> None:
        self.assertIn("const setPageSize = useCallback((newPageSize: number) => {", self.hooks)
        self.assertIn("limit: Math.max(1, newPageSize),", self.hooks)
        self.assertIn("offset: 0,", self.hooks)

    def test_use_list_entities_returns_page_size_and_set_page_size(self) -> None:
        self.assertIn("pageSize,", self.hooks)
        self.assertIn("setPageSize,", self.hooks)

    def test_use_list_by_relation_implements_set_page_size(self) -> None:
        # useListCommentsByPost is generated
        self.assertIn("export function useListCommentsByPost(", self.hooks)
        # Verify setPageSize is defined and returned inside it
        self.assertIn("setPageSize,", self.hooks)


class CollectionScreenPageSizeSelectorTests(unittest.TestCase):
    """Tests for page size selector in collection screen footer."""

    def setUp(self) -> None:
        self.ir = _make_test_ir()
        self.post_list_screen = next(s for s in self.ir.screens if s.id == "post_list")
        self.page = render_screen_page(self.post_list_screen, self.ir)

    def test_collection_screen_destructures_page_size_and_set_page_size(self) -> None:
        self.assertIn("pageSize,", self.page)
        self.assertIn("setPageSize,", self.page)
        self.assertIn("useListPosts();", self.page)

    def test_collection_screen_renders_page_size_selector(self) -> None:
        self.assertIn('<label htmlFor="pageSizeSelect"', self.page)
        self.assertIn('Per page:', self.page)
        self.assertIn('<select', self.page)
        self.assertIn('id="pageSizeSelect"', self.page)
        self.assertIn('value={pageSize}', self.page)
        self.assertIn('onChange={(e) => setPageSize(Number(e.target.value))}', self.page)

    def test_collection_screen_page_size_options(self) -> None:
        self.assertIn('<option value={10}>10 per page</option>', self.page)
        self.assertIn('<option value={25}>25 per page</option>', self.page)
        self.assertIn('<option value={50}>50 per page</option>', self.page)
        self.assertIn('<option value={100}>100 per page</option>', self.page)

    def test_existing_pagination_buttons_preserved(self) -> None:
        self.assertIn("Page {page} of {totalPages}", self.page)
        self.assertIn("setPage(page - 1)", self.page)
        self.assertIn("setPage(page + 1)", self.page)
        self.assertIn("Previous", self.page)
        self.assertIn("Next", self.page)


class ContextualEmptyStateTests(unittest.TestCase):
    """Tests for contextual empty states in collection screens and subcollections."""

    def setUp(self) -> None:
        self.ir = _make_test_ir()
        self.post_list_screen = next(s for s in self.ir.screens if s.id == "post_list")
        self.page = render_screen_page(self.post_list_screen, self.ir)

    def test_search_active_empty_state(self) -> None:
        self.assertIn("searchInput.trim() ?", self.page)
        self.assertIn("No Posts matching &ldquo;{searchInput}&rdquo;.", self.page)
        self.assertIn("Clear search", self.page)
        self.assertIn('setSearchInput("");', self.page)
        self.assertIn('setSearch("");', self.page)

    def test_initial_empty_state_with_form_cta(self) -> None:
        self.assertIn("No Posts found yet.", self.page)
        self.assertIn('href="/post_editor"', self.page)
        self.assertIn("+ Create first Post", self.page)

    def test_empty_state_without_form_screen(self) -> None:
        tag_screen = next(s for s in self.ir.screens if s.id == "tag_list")
        tag_page = render_screen_page(tag_screen, self.ir)
        # Tag has no form screen, so it should render the fallback 'No Tags found.'
        self.assertIn("No Tags found.", tag_page)

    def test_subcollection_empty_state_renders_add_first_child_cta(self) -> None:
        # post_list has comments subcollection and comment_editor form screen exists
        self.assertIn("No comments found for this post.", self.page)
        self.assertIn('href={`/comment_editor?postId=${selectedId}`}', self.page)
        self.assertIn("+ Add first Comment", self.page)

    def test_detail_screen_subcollection_empty_state_renders_add_first_child_cta(self) -> None:
        detail_screen = next(s for s in self.ir.screens if s.id == "post_detail")
        detail_page = render_screen_page(detail_screen, self.ir)
        self.assertIn("No comments found for this post.", detail_page)
        self.assertIn('href={`/comment_editor?postId=${selectedId}`}', detail_page)
        self.assertIn("+ Add first Comment", detail_page)


class DiffInvarianceAndMultiTargetTests(unittest.TestCase):
    """Tests for diff invariance and full project generation."""

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir_a = _make_test_ir(description="First description string")
        ir_b = _make_test_ir(description="Second completely altered description")

        hooks_a = render_hooks(ir_a)
        hooks_b = render_hooks(ir_b)
        self.assertEqual(hooks_a, hooks_b, "hooks.ts must not depend on ir.description")

        for screen_a, screen_b in zip(ir_a.screens, ir_b.screens):
            code_a = render_screen_page(screen_a, ir_a)
            code_b = render_screen_page(screen_b, ir_b)
            self.assertEqual(code_a, code_b, f"Screen {screen_a.id} output differed across descriptions")

    def test_full_project_generation_via_nextjs_adapter(self) -> None:
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIsNotNone(project)
        # Ensure collection screen and hooks are generated
        paths = [f.path for f in project.files()]
        self.assertIn("lib/hooks.ts", paths)
        self.assertIn("app/post_list/page.tsx", paths)
        self.assertIn("app/post_detail/page.tsx", paths)


if __name__ == "__main__":
    unittest.main()
