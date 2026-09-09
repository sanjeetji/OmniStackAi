"""Tests for Next.js interactive screen component generator [R-263]."""

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
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_screen_page,
)

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
    BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


class ScreenGenerationTests(TestCase):
    def setUp(self) -> None:
        self.adapter = NextjsWebAdapter()

    def test_all_screens_emit_use_client_directive(self) -> None:
        for ir_name in ("minimal-blog", "rideshare-favourites"):
            ir = example_ir(ir_name)
            for screen in ir.screens:
                page_content = render_screen_page(screen, ir)
                self.assertTrue(
                    page_content.startswith('"use client";'),
                    f"Screen {screen.id} in {ir_name} missing 'use client' directive",
                )

    def test_minimal_blog_post_list_screen(self) -> None:
        ir = example_ir("minimal-blog")
        post_list_screen = next(s for s in ir.screens if s.id == "post_list")
        content = render_screen_page(post_list_screen, ir)

        # 1. "use client" directive
        self.assertIn('"use client";', content)

        # 2. Imports hook and types
        self.assertIn('import { useListPosts } from "../lib/hooks";', content)
        self.assertIn('import type { Post } from "../lib/types";', content)

        # 3. Hook usage and data binding
        self.assertIn("useListPosts()", content)
        self.assertIn("data,", content)
        self.assertIn("total,", content)
        self.assertIn("loading,", content)
        self.assertIn("error,", content)
        self.assertIn("setPage,", content)
        self.assertIn("setSearch,", content)
        self.assertIn("setSort,", content)
        self.assertIn("refetch,", content)

        # 4. Search input: debounced commit (R-280) — onChange updates local state only,
        #    the debounced timer and the form submit commit via setSearch(searchInput).
        self.assertIn('type="search"', content)
        self.assertIn("placeholder=\"Search Posts...\"", content)
        self.assertIn("setSearchInput(e.target.value)", content)
        self.assertNotIn("setSearch(e.target.value)", content)
        self.assertIn("setSearch(searchInput)", content)

        # 5. Sortable table headers
        self.assertIn('onClick={() => setSort("title")}', content)
        self.assertIn('onClick={() => setSort("body")}', content)
        self.assertIn('onClick={() => setSort("published")}', content)

        # 6. Pagination controls
        self.assertIn("Page {page} of {totalPages}", content)
        self.assertIn("setPage(page - 1)", content)
        self.assertIn("setPage(page + 1)", content)
        self.assertIn("Previous", content)
        self.assertIn("Next", content)

        # 7. Navigation to complementary editor screen
        self.assertIn('href="/post_editor"', content)
        self.assertIn("+ New Post", content)

        # 8. Role badge
        self.assertIn("reader", content)

    def test_minimal_blog_post_editor_screen(self) -> None:
        ir = example_ir("minimal-blog")
        post_editor_screen = next(s for s in ir.screens if s.id == "post_editor")
        content = render_screen_page(post_editor_screen, ir)

        # 1. "use client" directive
        self.assertIn('"use client";', content)

        # 2. Imports mutation hook and types
        self.assertIn('import { useCreatePost } from "../lib/hooks";', content)
        self.assertIn('import type { Post } from "../lib/types";', content)

        # 3. Hook usage
        self.assertIn("useCreatePost()", content)
        self.assertIn("create, loading: submitting, error: submitError, reset", content)

        # 4. Schema-derived inputs
        # Title (STRING): text input
        self.assertIn('type="text"', content)
        self.assertIn('placeholder="Enter title..."', content)
        # Body (TEXT): textarea
        self.assertIn("<textarea", content)
        self.assertIn('placeholder="Enter body..."', content)
        # Published (BOOL): checkbox
        self.assertIn('type="checkbox"', content)

        # 5. Form submission calling create
        self.assertIn("await create(formData);", content)
        self.assertIn("Post saved successfully!", content)
        self.assertIn("Save Post", content)

        # 6. Navigation back to post_list
        self.assertIn('href="/post_list"', content)
        self.assertIn("Back to Posts", content)

        # 7. Role badge
        self.assertIn("author", content)

    def test_rideshare_favourites_collection_screen(self) -> None:
        ir = example_ir("rideshare-favourites")
        fav_screen = ir.screens[0]
        content = render_screen_page(fav_screen, ir)

        # Collection with useListFavouriteDrivers
        self.assertIn('"use client";', content)
        self.assertIn("useListFavouriteDrivers", content)
        self.assertIn("useListFavouriteDrivers()", content)

        # Search and pagination
        self.assertIn('type="search"', content)
        self.assertIn("setSearch", content)
        self.assertIn("setPage", content)
        self.assertIn("Previous", content)
        self.assertIn("Next", content)
        self.assertIn("Page {page} of {totalPages}", content)

        # Displays created_at column
        self.assertIn("Created At", content)

    def test_collection_screen_with_delete_hook_when_op_delete_wired(self) -> None:
        ir = ApplicationIR(
            name="Blog App",
            description="Blog with delete operation",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            roles=(Role("admin"),),
            entities=(
                Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
            ),
            apis=(
                ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
                ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"),
            ),
            screens=(
                Screen("post_list", "admin", components=("list",), actions=("delete",)),
            ),
        )
        content = render_screen_page(ir.screens[0], ir)

        # Should include useDeletePost and Delete button
        self.assertIn('"use client";', content)
        self.assertIn("useListPosts", content)
        self.assertIn("useDeletePost", content)
        self.assertIn("const { remove } = useDeletePost();", content)
        self.assertIn("handleDelete", content)
        self.assertIn("Delete", content)

    def test_fallback_screen_when_no_api_hooks_available(self) -> None:
        # Entity exists but no API endpoints wired
        ir = ApplicationIR(
            name="Unwired App",
            description="App with entities but no APIs",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            roles=(Role("member"),),
            entities=(
                Entity("Widget", (Field("id", FieldType.UUID), Field("label", FieldType.STRING))),
            ),
            apis=(),
            screens=(
                Screen("widgets", "member", components=("list",), actions=("view",)),
            ),
        )
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('"use client";', content)
        # Must not import missing hook
        self.assertNotIn("useListWidgets", content)
        self.assertIn("WidgetsPage", content)
        self.assertIn("Role:</strong> member", content)
        self.assertIn("Components:</strong> list", content)


    def test_fallback_screen_when_no_entities_in_ir(self) -> None:
        # Static screens without entities
        ir = ApplicationIR(
            name="Static App",
            description="App without entities",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            roles=(Role("guest"),),
            entities=(),
            apis=(),
            screens=(
                Screen("about", "guest", components=("card",), actions=(), navigation=("home",)),
            ),
        )
        content = render_screen_page(ir.screens[0], ir)
        self.assertIn('"use client";', content)
        self.assertIn("AboutPage", content)
        self.assertIn("Role:</strong> guest", content)
        self.assertIn('href="/home"', content)

    def test_project_generation_emits_screen_pages(self) -> None:
        ir = example_ir("minimal-blog")
        project = self.adapter.generate(ir)

        self.assertIn("app/post_list/page.tsx", project.paths())
        self.assertIn("app/post_editor/page.tsx", project.paths())

        list_file = project.get("app/post_list/page.tsx")
        self.assertIn('"use client";', list_file.content)
        self.assertIn("useListPosts", list_file.content)

        editor_file = project.get("app/post_editor/page.tsx")
        self.assertIn('"use client";', editor_file.content)
        self.assertIn("useCreatePost", editor_file.content)

    def test_screen_page_does_not_depend_on_ir_description(self) -> None:
        # Diff predictability: modifying description must NOT change screen page content
        ir1 = example_ir("minimal-blog")
        ir2 = ApplicationIR(
            name=ir1.name,
            description="Completely different description for diff test",
            platforms=ir1.platforms,
            project_strategy=ir1.project_strategy,
            roles=ir1.roles,
            entities=ir1.entities,
            apis=ir1.apis,
            screens=ir1.screens,
            acceptance_criteria=ir1.acceptance_criteria,
            fixtures=ir1.fixtures,
        )

        for s1, s2 in zip(ir1.screens, ir2.screens):
            content1 = render_screen_page(s1, ir1)
            content2 = render_screen_page(s2, ir2)
            self.assertEqual(
                content1,
                content2,
                f"Screen {s1.id} content changed when only IR description changed!",
            )
