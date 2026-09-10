"""Task R-277: Form Screen Dirty State Tracking, Unsaved Changes Guard & Reset Confirmation in Generated Next.js Forms.

Covers:
1. Form screen imports useMemo from "react".
2. Form screen declares initialValues for default form fields.
3. Form screen computes baselineData from initialValues (in create mode) or initialData (in edit mode).
4. Form screen computes isDirty by comparing formData with baselineData.
5. Form screen registers beforeunload event listener guarding against page leave when dirty.
6. Form screen cleans up beforeunload event listener on unmount.
7. Form screen renders amber "Unsaved changes" visual badge in header when isDirty && !success.
8. Form screen renders "You have unsaved changes" notice in form footer when isDirty && !success.
9. Cancel button guards navigation with confirmation dialog when isDirty.
10. Reset button guards reset action with confirmation dialog when isDirty.
11. Edit mode computes baselineData using initialData.
12. Create mode computes baselineData using initialValues.
13. Strict diff invariance across ir.description modifications.
14. minimal-blog post_editor screen contains unsaved changes guard.
15. rideshare-favourites form screen contains unsaved changes guard.
16. Reset button resets formData to baseline and clears fieldErrors and success.
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
    with_update: bool = True,
    with_delete: bool = True,
    with_detail_screen: bool = True,
    with_list_screen: bool = True,
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
                Field("body", FieldType.TEXT, required=True),
            ),
        ),
    )

    apis = [
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
    ]
    if with_update:
        apis.append(ApiEndpoint(HttpMethod.PUT, "/posts/{id}", request_schema="Post", response_schema="Post"))
    if with_delete:
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"))

    screens_list = []
    if with_list_screen:
        screens_list.append(
            Screen("post_list", "admin", components=("list",), actions=("view",), navigation=("post_form",))
        )
    screens_list.append(
        Screen("post_form", "admin", components=("form",), actions=("create", "update") if with_update else ("create",), navigation=("post_list",))
    )
    if with_detail_screen:
        screens_list.append(
            Screen("post_detail", "admin", components=("detail",), actions=("view",), navigation=("post_list",))
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


class FormUnsavedChangesGuardTests(unittest.TestCase):
    """Test suite verifying dirty state tracking and unsaved changes guards in Next.js form screens."""

    def test_form_screen_imports_usememo(self) -> None:
        """Verify form screen imports useMemo alongside useEffect and useState."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn('import { useEffect, useMemo, useState } from "react";', content)

    def test_form_screen_declares_initial_values(self) -> None:
        """Verify form screen extracts and types initialValues dictionary."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("const initialValues: Partial<Post> =", content)
        self.assertIn("const [formData, setFormData] = useState<Partial<Post>>(initialValues);", content)

    def test_form_screen_declares_baseline_data(self) -> None:
        """Verify form screen sets up baselineData for change comparison."""
        ir = _make_test_ir(with_update=True)
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("const baselineData = useMemo(() => {", content)
        self.assertIn("(isEdit && initialData) ? initialData : initialValues", content)

    def test_form_screen_declares_isdirty_computation(self) -> None:
        """Verify form screen computes isDirty using useMemo comparing formData with baselineData."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("const isDirty = useMemo(() => {", content)
        self.assertIn("Object.keys(formData).some((key) => {", content)
        self.assertIn("return cur !== base;", content)

    def test_form_screen_registers_beforeunload_listener(self) -> None:
        """Verify form screen attaches window beforeunload event listener."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn('window.addEventListener("beforeunload", handleBeforeUnload);', content)
        self.assertIn("if (isDirty && !submitting && !success) {", content)

    def test_form_screen_cleans_up_beforeunload_listener(self) -> None:
        """Verify form screen removes beforeunload event listener in cleanup."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn('return () => window.removeEventListener("beforeunload", handleBeforeUnload);', content)

    def test_form_screen_renders_header_unsaved_changes_badge(self) -> None:
        """Verify form header renders amber 'Unsaved changes' badge when dirty."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("{isDirty && !success && (", content)
        self.assertIn("Unsaved changes", content)

    def test_form_screen_renders_footer_unsaved_changes_notice(self) -> None:
        """Verify form footer renders 'You have unsaved changes' notice when dirty."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("&bull; You have unsaved changes", content)

    def test_form_screen_cancel_button_guards_with_confirmation(self) -> None:
        """Verify Cancel link uses async confirmAsync dialog before navigating away when isDirty."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        # R-304: Cancel now uses accessible async confirmAsync() instead of window.confirm().
        self.assertIn('confirmAsync("Discard Changes"', content)
        self.assertIn("e.preventDefault();", content)
        self.assertNotIn('confirm("You have unsaved changes. Discard them and leave?")', content)

    def test_form_screen_reset_button_guards_with_confirmation(self) -> None:
        """Verify Reset button uses async confirmAsync dialog when form is dirty."""
        ir = _make_test_ir()
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        # R-304: Reset now uses accessible async confirmAsync() instead of window.confirm().
        self.assertIn('confirmAsync("Reset Form"', content)
        self.assertNotIn('confirm("Discard all changes and reset form?")', content)

    def test_form_screen_edit_mode_baseline_uses_initial_data(self) -> None:
        """Verify edit mode baseline uses initialData."""
        ir = _make_test_ir(with_update=True)
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("(isEdit && initialData) ? initialData : initialValues", content)

    def test_form_screen_create_mode_baseline_uses_initial_values(self) -> None:
        """Verify create-only mode sets baselineData to initialValues."""
        ir = _make_test_ir(with_update=False)
        form_screen = next(s for s in ir.screens if s.id == "post_form")
        content = render_screen_page(form_screen, ir)
        self.assertIn("const baselineData = initialValues;", content)

    def test_form_screen_diff_invariance(self) -> None:
        """Verify form screen is byte-identical across ir.description modifications."""
        ir1 = _make_test_ir(description="Description A")
        ir2 = _make_test_ir(description="Description B")
        screen1 = next(s for s in ir1.screens if s.id == "post_form")
        screen2 = next(s for s in ir2.screens if s.id == "post_form")
        c1 = render_screen_page(screen1, ir1)
        c2 = render_screen_page(screen2, ir2)
        self.assertEqual(c1, c2)

    def test_minimal_blog_post_editor_has_unsaved_guard(self) -> None:
        """Verify minimal-blog post_editor screen contains unsaved changes guard."""
        ir = example_ir("minimal-blog")
        editor_screen = next(s for s in ir.screens if s.id == "post_editor")
        content = render_screen_page(editor_screen, ir)
        self.assertIn("isDirty", content)
        self.assertIn("Unsaved changes", content)
        self.assertIn("beforeunload", content)
        # R-304: guard now uses confirmAsync() modal instead of window.confirm().
        self.assertIn("confirmAsync(", content)

    def test_rideshare_favourites_form_screens_have_unsaved_guard(self) -> None:
        """Verify rideshare-favourites form screens contain unsaved changes guard."""
        ir = example_ir("rideshare-favourites")
        for s in ir.screens:
            if s.components and "form" in s.components:
                content = render_screen_page(s, ir)
                self.assertIn("isDirty", content)
                self.assertIn("Unsaved changes", content)
                self.assertIn("beforeunload", content)

    def test_minimal_blog_full_adapter_generate(self) -> None:
        """Verify full project generation via NextjsWebAdapter generates valid post_editor with guard."""
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        editor_page = project.get("app/post_editor/page.tsx").content
        self.assertIn("isDirty", editor_page)
        self.assertIn("Unsaved changes", editor_page)
        self.assertIn("Cancel", editor_page)
        self.assertIn("Reset", editor_page)


if __name__ == "__main__":
    unittest.main()
