"""Task R-274: Form Screen Post-Submit Contextual CTAs, Record Navigation & Cancel Actions.

Tests:
1. Form screen declares lastSavedId state hook.
2. Form screen captures created record id from create(formData) response.
3. Form screen captures updated record id from editId in update branch.
4. Form screen success banner preserves existing message text format.
5. Form screen renders 'View {name} ->' link when detail screen exists.
6. Form screen omits 'View {name} ->' link when no detail screen exists.
7. Form screen renders '<- Back to {plural}' link when list screen exists.
8. Form screen renders '+ Create another {name}' action button in create mode.
9. Form screen renders dismiss button in success banner.
10. Form screen renders Cancel link button in form footer.
11. Form screen Cancel button links to collection screen when list screen exists.
12. Form screen Cancel button links to root ('/') when no list screen exists.
13. Form screen Reset button clears lastSavedId along with errors and form data.
14. Form screen preserves byte-for-byte diff invariance across ir.description modifications.
15. Full Next.js project generation succeeds with contextual CTAs and navigation links.
16. Form screens without update operation still capture id and render contextual CTAs.
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


def _cta_capable_ir() -> ApplicationIR:
    """IR with Article (list, editor, detail), Product (list, editor, no detail), and Tag (editor only)."""
    return ApplicationIR(
        name="Publishing and Store Platform",
        description="Platform with articles, products, and tags.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("author"), Role("reader"), Role("admin")),
        entities=(
            Entity(
                "Article",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, required=True),
                    Field("content", FieldType.TEXT),
                    Field("published", FieldType.BOOL),
                ),
            ),
            Entity(
                "Product",
                (
                    Field("id", FieldType.UUID),
                    Field("name", FieldType.STRING, required=True),
                    Field("price", FieldType.FLOAT, required=True),
                ),
            ),
            Entity(
                "Tag",
                (
                    Field("id", FieldType.UUID),
                    Field("label", FieldType.STRING, required=True),
                ),
            ),
        ),
        apis=(
            # Article APIs (CRUD)
            ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
            ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"),
            ApiEndpoint(HttpMethod.DELETE, "/articles/{id}"),
            # Product APIs (Create, List, Update)
            ApiEndpoint(HttpMethod.POST, "/products", request_schema="Product", response_schema="Product"),
            ApiEndpoint(HttpMethod.GET, "/products", response_schema="Product"),
            ApiEndpoint(HttpMethod.PUT, "/products/{id}", request_schema="Product", response_schema="Product"),
            # Tag APIs (Create only)
            ApiEndpoint(HttpMethod.POST, "/tags", request_schema="Tag", response_schema="Tag"),
        ),
        screens=(
            # Article has list, form (editor), and detail
            Screen("article_list", "reader", components=("list",), actions=("view",)),
            Screen("article_editor", "author", components=("form",), actions=("create", "update")),
            Screen("article_detail", "reader", components=("detail",), actions=("view",)),
            # Product has list and form (editor), but no detail
            Screen("product_list", "reader", components=("list",), actions=("view",)),
            Screen("product_editor", "admin", components=("form",), actions=("create", "update")),
            # Tag has only form (editor), no list and no detail
            Screen("tag_editor", "admin", components=("form",), actions=("create",)),
        ),
    )


class FormNavigationCTATests(TestCase):
    """Automated tests for post-submit contextual CTAs, record navigation, and Cancel actions."""

    def test_form_declares_lastsavedid_state(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("const [lastSavedId, setLastSavedId] = useState<string | null>(null);", page)

    def test_form_captures_created_record_id(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("const res = await create(formData);", page)
        self.assertIn("if (res && (res as any).id) {", page)
        self.assertIn("setLastSavedId(String((res as any).id));", page)

    def test_form_captures_updated_record_id(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("await update(editId, formData);", page)
        self.assertIn("setLastSavedId(editId);", page)

    def test_success_banner_preserves_existing_message(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('{isEdit ? "Article updated successfully!" : "Article saved successfully!"}', page)

    def test_view_record_link_rendered_when_detail_screen_exists(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("href={`/article_detail?id=${lastSavedId || (isEdit ? editId : null)}`}", page)
        self.assertIn("View Article &rarr;", page)

    def test_view_record_link_omitted_when_no_detail_screen(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "product_editor")
        page = render_screen_page(screen, ir)

        self.assertNotIn("View Product", page)
        self.assertNotIn("/product_detail", page)

    def test_back_to_collection_link_in_success_banner(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('href="/article_list"', page)
        self.assertIn("&larr; Back to Articles", page)

    def test_create_another_button_in_create_mode(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("+ Create another Article", page)
        self.assertIn("setSuccess(false); setLastSavedId(null);", page)

    def test_dismiss_button_in_success_banner(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('aria-label="Dismiss"', page)
        self.assertIn("onClick={() => setSuccess(false)}", page)
        self.assertIn("&times;", page)

    def test_cancel_button_rendered_in_footer(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("Cancel", page)
        self.assertIn("Reset", page)

    def test_cancel_button_links_to_list_screen(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('href="/article_list"', page)

    def test_cancel_button_links_to_root_when_no_list_screen(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "tag_editor")
        page = render_screen_page(screen, ir)

        self.assertIn('href="/"', page)
        self.assertIn("Cancel", page)

    def test_form_reset_clears_lastsavedid(self) -> None:
        ir = _cta_capable_ir()
        screen = next(s for s in ir.screens if s.id == "article_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("setLastSavedId(null);", page)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir_a = _cta_capable_ir()
        ir_b = ApplicationIR(
            name=ir_a.name,
            description="Completely modified description testing diff invariance in form CTAs.",
            platforms=ir_a.platforms,
            project_strategy=ir_a.project_strategy,
            roles=ir_a.roles,
            entities=ir_a.entities,
            apis=ir_a.apis,
            screens=ir_a.screens,
        )

        for sid in ("article_editor", "product_editor", "tag_editor"):
            screen_a = next(s for s in ir_a.screens if s.id == sid)
            screen_b = next(s for s in ir_b.screens if s.id == sid)
            code_a = render_screen_page(screen_a, ir_a)
            code_b = render_screen_page(screen_b, ir_b)
            self.assertEqual(code_a, code_b, f"Screen {sid} output differed across description changes!")

    def test_full_project_generation_succeeds(self) -> None:
        ir = _cta_capable_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)

        self.assertIn("app/article_editor/page.tsx", project.paths())
        self.assertIn("app/product_editor/page.tsx", project.paths())
        self.assertIn("app/tag_editor/page.tsx", project.paths())

        article_page = project.get("app/article_editor/page.tsx").content
        self.assertIn("lastSavedId", article_page)
        self.assertIn("View Article &rarr;", article_page)
        self.assertIn("&larr; Back to Articles", article_page)
        self.assertIn("+ Create another Article", article_page)
        self.assertIn("Cancel", article_page)

    def test_form_screens_without_update_op(self) -> None:
        ir = example_ir("minimal-blog")
        screen = next(s for s in ir.screens if s.id == "post_editor")
        page = render_screen_page(screen, ir)

        self.assertIn("const [lastSavedId, setLastSavedId] = useState<string | null>(null);", page)
        self.assertIn("const res = await create(formData);", page)
        self.assertIn("setLastSavedId(String((res as any).id));", page)
        self.assertIn("+ Create another Post", page)
        self.assertIn("&larr; Back to Posts", page)
        self.assertIn('href="/post_list"', page)
        self.assertIn("Cancel", page)
