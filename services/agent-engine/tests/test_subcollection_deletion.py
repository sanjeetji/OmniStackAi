"""Task R-268: Subcollection Child Item Deletion & Mutation Feedback in Master-Detail Views.

Tests:
1. Subcollection detection identifies can_delete=True when child entity has Op.DELETE.
2. Subcollection detection identifies can_delete=False when child entity lacks Op.DELETE.
3. Path-based DELETE fallback detection without response_schema.
4. Collection screens import useDelete<Child> hooks for deletable subcollections.
5. Collection screens instantiate delete hooks with remove, loading, and error states.
6. Collection screens declare handleDelete<Child> handler with confirmation prompt and refetch.
7. Collection screens render styled Delete button on child cards with stopPropagation and disabled state.
8. Collection screens render mutation error feedback alert banner when deletion fails.
9. Non-deletable subcollections omit delete hooks, handlers, error banners, and buttons.
10. Dedicated detail screens (_detail_screen_page) mirror child deletion hooks, handlers, and buttons.
11. Multi-subcollection entity with mixed delete permissions wires deletion selectively.
12. Screen generator maintains strict diff invariance across ir.description modifications.
13. Full project generation via NextjsWebAdapter emits working subcollection deletion code.
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


def _deletable_subcol_ir() -> ApplicationIR:
    """IR where Article has Comment subcollection and Comment supports DELETE."""
    return ApplicationIR(
        name="Blog App",
        description="Blog application with articles and deletable comments.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("author"), Role("reader")),
        entities=(
            Entity(
                "Article",
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
                    Field("article_id", FieldType.UUID),
                ),
                relations=(
                    Relation("article", "Article", RelationKind.MANY_TO_ONE),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.DELETE, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.POST, "/articles/{article_id}/comments", request_schema="Comment", response_schema="Comment"),
            ApiEndpoint(HttpMethod.DELETE, "/comments/{id}", response_schema="Comment"),
        ),
        screens=(
            Screen("article_list", "reader", components=("list",), actions=("view",)),
            Screen("article_detail", "reader", components=("detail",), actions=("view",)),
            Screen("comment_editor", "reader", components=("form",), actions=("create",)),
        ),
    )


def _mixed_subcol_ir() -> ApplicationIR:
    """IR where Article has two subcollections: Comment (deletable) and Tag (not deletable)."""
    return ApplicationIR(
        name="Tagged Blog",
        description="Blog with deletable comments and non-deletable tags.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("reader"),),
        entities=(
            Entity(
                "Article",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING),
                ),
            ),
            Entity(
                "Comment",
                (
                    Field("id", FieldType.UUID),
                    Field("body", FieldType.TEXT),
                    Field("article_id", FieldType.UUID),
                ),
                relations=(Relation("article", "Article", RelationKind.MANY_TO_ONE),),
            ),
            Entity(
                "Tag",
                (
                    Field("id", FieldType.UUID),
                    Field("label", FieldType.STRING),
                    Field("article_id", FieldType.UUID),
                ),
                relations=(Relation("article", "Article", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.DELETE, "/comments/{id}", response_schema="Comment"),
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/tags", response_schema="Tag"),
        ),
        screens=(
            Screen("article_list", "reader", components=("list",), actions=("view",)),
            Screen("article_detail", "reader", components=("detail",), actions=("view",)),
        ),
    )


class SubcollectionDeletionTests(unittest.TestCase):
    def test_subcollection_detection_identifies_can_delete_true(self) -> None:
        ir = _deletable_subcol_ir()
        subcols = _subcollections_for_parent("Article", ir)
        self.assertEqual(len(subcols), 1)
        sub = subcols[0]
        self.assertEqual(sub.child_entity.name, "Comment")
        self.assertTrue(sub.can_delete)

    def test_subcollection_detection_identifies_can_delete_false_when_no_delete(self) -> None:
        ir = example_ir("minimal-blog")
        subcols = _subcollections_for_parent("Post", ir)
        self.assertEqual(len(subcols), 1)
        sub = subcols[0]
        self.assertEqual(sub.child_entity.name, "Comment")
        self.assertFalse(sub.can_delete)

    def test_delete_fallback_without_response_schema(self) -> None:
        ir = ApplicationIR(
            name="Fallback Blog",
            description="Blog where DELETE endpoint omits response_schema.",
            platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=_STRATEGY,
            roles=(Role("reader"),),
            entities=(
                Entity(
                    "Article",
                    (Field("id", FieldType.UUID), Field("title", FieldType.STRING)),
                ),
                Entity(
                    "Comment",
                    (Field("id", FieldType.UUID), Field("body", FieldType.TEXT)),
                    relations=(Relation("article", "Article", RelationKind.MANY_TO_ONE),),
                ),
            ),
            apis=(
                ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
                ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
                ApiEndpoint(HttpMethod.DELETE, "/comments/{id}"),
            ),
            screens=(
                Screen("article_list", "reader", components=("list",), actions=("view",)),
            ),
        )
        subcols = _subcollections_for_parent("Article", ir)
        self.assertEqual(len(subcols), 1)
        self.assertTrue(subcols[0].can_delete)

    def test_collection_screen_imports_use_delete_child_hook(self) -> None:
        ir = _deletable_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        self.assertIn("useDeleteComment", page)
        self.assertIn('import { useListCommentsByArticle, useDeleteComment } from "../lib/hooks";', page)

    def test_collection_screen_instantiates_delete_hook(self) -> None:
        ir = _deletable_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        self.assertIn(
            "const { remove: removeComment, loading: deletingComment, error: deleteCommentError } = useDeleteComment();",
            page,
        )

    def test_collection_screen_generates_handle_delete_child_with_confirm_and_refetch(self) -> None:
        ir = _deletable_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        self.assertIn("const handleDeleteComment = async (id: string) => {", page)
        self.assertIn('if (confirm("Are you sure you want to delete this Comment?")) {', page)
        self.assertIn("await removeComment(id);", page)
        self.assertIn("commentsSubcol.refetch();", page)

    def test_collection_screen_renders_delete_button_on_child_cards(self) -> None:
        ir = _deletable_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        self.assertIn("handleDeleteComment((child as any).id)", page)
        self.assertIn("e.stopPropagation()", page)
        self.assertIn("disabled={deletingComment}", page)
        self.assertIn('{deletingComment ? "Deleting..." : "Delete"}', page)

    def test_collection_screen_renders_delete_error_alert(self) -> None:
        ir = _deletable_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        self.assertIn("{deleteCommentError && (", page)
        self.assertIn("Error deleting comment: {deleteCommentError.message}", page)

    def test_non_deletable_subcollection_omits_delete_code(self) -> None:
        ir = example_ir("minimal-blog")
        screen = next(s for s in ir.screens if s.id == "post_list")
        page = render_screen_page(screen, ir)

        self.assertNotIn("useDeleteComment", page)
        self.assertNotIn("handleDeleteComment", page)
        self.assertNotIn("deletingComment", page)
        self.assertNotIn("deleteCommentError", page)

    def test_detail_screen_wires_child_deletion_and_feedback(self) -> None:
        ir = _deletable_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_detail")
        page = render_screen_page(screen, ir)

        self.assertIn("useDeleteComment", page)
        self.assertIn(
            "const { remove: removeComment, loading: deletingComment, error: deleteCommentError } = useDeleteComment();",
            page,
        )
        self.assertIn("const handleDeleteComment = async (id: string) => {", page)
        self.assertIn('if (confirm("Are you sure you want to delete this Comment?")) {', page)
        self.assertIn("await removeComment(id);", page)
        self.assertIn("commentsSubcol.refetch();", page)
        self.assertIn("{deleteCommentError && (", page)
        self.assertIn("Error deleting comment: {deleteCommentError.message}", page)
        self.assertIn("handleDeleteComment((child as any).id)", page)
        self.assertIn('{deletingComment ? "Deleting..." : "Delete"}', page)

    def test_multi_subcollection_mixed_delete_wiring(self) -> None:
        ir = _mixed_subcol_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        # Comment has delete
        self.assertIn("useDeleteComment", page)
        self.assertIn("removeComment", page)
        self.assertIn("handleDeleteComment", page)
        self.assertIn("deleteCommentError", page)

        # Tag does NOT have delete
        self.assertNotIn("useDeleteTag", page)
        self.assertNotIn("removeTag", page)
        self.assertNotIn("handleDeleteTag", page)
        self.assertNotIn("deleteTagError", page)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir1 = _deletable_subcol_ir()
        ir2 = ApplicationIR(
            name=ir1.name,
            description="Completely different description to test diff invariance.",
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

    def test_full_project_generation_with_subcollection_deletion(self) -> None:
        adapter = NextjsWebAdapter()
        ir = _deletable_subcol_ir()
        project = adapter.generate(ir)

        # API client emits deleteComment
        api_ts = project.get("lib/api.ts").content
        self.assertIn("deleteComment(id: string", api_ts)

        # Hooks emit useDeleteComment
        hooks_ts = project.get("lib/hooks.ts").content
        self.assertIn("export function useDeleteComment()", hooks_ts)

        # Collection page includes child deletion
        page_tsx = project.get("app/article_list/page.tsx").content
        self.assertIn("useDeleteComment", page_tsx)
        self.assertIn("handleDeleteComment", page_tsx)
        self.assertIn("commentsSubcol.refetch()", page_tsx)


if __name__ == "__main__":
    unittest.main()
