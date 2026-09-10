"""Task R-266: Update/Edit Mode in Generated Next.js Forms & Collection Screen Edit Actions.

Tests:
1. Form screen imports useUpdate and useGet hooks when Op.UPDATE and Op.GET are available.
2. Form screen imports useSearchParams from next/navigation in update-capable forms.
3. Form screen reads editId and computes isEdit boolean.
4. Form screen declares useEffect to populate form data when initialData arrives.
5. Form screen calls update(editId, formData) in edit mode vs create(formData) in create mode.
6. Form screen renders dynamic page title, submit button label, and success banner.
7. Form screen renders loading state while fetching initial data in edit mode.
8. Form screen omits update hooks, useSearchParams, and edit branching when Op.UPDATE is absent.
9. Collection screen renders "Edit" action link in table when Op.UPDATE and form screen exist.
10. Collection screen Edit link includes onClick stopPropagation to prevent row selection toggle.
11. Collection screen omits "Edit" link when Op.UPDATE is not wired.
12. Subcollection master-detail view renders "+ New <Child>" link when child form screen exists.
13. Screen generation preserves byte-for-byte diff invariance across ir.description modifications.
14. NextjsWebAdapter emits complete, valid project with update-enabled screens.
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


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _update_capable_ir() -> ApplicationIR:
    """IR where Article supports full CRUD (CREATE, LIST, GET, UPDATE, DELETE) and Comment is a subcollection."""
    return ApplicationIR(
        name="Article Publishing Platform",
        description="Publishing platform with articles and comments.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("author"), Role("reader")),
        entities=(
            Entity(
                "Article",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("content", FieldType.TEXT),
                    Field("category", FieldType.STRING, validation=("enum:tech|lifestyle|news",)),
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
            # Article endpoints
            ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.DELETE, "/articles/{id}"),
            # Comment endpoints
            ApiEndpoint(HttpMethod.POST, "/articles/{article_id}/comments", request_schema="Comment", response_schema="Comment"),
            ApiEndpoint(HttpMethod.GET, "/articles/{article_id}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.GET, "/comments/{id}", response_schema="Comment"),
            ApiEndpoint(HttpMethod.PUT, "/comments/{id}", request_schema="Comment", response_schema="Comment"),
        ),
        screens=(
            Screen("article_list", "reader", components=("list",), actions=("view",)),
            Screen("article_editor", "author", components=("form",), actions=("create", "update")),
            Screen("comment_list", "reader", components=("list",), actions=("view",)),
            Screen("comment_editor", "reader", components=("form",), actions=("create", "update")),
        ),
    )


class FormUpdateScreenTests(TestCase):
    """Automated tests for dual create/update form screens and collection edit actions."""

    def test_form_screen_imports_update_and_get_hooks(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('import { useArticle, useUpdateArticle } from "../lib/hooks";', page)
        self.assertIn('import { useCreateArticle } from "../lib/hooks";', page)

    def test_form_screen_imports_search_params(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('import { useSearchParams } from "next/navigation";', page)

    def test_form_screen_reads_edit_id_and_computes_is_edit(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('const searchParams = useSearchParams();', page)
        self.assertIn('const editId = searchParams.get("id");', page)
        self.assertIn('const isEdit = Boolean(editId);', page)

    def test_form_screen_wires_hooks_and_effect_for_edit_mode(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('const { update, loading: updating, error: updateError } = useUpdateArticle();', page)
        self.assertIn('const { data: initialData, loading: fetchingInitial } = useArticle(editId);', page)
        self.assertIn('useEffect(() => {', page)
        self.assertIn('if (initialData) {', page)
        self.assertIn('setFormData(initialData);', page)

    def test_form_screen_submits_update_in_edit_mode(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('if (isEdit && editId) {', page)
        self.assertIn('await update(editId, formData);', page)
        self.assertIn('} else {', page)
        self.assertIn('await create(formData);', page)

    def test_form_screen_renders_dynamic_labels_and_banners(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        # Dynamic header title
        self.assertIn('{isEdit ? "Edit Article" : "Article Editor"}', page)

        # Dynamic submit button
        self.assertIn('{((submitting || updating) ? "Saving..." : (isEdit ? "Update Article" : "Save Article"))}', page)

        # Dynamic success banner
        self.assertIn('{isEdit ? "Article updated successfully!" : "Article saved successfully!"}', page)

        # Initial loading indicator banner — R-293 renders skeleton blocks instead of text.
        self.assertIn('{isEdit && fetchingInitial && (', page)
        self.assertIn('<div key={i} style={{ height: 34, background: "#e2e8f0", borderRadius: 6, opacity: 1 - i * 0.2 }} />', page)

    def test_form_screen_omits_update_when_no_update_op(self) -> None:
        ir = example_ir("minimal-blog")
        screen = next(s for s in ir.screens if s.id == "post_editor")
        page = render_screen_page(screen, ir)

        self.assertNotIn("useUpdatePost", page)
        self.assertNotIn("usePost", page)
        self.assertNotIn("useSearchParams", page)
        self.assertNotIn("isEdit", page)
        self.assertNotIn("editId", page)
        self.assertIn("Save Post", page)
        self.assertIn("await create(formData);", page)

    def test_collection_screen_renders_edit_action_when_update_available(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        self.assertIn('<th style={{ padding: "12px 16px", textAlign: "right", fontWeight: 600, color: "#475569" }}>Actions</th>', page)
        self.assertIn('href={`/article_editor?id=${(item as any).id}`}', page)
        self.assertIn('Edit', page)
        # Verify stopPropagation prevents row selection toggle on edit click
        self.assertIn('onClick={(e) => e.stopPropagation()}', page)

    def test_collection_screen_omits_edit_when_no_update_op(self) -> None:
        ir = example_ir("minimal-blog")
        screen = next(s for s in ir.screens if s.id == "post_list")
        page = render_screen_page(screen, ir)

        self.assertNotIn("/post_editor?id=", page)
        self.assertNotIn(">Edit<", page)

    def test_subcollection_view_renders_new_child_link(self) -> None:
        ir = _update_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_list")
        page = render_screen_page(screen, ir)

        # Subcollection view has + New Comment link
        self.assertIn('href={`/comment_editor?article_id=${selectedId}`}', page)
        self.assertIn('+ New Comment', page)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir_a = _update_capable_ir()
        ir_b = ApplicationIR(
            name=ir_a.name,
            description="Completely altered description string for diff invariance verification.",
            platforms=ir_a.platforms,
            project_strategy=ir_a.project_strategy,
            roles=ir_a.roles,
            entities=ir_a.entities,
            apis=ir_a.apis,
            screens=ir_a.screens,
        )

        for sid in ("article_list", "article_editor", "comment_list", "comment_editor"):
            screen_a = next(s for s in ir_a.screens if s.id == sid)
            screen_b = next(s for s in ir_b.screens if s.id == sid)
            code_a = render_screen_page(screen_a, ir_a)
            code_b = render_screen_page(screen_b, ir_b)
            self.assertEqual(code_a, code_b, f"Screen {sid} output differed across description changes!")

    def test_nextjs_web_adapter_generates_complete_project(self) -> None:
        ir = _update_capable_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)

        self.assertIn("app/article_editor/page.tsx", project.paths())
        self.assertIn("app/article_list/page.tsx", project.paths())
        self.assertIn("app/comment_editor/page.tsx", project.paths())
        self.assertIn("app/comment_list/page.tsx", project.paths())

        art_form = project.get("app/article_editor/page.tsx").content
        self.assertIn("useUpdateArticle", art_form)
        self.assertIn("useSearchParams", art_form)

        art_list = project.get("app/article_list/page.tsx").content
        self.assertIn("article_editor?id=", art_list)
        self.assertIn("comment_editor?article_id=", art_list)
