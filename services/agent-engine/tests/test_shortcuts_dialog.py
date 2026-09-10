"""Tests for generated Keyboard Shortcuts Help Modal (components/shortcuts-dialog.tsx) and Navbar integration (R-305)."""

import unittest

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    render_shortcuts_dialog_component,
)

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.GO,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _make_test_ir(description: str = "A test application.") -> ApplicationIR:
    return ApplicationIR(
        name="TestApp",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=(Role("admin", ("read", "write")), Role("member", ("read",))),
        entities=(
            Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
        ),
        screens=(
            Screen("post_list", "member", components=("list", "table")),
            Screen("post_form", "admin", components=("form",), actions=("save", "create")),
        ),
    )


class ShortcutsDialogComponentTests(unittest.TestCase):
    """Tests for the static ShortcutsDialog component template (components/shortcuts-dialog.tsx)."""

    def setUp(self) -> None:
        self.code = render_shortcuts_dialog_component()

    def test_shortcuts_dialog_is_client_component(self) -> None:
        """Component starts with 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_shortcuts_dialog_exports(self) -> None:
        """Component exports ShortcutsDialog and SHORTCUT_GROUPS."""
        self.assertIn("export function ShortcutsDialog(", self.code)
        self.assertIn("export const SHORTCUT_GROUPS", self.code)
        self.assertIn("export interface ShortcutsDialogProps", self.code)

    def test_shortcuts_dialog_aria_attributes(self) -> None:
        """Component includes WAI-ARIA dialog accessibility attributes."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-modal="true"', self.code)
        self.assertIn('aria-labelledby="shortcuts-dialog-title"', self.code)

    def test_shortcuts_dialog_groups(self) -> None:
        """Component groups shortcuts by context: Global, Collection, Detail, and Form."""
        self.assertIn("Global Navigation", self.code)
        self.assertIn("Collection Screens", self.code)
        self.assertIn("Record Detail Screens", self.code)
        self.assertIn("Form Editor Screens", self.code)

    def test_shortcuts_dialog_key_badges(self) -> None:
        """Component renders styled <kbd> elements with monospace font and key combinations."""
        self.assertIn("<kbd", self.code)
        self.assertIn("fontFamily", self.code)
        self.assertIn("monospace", self.code)
        self.assertIn("Esc", self.code)
        self.assertIn("Ctrl+Enter", self.code)

    def test_shortcuts_dialog_close_affordances(self) -> None:
        """Component includes an accessible close button and Escape handler."""
        self.assertIn('aria-label="Close shortcuts dialog"', self.code)
        self.assertIn('"Escape"', self.code)
        self.assertIn("onClose()", self.code)

    def test_shortcuts_dialog_diff_invariance(self) -> None:
        """Static component is 100% diff-invariant across IR changes."""
        code1 = render_shortcuts_dialog_component()
        code2 = render_shortcuts_dialog_component()
        self.assertEqual(code1, code2)


class NavbarShortcutsIntegrationTests(unittest.TestCase):
    """Tests for Navbar integration of ShortcutsDialog and '?' hotkey listener."""

    def setUp(self) -> None:
        self.adapter = NextjsWebAdapter()
        self.ir = _make_test_ir()
        self.project = self.adapter.generate(self.ir)
        self.navbar = self.project.get("components/navbar.tsx").content

    def test_navbar_imports_shortcuts_dialog(self) -> None:
        """Navbar imports ShortcutsDialog from ./shortcuts-dialog."""
        self.assertIn('import { ShortcutsDialog } from "./shortcuts-dialog";', self.navbar)

    def test_navbar_renders_shortcuts_button(self) -> None:
        """Navbar renders an accessible trigger button with 'Shortcuts' and '?' badge."""
        self.assertIn('aria-label="View keyboard shortcuts"', self.navbar)
        self.assertIn('title="Keyboard shortcuts (?)"', self.navbar)
        self.assertIn("Shortcuts", self.navbar)
        self.assertIn("?", self.navbar)

    def test_navbar_renders_shortcuts_dialog_component(self) -> None:
        """Navbar mounts <ShortcutsDialog /> with state."""
        self.assertIn("<ShortcutsDialog", self.navbar)
        self.assertIn("isOpen={shortcutsOpen}", self.navbar)

    def test_navbar_wires_question_mark_keydown(self) -> None:
        """Navbar registers global keydown listener for '?' key to toggle modal."""
        self.assertIn('addEventListener("keydown"', self.navbar)
        self.assertIn('removeEventListener("keydown"', self.navbar)
        self.assertIn('e.key === "?"', self.navbar)
        self.assertIn("setShortcutsOpen", self.navbar)

    def test_navbar_diff_invariance_across_ir_description(self) -> None:
        """Navbar preserves byte-identical diff invariance across ir.description."""
        proj_a = self.adapter.generate(_make_test_ir(description="Description A"))
        proj_b = self.adapter.generate(_make_test_ir(description="Description B"))
        self.assertEqual(
            proj_a.get("components/navbar.tsx").content,
            proj_b.get("components/navbar.tsx").content,
        )


class FullProjectShortcutsDialogTests(unittest.TestCase):
    """Integration tests verifying components/shortcuts-dialog.tsx in full projects."""

    def test_full_project_includes_shortcuts_dialog_in_minimal_blog(self) -> None:
        """minimal-blog generated project includes components/shortcuts-dialog.tsx."""
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/shortcuts-dialog.tsx", set(project.paths()))
        content = project.get("components/shortcuts-dialog.tsx").content
        self.assertIn("ShortcutsDialog", content)

    def test_full_project_includes_shortcuts_dialog_in_rideshare(self) -> None:
        """rideshare-favourites generated project includes components/shortcuts-dialog.tsx."""
        ir = example_ir("rideshare-favourites")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/shortcuts-dialog.tsx", set(project.paths()))
        content = project.get("components/shortcuts-dialog.tsx").content
        self.assertIn("ShortcutsDialog", content)


if __name__ == "__main__":
    unittest.main()
