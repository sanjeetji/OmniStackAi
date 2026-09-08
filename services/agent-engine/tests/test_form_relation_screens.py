"""Tests for foreign-key relation selectors and parent auto-population in generated Next.js forms (Task R-267)."""

from __future__ import annotations

import dataclasses
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
    _form_screen_page,
    _get_ops_by_entity,
    _parent_relations_for_entity,
)


def _article_comment_ir() -> ApplicationIR:
    """IR with Article (parent) and Comment (child with MANY_TO_ONE foreign key)."""
    return ApplicationIR(
        name="Blog with Comments",
        description="A blog with articles and child comments.",
        platforms=(Platform.WEB, Platform.ADMIN, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NEXTJS,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("author", ("read", "write")), Role("reader", ("read",))),
        entities=(
            Entity(
                "Article",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("content", FieldType.TEXT),
                    Field("published", FieldType.BOOL),
                ),
                relations=(
                    Relation("comments", "Comment", RelationKind.ONE_TO_MANY),
                ),
            ),
            Entity(
                "Comment",
                (
                    Field("id", FieldType.UUID),
                    Field("article_id", FieldType.UUID, required=True),
                    Field("author", FieldType.STRING, required=True),
                    Field("body", FieldType.TEXT, required=True),
                ),
                relations=(
                    Relation("article", "Article", RelationKind.MANY_TO_ONE),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.DELETE, "/articles/{id}"),
            ApiEndpoint(HttpMethod.POST, "/comments", request_schema="Comment", response_schema="Comment"),
            ApiEndpoint(HttpMethod.POST, "/articles/{article_id}/comments", request_schema="Comment", response_schema="Comment"),
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.GET, "/comments/{id}", response_schema="Comment"),
            ApiEndpoint(HttpMethod.PUT, "/comments/{id}", request_schema="Comment", response_schema="Comment"),
            ApiEndpoint(HttpMethod.DELETE, "/comments/{id}"),
        ),
        screens=(
            Screen("article_list", "reader", components=("list",), actions=("view",)),
            Screen("article_editor", "author", components=("form",), actions=("create", "update")),
            Screen("comment_list", "reader", components=("list",), actions=("view",)),
            Screen("comment_editor", "reader", components=("form",), actions=("create", "update")),
        ),
    )


class FormRelationScreensTests(unittest.TestCase):
    """Verify foreign-key relation selectors and parent auto-population."""

    def setUp(self) -> None:
        self.ir = _article_comment_ir()
        self.ops_by_entity = _get_ops_by_entity(self.ir)
        self.comment_entity = next(e for e in self.ir.entities if e.name == "Comment")
        self.article_entity = next(e for e in self.ir.entities if e.name == "Article")
        self.comment_screen = next(s for s in self.ir.screens if s.id == "comment_editor")
        self.article_screen = next(s for s in self.ir.screens if s.id == "article_editor")

    def test_parent_relations_helper_detects_many_to_one(self) -> None:
        rels = _parent_relations_for_entity(self.comment_entity, self.ir)
        self.assertEqual(len(rels), 1)
        rel = rels[0]
        self.assertEqual(rel.field_name, "article_id")
        self.assertEqual(rel.relation_name, "article")
        self.assertEqual(rel.parent_entity.name, "Article")
        self.assertEqual(rel.parent_plural, "Articles")
        self.assertEqual(rel.hook_name, "useListArticles")
        self.assertEqual(rel.title_field, "title")
        self.assertEqual(rel.label, "Article")

    def test_parent_relations_empty_for_independent_entity(self) -> None:
        rels = _parent_relations_for_entity(self.article_entity, self.ir)
        self.assertEqual(rels, [])

    def test_child_form_imports_parent_list_hook(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        self.assertIn('import { useListArticles } from "../lib/hooks";', page)
        self.assertIn('import { useSearchParams } from "next/navigation";', page)
        self.assertIn('import { useCreateComment } from "../lib/hooks";', page)

    def test_child_form_invokes_parent_list_hook(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        self.assertIn("const articlesList = useListArticles();", page)

    def test_child_form_renders_select_dropdown_instead_of_text_input(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        # Foreign key field must render as <select>, NOT <input type="text"
        self.assertNotIn('placeholder="Enter article_id..."', page)
        self.assertIn("<select", page)
        self.assertIn('value={String((formData as any).article_id ?? "")}', page)
        self.assertIn('aria-invalid={!!fieldErrors.article_id}', page)

        # Renders parent options and loading placeholder
        self.assertIn('{articlesList.loading ? "Loading articles..." : "Select article..."}', page)
        self.assertIn("(articlesList.data || []).map((item) =>", page)
        self.assertIn("<option key={item.id} value={item.id}>", page)
        self.assertIn("{String((item as any).title ?? (item as any).name ?? item.id)}", page)

    def test_child_form_renders_visual_parent_link_badge(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        self.assertIn("{Boolean((formData as any).article_id) && (", page)
        self.assertIn("&bull; Selected Article linked", page)

    def test_child_form_prepopulates_foreign_key_from_url_search_params(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        # URL aliases checked: article_id, articleId, article
        self.assertIn("searchParams.get(\"article_id\")", page)
        self.assertIn("searchParams.get(\"articleId\")", page)
        self.assertIn("searchParams.get(\"article\")", page)
        self.assertIn('updates["article_id"] = articleParam;', page)

    def test_foreign_key_client_side_validation(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        # Client-side error validation for required foreign key
        self.assertIn('if (!(formData as any).article_id || !String((formData as any).article_id).trim()) {', page)
        self.assertIn('clientErrors.article_id = "Article is required";', page)
        self.assertIn("{fieldErrors.article_id && <span", page)

    def test_parent_form_omits_relation_hooks_and_dropdowns(self) -> None:
        ops = self.ops_by_entity.get("Article", set())
        page = _form_screen_page(self.article_screen, self.article_entity, self.ir, ops)

        self.assertNotIn("useList", page)
        self.assertNotIn("List()", page)
        self.assertNotIn("&bull; Selected", page)
        self.assertIn('placeholder="Enter title..."', page)

    def test_minimal_blog_post_editor_remains_clean(self) -> None:
        blog_ir = example_ir("minimal-blog")
        ops_by_ent = _get_ops_by_entity(blog_ir)
        post_ent = next(e for e in blog_ir.entities if e.name == "Post")
        post_screen = next(s for s in blog_ir.screens if s.id == "post_editor")
        ops = ops_by_ent.get("Post", set())

        page = _form_screen_page(post_screen, post_ent, blog_ir, ops)

        self.assertNotIn("useList", page)
        self.assertNotIn("<select", page)
        self.assertIn('placeholder="Enter title..."', page)
        self.assertIn('placeholder="Enter body..."', page)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ops = self.ops_by_entity.get("Comment", set())
        page_before = _form_screen_page(self.comment_screen, self.comment_entity, self.ir, ops)

        ir_mutated = dataclasses.replace(self.ir, description="A completely mutated description string that should not affect codegen.")
        page_after = _form_screen_page(self.comment_screen, self.comment_entity, ir_mutated, ops)

        self.assertEqual(page_before, page_after)

    def test_full_project_generation_with_relation_form(self) -> None:
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)

        self.assertIn("app/comment_editor/page.tsx", project.paths())
        comment_page = project.get("app/comment_editor/page.tsx").content

        self.assertIn("useListArticles", comment_page)
        self.assertIn("articlesList = useListArticles()", comment_page)
        self.assertIn("<select", comment_page)
        self.assertIn("Selected Article linked", comment_page)
        self.assertIn("Article is required", comment_page)


if __name__ == "__main__":
    unittest.main()
