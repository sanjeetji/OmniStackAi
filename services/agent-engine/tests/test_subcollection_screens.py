"""Task R-265: Subcollection Navigation & Master-Detail Views in Generated Screens.

Tests:
1. Subcollection detection helper identifies child subcollections and relations from IR.
2. Subcollection detection returns empty list for entities without subcollections.
3. Collection screens import subcollection hooks (e.g. useListCommentsByPost) for parent entities.
4. Collection screens import child entity types (e.g. Comment).
5. Collection screens declare and manage selectedId state.
6. Collection screens wire subcollection hooks to selectedId.
7. Collection screens render total count badge for child subcollection.
8. Collection screens render child items list with display fields.
9. Collection screens render subcollection states (prompt, loading, error, empty).
10. Master table rows support click-to-select and "View Details" toggle button.
11. Entities without subcollections emit clean code without subcollection overhead.
12. Multi-subcollection entities render tabbed navigation with live count badges.
13. Dedicated detail screens (intent == 'detail') render parent attributes and subcollections.
14. Screen generator maintains strict diff invariance across ir.description modifications.
15. NextjsWebAdapter.generate emits complete project with subcollection screens.
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
from omnistackai_agent_engine.codegen.nextjs import _subcollections_for_parent


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _multi_subcol_ir() -> ApplicationIR:
    """IR where Post has two subcollections: Comment and Reaction."""
    return ApplicationIR(
        name="Forum App",
        description="Community forum with posts, comments, and reactions.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("member"),),
        entities=(
            Entity(
                "Post",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING),
                    Field("content", FieldType.TEXT),
                ),
            ),
            Entity(
                "Comment",
                (
                    Field("id", FieldType.UUID),
                    Field("body", FieldType.TEXT),
                ),
                relations=(Relation("post", "Post", RelationKind.MANY_TO_ONE),),
            ),
            Entity(
                "Reaction",
                (
                    Field("id", FieldType.UUID),
                    Field("emoji", FieldType.STRING),
                ),
                relations=(Relation("post", "Post", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.GET, "/posts/{postId}/reactions", response_schema="Reaction"),
        ),
        screens=(
            Screen("post_list", "member", components=("list",), actions=("open",)),
            Screen("post_detail", "member", components=("detail",), actions=("view",)),
        ),
    )


class SubcollectionDetectionTests(TestCase):
    def test_subcollection_detection_from_ir(self) -> None:
        ir = example_ir("minimal-blog")
        subcols = _subcollections_for_parent("Post", ir)
        self.assertEqual(len(subcols), 1)
        sub = subcols[0]
        self.assertEqual(sub.child_entity.name, "Comment")
        self.assertEqual(sub.relation, "post")
        self.assertEqual(sub.id_param, "postId")
        self.assertEqual(sub.hook_name, "useListCommentsByPost")
        self.assertEqual(sub.child_plural, "Comments")
        field_names = [f.name for f in sub.display_fields]
        self.assertIn("body", field_names)
        self.assertNotIn("id", field_names)

    def test_entity_without_subcollections_returns_empty(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(_subcollections_for_parent("Comment", ir), [])

        rideshare = example_ir("rideshare-favourites")
        self.assertEqual(_subcollections_for_parent("FavouriteDriver", rideshare), [])

    def test_multi_subcollection_detection(self) -> None:
        ir = _multi_subcol_ir()
        subcols = _subcollections_for_parent("Post", ir)
        self.assertEqual(len(subcols), 2)
        hook_names = {s.hook_name for s in subcols}
        self.assertEqual(hook_names, {"useListCommentsByPost", "useListReactionsByPost"})


class SubcollectionCollectionScreenTests(TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.post_list_screen = next(s for s in self.ir.screens if s.id == "post_list")
        self.page = render_screen_page(self.post_list_screen, self.ir)

    def test_post_list_screen_imports_subcollection_hook(self) -> None:
        self.assertIn('import { useListPosts } from "../lib/hooks";', self.page)
        self.assertIn('import { useListCommentsByPost } from "../lib/hooks";', self.page)

    def test_post_list_screen_imports_child_type(self) -> None:
        self.assertIn('import type { Post } from "../lib/types";', self.page)
        self.assertIn('import type { Comment } from "../lib/types";', self.page)

    def test_post_list_screen_declares_selection_state(self) -> None:
        self.assertIn("const [selectedId, setSelectedId] = useState<string | null>(null);", self.page)

    def test_post_list_screen_wires_subcollection_hook_to_selected_id(self) -> None:
        self.assertIn("const commentsSubcol = useListCommentsByPost(selectedId);", self.page)

    def test_post_list_screen_renders_total_count_badge(self) -> None:
        self.assertIn("{commentsSubcol.total}", self.page)

    def test_post_list_screen_renders_child_items_and_states(self) -> None:
        # Loading state
        self.assertIn("Loading comments...", self.page)
        # Error state
        self.assertIn("commentsSubcol.error", self.page)
        self.assertIn("commentsSubcol.error.message", self.page)
        # Empty state
        self.assertIn("No comments found for this post.", self.page)
        # Prompt when not selected
        self.assertIn("Select a Post from the table above to view associated Comments.", self.page)
        # Child data list
        self.assertIn("commentsSubcol.data.map(", self.page)
        self.assertIn("(child as any).body", self.page)

    def test_master_table_rows_have_selection_interaction(self) -> None:
        self.assertIn("setSelectedId(selectedId === (item as any).id ? null : (item as any).id)", self.page)
        self.assertIn("View Details", self.page)
        self.assertIn("Hide Details", self.page)
        self.assertIn("e.stopPropagation()", self.page)
        self.assertIn("Deselect", self.page)

    def test_subcollection_refresh_button(self) -> None:
        self.assertIn("commentsSubcol.refetch()", self.page)
        self.assertIn("Refresh", self.page)

    def test_entity_without_subcollections_clean(self) -> None:
        ir = example_ir("rideshare-favourites")
        screen = ir.screens[0]
        page = render_screen_page(screen, ir)

        self.assertNotIn("Subcol", page)
        self.assertNotIn("selectedId", page)
        self.assertNotIn("Deselect", page)


class MultiSubcollectionTests(TestCase):
    def setUp(self) -> None:
        self.ir = _multi_subcol_ir()
        self.post_list_screen = next(s for s in self.ir.screens if s.id == "post_list")
        self.page = render_screen_page(self.post_list_screen, self.ir)

    def test_multi_subcollection_imports(self) -> None:
        self.assertIn("useListCommentsByPost", self.page)
        self.assertIn("useListReactionsByPost", self.page)
        self.assertIn("Comment", self.page)
        self.assertIn("Reaction", self.page)

    def test_multi_subcollection_tabs(self) -> None:
        self.assertIn("const [activeTab, setActiveTab] = useState<number>(0);", self.page)
        self.assertIn("onClick={() => setActiveTab(0)}", self.page)
        self.assertIn("onClick={() => setActiveTab(1)}", self.page)
        self.assertIn("<span>Comments</span>", self.page)
        self.assertIn("<span>Reactions</span>", self.page)
        self.assertIn("{commentsSubcol.total}", self.page)
        self.assertIn("{reactionsSubcol.total}", self.page)


class DedicatedDetailScreenTests(TestCase):
    def setUp(self) -> None:
        self.ir = _multi_subcol_ir()
        self.detail_screen = next(s for s in self.ir.screens if s.id == "post_detail")
        self.page = render_screen_page(self.detail_screen, self.ir)

    def test_detail_screen_imports(self) -> None:
        self.assertIn('"use client";', self.page)
        self.assertIn("usePost", self.page)
        self.assertIn("useListCommentsByPost", self.page)
        self.assertIn("useListReactionsByPost", self.page)
        self.assertIn("Post", self.page)

    def test_detail_screen_id_loader(self) -> None:
        self.assertIn('placeholder="Enter Post ID..."', self.page)
        self.assertIn("Load Post", self.page)
        self.assertIn("usePost(selectedId)", self.page)

    def test_detail_screen_parent_attributes_and_subcollections(self) -> None:
        self.assertIn("Loading Post...", self.page)
        self.assertIn("Title:", self.page)
        self.assertIn("Content:", self.page)
        self.assertIn("Comments", self.page)
        self.assertIn("Reactions", self.page)


class DiffInvarianceAndProjectGenerationTests(TestCase):
    def test_diff_invariance_across_ir_description_change(self) -> None:
        ir1 = example_ir("minimal-blog")
        ir2 = ApplicationIR(
            name=ir1.name,
            description="Completely different description for diff invariance test",
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
            page1 = render_screen_page(s1, ir1)
            page2 = render_screen_page(s2, ir2)
            self.assertEqual(
                page1,
                page2,
                f"Screen {s1.id} output changed when only ir.description was modified!",
            )

    def test_project_generation_emits_subcollection_screens(self) -> None:
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)

        self.assertIn("app/post_list/page.tsx", project.paths())
        list_file = project.get("app/post_list/page.tsx")
        self.assertIn("useListCommentsByPost", list_file.content)
        self.assertIn("commentsSubcol", list_file.content)
