"""Task R-304: Generated Accessible Confirmation Dialog — Replace window.confirm() with ConfirmDialog Component.

Verifies:
1. components/confirm-dialog.tsx is emitted as a GeneratedFile in NextjsWebAdapter.
2. confirm-dialog.tsx exports ConfirmDialog component and useConfirm hook.
3. confirm-dialog.tsx uses ARIA role=dialog, aria-modal, aria-labelledby, aria-describedby.
4. confirm-dialog.tsx has a confirmAsync function returning a Promise<boolean>.
5. confirm-dialog.tsx handles Escape key to cancel the dialog.
6. Generated collection screens import useConfirm from '../components/confirm-dialog'.
7. Generated collection screens render <ConfirmDialog /> in JSX.
8. Generated collection screens do NOT use window.confirm() for destructive actions.
9. Generated detail screens import useConfirm and render <ConfirmDialog />.
10. Generated detail screens do NOT use window.confirm() for destructive actions.
11. Generated form screens import useConfirm and render <ConfirmDialog />.
12. Generated form screens do NOT use window.confirm() (incl. unsaved-changes guards).
13. Strict diff invariance across ir.description edits.
14. Full project generation via NextjsWebAdapter succeeds for both demo IRs.
"""

from __future__ import annotations

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
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter
from omnistackai_agent_engine.codegen.nextjs import (
    _collection_screen_page,
    _detail_screen_page,
    _form_screen_page,
    _get_ops_by_entity,
)

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _make_crud_ir(description: str = "A CRUD application.") -> ApplicationIR:
    """IR with an entity that supports full CRUD — collection, form, detail screens."""
    entity = Entity(
        "Article",
        (
            Field("id", FieldType.UUID),
            Field("title", FieldType.STRING, required=True),
            Field("body", FieldType.TEXT),
        ),
    )
    apis = [
        ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
        ApiEndpoint(HttpMethod.POST, "/articles", response_schema="Article"),
        ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
        ApiEndpoint(HttpMethod.PATCH, "/articles/{id}", response_schema="Article"),
        ApiEndpoint(HttpMethod.DELETE, "/articles/{id}", response_schema="Article"),
    ]
    screens = [
        Screen("article_list", "user", components=("list",), actions=("view", "delete")),
        Screen("article_form", "user", components=("form",), actions=("create", "update")),
        Screen("article_detail", "user", components=("detail",), actions=("view", "delete")),
    ]
    return ApplicationIR(
        name="Blog App",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=(Role("user"),),
        entities=(entity,),
        apis=tuple(apis),
        screens=tuple(screens),
    )


def _get_file(proj, path: str) -> str | None:
    """Return the content of a generated file, or None if not found."""
    f = next((f for f in proj.files() if f.path == path), None)
    return f.content if f else None


def _get_ops(ir: ApplicationIR, entity_name: str) -> set:
    """Derive Op set for an entity from the IR APIs."""
    return _get_ops_by_entity(ir).get(entity_name, set())


class ConfirmDialogComponentTests(unittest.TestCase):
    """Tests for the generated components/confirm-dialog.tsx static component."""

    def _get_confirm_dialog_content(self) -> str:
        ir = _make_crud_ir()
        adapter = NextjsWebAdapter()
        proj = adapter.generate(ir)
        content = _get_file(proj, "components/confirm-dialog.tsx")
        self.assertIsNotNone(content, "components/confirm-dialog.tsx must be emitted by NextjsWebAdapter")
        return content  # type: ignore[return-value]

    def test_confirm_dialog_file_is_emitted(self) -> None:
        """NextjsWebAdapter emits components/confirm-dialog.tsx."""
        content = self._get_confirm_dialog_content()
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 100)

    def test_confirm_dialog_exports_use_confirm_hook(self) -> None:
        """confirm-dialog.tsx exports useConfirm function."""
        content = self._get_confirm_dialog_content()
        self.assertIn("export function useConfirm", content)

    def test_confirm_dialog_exports_confirm_dialog_component(self) -> None:
        """confirm-dialog.tsx exports ConfirmDialog component."""
        content = self._get_confirm_dialog_content()
        self.assertIn("export function ConfirmDialog", content)

    def test_confirm_dialog_has_aria_role_dialog(self) -> None:
        """ConfirmDialog has proper ARIA role=dialog for accessibility."""
        content = self._get_confirm_dialog_content()
        self.assertIn('role="dialog"', content)

    def test_confirm_dialog_has_aria_modal(self) -> None:
        """ConfirmDialog has aria-modal=true."""
        content = self._get_confirm_dialog_content()
        self.assertIn("aria-modal", content)

    def test_confirm_dialog_has_aria_labelledby(self) -> None:
        """ConfirmDialog has aria-labelledby linking title to the dialog heading."""
        content = self._get_confirm_dialog_content()
        self.assertIn("aria-labelledby", content)

    def test_confirm_dialog_has_aria_describedby(self) -> None:
        """ConfirmDialog has aria-describedby linking message to the dialog body."""
        content = self._get_confirm_dialog_content()
        self.assertIn("aria-describedby", content)

    def test_confirm_dialog_has_confirm_async(self) -> None:
        """useConfirm exposes a confirmAsync function."""
        content = self._get_confirm_dialog_content()
        self.assertIn("confirmAsync", content)

    def test_confirm_dialog_handles_escape_key(self) -> None:
        """ConfirmDialog dismisses/cancels on Escape key press."""
        content = self._get_confirm_dialog_content()
        self.assertIn("Escape", content)

    def test_confirm_dialog_uses_promise(self) -> None:
        """confirmAsync returns a Promise<boolean>."""
        content = self._get_confirm_dialog_content()
        self.assertIn("Promise", content)

    def test_confirm_dialog_has_confirm_and_cancel_buttons(self) -> None:
        """ConfirmDialog renders accessible Confirm and Cancel buttons."""
        content = self._get_confirm_dialog_content()
        self.assertIn("Confirm", content)
        self.assertIn("Cancel", content)

    def test_confirm_dialog_uses_use_client(self) -> None:
        """confirm-dialog.tsx is a client component."""
        content = self._get_confirm_dialog_content()
        self.assertIn('"use client"', content)

    def test_confirm_dialog_has_backdrop_overlay(self) -> None:
        """ConfirmDialog renders a backdrop overlay."""
        content = self._get_confirm_dialog_content()
        # Modal overlay typically covers the viewport with a semi-transparent background
        self.assertIn("position", content)
        self.assertIn("fixed", content)


class CollectionScreenConfirmDialogTests(unittest.TestCase):
    """Tests that generated collection screens use ConfirmDialog instead of window.confirm()."""

    def _get_collection_page(self, description: str = "Test") -> str:
        ir = _make_crud_ir(description=description)
        entity = ir.entities[0]
        screen = next(s for s in ir.screens if "list" in s.id)
        ops = _get_ops(ir, entity.name)
        return _collection_screen_page(screen, entity, ir, ops)

    def test_collection_screen_imports_use_confirm(self) -> None:
        """Generated collection screen imports useConfirm from confirm-dialog."""
        page = self._get_collection_page()
        self.assertIn("useConfirm", page)
        self.assertIn("confirm-dialog", page)

    def test_collection_screen_renders_confirm_dialog(self) -> None:
        """Generated collection screen renders <ConfirmDialog /> component."""
        page = self._get_collection_page()
        self.assertIn("ConfirmDialog", page)

    def test_collection_screen_no_window_confirm(self) -> None:
        """Generated collection screen does NOT use window.confirm() for single delete."""
        page = self._get_collection_page()
        self.assertNotIn("window.confirm", page)
        # The bare confirm() call (without window.) should also be gone
        # Check there's no standalone confirm( call (excluding "confirmAsync", "ConfirmDialog", etc.)
        import re
        # Match literal confirm( that is NOT preceded by letter/digit/_ (i.e. standalone call)
        raw_confirms = re.findall(r'(?<![A-Za-z0-9_])confirm\(', page)
        self.assertEqual(raw_confirms, [], f"Unexpected raw confirm() calls: {raw_confirms}")

    def test_collection_screen_uses_confirm_async(self) -> None:
        """Generated collection screen calls confirmAsync for destructive actions."""
        page = self._get_collection_page()
        self.assertIn("confirmAsync", page)

    def test_collection_screen_diff_invariance(self) -> None:
        """Collection screen is byte-identical across ir.description changes."""
        page1 = self._get_collection_page(description="Version A description.")
        page2 = self._get_collection_page(description="Version B different description.")
        self.assertEqual(page1, page2)


class DetailScreenConfirmDialogTests(unittest.TestCase):
    """Tests that generated detail screens use ConfirmDialog instead of window.confirm()."""

    def _get_detail_page(self, description: str = "Test") -> str:
        ir = _make_crud_ir(description=description)
        entity = ir.entities[0]
        screen = next(s for s in ir.screens if "detail" in s.id)
        ops = _get_ops(ir, entity.name)
        return _detail_screen_page(screen, entity, ir, ops)

    def test_detail_screen_imports_use_confirm(self) -> None:
        """Generated detail screen imports useConfirm from confirm-dialog."""
        page = self._get_detail_page()
        self.assertIn("useConfirm", page)
        self.assertIn("confirm-dialog", page)

    def test_detail_screen_renders_confirm_dialog(self) -> None:
        """Generated detail screen renders <ConfirmDialog /> component."""
        page = self._get_detail_page()
        self.assertIn("ConfirmDialog", page)

    def test_detail_screen_no_window_confirm(self) -> None:
        """Generated detail screen does NOT use window.confirm() for delete."""
        page = self._get_detail_page()
        self.assertNotIn("window.confirm", page)
        import re
        raw_confirms = re.findall(r'(?<![A-Za-z0-9_])confirm\(', page)
        self.assertEqual(raw_confirms, [], f"Unexpected raw confirm() calls: {raw_confirms}")

    def test_detail_screen_uses_confirm_async(self) -> None:
        """Generated detail screen calls confirmAsync for delete action."""
        page = self._get_detail_page()
        self.assertIn("confirmAsync", page)

    def test_detail_screen_diff_invariance(self) -> None:
        """Detail screen is byte-identical across ir.description changes."""
        page1 = self._get_detail_page(description="Version A description.")
        page2 = self._get_detail_page(description="Version B different description.")
        self.assertEqual(page1, page2)


class FormScreenConfirmDialogTests(unittest.TestCase):
    """Tests that generated form screens use ConfirmDialog instead of window.confirm()."""

    def _get_form_page(self, description: str = "Test") -> str:
        ir = _make_crud_ir(description=description)
        entity = ir.entities[0]
        screen = next(s for s in ir.screens if "form" in s.id)
        ops = _get_ops(ir, entity.name)
        return _form_screen_page(screen, entity, ir, ops)

    def test_form_screen_imports_use_confirm(self) -> None:
        """Generated form screen imports useConfirm from confirm-dialog."""
        page = self._get_form_page()
        self.assertIn("useConfirm", page)
        self.assertIn("confirm-dialog", page)

    def test_form_screen_renders_confirm_dialog(self) -> None:
        """Generated form screen renders <ConfirmDialog /> component."""
        page = self._get_form_page()
        self.assertIn("ConfirmDialog", page)

    def test_form_screen_no_window_confirm(self) -> None:
        """Generated form screen does NOT use window.confirm() for unsaved-changes guard or reset."""
        page = self._get_form_page()
        self.assertNotIn("window.confirm", page)
        import re
        raw_confirms = re.findall(r'(?<![A-Za-z0-9_])confirm\(', page)
        self.assertEqual(raw_confirms, [], f"Unexpected raw confirm() calls: {raw_confirms}")

    def test_form_screen_uses_confirm_async(self) -> None:
        """Generated form screen calls confirmAsync for unsaved-changes guard and reset."""
        page = self._get_form_page()
        self.assertIn("confirmAsync", page)

    def test_form_screen_diff_invariance(self) -> None:
        """Form screen is byte-identical across ir.description changes."""
        page1 = self._get_form_page(description="Version A description.")
        page2 = self._get_form_page(description="Version B different description.")
        self.assertEqual(page1, page2)


class FullProjectConfirmDialogTests(unittest.TestCase):
    """Full-project integration tests via NextjsWebAdapter for both demo IRs."""

    def test_full_project_confirm_dialog_in_minimal_blog(self) -> None:
        """minimal-blog full project includes confirm-dialog.tsx and no window.confirm() in screens."""
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        proj = adapter.generate(ir)

        # Confirm dialog component is emitted
        confirm_file = _get_file(proj, "components/confirm-dialog.tsx")
        self.assertIsNotNone(confirm_file)
        assert confirm_file is not None
        self.assertIn("useConfirm", confirm_file)
        self.assertIn("ConfirmDialog", confirm_file)

        # Screen pages do not use window.confirm()
        for f in proj.files():
            if f.path.startswith("app/") and f.path.endswith("/page.tsx") and f.path != "app/page.tsx":
                self.assertNotIn(
                    "window.confirm",
                    f.content,
                    f"window.confirm() found in {f.path} for minimal-blog",
                )

    def test_full_project_confirm_dialog_in_rideshare_favourites(self) -> None:
        """rideshare-favourites full project includes confirm-dialog.tsx and no window.confirm() in screens."""
        ir = example_ir("rideshare-favourites")
        adapter = NextjsWebAdapter()
        proj = adapter.generate(ir)

        confirm_file = _get_file(proj, "components/confirm-dialog.tsx")
        self.assertIsNotNone(confirm_file)
        assert confirm_file is not None
        self.assertIn("useConfirm", confirm_file)

        for f in proj.files():
            if f.path.startswith("app/") and f.path.endswith("/page.tsx") and f.path != "app/page.tsx":
                self.assertNotIn(
                    "window.confirm",
                    f.content,
                    f"window.confirm() found in {f.path} for rideshare-favourites",
                )

    def test_confirm_dialog_is_static_not_ir_description_dependent(self) -> None:
        """components/confirm-dialog.tsx is byte-identical regardless of ir.description."""
        ir1 = _make_crud_ir(description="Alpha version.")
        ir2 = _make_crud_ir(description="Omega completely different description text.")
        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1)
        p2 = adapter.generate(ir2)
        c1 = _get_file(p1, "components/confirm-dialog.tsx")
        c2 = _get_file(p2, "components/confirm-dialog.tsx")
        self.assertEqual(c1, c2)


if __name__ == "__main__":
    unittest.main()
